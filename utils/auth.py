"""
Auth0 OAuth token verification for YouTube MCP Server.
"""

import os
import asyncio
import logging
from typing import Optional
from jwt import PyJWKClient, decode, InvalidTokenError
from mcp.server.auth.provider import AccessToken, TokenVerifier

logger = logging.getLogger('yt_mcp.auth')


class Auth0TokenVerifier(TokenVerifier):
    """Verifies OAuth tokens issued by Auth0."""

    def __init__(self, domain: str, audience: str, algorithms: Optional[list[str]] = None):
        self.domain = domain
        self.audience = audience
        self.algorithms = algorithms or ["RS256"]
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self.issuer = f"https://{domain}/"
        # PyJWKClient handles JWKS fetching and caching
        self.jwks_client = PyJWKClient(self.jwks_url)

        logger.info(f"Auth0TokenVerifier initialized")
        logger.debug(f"  Domain: {self.domain}")
        logger.debug(f"  Audience: {self.audience}")
        logger.debug(f"  Algorithms: {self.algorithms}")
        logger.debug(f"  JWKS URL: {self.jwks_url}")
        logger.debug(f"  Issuer: {self.issuer}")

    def _get_token_header_info(self, token: str) -> dict:
        """Extract header information from JWT token without verification (for logging only)."""
        try:
            import base64
            import json
            header = token.split('.')[0]
            # Add padding if needed
            header += '=' * (4 - len(header) % 4)
            decoded_header = base64.urlsafe_b64decode(header)
            return json.loads(decoded_header)
        except Exception as e:
            logger.debug(f"Could not extract token header: {e}")
            return {}

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify Auth0 JWT token and return access information."""
        # Sanitize token for logging (show first 10 and last 6 chars only)
        token_preview = f"{token[:10]}...{token[-6:]}" if len(token) > 16 else "***SHORT***"

        logger.info(f"Token verification started for token: {token_preview}")

        try:
            # Step 1: Extract signing key from JWKS
            logger.debug("Step 1: Fetching signing key from JWKS")
            try:
                signing_key = await asyncio.to_thread(
                    self.jwks_client.get_signing_key_from_jwt, token
                )
                key_id = signing_key.key_id if hasattr(signing_key, 'key_id') else 'unknown'
                logger.debug(f"Signing key fetched successfully (kid: {key_id})")
            except Exception as jwks_error:
                logger.error(f"JWKS fetch failed: {type(jwks_error).__name__}: {jwks_error}")
                logger.error(f"JWKS URL: {self.jwks_url}")
                header_info = self._get_token_header_info(token)
                if header_info:
                    logger.error(f"Token header info: {header_info}")
                return None

            # Step 2: Decode and verify JWT
            logger.debug("Step 2: Decoding and verifying JWT")
            logger.debug(f"  Expected audience: {self.audience}")
            logger.debug(f"  Expected issuer: {self.issuer}")
            logger.debug(f"  Algorithms: {self.algorithms}")

            try:
                payload = decode(
                    token,
                    signing_key.key,
                    algorithms=self.algorithms,
                    audience=self.audience,
                    issuer=self.issuer,
                    options={
                        "verify_signature": True,
                        "verify_aud": True,
                        "verify_iat": True,
                        "verify_exp": True,
                        "verify_iss": True,
                    }
                )
                logger.debug("JWT decoded successfully")
                logger.debug(f"  Token claims: sub={payload.get('sub', 'N/A')}, exp={payload.get('exp', 'N/A')}, iat={payload.get('iat', 'N/A')}")
            except Exception as decode_error:
                logger.error(f"JWT decode/verification failed: {type(decode_error).__name__}: {decode_error}")
                return None

            # Step 3: Extract scopes
            logger.debug("Step 3: Extracting scopes from token")
            scopes = []
            if "scope" in payload:
                scopes = payload["scope"].split()
                logger.debug(f"  Scopes from 'scope' claim: {scopes}")
            elif "permissions" in payload:
                scopes = payload["permissions"]
                logger.debug(f"  Scopes from 'permissions' claim: {scopes}")
            else:
                logger.warning("  No scopes found in token (neither 'scope' nor 'permissions' claim)")

            # Step 4: Build AccessToken
            client_id = payload.get("azp") or payload.get("client_id", "unknown")
            expires_at = payload.get("exp")

            logger.info(f"Token verification SUCCEEDED")
            logger.debug(f"  Client ID: {client_id}")
            logger.debug(f"  Scopes: {scopes}")
            logger.debug(f"  Expires at: {expires_at}")
            logger.debug(f"  Resource: {self.audience}")

            # Return AccessToken model (issuer/audience already validated)
            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=scopes,
                expires_at=expires_at,
                resource=self.audience,
            )

        except InvalidTokenError as e:
            logger.error(f"Token verification FAILED (InvalidTokenError): {e}")
            logger.error(f"  Token preview: {token_preview}")
            logger.error(f"  Error type: {type(e).__name__}")
            logger.error(f"  Expected audience: {self.audience}")
            logger.error(f"  Expected issuer: {self.issuer}")
            return None
        except Exception as e:
            logger.error(f"Token verification FAILED (Unexpected error): {type(e).__name__}: {e}")
            logger.error(f"  Token preview: {token_preview}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
            return None


def create_auth0_verifier() -> Auth0TokenVerifier:
    """Create Auth0TokenVerifier from environment variables."""
    logger.info("Creating Auth0TokenVerifier from environment variables")

    domain = os.getenv("AUTH0_DOMAIN")
    audience = os.getenv("AUTH0_AUDIENCE")
    algorithms_str = os.getenv("AUTH0_ALGORITHMS", "RS256")

    logger.debug(f"  AUTH0_DOMAIN: {domain}")
    logger.debug(f"  AUTH0_AUDIENCE: {audience}")
    logger.debug(f"  AUTH0_ALGORITHMS: {algorithms_str}")

    if not domain:
        logger.error("AUTH0_DOMAIN environment variable is missing")
        raise ValueError("AUTH0_DOMAIN environment variable is required")
    if not audience:
        logger.error("AUTH0_AUDIENCE environment variable is missing")
        raise ValueError("AUTH0_AUDIENCE environment variable is required")

    algorithms = [alg.strip() for alg in algorithms_str.split(",")]
    logger.debug(f"  Parsed algorithms: {algorithms}")

    verifier = Auth0TokenVerifier(
        domain=domain,
        audience=audience,
        algorithms=algorithms
    )

    logger.info("Auth0TokenVerifier created successfully")
    return verifier
