# Docker Setup Guide

This guide explains how to run the RegosPartnerBot application in Docker containers for production.

## Prerequisites

- Docker Engine 20.10 or later
- Docker Compose 2.0 or later

## Quick Start

1. **Copy the environment file:**
   ```bash
   cp env.example .env
   ```

2. **Edit `.env` file and set your configuration:**
   ```bash
   # Required: Set your public domain
   WEBHOOK_BASE_URL=https://your-domain.com
   
   # Optional: Change frontend port (default: 80)
   FRONTEND_PORT=80
   ```

3. **Build and start the containers:**
   ```bash
   docker-compose up -d
   ```

4. **Check the logs:**
   ```bash
   docker-compose logs -f
   ```

5. **Stop the containers:**
   ```bash
   docker-compose down
   ```

## Architecture

The application consists of two main services:

### Backend Service
- **Image**: Built from `Dockerfile.backend`
- **Technology**: Python 3.11 + FastAPI + Uvicorn
- **Port**: 8000 (internal)
- **Health Check**: `/health` endpoint
- **Data Persistence**: 
  - Database: `./data/telegram_bots.db` (mounted volume)
  - Exports: `./exports/` (mounted volume)

### Frontend Service
- **Image**: Built from `Dockerfile.frontend`
- **Technology**: Nginx (serving static React builds)
- **Port**: 80 (exposed to host)
- **Routes**:
  - `/` - Telegram WebApp
  - `/admin` - Admin Panel
  - `/api/*` - API proxy to backend
  - `/webhook/*` - Telegram webhook proxy
  - `/regos/webhook` - REGOS webhook proxy

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `WEBHOOK_BASE_URL` | Public domain for Telegram webhooks | `https://your-domain.com` |
| `DATABASE_PATH` | Path to SQLite database | `/app/data/telegram_bots.db` |
| `HOST` | Backend host | `0.0.0.0` |
| `PORT` | Backend port | `8000` |
| `APP_NAME` | Application name | `RegosPartnerBot` |
| `FRONTEND_PORT` | Frontend port on host | `80` |

### Volume Mounts

The following directories are mounted as volumes for data persistence:

- `./data` → `/app/data` (database files)
- `./exports` → `/app/exports` (exported files)

## Building Images

### Build all services:
```bash
docker-compose build
```

### Build specific service:
```bash
docker-compose build backend
docker-compose build frontend
```

## Running in Production

### Start services:
```bash
docker-compose up -d
```

### View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Stop services:
```bash
docker-compose down
```

### Stop and remove volumes (⚠️ deletes data):
```bash
docker-compose down -v
```

## Updating the Application

1. **Pull latest code:**
   ```bash
   git pull
   ```

2. **Rebuild and restart:**
   ```bash
   docker-compose up -d --build
   ```

## Health Checks

Both services have health checks configured:

- **Backend**: Checks `/health` endpoint every 30 seconds
- **Frontend**: Checks nginx health endpoint every 30 seconds

View health status:
```bash
docker-compose ps
```

## Troubleshooting

### Backend won't start
1. Check logs: `docker-compose logs backend`
2. Verify database path is writable
3. Check environment variables in `.env`

### Frontend shows 502 Bad Gateway
1. Check if backend is healthy: `docker-compose ps`
2. Check backend logs: `docker-compose logs backend`
3. Verify network connectivity between services

### Database issues
1. Ensure `./data` directory exists and is writable
2. Check file permissions: `chmod 755 ./data`
3. Verify database path in `.env`

### Port already in use
1. Change `FRONTEND_PORT` in `.env` to a different port
2. Restart: `docker-compose down && docker-compose up -d`

## Security Considerations

1. **Change default ports** if exposing to the internet
2. **Use HTTPS** in production (configure reverse proxy with SSL)
3. **Set strong passwords** for any authentication
4. **Limit exposed ports** to only what's necessary
5. **Regularly update** Docker images and dependencies

## Using PostgreSQL (Optional)

To use PostgreSQL instead of SQLite:

1. Add PostgreSQL service to `docker-compose.yml`:
   ```yaml
   postgres:
     image: postgres:15-alpine
     environment:
       POSTGRES_USER: regos_user
       POSTGRES_PASSWORD: your_password
       POSTGRES_DB: regos_bot
     volumes:
       - postgres_data:/var/lib/postgresql/data
     networks:
       - regos-network
   ```

2. Update `.env`:
   ```bash
   DATABASE_PATH=postgresql+asyncpg://regos_user:your_password@postgres:5432/regos_bot
   ```

3. Update `requirements.txt` to include `asyncpg`

4. Rebuild and restart:
   ```bash
   docker-compose up -d --build
   ```

## Monitoring

### View resource usage:
```bash
docker stats
```

### View service status:
```bash
docker-compose ps
```

### Execute commands in containers:
```bash
# Backend
docker-compose exec backend bash

# Frontend
docker-compose exec frontend sh
```

## Backup

### Backup database:
```bash
docker-compose exec backend cp /app/data/telegram_bots.db /app/data/telegram_bots.db.backup
```

### Backup entire data directory:
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz ./data ./exports
```
