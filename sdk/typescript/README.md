# Remembr TypeScript SDK

`@remembr/sdk` is the official TypeScript client for Remembr. It lets Node and TypeScript apps create sessions, store memories, search prior context, and manage export and forget flows against a self-hosted Remembr API.

## Install

```bash
# From a Remembr 0.2.1 source checkout:
cd sdk/typescript
npm ci
npm run build
npm pack
# In your application directory:
npm install /absolute/path/to/remembr-sdk-0.2.1.tgz
```

The 0.2.1 npm publication is pending. The published 0.2.0 package supports private/session memory, but does not include `client.projects`. Follow [getting started](https://github.com/emartai/remembr/blob/main/docs/getting-started.md) to start a server, create an account and issue credentials. For shared spaces use a separately granted `rmsp_` credential and `client.projects`; the example below uses a legacy `rmbr_` private-memory key.

## Quick Start

```typescript
import { RemembrClient } from '@remembr/sdk';

async function main() {
  const client = new RemembrClient({
    apiKey: process.env.REMEMBR_API_KEY!,
    baseUrl: 'http://localhost:8000/api/v1'
  });

  const session = await client.createSession({
    user: 'demo',
    context: 'support'
  });

  const episode = await client.store({
    content: 'User prefers dark mode interface',
    role: 'user',
    sessionId: session.session_id,
    tags: ['preference', 'ui']
  });

  const deadline = Date.now() + 120_000;
  while (true) {
    const response = await fetch(
      `http://localhost:8000/api/v1/memory/${episode.episode_id}/status`,
      { headers: { 'X-API-Key': process.env.REMEMBR_API_KEY! } }
    );
    if (!response.ok) throw new Error(`Status check failed: ${response.status}`);
    const { data } = await response.json();
    if (data.embedding_status === 'ready') break;
    if (data.embedding_status === 'failed') throw new Error('Embedding failed');
    if (Date.now() >= deadline) throw new Error('Memory processing timed out');
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  const results = await client.search({
    query: 'What are the user UI preferences?',
    sessionId: session.session_id,
    limit: 5,
    searchMode: 'hybrid',
    weights: { semantic: 0.6, keyword: 0.3, recency: 0.1 }
  });

  results.results.forEach((memory) => {
    console.log(`[${memory.role}] ${memory.content} (score: ${memory.score})`);
  });
}

main();
```

## Docs

- Full docs: https://github.com/emartai/remembr/tree/main/docs
- Quick start: https://github.com/emartai/remembr#quick-start
- API reference: https://github.com/emartai/remembr/blob/main/docs/api-reference.md
