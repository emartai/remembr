# Self-Hosted Setup

Run Remembr server locally while using hosted Supabase (Postgres + pgvector) and Upstash (Redis).

## 1) Prerequisites

- Python 3.11+
- Access to Supabase Postgres connection string (with `pgvector` enabled)
- Access to Upstash Redis URL
- Jina API key for embeddings

## 2) Install server

```bash
cd server
pip install -r requirements.txt
```

## 3) Environment variables

Create `.env` in `server/` (or export vars directly).

| Variable | Required | Description | Example |
|---|---:|---|---|
| `DATABASE_URL` | ✅ | Async SQLAlchemy DB URL | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | ✅ | Redis URL (Upstash works) | `rediss://default:pass@...upstash.io:6379` |
| `SECRET_KEY` | ✅ | JWT signing key | `openssl rand -hex 32` output |
| `JINA_API_KEY` | ✅ | Embeddings provider key | `jina_xxx` |
| `ENVIRONMENT` | ✅ | `local` / `staging` / `production` | `local` |
| `LOG_LEVEL` | ✅ | `DEBUG`, `INFO`, etc. | `INFO` |
| `API_V1_PREFIX` (`api_v1_prefix`) | optional | API prefix | `/api/v1` |
| `HOST` | optional | Bind host | `0.0.0.0` |
| `PORT` | optional | Bind port | `8000` |
| `CORS_ORIGINS` / `cors_origins` | optional | Allowed origins (JSON list) | `["http://localhost:3000"]` |
| `RATE_LIMIT_DEFAULT_PER_MINUTE` | optional | Default API limit per key/token | `100` |
| `RATE_LIMIT_SEARCH_PER_MINUTE` | optional | Search endpoint limit per key/token | `30` |
| `DB_POOL_SIZE` | optional | SQLAlchemy async pool size | `10` |
| `DB_MAX_OVERFLOW` | optional | SQLAlchemy overflow connections | `20` |
| `DB_POOL_TIMEOUT` | optional | Pool wait timeout seconds | `30` |
| `DB_POOL_RECYCLE` | optional | Pool recycle seconds | `1800` |
| `SENTRY_DSN` | optional | Error monitoring DSN | `https://...` |
| `UPSTASH_REDIS_REST_URL` | optional | Alternate Upstash config | from Upstash console |
| `UPSTASH_REDIS_REST_TOKEN` | optional | Alternate Upstash config | from Upstash console |

## 4) Run migrations

```bash
cd server
alembic upgrade head
```

Redis pool max connections is set to `20` in `server/app/db/redis.py` (verified production default).

## 5) Start API

```bash
cd server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/api/v1/health
```

## Common setup issues

### 1) `pgvector` errors
- Symptom: extension/operator errors in search queries.
- Fix: ensure Supabase project has `vector` extension enabled and migration history is current.

### 2) Redis TLS/connectivity failures
- Symptom: cannot connect to Upstash.
- Fix: use `rediss://` URL and verify firewall/network egress.

### 3) Auth token failures (`401`)
- Symptom: valid login but API returns unauthorized.
- Fix: verify `SECRET_KEY` is stable across processes and tokens are sent as `Authorization: Bearer <token>`.

### 4) Embeddings/search degradation
- Symptom: poor semantic matches or embedding errors.
- Fix: validate `JINA_API_KEY`, quotas, and outbound connectivity to Jina APIs.

### 5) Migration drift
- Symptom: runtime schema mismatch.
- Fix:

```bash
cd server
alembic current
alembic history --verbose
alembic upgrade head
```
