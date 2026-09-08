# Switch Health Dashboard - Docker Deployment Guide

Your application is now published to Docker Hub at: **mrmsmith/localswitchcontrolhub:latest**

## Quick Start (Any Machine)

### 1. Pull and Run with Docker

```bash
docker run -d \
  --name switch-health-dashboard \
  -p 8787:8787 \
  -e SWITCH_USERNAME=networks \
  -e SWITCH_PASSWORD=w00Lw0rTh$ \
  -e SWITCH_ENABLE_SECRET=w00Lw0rTh$ \
  -e WEBHOOK_URL=https://webhook.site/62b6e93a-fc92-45c7-a4e1-06418c0f497c \
  mrmsmith/localswitchcontrolhub:latest
```

Then open: http://localhost:8787

### 2. Using Docker Compose (Recommended)

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  switch-health-dashboard:
    image: mrmsmith/localswitchcontrolhub:latest
    container_name: switch-health-dashboard
    ports:
      - "8787:8787"
    environment:
      SWITCH_USERNAME: networks
      SWITCH_PASSWORD: w00Lw0rTh$
      SWITCH_ENABLE_SECRET: w00Lw0rTh$
      WEBHOOK_URL: https://webhook.site/62b6e93a-fc92-45c7-a4e1-06418c0f497c
      SWITCH_DASHBOARD_HOST: 0.0.0.0
      SWITCH_DASHBOARD_PORT: 8787
      CHECK_INTERVAL_SECONDS: 30
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; socket.create_connection(('127.0.0.1', 8787), timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
```

Then run:

```bash
docker compose up -d
```

### 3. Using .env File for Credentials (More Secure)

Create `.env`:

```env
SWITCH_USERNAME=networks
SWITCH_PASSWORD=w00Lw0rTh$
SWITCH_ENABLE_SECRET=w00Lw0rTh$
WEBHOOK_URL=https://webhook.site/62b6e93a-fc92-45c7-a4e1-06418c0f497c
CHECK_INTERVAL_SECONDS=30
```

Update `docker-compose.yml` to reference it:

```yaml
services:
  switch-health-dashboard:
    image: mrmsmith/localswitchcontrolhub:latest
    ports:
      - "8787:8787"
    env_file: .env
    restart: unless-stopped
```

## Common Commands

### View logs
```bash
docker compose logs -f switch-health-dashboard
```

### Stop the container
```bash
docker compose down
```

### Restart
```bash
docker compose restart
```

### Check health status
```bash
docker ps
```

Look for `(healthy)` in the STATUS column.

## Customization

### Change port mapping
In `docker-compose.yml`, change:
```yaml
ports:
  - "9000:8787"  # Access at http://localhost:9000
```

### Change polling interval
```env
CHECK_INTERVAL_SECONDS=60  # Check every 60 seconds instead of 30
```

### Update credentials
Update the environment variables in `.env` or `docker-compose.yml` and restart:
```bash
docker compose up -d
```

## Image Details

- **Repository:** mrmsmith/localswitchcontrolhub
- **Tag:** latest
- **Size:** 70.1 MB (compressed)
- **Base Image:** python:3.11-slim
- **Architecture:** Linux (amd64)
- **Exposed Port:** 8787

## Deployment to Other Machines

On any machine with Docker installed:

```bash
# Pull the latest image
docker pull mrmsmith/localswitchcontrolhub:latest

# Run directly
docker run -d -p 8787:8787 \
  -e SWITCH_USERNAME=networks \
  -e SWITCH_PASSWORD=w00Lw0rTh$ \
  -e SWITCH_ENABLE_SECRET=w00Lw0rTh$ \
  mrmsmith/localswitchcontrolhub:latest
```

## Production Recommendations

1. **Use secrets management** — Don't hardcode credentials. Use Docker secrets or external vaults.
2. **Enable logging** — Add `logging` to docker-compose.yml for centralized logs.
3. **Set resource limits** — Add `mem_limit` and `cpu_shares` to docker-compose.yml.
4. **Use version tags** — Tag releases with versions (v1.0, v1.1, etc.) instead of just `latest`.
5. **Network security** — If exposing externally, use a reverse proxy (nginx, traefik) with SSL/TLS.

## Troubleshooting

### Container won't start
```bash
docker compose logs switch-health-dashboard
```

### Port 8787 already in use
Change the port mapping in docker-compose.yml:
```yaml
ports:
  - "8888:8787"
```

### Can't connect to switch
Check the logs and verify:
- Switch IP is correct and reachable
- Credentials are correct
- Firewall allows SSH (port 22) to the switch

Feel free to ask if you need anything else!
