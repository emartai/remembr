# Shared memory across independent processes

Start the current Remembr server, then create a project, space and separate
credentials in `/explorer`. Install the published `remembr[mcp]==0.2.1` package
or the current source SDK, and install LangGraph in the environment used for
`langgraph_writer.py`. Each agent needs read and write grants on the same
dedicated demo space.

The graph writer reads `REMEMBR_URL`, `REMEMBR_SPACE_ID`, `REMEMBR_API_KEY`, `REMEMBR_DEMO_KEY` and `REMEMBR_DEMO_FINDING` from its environment. It saves a synthetic finding and prints only its memory ID. It does not call an LLM or persist LangGraph workflow state.

Use the two host configuration examples with **different** credentials to connect Claude Code and Codex. Ask the second host to recall the finding, then append a correction linked through `supersedes_id`. Close that host. In the third host, recall the correction and inspect its original source. Do not put the finding's content in the third host's prompt as a substitute for retrieval.

## A two-agent correction demo

1. Connect two MCP hosts with different principal credentials and the same
   space UUID, following the example configuration files.
2. In the first host, ask it to store: "The demo service stores its data in
   PostgreSQL." Set `source_ref` to `demo-design-v1`, use a unique idempotency
   key, and wait for processing status `ready`. Record the returned memory ID.
3. In the second host, ask which database the demo service uses. Check that the
   retrieved memory identifies the first agent and `demo-design-v1`.
4. Ask that second host to save "The demo service stores its data in PostgreSQL
   with pgvector." Supply the original ID as `supersedes_id`, source
   `demo-design-v2`, and a new idempotency key. Wait for `ready`.
5. In the first host, ask the original database question again. Check that the
   result contains the correction and the second agent's authenticated author.
   Use the original memory ID to inspect the prior revision.
6. Stop the local server and worker with `docker compose stop server worker`,
   then start them with `docker compose up -d server worker`. Once readiness
   succeeds, open a fresh host session and repeat the question. Preserve the
   database volumes.
7. In the explorer, revoke the second connection. Confirm it loses access and
   that the first still retrieves the correction.

Record actual tool outputs when making a demo video. Agent prose alone does
not prove retrieval. Stop the local stack when finished and preserve volumes
if you want to inspect the example again.

The published Python SDK includes these shared-space operations. The current
0.2.2 candidate also prepares the TypeScript package for publication.
See [agent connections](../../docs/agent-connections.md) and
[shared-memory API](../../docs/shared-project-memory.md) for permissions, retry
keys, status checks and limitations.
