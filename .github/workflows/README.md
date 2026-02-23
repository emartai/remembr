# GitHub Actions CI/CD

## CI Workflow

The CI workflow (`.github/workflows/ci.yml`) runs automatically on:
- Every push to `main` branch
- Every pull request targeting `main` branch

### What It Does

1. **Linting**: Runs `ruff` to check code style and formatting
2. **Testing**: Runs pytest with coverage reporting
3. **Coverage Check**: Fails if coverage drops below 70%

### Services

The workflow spins up test services:
- PostgreSQL 15 (for database tests)
- Redis 7 (for cache tests)

### Skipping CI

CI is automatically skipped when only documentation files change:
- `*.md` files
- Files in `docs/` directory

To skip CI manually, add `[skip ci]` to your commit message:
```bash
git commit -m "Update README [skip ci]"
```

## Running Tests Locally

### Prerequisites

Ensure you have test services running:

```bash
# Using Docker Compose (recommended)
docker-compose -f docker-compose.test.yml up -d

# Or manually
# PostgreSQL
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15

# Redis
docker run -d -p 6379:6379 redis:7
```

### Run Tests

```bash
cd server

# Set test environment variables
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/remembr_test
export REDIS_URL=redis://localhost:6379
export SECRET_KEY=test-secret-key
export JINA_API_KEY=test-jina-key

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Coverage Requirements

- Minimum coverage: 70%
- Coverage is calculated for the `app/` directory only
- Test files are excluded from coverage

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Check Python version (CI uses 3.11)
- Ensure test services are running
- Verify environment variables are set

### Coverage Below 70%

Add more tests to increase coverage:
```bash
# See which lines are not covered
pytest --cov=app --cov-report=term-missing
```

### Linting Errors

Fix with ruff:
```bash
# Auto-fix issues
ruff check server/app --fix

# Format code
ruff format server/app
```
