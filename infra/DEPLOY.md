# Deployment Guide — QuantiText

## Overview

This guide covers deploying QuantiText to a production environment.
The recommended stack is AWS EC2 + RDS, but any Linux server with Docker works.

## Prerequisites

- Linux server (Ubuntu 22.04+ recommended) with Docker 24+ and Docker Compose v2
- PostgreSQL 16 (RDS or self-hosted)
- Redis 7 (ElastiCache or self-hosted)
- Domain name with DNS configured
- Gemini API key from [Google AI Studio](https://aistudio.google.com/)

## Quick Deploy (Single Server)

```bash
# 1. Clone and configure
git clone <repo-url> /opt/quantitext
cd /opt/quantitext
cp .env.example .env

# 2. Edit .env with production values
#    - Set strong SECRET_KEY (64+ random chars)
#    - Set POSTGRES_PASSWORD (strong, random)
#    - Set GEMINI_API_KEY
#    - Set DEBUG=false
#    - Set DATABASE_URL to point to your PostgreSQL
#    - Set REDIS_URL to point to your Redis
nano .env

# 3. Build and start
docker compose -f docker-compose.prod.yml up --build -d

# 4. Run migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 5. Seed demo data (optional)
docker compose -f docker-compose.prod.yml exec backend python -m data.seed

# 6. Verify
curl http://localhost/health
```

## AWS EC2 + RDS Setup

### EC2 Instance

- **Instance type**: t3.medium (2 vCPU, 4 GB RAM) minimum
- **Storage**: 30 GB gp3
- **Security group**:
  - Inbound: 80 (HTTP), 443 (HTTPS), 22 (SSH from your IP only)
  - Outbound: All traffic

### RDS PostgreSQL

- **Engine**: PostgreSQL 16
- **Instance**: db.t3.micro (dev) or db.t3.medium (prod)
- **Storage**: 20 GB gp3
- **VPC**: Same VPC as EC2
- **Security group**: Allow inbound 5432 from EC2 security group only

### ElastiCache Redis

- **Engine**: Redis 7
- **Node type**: cache.t3.micro
- **VPC**: Same VPC as EC2

### Environment Variables

Update `.env` to point to RDS/ElastiCache:

```env
DATABASE_URL=postgresql+asyncpg://quantitext:<password>@<rds-endpoint>:5432/quantitext
DATABASE_URL_SYNC=postgresql+psycopg2://quantitext:<password>@<rds-endpoint>:5432/quantitext
DB_READONLY_URL=postgresql+asyncpg://quantitext_readonly:<password>@<rds-endpoint>:5432/quantitext
REDIS_URL=redis://:<password>@<elasticache-endpoint>:6379/0
```

## HTTPS with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

## Backup

### Database Backup Script

```bash
#!/bin/bash
# infra/backup.sh — run daily via cron
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/backups

mkdir -p $BACKUP_DIR

# PostgreSQL dump
docker compose -f /opt/quantitext/docker-compose.prod.yml exec -T postgres \
  pg_dump -U ${POSTGRES_USER:-quantitext} ${POSTGRES_DB:-quantitext} \
  | gzip > $BACKUP_DIR/db_${TIMESTAMP}.sql.gz

# Keep last 7 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_${TIMESTAMP}.sql.gz"
```

```bash
# Add to crontab
crontab -e
# Add: 0 2 * * * /opt/quantitext/infra/backup.sh >> /var/log/backup.log 2>&1
```

## Monitoring

### Health Endpoint

```bash
# Check application health
curl http://localhost/health | python3 -m json.tool
```

Response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-01-01T00:00:00Z",
  "services": {
    "postgres": "connected",
    "redis": "connected"
  }
}
```

### Log Monitoring

```bash
# View backend logs
docker compose -f docker-compose.prod.yml logs -f backend

# View NGINX access logs
docker compose -f docker-compose.prod.yml logs -f nginx
```

## Security Checklist

- [ ] `.env` is not committed to git (in `.gitignore`)
- [ ] `SECRET_KEY` is a random 64+ character string
- [ ] `DEBUG=false` in production
- [ ] PostgreSQL password is strong and unique
- [ ] Redis is password-protected
- [ ] NGINX rate limits are enabled
- [ ] Security headers are set (X-Frame-Options, CSP, etc.)
- [ ] SSH key-only authentication on the server
- [ ] Firewall allows only 80, 443, and SSH
- [ ] Database is not exposed to the internet
- [ ] API docs are disabled in production (`docs_url=None` when `DEBUG=false`)
- [ ] No secrets or API keys in the codebase

## Demo Mode

To run in demo mode with synthetic data:

```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m data.seed
```

Login with: **admin@demo.local** / **admin123**

> ⚠️ Demo data is SYNTHETIC. Never use demo credentials in production.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend won't start | Check `docker compose logs backend` — likely DB connection issue |
| 502 Bad Gateway | Backend container may have crashed — restart with `docker compose restart backend` |
| Slow queries | Check PostgreSQL slow query log; add indexes on frequently filtered columns |
| Redis connection refused | Verify REDIS_URL and that Redis container is healthy |
| LLM errors | Check GEMINI_API_KEY is valid; copilot falls back gracefully on LLM failure |
| Upload fails | Check file size limit (50MB); verify manager+ role |
