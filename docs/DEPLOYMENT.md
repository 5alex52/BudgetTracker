# Deployment Guide

This guide covers deploying BudgetTracker to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Ansible Deployment](#ansible-deployment)
- [Reverse Proxy Setup](#reverse-proxy-setup)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Database Backup](#database-backup)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: 2+ cores (4+ recommended for production)
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 20GB+ SSD
- **OS**: Ubuntu 22.04+ or equivalent

### Required Software

- Docker 24.0+
- Docker Compose 2.20+
- Nginx or Caddy (for reverse proxy)
- Certbot or Caddy (for SSL certificates)

## Environment Configuration

### Production Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Security
SECRET_KEY=<generate-64-random-chars>
POSTGRES_PASSWORD=<strong-password>

# Environment
ENVIRONMENT=PROD

# Database
POSTGRES_USER=budgettracker
POSTGRES_DB=budgettracker
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Backend
BACKEND_HOST_PORT=8000
FRONTEND_HOST_PORT=5173
WORKERS=4
LOG_LEVEL=INFO

# Frontend
VITE_API_PROXY_TARGET=http://backend:8000
VITE_TELEGRAM_SUPPORT_URL=https://t.me/your_support_bot
```

### Generate Secure Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate POSTGRES_PASSWORD
openssl rand -base64 32
```

## Docker Compose Deployment

### 1. Clone Repository

```bash
git clone https://github.com/yourorg/budgettracker.git
cd budgettracker
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your values
```

### 3. Build and Start

```bash
# Build production images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check logs
docker compose logs -f
```

### 4. Apply Database Migrations

```bash
docker compose exec backend alembic upgrade head
```

### 5. Seed Initial Data (Optional)

```bash
# Create admin user
docker compose exec backend python -m scripts.create_admin

# Seed demo data (development only)
docker compose exec backend python -m scripts.seed_demo
```

### 6. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Check services
docker compose ps
```

## Ansible Deployment

Ansible playbooks are located in the `ansible/` directory.

### Inventory Setup

Create `ansible/inventory.yml`:

```yaml
all:
  hosts:
    budgettracker:
      ansible_host: your-server-ip
      ansible_user: deploy
      ansible_ssh_private_key_file: ~/.ssh/id_rsa
```

### Configure Variables

Edit `ansible/group_vars/all.yml`:

```yaml
---
app_domain: budgettracker.example.com
admin_email: admin@example.com
postgres_password: "{{ lookup('env', 'POSTGRES_PASSWORD') }}"
secret_key: "{{ lookup('env', 'SECRET_KEY') }}"
environment: PROD
```

### Run Deployment

```bash
cd ansible

# Install dependencies
ansible-galaxy install -r requirements.yml

# Run full deployment
ansible-playbook -i inventory.yml deploy.yml

# Run specific tasks
ansible-playbook -i inventory.yml deploy.yml --tags "setup"
ansible-playbook -i inventory.yml deploy.yml --tags "deploy"
ansible-playbook -i inventory.yml deploy.yml --tags "ssl"
```

### Ansible Playbook Structure

```
ansible/
├── inventory.yml              # Server inventory
├── group_vars/
│   └── all.yml               # Global variables
├── roles/
│   ├── setup/                # System setup
│   │   └── tasks/main.yml
│   ├── docker/               # Docker installation
│   │   └── tasks/main.yml
│   ├── app/                  # Application deployment
│   │   └── tasks/main.yml
│   ├── nginx/                # Reverse proxy
│   │   └── tasks/main.yml
│   └── ssl/                  # SSL certificates
│       └── tasks/main.yml
└── deploy.yml                # Main playbook
```

## Reverse Proxy Setup

### Nginx Configuration

Create `/etc/nginx/sites-available/budgettracker`:

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend {
    server 127.0.0.1:5173;
}

server {
    listen 80;
    server_name budgettracker.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name budgettracker.example.com;

    ssl_certificate /etc/letsencrypt/live/budgettracker.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/budgettracker.example.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }
}
```

### Caddy Configuration (Alternative)

Create `Caddyfile`:

```
budgettracker.example.com {
    reverse_proxy /api/* localhost:8000
    reverse_proxy /* localhost:5173
}
```

## SSL/TLS Configuration

### Using Certbot

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d budgettracker.example.com

# Auto-renewal (already configured by certbot)
sudo systemctl status certbot.timer
```

### Manual Certificate Management

```bash
# Renew certificate
sudo certbot renew

# Force renewal
sudo certbot renew --force-renewal
```

## Database Backup

### Automated Backups

Create backup script `/usr/local/bin/backup-budgettracker.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/budgettracker"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# PostgreSQL backup
docker compose exec -T db pg_dump -U budgettracker budgettracker | \
    gzip > $BACKUP_DIR/db_$TIMESTAMP.sql.gz

# Redis backup (if persistence enabled)
docker compose exec -T redis redis-cli BGSAVE
sleep 2
cp /var/lib/docker/volumes/budgettracker_redis/_data/dump.rdb \
   $BACKUP_DIR/redis_$TIMESTAMP.rdb

# Keep last 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

### Cron Job

```bash
# Daily backup at 2 AM
echo "0 2 * * * /usr/local/bin/backup-budgettracker.sh" | sudo crontab -
```

### Restore from Backup

```bash
# Stop services
docker compose stop backend

# Restore database
gunzip -c db_20261104_120000.sql.gz | docker compose exec -T db psql -U budgettracker budgettracker

# Start services
docker compose start backend
```

## Monitoring

### Docker Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f db
```

### Resource Monitoring

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Volume usage
docker volume ls
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database connectivity
docker compose exec db pg_isready -U budgettracker

# Redis connectivity
docker compose exec redis redis-cli ping
```

### Application Metrics

```bash
# Database query stats
docker compose exec db psql -U budgettracker -c "SELECT * FROM pg_stat_activity;"

# Redis info
docker compose exec redis redis-cli INFO
```

## Troubleshooting

### Common Issues

#### Backend won't start

```bash
# Check logs
docker compose logs backend

# Common causes:
# - Database not ready (wait 10 seconds)
# - Invalid environment variables
# - Port already in use
```

#### Database connection errors

```bash
# Check database status
docker compose ps db

# Restart database
docker compose restart db

# Check connection
docker compose exec backend python -c "from src.database import engine; print(engine)"
```

#### Frontend build errors

```bash
# Rebuild frontend
docker compose build frontend

# Clear cache
docker compose down
docker volume rm budgettracker_frontend_node_modules
docker compose up -d
```

#### Migration errors

```bash
# Check current migration
docker compose exec backend alembic current

# View migration history
docker compose exec backend alembic history

# Rollback last migration
docker compose exec backend alembic downgrade -1

# Re-apply
docker compose exec backend alembic upgrade head
```

### Logs Location

```bash
# Docker logs
/var/lib/docker/containers/*/
docker compose logs > /tmp/budgettracker.log

# Application logs (if configured)
docker compose exec backend cat /app/logs/app.log
```

### Performance Tuning

#### Backend Workers

Edit `.env`:

```bash
WORKERS=8  # Increase for high traffic
```

#### Database Connection Pool

Edit `backend/src/config.py`:

```python
DATABASE_POOL_SIZE = 20  # Increase for more connections
DATABASE_MAX_OVERFLOW = 10
```

#### Redis Memory

Edit `docker-compose.yml`:

```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### Security Checklist

- [ ] Change default `SECRET_KEY`
- [ ] Change default `POSTGRES_PASSWORD`
- [ ] Set `ENVIRONMENT=PROD`
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall (UFW/iptables)
- [ ] Set up automated backups
- [ ] Enable database connection encryption
- [ ] Review CORS origins
- [ ] Set up rate limiting (future feature)
- [ ] Enable fail2ban for SSH

## Production Checklist

Before going live:

1. ✅ Configure production environment variables
2. ✅ Set up SSL certificates
3. ✅ Configure reverse proxy
4. ✅ Set up automated backups
5. ✅ Enable monitoring
6. ✅ Test disaster recovery
7. ✅ Configure log rotation
8. ✅ Set up alerts
9. ✅ Review security settings
10. ✅ Load test the application

---

**Need help?** Contact support@budgettracker.local
