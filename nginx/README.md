# Nginx Reverse Proxy Setup

This directory contains the nginx reverse proxy configuration for the YouTube MCP Remote Server with SSL termination and multi-service routing support.

## Architecture

```
Internet → nginx:443 (SSL) → yt-mcp-server:8000
              ↓
         [Docker Network: mcp-network]
```

## Prerequisites

- Docker and Docker Compose installed
- SSL certificates in `certs/` folder:
  - `ingress-tls.crt` (SSL certificate)
  - `ingress-tls.key` (SSL private key)
- Domain `odoo-mcp.cssapps.net` pointing to your server IP

## Setup Instructions

### 1. Create Docker Network

First, create a Docker network that both nginx and yt-mcp-server will use:

```bash
docker network create mcp-network
```

Verify the network was created:

```bash
docker network ls | grep mcp-network
```

### 2. Start the YT-MCP Server

Start the yt-mcp-server using the main docker-compose file:

```bash
# From the project root directory
docker-compose up -d
```

Verify the container is running:

```bash
docker ps | grep yt-mcp-server
```

### 3. Start Nginx Proxy

Start the nginx reverse proxy using the nginx-specific compose file:

```bash
# From the project root directory
docker-compose -f docker-compose-nginx.yml up -d
```

Verify nginx is running:

```bash
docker ps | grep nginx-proxy
```

### 4. Verify Connectivity

Test the setup:

```bash
# Test HTTPS access (using -k to skip certificate verification for self-signed certs)
curl -k https://odoo-mcp.cssapps.net

# Test HTTP to HTTPS redirect
curl -I http://odoo-mcp.cssapps.net
# Should return: HTTP/1.1 301 Moved Permanently
# Location: https://odoo-mcp.cssapps.net/
```

## Configuration Files

### docker-compose-nginx.yml
Main Docker Compose file for nginx service.

**Key features:**
- Uses `nginx:alpine` image for minimal footprint
- Mounts SSL certificates from `certs/` folder
- Mounts nginx configuration from `nginx/rules.conf`
- Connects to `mcp-network` for container communication
- Exposes ports 80 (HTTP) and 443 (HTTPS)

### nginx/rules.conf
Nginx server configuration with SSL and reverse proxy rules.

**Current configuration:**
- HTTP to HTTPS redirect for `odoo-mcp.cssapps.net`
- SSL termination with TLSv1.2 and TLSv1.3
- Reverse proxy to `yt-mcp-server:8000`
- Optimized buffer and timeout settings
- WebSocket support enabled
- Access and error logging

**Adding new services:**
See the commented templates in `rules.conf` for examples of:
- Adding new domain-based services
- Path-based routing on a single domain
- Advanced routing patterns

## Managing Services

### Start all services

```bash
# Start yt-mcp-server
docker-compose up -d

# Start nginx
docker-compose -f docker-compose-nginx.yml up -d
```

### Stop all services

```bash
# Stop nginx
docker-compose -f docker-compose-nginx.yml down

# Stop yt-mcp-server
docker-compose down
```

### View logs

```bash
# Nginx logs
docker-compose -f docker-compose-nginx.yml logs -f nginx

# YT-MCP server logs
docker-compose logs -f yt-mcp-server
```

### Reload nginx configuration

After editing `nginx/rules.conf`:

```bash
# Test configuration
docker exec nginx-proxy nginx -t

# Reload nginx (no downtime)
docker exec nginx-proxy nginx -s reload

# Or restart the container
docker-compose -f docker-compose-nginx.yml restart
```

## Adding New Services

To add a new service to the reverse proxy:

### 1. Add service to Docker Compose

Create a new service in `docker-compose.yml` or a separate compose file:

```yaml
services:
  new-service:
    image: your-image:tag
    container_name: new-service
    networks:
      - mcp-network
    restart: unless-stopped
```

### 2. Update nginx/rules.conf

Add a new server block using the template in `rules.conf`:

```nginx
# HTTP redirect
server {
    listen 80;
    server_name new-service.cssapps.net;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl;
    server_name new-service.cssapps.net;

    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://new-service:PORT;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Reload nginx

```bash
docker exec nginx-proxy nginx -t && docker exec nginx-proxy nginx -s reload
```

## Troubleshooting

### Cannot connect to backend service

**Check network connectivity:**
```bash
# Verify both containers are on the same network
docker network inspect mcp-network

# Test connectivity from nginx to backend
docker exec nginx-proxy ping yt-mcp-server
```

### SSL certificate errors

**Verify certificates are mounted:**
```bash
# Check if certificates exist in nginx container
docker exec nginx-proxy ls -la /etc/nginx/ssl/
```

**Test nginx configuration:**
```bash
docker exec nginx-proxy nginx -t
```

### Port conflicts

**Check if ports 80 or 443 are already in use:**
```bash
# On macOS/Linux
sudo lsof -i :80
sudo lsof -i :443

# Stop conflicting services or change nginx ports
```

### Container not starting

**View detailed logs:**
```bash
docker-compose -f docker-compose-nginx.yml logs nginx
```

**Common issues:**
- Network `mcp-network` doesn't exist → Create it with `docker network create mcp-network`
- Certificate files not found → Check paths in `docker-compose-nginx.yml`
- Configuration syntax error → Run `docker exec nginx-proxy nginx -t`

### Verify backend is accessible

**Test direct connection to backend (before nginx):**
```bash
# From host (if port 8000 is exposed)
curl http://localhost:8000

# From nginx container
docker exec nginx-proxy wget -O- http://yt-mcp-server:8000
```

## Security Considerations

1. **SSL/TLS Configuration**: Uses TLSv1.2 and TLSv1.3 with strong cipher suites
2. **No Direct Backend Access**: Port 8000 is not exposed to host, only accessible via nginx
3. **Header Forwarding**: Proper headers set for client IP tracking and SSL offloading
4. **Certificate Management**: Keep SSL certificates up to date

### Recommended Enhancements

Consider adding these security features:

```nginx
# In server block:

# Security headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;

# Rate limiting
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req zone=general burst=20 nodelay;

# IP whitelisting (example)
# allow 192.168.1.0/24;
# deny all;
```

## Network Cleanup

To remove the Docker network (only when all services are stopped):

```bash
# Stop all services first
docker-compose down
docker-compose -f docker-compose-nginx.yml down

# Remove network
docker network rm mcp-network
```

## Files Reference

| File | Purpose |
|------|---------|
| `docker-compose-nginx.yml` | Nginx service configuration |
| `nginx/rules.conf` | Nginx server blocks and routing rules |
| `nginx/README.md` | This documentation |
| `certs/ingress-tls.crt` | SSL certificate |
| `certs/ingress-tls.key` | SSL private key |

## Support

For issues or questions:
1. Check nginx logs: `docker-compose -f docker-compose-nginx.yml logs nginx`
2. Verify configuration: `docker exec nginx-proxy nginx -t`
3. Test connectivity: `docker network inspect mcp-network`
