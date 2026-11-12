# BudgetTracker — Agents & Architecture Guide

## Project Overview

**BudgetTracker** is a free, source-available personal finance management system (Apache 2.0 + Commons Clause) with multi-currency support and advanced analytics. Built with a modern stack: FastAPI backend, React frontend, PostgreSQL, and Redis.

## Architecture

### Layered Architecture (Backend)

Each domain module follows a consistent layered pattern:

```
┌─────────────────────────────────────────────────┐
│  Router (HTTP layer)                            │
│  - FastAPI endpoints                            │
│  - Request/response models                      │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  ViewSet (orchestration)                        │
│  - Business logic coordination                  │
│  - Permission checks                            │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  Service (business logic)                       │
│  - Domain rules                                 │
│  - Transaction management                       │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  DAO (data access)                              │
│  - Database queries                             │
│  - SQLAlchemy models                            │
└─────────────────────────────────────────────────┘
```

### Domain Modules

1. **`src/users/`** — Authentication, user management, email verification
2. **`src/finance/`** — Core financial operations (accounts, categories, transactions)
3. **`src/analytics/`** — Reporting and analytics (read-only, aggregates data)
4. **`src/notifications/`** — Email/SMS notifications (extensible)

### Key Design Decisions

- **Isolation by ownership**: All financial data filtered by `user_id` — cross-user access returns 404
- **Base currency normalization**: All analytics calculated in user's base currency with personal exchange rates
- **Cache strategy**: Redis caching with scope-based invalidation (analytics, categories)
- **Fully free**: no paid tiers or limits, all features available to every user
- **JWT in httpOnly cookies**: No localStorage tokens, automatic session restoration

## Frontend Structure

```
frontend/src/
├── app/              # Entry point, routing, session gate
├── api/              # API client, DTOs, mappers
├── store/            # Zustand stores (auth, finance)
├── __pages__/        # Page components
├── components/       # Reusable UI components
└── __shared__/       # Shared types, utilities
```

### State Management

- **Auth store**: Session state, JWT in httpOnly cookies
- **Finance store**: Accounts, categories, transactions (cached, invalidated on mutations)
- **Query hooks**: `useApiQuery` for reactive data fetching

## Features

- Unlimited accounts
- Multi-currency support with personal rates
- Extended analytics:
  - Period comparison with trends
  - Category breakdowns (income/expense)
  - Account activity insights
  - Data export capabilities

## API Endpoints

### Authentication
- `POST /api/auth/register` — Create account (sends verification email)
- `POST /api/auth/login` — Authenticate (returns JWT)
- `POST /api/auth/verify-email` — Confirm email with auto-login
- `POST /api/auth/logout` — Invalidate session

### Finance
- `GET/POST /api/finance/accounts` — Account CRUD
- `GET/POST /api/finance/categories` — Category tree with caching
- `GET/POST /api/finance/transactions` — Transaction management
- `GET /api/finance/currencies` — Currency catalog
- `PUT/DELETE /api/finance/currencies/{code}/rate` — Personal rates

### Analytics
- `GET /api/analytics/summary` — Period totals with comparison
- `GET /api/analytics/timeseries` — Balance/cashflow series
- `GET /api/analytics/by-category` — Category breakdowns
- `GET /api/analytics/by-account` — Account activity
- `GET /api/analytics/matrix` — Category × month report

## Development Workflow

### Running Locally

```bash
# Start all services
docker compose up --build

# Access points
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

### Database Migrations

```bash
# Apply migrations
docker compose exec backend alembic upgrade head

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Rollback one migration
docker compose exec backend alembic downgrade -1
```

### Testing

```bash
# Run all tests
docker compose exec backend python -m pytest tests -q

# Run specific module
docker compose exec backend python -m pytest tests/finance -q

# Run with coverage
docker compose exec backend python -m pytest --cov=src tests
```

### Demo Data

```bash
# Seed demo user with 6 accounts, 25 categories, 387 transactions
docker compose exec backend python -m scripts.seed_demo

# Reset and reseed
docker compose exec backend python -m scripts.seed_demo --reset
```

Default credentials printed by script or check `frontend/src/__shared__/constants/demo.ts`.

## Key Implementation Details

### Currency Conversion

All monetary calculations use the formula:
```python
amount_base = amount * rate_to_base / base_rate
```

Where:
- `rate_to_base` — personal rate if set, otherwise catalog rate
- `base_rate` — rate of user's base currency (e.g., BYN/USD)

### Category Caching

Categories cached in Redis with TTL 3600s. Invalidation on:
- Create/update/delete category
- Import/seed operations

Cache key pattern: `categories:{user_id}:{type}:{scope}`

### Transaction Exclusion Logic

Transfers excluded from:
- Income/expense totals
- Category breakdowns
- Transaction counts

But included in:
- Balance calculations
- Balance series

## Deployment

### Production Build

```bash
# Set environment variables
cp .env.example .env
# Edit: SECRET_KEY, POSTGRES_PASSWORD, ENVIRONMENT=PROD

# Build and deploy
docker compose -f docker-compose.prod.yml up --build -d
```

### Environment Variables

Critical for production:
- `SECRET_KEY` — JWT signing (minimum 32 chars)
- `POSTGRES_PASSWORD` — Database password
- `ENVIRONMENT` — Set to `PROD`
- `CORS_ORIGINS` — Allowed frontend origins

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port conflicts | Override in `.env`: `BACKEND_HOST_PORT`, `FRONTEND_HOST_PORT` |
| Stale database | `docker compose down -v` (WARNING: deletes all data) |
| Migration errors | `docker compose exec backend alembic current` to check state |
| Frontend API errors | Check `VITE_API_PROXY_TARGET` and backend health |
| Cache issues | Redis restart or scope invalidation via API |

## Contributing

### Adding a New Domain Module

1. Create directory: `backend/src/{module}/`
2. Implement layers: `models.py`, `schemas.py`, `dao.py`, `service.py`, `viewsets.py`, `router.py`
3. Register router in `backend/src/main.py`
4. Add permissions in `permissions.py`
5. Write tests in `backend/tests/{module}/`
6. Add API client in `frontend/src/api/{module}.ts`
7. Add store if needed: `frontend/src/store/{module}.ts`

### Code Style

- **Backend**: Black formatter, mypy type checking, pytest for tests
- **Frontend**: ESLint, Prettier, TypeScript strict mode
- **Commits**: Conventional commits (`feat:`, `fix:`, `docs:`)

## Performance Considerations

- **Analytics queries**: Aggregated at database level, cached in Redis
- **Category tree**: Cached with scope invalidation, not re-fetched on every page
- **Transaction list**: Paginated (default 50 items), server-side filtering
- **Balance calculations**: Computed once per period, not per transaction

## Security

- **JWT**: httpOnly cookies, short expiration (15min access, 7d refresh)
- **Passwords**: Bcrypt hashing with work factor 12
- **Ownership**: All queries filtered by `user_id`, cross-user access returns 404
- **CORS**: Restricted to configured origins
- **Rate limiting**: Not implemented yet (TODO)

## Future Enhancements

- Bank statement import (CSV/OFX)
- Recurring transaction templates
- Budget limits per category
- Multi-user households
- Mobile app (React Native)
- Open banking API integration
