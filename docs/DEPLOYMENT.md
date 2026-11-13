# Production Deployment

This guide covers deploying BudgetTracker on a single Linux server with Docker Compose
and a host nginx reverse proxy. Replace `your-domain` and `your-email` with your own
values everywhere.

## Architecture

```
Internet → host nginx (TLS, ports 80/443)
             ├── /            → 127.0.0.1:5173  frontend container (nginx serving the SPA)
             └── /api/, /health → 127.0.0.1:8000  backend container (FastAPI/uvicorn)
postgres + redis: internal Docker network only, no published ports
```

- Both compose ports are bound to `127.0.0.1` only. Docker publishes bypass ufw, so the
  localhost binding — not the firewall — is what keeps the containers private.
- A single clean initial migration runs automatically on backend start (the entrypoint
  runs `alembic upgrade head` when `RUN_MIGRATIONS=true`, the default).
- Background jobs (subscription billing, crypto sync, Telegram polling/reminders) run
  in-process. The backend runs `uvicorn --workers 1` **on purpose**: multiple workers
  would duplicate these loops and race Telegram `getUpdates` offsets. Do not raise it.
- The backend trusts proxy headers from any IP (`--forwarded-allow-ips '*'`); this is
  safe because it is only reachable through host nginx. `X-Forwarded-Proto` makes
  `request.base_url` yield `https://your-domain`, which the GitHub OAuth redirect needs.

## Prerequisites

- Debian 12 or Ubuntu server
- Docker with the compose plugin, git, ufw
- A DNS A record pointing `your-domain` to the server's public IP

## 1. Clone and configure

```bash
git clone https://github.com/5alex52/BudgetTracker.git /opt/budgettracker
cd /opt/budgettracker
cp .env.example .env
```

Edit `.env` and set at least:

```bash
DOMAIN=your-domain
ENVIRONMENT=PROD
SECRET_KEY=<output of: openssl rand -hex 32>        # required, min 32 chars
POSTGRES_PASSWORD=<output of: openssl rand -base64 24>  # required
POSTGRES_USER=budget
POSTGRES_DB=budgettracker
```

Optional integrations (features stay disabled while the values are empty):

```bash
TELEGRAM_BOT_TOKEN=            # from @BotFather
VAPID_PUBLIC_KEY=              # npx web-push generate-vapid-keys
VAPID_PRIVATE_KEY=
OAUTH_GITHUB_CLIENT_ID=        # see "GitHub OAuth" below
OAUTH_GITHUB_CLIENT_SECRET=
CRYPTO_ETHERSCAN_API_KEY=      # EVM balance-history backfill
```

`FRONTEND_URL`, `OAUTH_RETURN_URL` and `CORS_ORIGINS` are derived from `DOMAIN` by
`docker-compose.prod.yml` — no need to set them manually. Then lock the file down:

```bash
chmod 600 .env
```

## 2. Host nginx

```bash
sudo apt install nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/budgettracker`:

```nginx
server {
    listen 80;
    server_name your-domain;

    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }
}
```

Enable it and open the firewall (keep SSH!):

```bash
sudo ln -s /etc/nginx/sites-available/budgettracker /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo ufw allow 22/tcp
sudo ufw allow 80,443/tcp
sudo ufw enable
```

## 3. Free SSL (Let's Encrypt)

```bash
sudo certbot --nginx -d your-domain --agree-tos -m your-email
```

Certbot edits the server block for HTTPS and sets up auto-renewal (systemd timer or
cron, depending on the distro). Verify: `curl -I https://your-domain`.

## 4. Launch

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Migrations apply automatically on backend start. Check:

```bash
docker compose -f docker-compose.prod.yml ps
curl https://your-domain/health    # {"status":"ok","environment":"PROD"}
```

## Security checklist

- Only 80/443 are public (ufw); SSH kept on 22.
- Compose ports are bound to `127.0.0.1`. Verify from an external machine that
  5432, 6379, 8000 and 5173 are **not** reachable on the server's public IP.
- `/docs`, `/redoc` and `/openapi.json` are disabled when `ENVIRONMENT=PROD`.
- A strong `SECRET_KEY` (min 32 chars) is enforced at startup in PROD; compose also
  refuses to start without `SECRET_KEY`, `POSTGRES_PASSWORD` and `DOMAIN`.

## Optional seeding

```bash
# Superuser (management account, no demo data)
docker compose -f docker-compose.prod.yml exec \
    -e ADMIN_USER_EMAIL=your-email -e ADMIN_USER_PASSWORD='strong-password' \
    backend python -m scripts.seed_admin

# Demo data (6 accounts, 25 categories, ~387 transactions).
# Requires the currency catalog, which the initial migration seeds.
docker compose -f docker-compose.prod.yml exec backend python -m scripts.seed_demo
```

## GitHub OAuth

1. Create an OAuth App at <https://github.com/settings/developers>:
   - Homepage URL: `https://your-domain`
   - Authorization callback URL: `https://your-domain/api/auth/oauth/github/callback`
2. Put the credentials into `.env`:

   ```bash
   OAUTH_GITHUB_CLIENT_ID=...
   OAUTH_GITHUB_CLIENT_SECRET=...
   ```

3. Restart the backend: `docker compose -f docker-compose.prod.yml restart backend`

Empty values disable the GitHub login button.

## Telegram Mini App (optional)

Set `TELEGRAM_BOT_TOKEN` in `.env` and restart the backend. In @BotFather use
`/setmenubutton` to point the bot's menu button at `https://your-domain`. Users must
first link their Telegram account in Settings before reminders and Mini App login work.

## Updates and backups

Update:

```bash
cd /opt/budgettracker
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Back up the database through the `postgres` service (data lives in the named volume
`budgettracker-prod_postgres_data`):

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U budget budgettracker | gzip > backup_$(date +%Y%m%d).sql.gz
```

Restore:

```bash
gunzip -c backup_YYYYMMDD.sql.gz | docker compose -f docker-compose.prod.yml exec -T \
    postgres psql -U budget budgettracker
```

Automated deployment and backups are also available via Ansible (`ansible/`):
configure `inventory.yml` and `group_vars/` (domain, vault secrets), then run
`ansible-playbook -i inventory.yml deploy.yml`. It installs Docker, renders `.env`,
deploys the prod compose stack, sets up host nginx + Let's Encrypt and a nightly
`pg_dump` cron job with retention.
