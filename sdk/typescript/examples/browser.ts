import { RemembrClient } from '../src';

async function runBrowserExample(apiKey: string): Promise<void> {
  const client = new RemembrClient({ apiKey });

  const session = await client.createSession({ source: 'browser-example' });
  await client.store({
    content: 'Hello from browser',
    role: 'user',
    sessionId: session.session_id,
    metadata: { ui: true },
  });

  const history = await client.getSessionHistory(session.session_id, { limit: 10 });
  console.log('History size:', history.length);
}

// Example usage in app code:
// runBrowserExample('<your-api-key>');

export { runBrowserExample };
