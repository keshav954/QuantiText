# Deployment Guide — QuantiText

## Overview

This guide covers deploying QuantiText to production on a single Linux server (AWS EC2, DigitalOcean, or any VPS) using Docker Compose. The production stack runs NGINX, the React Frontend, FastAPI Backend, PostgreSQL 16, and Redis 7 within Docker containers.

---

## AWS EC2 Sizing & Server Setup

### 1. EC2 Instance Specification
- **OS**: Ubuntu 22.04 LTS (or 24.04 LTS), 64-bit (x86_64)
- **Instance Type**: `t3.medium` (2 vCPU, 4 GB RAM) minimum (or `t3.large` / 8 GB if available)
- **Storage**: **40 GB gp3** (required for ML dependencies and build caches)
- **Elastic IP**: Allocate and associate an Elastic IP so the public address does not change on reboot

### 2. Security Group Rules
- **Port 80 (HTTP)**: `0.0.0.0/0` (Anywhere)
- **Port 443 (HTTPS)**: `0.0.0.0/0` (Anywhere)
- **Port 22 (SSH)**: `Your IP only`
- *Never expose ports 5432, 6379, or 8000 to the public internet.*

### 3. Server Initialization (Docker & 4GB Swap)

Connect to the server:
```bash
ssh -i "your-key.pem" ubuntu@<your-elastic-ip>
```

Install Docker and configure 4GB swap space (essential on 4GB instances to prevent OOM errors during ML initialization):
```bash
# Update packages and install Docker
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git curl
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu

# Configure 4GB swap
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Apply group changes
newgrp docker
```

---

## Deploying QuantiText

### 1. Clone Repository & Setup Directory
```bash
sudo mkdir -p /opt/quantitext
sudo chown -R ubuntu:ubuntu /opt/quantitext
cd /opt/quantitext

git clone https://github.com/keshav954/QuantiText.git .
```

### 2. Configure Environment (`.env`)
```bash
cp .env.production.example .env
nano .env
```

Ensure the following are set:
- `DEBUG=false`
- `SECRET_KEY`: Generate a random 64-character string (`openssl rand -hex 32`)
- `POSTGRES_PASSWORD`: Strong random password (e.g., `pg_prod_948f21`)
- `REDIS_PASSWORD`: Strong random password (e.g., `redis_prod_831a47`)
- `REDIS_URL`: `redis://:<your-redis-password>@redis:6379/0`
- `DATABASE_URL`: `postgresql+asyncpg://quantitext:<your-pg-password>@postgres:5432/quantitext`
- `DATABASE_URL_SYNC`: `postgresql+psycopg2://quantitext:<your-pg-password>@postgres:5432/quantitext`
- `DB_READONLY_URL`: `postgresql+asyncpg://bi_readonly:<readonly-password>@postgres:5432/quantitext`
- `LLM_PROVIDER`: `gemini`
- `GEMINI_API_KEY`: Your key from [Google AI Studio](https://aistudio.google.com/)
- `LLM_MODEL`: `gemini-3.5-flash`
- `MLFLOW_TRACKING_URI`: `file:/tmp/mlruns`

### 3. Start Production Containers
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### 4. Run Migrations & Enable Read-Only Role
```bash
# Apply schema migrations
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# Activate bi_readonly login role for secure, unprivileged NL2SQL queries
docker compose -f docker-compose.prod.yml exec -T postgres psql -U quantitext -d quantitext \
  -c "ALTER ROLE bi_readonly WITH LOGIN PASSWORD '<readonly-password>';"

# Restart backend to connect with the read-only credentials
docker compose -f docker-compose.prod.yml restart backend
```

### 5. Seed Initial Data
```bash
docker compose -f docker-compose.prod.yml exec -T backend python -m data.seed
```

### 6. Reset Admin Password
For production security, update the default password (`admin123`) for `admin@demo.local`:
```bash
# Generate argon2 hash for your new password
docker compose -f docker-compose.prod.yml exec -T backend python -c \
  "from app.core.security import hash_password; print(hash_password('YourNewSecurePassword'))"

# Update user table with the printed hash
docker compose -f docker-compose.prod.yml exec -T postgres psql -U quantitext -d quantitext \
  -c "UPDATE users SET hashed_password='<paste-printed-hash>' WHERE email='admin@demo.local';"
```

### 7. Install Automated Crontab
```bash
crontab /opt/quantitext/infra/crontab
```
This runs:
- Daily encrypted database backup at 02:00 UTC.
- Weekly LightGBM demand forecast retraining on Sundays at 03:00 UTC.

---

## Domain & HTTPS Configuration (Optional)

If accessing directly via your EC2 Elastic IP, the site works over HTTP:
`http://<your-elastic-ip>`

If you have a domain (e.g. `bi.yourdomain.com`) pointing to your Elastic IP:

1. Stop the NGINX container temporarily to free port 80:
```bash
docker compose -f docker-compose.prod.yml stop nginx
```

2. Generate Let's Encrypt certificates via standalone mode:
```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d bi.yourdomain.com
```

3. Update `docker-compose.prod.yml` to mount the SSL config and certificates:
```yaml
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infra/nginx.ssl.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
```
*(In `infra/nginx.ssl.conf`, replace `your-domain.com` with `bi.yourdomain.com`).*

4. Start NGINX:
```bash
docker compose -f docker-compose.prod.yml up -d nginx
```

---

## Verification & Health Check

```bash
# Verify health endpoint returns 'healthy' for both Postgres and Redis
curl http://localhost/health

# Check running containers
docker compose -f docker-compose.prod.yml ps

# View backend logs
docker compose -f docker-compose.prod.yml logs backend --tail 50
```
