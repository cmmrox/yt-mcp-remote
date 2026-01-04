# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Copy application code
COPY main.py ./
COPY utils/ ./utils/
COPY prompts/ ./prompts/

# Expose port
EXPOSE 8000

# Set environment variable for port
ENV PORT=8000

# Run the application
CMD ["uv", "run", "python", "main.py"]
