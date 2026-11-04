# Contributing to BudgetTracker

Thank you for your interest in contributing to BudgetTracker. This document outlines the development workflow and code conventions.

> **Note:** This is a proprietary project. By contributing, you agree that your contributions become the property of the copyright holder.

## Development Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.13+ (for local backend development)
- Node.js 20+ (for local frontend development)

### Getting Started

```bash
# Clone the repository
git clone https://github.com/yourorg/budgettracker.git
cd budgettracker

# Copy environment file
cp .env.example .env

# Start the stack
docker compose up --build

# Seed demo data
docker compose exec backend python -m scripts.seed_demo
```

## Architecture

The project follows a **layered architecture** for both backend and frontend:

### Backend Layers

```
Router → ViewSet → Service → DAO → Model
```

- **Router** (`router.py`): HTTP endpoints, request/response schemas
- **ViewSet** (`viewsets.py`): Orchestration, permission checks
- **Service** (`service.py`): Business logic, domain rules
- **DAO** (`dao.py`): Database queries, inherits from `BaseDAO`
- **Model** (`models.py`): SQLAlchemy models

### Frontend Structure

```
src/
├── app/              # Routing, session gate
├── api/              # API client, DTOs, mappers
├── store/            # Zustand stores
├── __pages__/        # Page components
├── components/       # Reusable UI
└── __shared__/       # Types, utilities
```

## Code Style

### Backend (Python)

- **Formatter**: Black (`--line-length 120`)
- **Comments**: English only
- **Docstrings**: English, triple-quoted
- **Type hints**: Required for all function signatures
- **Imports**: Sorted alphabetically, grouped (stdlib → third-party → local)

```bash
# Format code
docker compose exec backend black --line-length 120 src/

# Type check
docker compose exec backend mypy src/

# Run tests
docker compose exec backend python -m pytest tests -q
```

### Frontend (TypeScript)

- **Formatter**: Prettier (via ESLint)
- **Comments**: English only
- **Strict mode**: Enabled
- **Component naming**: PascalCase
- **File naming**: camelCase for utilities, PascalCase for components

```bash
# Type check
cd frontend && npx tsc --noEmit

# Lint
cd frontend && npx eslint src/
```

## Adding a New Feature

### 1. Backend

```bash
# Create domain module
mkdir -p backend/src/{module}

# Implement layers
touch backend/src/{module}/__init__.py
touch backend/src/{module}/models.py
touch backend/src/{module}/schemas.py
touch backend/src/{module}/dao.py
touch backend/src/{module}/service.py
touch backend/src/{module}/viewsets.py
touch backend/src/{module}/router.py

# Register router in backend/src/main.py
# Write tests in backend/tests/{module}/
```

### 2. Frontend

```bash
# Create API client
touch frontend/src/api/{module}.ts

# Add types
# Edit frontend/src/api/types.ts

# Create page (if needed)
mkdir -p frontend/src/__pages__/{Module}
touch frontend/src/__pages__/{Module}/index.tsx

# Add route in frontend/src/app/main.tsx
# Add translations in frontend/src/i18n/locales/{ru,en}.ts
```

### 3. Database Migration

```bash
# Create migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Apply migration
docker compose exec backend alembic upgrade head

# Test rollback
docker compose exec backend alembic downgrade -1
docker compose exec backend alembic upgrade head
```

## Testing

### Backend Tests

```bash
# All tests
docker compose exec backend python -m pytest tests -q

# Specific module
docker compose exec backend python -m pytest tests/{module} -q

# With coverage
docker compose exec backend python -m pytest --cov=src tests

# Verbose output
docker compose exec backend python -m pytest tests -v
```

### Test Structure

- `tests/conftest.py` — Shared fixtures
- `tests/{module}/test_{module}.py` — Module-specific tests
- Use `verified_user_client` fixture for authenticated requests
- Use `session_maker` fixture for direct database access

### Frontend Tests

```bash
# Type check (ensures no TypeScript errors)
cd frontend && npx tsc --noEmit
```

## Git Workflow

### Branch Naming

- `feat/short-description` — New features
- `fix/short-description` — Bug fixes
- `refactor/short-description` — Code refactoring
- `docs/short-description` — Documentation updates

### Commit Messages

Use conventional commits:

```
feat: add multi-currency support
fix: correct balance calculation for transfers
refactor: extract currency conversion logic
docs: update API documentation
test: add tests for admin subscription grants
```

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Write/update tests
4. Run the test suite
5. Update documentation
6. Submit a pull request

## Key Patterns

### Authentication

JWT tokens in httpOnly cookies. Never use localStorage for tokens.

```python
# Backend: get current user
from src.users.dependencies import get_current_user

@router.get("/endpoint")
async def endpoint(user: User = Depends(get_current_user)):
    ...
```

### Database Queries

Always filter by `user_id` for data isolation:

```python
# DAO pattern
@classmethod
async def find_all_for_user(cls, session: AsyncSession, user_id: UUID):
    stmt = select(cls.model).where(cls.model.user_id == user_id)
    return (await session.execute(stmt)).scalars().all()
```

### Currency Conversion

Use the base currency normalization formula:

```python
amount_base = amount * rate_to_base / base_rate
```

### Caching

Categories cached in Redis with scope-based invalidation:

```python
cache_key = f"categories:{user_id}:{type}:{scope}"
```

## Environment Variables

See `.env.example` for all available options. Critical for production:

- `SECRET_KEY` — JWT signing (min 32 chars)
- `POSTGRES_PASSWORD` — Database password
- `ENVIRONMENT` — Set to `PROD` for secure cookies

## Getting Help

- **Architecture questions**: See `AGENTS.md`
- **API documentation**: http://localhost:8000/docs (after starting the stack)
- **Issues**: Use GitHub Issues (private repository)

---

Thank you for contributing to BudgetTracker!
