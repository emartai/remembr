# Railway Quick Start

Deploy Remembr to Railway in 5 minutes.

## Step 1: Prepare External Services

### Supabase (Database)

1. Go to https://supabase.com → New Project
2. Save the connection string from Settings → Database
3. Enable pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### Upstash (Redis)

1. Go to https://console.upstash.com → Create Database
2. Copy the Redis URL from the dashboard

### Jina AI (Embeddings)

1. Go to https://jina.ai → Sign up
2. Get your API key from the dashboard

## Step 2: Deploy to Railway

### Option A: Deploy Button (Fastest)

Click this button to deploy:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/yourusername/remembr)

### Option B: Manual Deployment

1. Go to https://railway.app/new
2. Select "Deploy from GitHub repo"
3. Choose the `remembr` repository
4. Railway auto-detects `railway.toml`

## Step 3: Set Environment Variables

In Railway project settings, add:

```bash
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
REDIS_URL=rediss://default:[PASSWORD]@[ENDPOINT]:6379
SECRET_KEY=<run: openssl rand -hex 32>
JINA_API_KEY=<your-jina-api-key>
ENVIRONMENT=production
LOG_LEVEL=INFO
```

Optional:
```bash
SENTRY_DSN=<your-sentry-dsn>
```

## Step 4: Verify Deployment

Once deployed, test the health endpoint:

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

## Step 5: Run Database Migrations

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link project
railway login
railway link

# Run migrations
railway run alembic upgrade head
```

## Done!

Your API is now live at: `https://your-app.up.railway.app`

## Next Steps

- Set up custom domain in Railway settings
- Configure Sentry for error tracking
- Set up staging environment
- Enable auto-deployments from GitHub

## Troubleshooting

**Deployment fails**: Check Railway logs for missing environment variables

**Health check fails**: Ensure all required env vars are set

**Database connection error**: Verify DATABASE_URL format and Supabase is running

For detailed instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)
