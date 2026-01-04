# Local Setup Guide: YouTube MCP Remote Server

This guide provides complete instructions for running the YouTube MCP server locally using pyenv for Python version management and uv for dependency management.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup Instructions](#detailed-setup-instructions)
- [Available MCP Tools](#available-mcp-tools)
- [Troubleshooting](#troubleshooting)
- [Development Workflow](#development-workflow)
- [Alternative Setup Methods](#alternative-setup-methods)

## Prerequisites

- **pyenv**: Python version manager (should already be installed)
- **uv**: Ultra-fast Python package manager (installation instructions below)
- **Python 3.13**: Required by this project
- **Auth0 account**: For OAuth authentication configuration

## Quick Start

Run these commands to get started:

```bash
# 1. Install Python 3.13 with pyenv
pyenv install 3.13.1
pyenv local 3.13.1

# 2. Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Navigate to project and install dependencies
cd /Users/cmmrox/Office/RND/yt-mcp-remote
uv sync

# 4. Configure environment variables
cp .env.example .env
nano .env  # Edit with your Auth0 credentials

# 5. Run the server
uv run python main.py
```

**Server will be running at:** `http://0.0.0.0:8000/mcp`

---

## Detailed Setup Instructions

### Step 1: Install Python 3.13 with pyenv

First, check available Python 3.13 versions:

```bash
pyenv install --list | grep "^\s*3\.13"
```

Install the latest Python 3.13 version:

```bash
# Install Python 3.13.1 (or latest available)
pyenv install 3.13.1

# Navigate to project directory
cd /Users/cmmrox/Office/RND/yt-mcp-remote

# Set Python 3.13 as the local version for this project
pyenv local 3.13.1

# Verify Python version
python --version  # Should show: Python 3.13.x
```

### Step 2: Install uv Package Manager

The project uses `uv` for fast dependency management. Choose one installation method:

**Option A: Standalone Installer (Recommended)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Option B: Homebrew**
```bash
brew install uv
```

**Option C: pip**
```bash
pip install uv
```

Verify installation:
```bash
uv --version
```

If the command is not found, reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc for zsh
```

### Step 3: Install Project Dependencies

Navigate to the project directory and sync dependencies:

```bash
cd /Users/cmmrox/Office/RND/yt-mcp-remote
uv sync
```

**What `uv sync` does:**
- Creates a virtual environment in `.venv/` directory
- Installs all dependencies from `pyproject.toml` using locked versions in `uv.lock`
- Installed dependencies:
  - `httpx>=0.28.1` - Async HTTP client
  - `mcp[cli]>=1.18.0` - Model Context Protocol framework
  - `pydantic>=2.12.3` - Data validation
  - `python-dotenv>=1.1.1` - Environment variable loading
  - `pyjwt[crypto]>=2.8.0` - JWT token verification
  - `youtube-transcript-api>=1.2.3` - YouTube transcript extraction

### Step 4: Configure Environment Variables

Create and configure your `.env` file:

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your preferred editor
nano .env  # or vim, code, etc.
```

**Required configuration in `.env`:**

```bash
# Auth0 OAuth Configuration
# Your Auth0 tenant domain (find in Auth0 Dashboard)
AUTH0_DOMAIN=your-auth0-domain.auth0.com

# Auth0 API identifier (from Auth0 API settings)
AUTH0_AUDIENCE=https://your-api-identifier.com

# Public URL where server will be accessible
# For local development:
RESOURCE_SERVER_URL=http://localhost:8000/mcp

# Optional: Server port (defaults to 8000)
PORT=8000

# Optional: JWT algorithm (defaults to RS256)
AUTH0_ALGORITHMS=RS256
```

**Important Notes:**
- The `.env.example` file already exists with template values
- Your current `.env` may have existing Auth0 credentials - verify they're correct
- For local development, use `http://localhost:8000/mcp` as `RESOURCE_SERVER_URL`
- `AUTH0_AUDIENCE` can match `RESOURCE_SERVER_URL` in this setup

**Getting Auth0 Credentials:**
1. Create an Auth0 account at https://auth0.com
2. Create a new API in your Auth0 dashboard
3. Copy the domain and API identifier to your `.env` file
4. Ensure your Auth0 application has required scopes: `openid`, `profile`, `email`, `address`, `phone`, `offline_access`

### Step 5: Run the Server

Start the MCP server:

```bash
uv run python main.py
```

**Expected output:**
```
Server running at: http://0.0.0.0:8000/mcp
```

**Server endpoints:**
- Local access: `http://localhost:8000/mcp`
- Network access: `http://0.0.0.0:8000/mcp` (accessible from other devices on your network)

### Step 6: Verify Server is Running

In a new terminal window, test the server:

```bash
curl http://localhost:8000/mcp
```

You should receive a response from the MCP server.

---

## Available MCP Tools

Once the server is running, it exposes two MCP tools via the Model Context Protocol:

### 1. `fetch_video_transcript(url: str)`

Extracts YouTube video transcripts with timestamps.

**Features:**
- Supports various YouTube URL formats
- Returns formatted transcript with timestamps in `[MM:SS]` format
- Uses `youtube-transcript-api` library

**Example:**
```python
fetch_video_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
```

**Output format:**
```
[00:00] First line of transcript
[00:15] Second line of transcript
[00:32] Third line of transcript
...
```

### 2. `fetch_instructions(prompt_name: str)`

Retrieves writing instruction templates from the `prompts/` directory.

**Available prompts:**
- `write_blog_post` - Blog post conversion guidelines with structure rules
- `write_social_post` - Platform-specific social media guidelines
- `write_video_chapters` - Video chapter formatting rules

**Example:**
```python
fetch_instructions("write_blog_post")
```

---

## Troubleshooting

### Issue: Python version not found

```bash
# List available Python versions
pyenv install --list | grep 3.13

# Install specific version
pyenv install 3.13.1
pyenv local 3.13.1

# Verify
python --version
```

### Issue: uv command not found

```bash
# Reload shell configuration
source ~/.bashrc  # or ~/.zshrc

# Or reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Issue: Auth0 authentication errors

**Checklist:**
- Verify `AUTH0_DOMAIN` is correct (format: `your-domain.auth0.com`)
- Verify `AUTH0_AUDIENCE` matches your Auth0 API identifier
- Check Auth0 dashboard for API settings
- Ensure Auth0 application has required scopes: `openid`, `profile`, `email`, `address`, `phone`, `offline_access`
- Verify JWT algorithm is set correctly (default: `RS256`)

### Issue: Port 8000 already in use

```bash
# Option 1: Change port in .env file
echo "PORT=8001" >> .env
uv run python main.py

# Option 2: Kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Issue: Dependencies not installing

```bash
# Clear uv cache and reinstall
rm -rf .venv
uv sync --reinstall

# Or use --no-cache flag
uv sync --no-cache
```

### Issue: Module import errors

```bash
# Ensure you're using uv to run Python
uv run python main.py

# NOT just: python main.py
# uv run ensures the virtual environment is activated
```

---

## Development Workflow

### Starting the Server

```bash
cd /Users/cmmrox/Office/RND/yt-mcp-remote
uv run python main.py
```

### Stopping the Server

Press `Ctrl+C` in the terminal running the server.

### Adding New Dependencies

```bash
# Add a new package
uv add package-name

# Add a development dependency
uv add --dev package-name
```

### Updating Dependencies

```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv add package-name@latest
```

### Viewing Installed Packages

```bash
# List installed packages
uv pip list

# Show dependency tree
uv pip tree
```

---

## Alternative Setup Methods

### Option 1: Using Docker (Recommended for Deployment)

If you prefer running in Docker:

```bash
# Build and run with Docker Compose
docker-compose up --build

# Server runs at http://localhost:8000/mcp

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop server
docker-compose down
```

### Option 2: Traditional venv + pip

If you prefer not to use uv:

```bash
# Create virtual environment with pyenv Python
cd /Users/cmmrox/Office/RND/yt-mcp-remote
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies using pip
pip install httpx "mcp[cli]" pydantic python-dotenv "pyjwt[crypto]" youtube-transcript-api

# Configure environment
cp .env.example .env
nano .env

# Run the server
python main.py
```

**Note:** When using venv, you need to activate the virtual environment each time:
```bash
source .venv/bin/activate
```

---

## Project Structure

```
/Users/cmmrox/Office/RND/yt-mcp-remote/
├── main.py                    # MCP server entry point
├── utils/
│   └── auth.py               # Auth0 token verification
├── prompts/
│   ├── server_instructions.md
│   ├── write_blog_post.md
│   ├── write_social_post.md
│   └── write_video_chapters.md
├── pyproject.toml            # Python dependencies
├── uv.lock                   # Dependency lock file
├── .env                      # Environment configuration (local)
├── .env.example              # Environment template
├── .python-version           # Python 3.13
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker compose setup
├── README.md                 # Project overview
├── CLAUDE.md                 # AI assistant instructions
└── LOCAL-SETUP.md           # This file
```

## Critical Files

- **main.py** - Server entry point and MCP tool definitions
- **utils/auth.py** - Auth0 JWT token verification logic
- **prompts/** - Writing instruction templates
- **.env** - Environment configuration (not committed to git)
- **pyproject.toml** - Python project and dependency definitions

---

## Additional Resources

- **Project README**: See `README.md` for project overview
- **FastMCP Documentation**: https://github.com/jlowin/fastmcp
- **Model Context Protocol**: https://modelcontextprotocol.io
- **Auth0 Documentation**: https://auth0.com/docs
- **YouTube Transcript API**: https://github.com/jdepoix/youtube-transcript-api

---

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Verify your `.env` configuration
3. Ensure Python 3.13 is active: `python --version`
4. Check server logs for error messages
5. Verify Auth0 credentials in your Auth0 dashboard

---

## Summary

**To run the server:**
1. Install Python 3.13 via pyenv
2. Install uv package manager
3. Run `uv sync` to install dependencies
4. Configure `.env` with Auth0 credentials
5. Run `uv run python main.py`

**Server will be accessible at:** `http://0.0.0.0:8000/mcp`

Happy coding!
