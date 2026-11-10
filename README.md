<div align="center">

# BudgetTracker

### Personal Finance Management System

[![License](https://img.shields.io/badge/license-proprietary-red?style=flat-square)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.13+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19+-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6+-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

**Track expenses, manage multi-currency accounts, and get insights into your spending habits with advanced analytics.**

[Features](#features) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Deployment](#deployment) • [License](#license)

</div>

---

## 📊 Preview

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/dashboard-preview-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/dashboard-preview-light.png">
    <img src="docs/assets/dashboard-preview-light.png" alt="BudgetTracker Dashboard Preview" width="90%">
  </picture>
</div>

<br>

## ✨ Features

### Core Functionality
- **Multi-currency accounts** with automatic conversion and personal exchange rates
- **Smart categorization** with auto-rules and category tree
- **Transfers between accounts** with real-time balance updates
- **Advanced analytics** with period comparison, trends, and category breakdowns
- **Admin panel** for user management
- Fully free and open-source: every feature is available to everyone
- Budget limits per category

### Security & Privacy
- JWT authentication in httpOnly cookies (no localStorage)
- Bcrypt password hashing (work factor 12)
- Row-level isolation: all queries filtered by `user_id`
- CORS restricted to configured origins
- Rate limiting ready (TODO)

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/yourorg/budgettracker.git
cd budgettracker
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set:
# - SECRET_KEY (minimum 32 characters)
# - POSTGRES_PASSWORD (strong password)
# - ENVIRONMENT=LOCAL (for development)
```

### 3. Start the stack

```bash
docker compose up --build
```

### 4. Access the application

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | React SPA |
| Backend API | http://localhost:8000 | FastAPI |
| Swagger Docs | http://localhost:8000/docs | API documentation |
| Admin Panel | http://localhost:5173/admin | Superuser only |

### 5. Create demo data (optional)

```bash
# Seed demo user with 6 accounts, 25 categories, 387 transactions
docker compose exec backend python -m scripts.seed_demo

# Create admin superuser
docker compose exec backend python -m scripts.seed_admin
```

**Demo credentials:**
- User: `demo@budgettracker.local` / `demo12345`
- Admin: `admin@budgettracker.local` / `admin12345`

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [AGENTS.md](./AGENTS.md) | Architecture guide for AI agents and developers |
| [API Reference](http://localhost:8000/docs) | Interactive Swagger UI (after starting the stack) |
| [Deployment Guide](./docs/DEPLOYMENT.md) | Production deployment with Ansible |
| [CI/CD Pipeline](./.github/workflows/README.md) | Automated testing and deployment |
| [Contributing](./CONTRIBUTING.md) | Development workflow and code style |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React + TypeScript + Vite)                   │
│  ├── Zustand state management                           │
│  ├── Glassmorphism UI with dark/light themes            │
│  └── i18n (Russian/English)                             │
└────────────────────┬────────────────────────────────────┘
                     │ REST API (JSON)
┌────────────────────▼────────────────────────────────────┐
│  Backend (FastAPI + SQLAlchemy + Pydantic)              │
│  ├── Layered architecture: Router → ViewSet → Service   │
│  ├── Domain modules: users, finance, analytics          │
│  ├── JWT auth in httpOnly cookies                       │
│  └── Redis caching with scope invalidation              │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   PostgreSQL    Redis        RabbitMQ
   (data)        (cache)      (async tasks)
```

See [AGENTS.md](./AGENTS.md) for detailed architecture documentation.

## 🛠️ Development

### Running tests

```bash
# All tests
docker compose exec backend python -m pytest tests -q

# Specific module
docker compose exec backend python -m pytest tests/finance -q

# With coverage
docker compose exec backend python -m pytest --cov=src tests
```

### Database migrations

```bash
# Apply migrations
docker compose exec backend alembic upgrade head

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Rollback one migration
docker compose exec backend alembic downgrade -1
```

### Code style

```bash
# Backend: Black formatter
docker compose exec backend black --line-length 120 src/

# Frontend: TypeScript + ESLint
cd frontend && npx tsc --noEmit
cd frontend && npx eslint src/
```

## 🚢 Deployment

### Production deployment

```bash
# Build production images
docker compose -f docker-compose.prod.yml up --build -d

# Apply migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Ansible deployment

For automated deployment to remote servers, see [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md).

```bash
cd ansible
ansible-playbook -i inventory.yml deploy.yml
```

## 🔧 Configuration

### Environment variables

See [.env.example](./.env.example) for all available options.

**Critical for production:**
- `SECRET_KEY` — JWT signing (minimum 32 characters)
- `POSTGRES_PASSWORD` — Database password
- `ENVIRONMENT` — Set to `PROD` for secure cookies
- `CORS_ORIGINS` — Allowed frontend origins

## 📖 API Examples

### Authentication

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123","firstname":"John","lastname":"Doe"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=secret123"
```

### Finance

```bash
# Create account
curl -X POST http://localhost:8000/api/finance/accounts \
  -H "Cookie: access_token=..." \
  -H "Content-Type: application/json" \
  -d '{"name":"Checking","type":"checking","currency":"USD","initial_balance":1000}'

# Get transactions
curl http://localhost:8000/api/finance/transactions \
  -H "Cookie: access_token=..."
```

### Analytics

```bash
# Get summary
curl "http://localhost:8000/api/analytics/summary?start_date=2026-01-01&end_date=2026-01-31" \
  -H "Cookie: access_token=..."

# Get category breakdown
curl "http://localhost:8000/api/analytics/by-category?start_date=2026-01-01&end_date=2026-01-31" \
  -H "Cookie: access_token=..."
```

## 🤖 AI Agent Support

This repository includes comprehensive documentation for AI coding agents:

- **AGENTS.md** — Architecture, conventions, and development workflow
- **.cursorrules** — Cursor IDE configuration
- **.github/copilot-instructions.md** — GitHub Copilot instructions

AI agents can understand the codebase structure, run tests, create migrations, and implement new features following the established patterns.

## 🔒 Security

- **No localStorage**: JWT tokens stored in httpOnly cookies
- **Password hashing**: Bcrypt with work factor 12
- **Row-level security**: All queries filtered by `user_id`
- **CORS**: Restricted to configured origins
- **Rate limiting**: Ready for implementation (TODO)

**Reporting vulnerabilities:** Contact security@yourorg.com

## 📄 License

**Proprietary License** — See [LICENSE](./LICENSE) for details.

This software is confidential and may not be copied, modified, or distributed without explicit permission from the copyright holder.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) — Modern web framework
- [React](https://reactjs.org/) — UI library
- [PostgreSQL](https://www.postgresql.org/) — Database
- [Redis](https://redis.io/) — Cache and session storage
- [SQLAlchemy](https://www.sqlalchemy.org/) — ORM
- [Radix UI](https://www.radix-ui.com/) — Accessible components


<div align="center">

**Built with ❤️ for personal finance management**

[Back to top](#budgettracker)

</div>
