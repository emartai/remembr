# Security Hardening Checklist

This checklist captures the MVP pre-launch hardening steps and links to automated validations where possible.

## 1) Secrets hygiene

- [x] No secrets committed in source.
- [x] Enforced via pre-commit scanning and CI checks.

Recommended local run:

```bash
pre-commit run --all-files
```

## 2) Protected endpoint auth verification

- [x] Automated test ensures protected `/api/v1` routes reject unauthenticated calls.
- [x] Public exceptions are explicitly documented (`/health`, `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`).

Run:

```bash
cd server
pytest tests/test_security_authz.py -v
```

## 3) RLS verification

- [x] RLS behavior is covered by existing tests (org-scope isolation and context propagation).

Run:

```bash
cd server
pytest tests/test_rls.py -v
pytest tests/test_context_integration.py -v
```

## 4) PII logging audit

- [x] Log statements avoid plaintext secrets (API keys, passwords, tokens).
- [x] Structured logging via Loguru enabled; avoid logging user payload bodies directly.

Recommended periodic audit:

```bash
rg "logger\.(debug|info|warning|error|exception)" server/app -n
```

## 5) CORS hardening

- [x] CORS origins are configurable from environment (`cors_origins`) instead of fixed code constants.
- [x] Local default remains permissive only when explicit origins are not set.

## 6) Rate limiting

- [x] Redis-backed rate limiting is enabled via SlowAPI.
- [x] Default global limit per API key/token is configurable.
- [x] Memory search has a stricter dedicated limit.
- [x] `429` responses include rate-limit headers and retry guidance.
- [x] Health endpoint is exempt.

## 7) Connection pool controls

- [x] Postgres async pool tuned for production defaults.
- [x] Redis pool `max_connections=20` is configured.
- [x] Pool exhaustion timeout warnings are logged.
