import re
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings
from youtube_transcript_api import YouTubeTranscriptApi
from pydantic import AnyHttpUrl
from dotenv import load_dotenv

from utils.auth import create_auth0_verifier

# Configure logging
log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler (INFO level for cleaner output)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# File handler with rotation (10MB max, keep 5 backup files)
file_handler = RotatingFileHandler(
    'yt-mcp-server.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

# Configure root logger
logging.basicConfig(
    level=getattr(logging, log_level, logging.DEBUG),
    handlers=[console_handler, file_handler]
)

logger = logging.getLogger('yt_mcp.main')

# Load environment variables from .env file
load_dotenv()

def log_auth0_diagnostics():
    """Log diagnostic information to help debug Auth0 configuration."""
    logger.info("=" * 80)
    logger.info("Auth0 Configuration Diagnostics")
    logger.info("=" * 80)

    domain = os.getenv("AUTH0_DOMAIN")
    audience = os.getenv("AUTH0_AUDIENCE")

    if domain:
        logger.info(f"✓ AUTH0_DOMAIN is set: {domain}")

        # Check for regional domain format
        if '.us.auth0.com' in domain:
            logger.info(f"  ℹ Regional domain detected: US region")
        elif '.eu.auth0.com' in domain:
            logger.info(f"  ℹ Regional domain detected: EU region")
        elif '.au.auth0.com' in domain:
            logger.info(f"  ℹ Regional domain detected: AU region")
        elif '.auth0.com' in domain and not any(x in domain for x in ['.us.', '.eu.', '.au.']):
            logger.warning(f"  ⚠ Legacy domain format detected. If tenant was created after June 2020, add regional suffix (e.g., .us.auth0.com)")

        jwks_url = f"https://{domain}/.well-known/jwks.json"
        logger.info(f"  JWKS URL will be: {jwks_url}")

        # Test JWKS URL accessibility
        try:
            import requests
            response = requests.get(jwks_url, timeout=5)
            if response.status_code == 200:
                logger.info(f"  ✓ JWKS endpoint is accessible")
                keys = response.json().get('keys', [])
                logger.info(f"  ✓ Found {len(keys)} signing key(s)")
                logger.debug(f"  JWKS response preview: {str(response.json())[:100]}...")
            else:
                logger.error(f"  ✗ JWKS endpoint returned status {response.status_code}")
                logger.error(f"  Suggestion: Check AUTH0_DOMAIN in .env file. Use exact domain from Auth0 Dashboard.")
        except ImportError:
            logger.debug(f"  'requests' library not available, skipping JWKS connectivity test")
        except Exception as e:
            logger.error(f"  ✗ Could not test JWKS endpoint: {e}")
            logger.error(f"  Suggestion: Verify AUTH0_DOMAIN is correct and network connectivity is available")
    else:
        logger.error(f"✗ AUTH0_DOMAIN is NOT set")

    if audience:
        logger.info(f"✓ AUTH0_AUDIENCE is set: {audience}")
    else:
        logger.error(f"✗ AUTH0_AUDIENCE is NOT set")

    logger.info("=" * 80)

# Log server startup
logger.info("=" * 80)
logger.info("YouTube MCP Remote Server Starting")
logger.info("=" * 80)

# Log environment configuration (sanitized)
auth0_domain = os.getenv("AUTH0_DOMAIN")
resource_server_url = os.getenv("RESOURCE_SERVER_URL")
auth0_algorithms = os.getenv("AUTH0_ALGORITHMS", "RS256")
port = int(os.getenv("PORT", "8000"))

logger.info(f"Configuration loaded:")
logger.info(f"  AUTH0_DOMAIN: {auth0_domain}")
logger.info(f"  AUTH0_AUDIENCE: {'***SET***' if os.getenv('AUTH0_AUDIENCE') else '***NOT SET***'}")
logger.info(f"  RESOURCE_SERVER_URL: {resource_server_url}")
logger.info(f"  AUTH0_ALGORITHMS: {auth0_algorithms}")
logger.info(f"  PORT: {port}")

# Validate required environment variables
if not auth0_domain:
    logger.error("FATAL: AUTH0_DOMAIN environment variable is required but not set")
    raise ValueError("AUTH0_DOMAIN environment variable is required")
if not resource_server_url:
    logger.error("FATAL: RESOURCE_SERVER_URL environment variable is required but not set")
    raise ValueError("RESOURCE_SERVER_URL environment variable is required")

logger.info("Environment validation passed")

# Run Auth0 diagnostics
log_auth0_diagnostics()

# Load server instructions
with open("prompts/server_instructions.md", "r") as file:
    server_instructions = file.read()

# Initialize Auth0 token verifier
token_verifier = create_auth0_verifier()
logger.info(f"Auth0 token verifier initialized successfully")
logger.info(f"JWKS URL: https://{auth0_domain}/.well-known/jwks.json")

# Create an MCP server with OAuth authentication
mcp = FastMCP(
    "yt-mcp",
    instructions=server_instructions,
    host="0.0.0.0",
    port=port,
    # OAuth Configuration
    token_verifier=token_verifier,
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(f"https://{auth0_domain}/"),
        resource_server_url=AnyHttpUrl(resource_server_url),
        required_scopes=["openid", "profile", "email", "address", "phone"],
    ),
)

@mcp.tool()
def fetch_video_transcript(url: str) -> str:
    """
    Extract transcript with timestamps from a YouTube video URL and format it for LLM consumption

    Args:
        url (str): YouTube video URL

    Returns:
        str: Formatted transcript with timestamps, where each entry is on a new line
             in the format: "[MM:SS] Text"
    """
    # Extract video ID from URL
    video_id_pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    video_id_match = re.search(video_id_pattern, url)

    if not video_id_match:
        raise ValueError("Invalid YouTube URL")

    video_id = video_id_match.group(1)

    def format_transcript(transcript):
        """Format transcript entries with timestamps"""
        formatted_entries = []
        for entry in transcript:
            # Convert seconds to MM:SS format
            minutes = int(entry.start // 60)
            seconds = int(entry.start % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"

            formatted_entry = f"{timestamp} {entry.text}"
            formatted_entries.append(formatted_entry)

        # Join all entries with newlines
        return "\n".join(formatted_entries)

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return format_transcript(transcript)
    except Exception as e:
        raise Exception(f"Error fetching transcript: {str(e)}")

@mcp.tool()
def fetch_instructions(prompt_name: str) -> str:
    """
    Fetch instructions for a given prompt name from the prompts/ directory

    Args:
        prompt_name (str): Name of the prompt to fetch instructions for
        Available prompts: 
            - write_blog_post
            - write_social_post
            - write_video_chapters

    Returns:
        str: Instructions for the given prompt
    """
    script_dir = os.path.dirname(__file__)
    prompt_path = os.path.join(script_dir, "prompts", f"{prompt_name}.md")
    with open(prompt_path, "r") as f:
        return f.read()

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info(f"Starting FastMCP server on {mcp.settings.host}:{mcp.settings.port}")
    logger.info(f"MCP endpoint: http://{mcp.settings.host}:{mcp.settings.port}{mcp.settings.streamable_http_path}")
    logger.info(f"Transport: streamable-http")
    logger.info(f"Authentication: OAuth 2.0 (Auth0)")
    logger.info(f"Required scopes: {mcp.settings.auth.required_scopes if mcp.settings.auth else 'None'}")
    logger.info("=" * 80)
    mcp.run(transport='streamable-http')