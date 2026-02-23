# Deployment Guide

This guide covers deploying Remembr to Railway with Supabase (PostgreSQL + pgvector) and Upstash (Redis).

## Prerequisites

- GitHub account with repository access
- Railway account (https://railway.app)
- Supabase account (https://supabase.com)
- Upstash account (https://upstash.com)
- Jina AI API key (https://jina.ai)

## Architecture

```
Railway (API Server)
├── Supabase (PostgreSQL + pgvector)
├── Upstash (Redis)
└── Sentry (Error Tracking - Optional)
```

## 1. Set Up Supabase Database

### Create Project

1. Go to https://supabase.com/dashboard
2. Click "New Project"
3. Choose organization and set:
   - Name: `remembr-production` (or `remembr-staging`)
   - Database Password: Generate a strong password
   - Region: Choose closest to your users
4. Wait for project to be provisioned (~2 minutes)

### Enable pgvector Extension

1. In your Supabase project, go to "SQL Editor"
2. Run this SQL command:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
3. Verify with:
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Get Connection String

1. Go to "Project Settings" → "Database"
2. Find "Connection string" section
3. Copy the "URI" format (not "Transaction" pooler)
4. It looks like:
```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

## 2. Set Up Upstash Redis

### Create Database

1. Go to https://console.upstash.com
2. Click "Create Database"
3. Configure:
   - Name: `remembr-production` (or `remembr-staging`)
   - Type: Regional (or Global for multi-region)
   - Region: Choose closest to your Railway deployment
   - TLS: Enabled (recommended)
4. Click "Create"

### Get Connection String

1. In your database dashboard, find "REST API" section
2. Copy the "Redis URL" (starts with `redis://` or `rediss://`)
3. Format:
```
rediss://default:[PASSWORD]@[ENDPOINT]:6379
```

## 3. Deploy to Railway

### Create Railway Project

1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub account
5. Select the `remembr` repository
6. Railway will detect the `railway.toml` configuration

### Configure Environment Variables

In Railway project settings, add these environment variables:

#### Required Variables

```bash
# Database (from Supabase)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Redis (from Upstash)
REDIS_URL=rediss://default:[PASSWORD]@[ENDPOINT]:6379

# JWT Authentication
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Environment
ENVIRONMENT=production

# Jina AI Embeddings
JINA_API_KEY=<your-jina-api-key>
JINA_EMBEDDING_MODEL=jina-embeddings-v3

# Logging
LOG_LEVEL=INFO
```

#### Optional Variables

```bash
# Sentry (Error Tracking)
SENTRY_DSN=<your-sentry-dsn>
```

### Generate SECRET_KEY

Run locally:
```bash
openssl rand -hex 32
```

Or use Python:
```python
import secrets
print(secrets.token_hex(32))
```

### Deploy

1. Railway will automatically deploy after environment variables are set
2. Monitor deployment logs in Railway dashboard
3. Once deployed, Railway provides a public URL like:
   ```
   https://remembr-production.up.railway.app
   ```

### Verify Deployment

Test the health endpoint:
```bash
curl https://your-app.up.railway.app/api/v1/health
```

Expected response:
```json
{
  "status": "ok",
  "environment": "production",
  "version": "0.1.0"
}
```

## 4. Set Up Custom Domain (Optional)

### In Railway

1. Go to your service settings
2. Click "Settings" → "Domains"
3. Click "Generate Domain" or "Custom Domain"
4. For custom domain:
   - Enter your domain (e.g., `api.remembr.com`)
   - Add the CNAME record to your DNS provider
   - Wait for DNS propagation (~5-60 minutes)

### Update CORS Settings

If using a custom domain, update CORS in `server/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Update this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 5. Staging vs Production Setup

### Recommended Approach

Create two separate Railway projects:

#### Staging Environment

- **Project Name**: `remembr-staging`
- **Branch**: Deploy from `develop` or `staging` branch
- **Database**: Separate Supabase project (`remembr-staging`)
- **Redis**: Separate Upstash database (`remembr-staging`)
- **Environment Variable**: `ENVIRONMENT=staging`
- **Purpose**: Testing before production deployment

#### Production Environment

- **Project Name**: `remembr-production`
- **Branch**: Deploy from `main` branch only
- **Database**: Production Supabase project (`remembr-production`)
- **Redis**: Production Upstash database (`remembr-production`)
- **Environment Variable**: `ENVIRONMENT=production`
- **Purpose**: Live user-facing API

### Branch-Based Deployment

Configure in Railway:
1. Go to project settings
2. Under "Source" → "Branch"
3. Set staging to deploy from `develop`
4. Set production to deploy from `main`

## 6. Database Migrations

### Run Migrations on Railway

After deployment, run Alembic migrations:

1. In Railway dashboard, go to your service
2. Click "Settings" → "Variables"
3. Ensure `DATABASE_URL` is set
4. Use Railway CLI or add a migration job:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Run migrations
railway run alembic upgrade head
```

Or add a one-time deployment command in Railway:
```bash
alembic upgrade head && uvicorn server.app.main:app --host 0.0.0.0 --port $PORT
```

## 7. Monitoring and Logs

### Railway Logs

- View real-time logs in Railway dashboard
- Logs are structured JSON (from loguru)
- Filter by log level, request ID, etc.

### Sentry Integration

If `SENTRY_DSN` is configured:
1. All errors automatically reported to Sentry
2. View errors at https://sentry.io
3. Get alerts for new errors
4. Track error frequency and impact

### Health Checks

Railway automatically monitors `/api/v1/health`:
- Checks every 30 seconds
- Restarts service if unhealthy
- Configurable in `railway.toml`

## 8. Scaling

### Vertical Scaling

In Railway:
1. Go to service settings
2. Adjust resources (CPU, Memory)
3. Railway automatically restarts with new resources

### Horizontal Scaling

For high traffic:
1. Enable multiple replicas in Railway
2. Railway handles load balancing automatically
3. Ensure your app is stateless (uses Redis for sessions)

## 9. Rollback

### Via Railway Dashboard

1. Go to "Deployments"
2. Find previous successful deployment
3. Click "Redeploy"

### Via Git

```bash
# Revert to previous commit
git revert HEAD
git push origin main

# Railway auto-deploys the reverted version
```

## 10. Cost Estimation

### Staging Environment

- Railway: $5-10/month (Hobby plan)
- Supabase: Free tier (up to 500MB database)
- Upstash: Free tier (10K commands/day)
- **Total**: ~$5-10/month

### Production Environment

- Railway: $20-50/month (depends on usage)
- Supabase: $25/month (Pro plan with more resources)
- Upstash: $10-30/month (depends on usage)
- Sentry: Free tier or $26/month (Team plan)
- **Total**: ~$55-130/month

## Troubleshooting

### Deployment Fails

Check Railway logs for errors:
- Missing environment variables
- Database connection issues
- Port binding problems

### Database Connection Errors

- Verify `DATABASE_URL` is correct
- Check Supabase project is running
- Ensure IP allowlist includes Railway (usually not needed)
- Test connection locally with same URL

### Redis Connection Errors

- Verify `REDIS_URL` format is correct
- Check Upstash database is active
- Ensure TLS is enabled if using `rediss://`

### Health Check Failing

- Verify `/api/v1/health` endpoint works locally
- Check if app is binding to `0.0.0.0` not `127.0.0.1`
- Ensure `$PORT` environment variable is used

## Security Checklist

- [ ] `SECRET_KEY` is randomly generated and unique per environment
- [ ] Database passwords are strong and rotated regularly
- [ ] `ENVIRONMENT=production` is set in production
- [ ] API documentation (`/docs`) is disabled in production
- [ ] CORS origins are restricted to your domains
- [ ] Sentry DSN is configured for error tracking
- [ ] All secrets are stored in Railway environment variables, not in code
- [ ] `.env` files are in `.gitignore`
