/**
 * Test script for Remembr TypeScript SDK
 */

import { RemembrClient } from './sdk/typescript/dist/index.js';

async function main() {
  console.log('='.repeat(80));
  console.log('REMEMBR TYPESCRIPT SDK TEST');
  console.log('='.repeat(80));

  // Initialize client with JWT token
  const client = new RemembrClient({
    apiKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwODY3ODhhYi0xNjc0LTRhODEtYjdkMi04MTcyNmFlYzUyNzUiLCJlbWFpbCI6Im53YW5ndW1hZW1tYW51ZWwyOUBnbWFpbC5jb20iLCJleHAiOjE3NzE5NzU0OTcsInR5cGUiOiJhY2Nlc3MifQ.k-BuPVa5oLwh_iyJr0i0pXyBtobFr6pOqrT426ypr7E',
    baseUrl: 'http://localhost:8000/api/v1',
  });

  try {
    // 1. Create a session
    console.log('\n1. Creating a session...');
    const session = await client.createSession({
      user: 'Emmanuel',
      purpose: 'TypeScript SDK Testing',
    });
    console.log(`✓ Session created: ${session.session_id}`);

    // 2. Store memories
    console.log('\n2. Storing memories...');
    const memories = [
      'The TypeScript SDK provides type-safe access to the Remembr API.',
      'TypeScript helps catch errors at compile time rather than runtime.',
      'The SDK supports async/await for clean asynchronous code.',
    ];

    for (let i = 0; i < memories.length; i++) {
      const episode = await client.store({
        content: memories[i],
        sessionId: session.session_id,
        role: 'user',
        tags: ['typescript', 'sdk'],
      });
      console.log(`  Memory ${i + 1} stored: ${episode.episode_id}`);
    }

    // 3. Search memories
    console.log('\n3. Searching memories...');
    const searchResults = await client.search({
      query: 'How does TypeScript help?',
      sessionId: session.session_id,
      limit: 5,
      mode: 'hybrid',
    });

    console.log(`Found ${searchResults.results?.length || 0} results:`);
    if (searchResults.results) {
      searchResults.results.forEach((result, i) => {
        console.log(`\n  Result ${i + 1}:`);
        console.log(`    Content: ${result.content.substring(0, 80)}...`);
        console.log(`    Score: ${result.score || 'N/A'}`);
        console.log(`    Role: ${result.role}`);
      });
    }

    // 4. Get session history
    console.log('\n4. Getting session history...');
    const episodes = await client.getSessionHistory(session.session_id, { limit: 10 });
    console.log(`Session: ${session.session_id}`);
    console.log(`Episodes: ${episodes.length}`);
    episodes.slice(0, 3).forEach((ep) => {
      console.log(`  - ${ep.role}: ${ep.content.substring(0, 50)}...`);
    });

    // 5. Create a checkpoint
    console.log('\n5. Creating a checkpoint...');
    const checkpoint = await client.checkpoint(session.session_id);
    console.log(`✓ Checkpoint created: ${checkpoint.checkpoint_id}`);
    console.log(`  Message count: ${checkpoint.message_count}`);

    // 6. List checkpoints
    console.log('\n6. Listing checkpoints...');
    const checkpoints = await client.listCheckpoints(session.session_id);
    console.log(`Total checkpoints: ${checkpoints.length}`);
    checkpoints.forEach((cp) => {
      console.log(`  - ${cp.checkpoint_id}: ${cp.message_count} messages`);
    });

    // 7. List all sessions
    console.log('\n7. Listing all sessions...');
    const sessions = await client.listSessions({ limit: 5 });
    console.log(`Total sessions: ${sessions.length}`);
    sessions.slice(0, 3).forEach((sess) => {
      console.log(`  - ${sess.session_id}: ${JSON.stringify(sess.metadata)}`);
    });

    console.log('\n' + '='.repeat(80));
    console.log('✓ TYPESCRIPT SDK TEST COMPLETED SUCCESSFULLY!');
    console.log('='.repeat(80));
  } catch (error) {
    console.error('\n❌ Error during test:');
    console.error(error);
    process.exit(1);
  }
}

main();
