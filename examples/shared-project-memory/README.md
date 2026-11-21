# Shared memory across independent processes

Start the current Remembr server, then create a project, space and separate
credentials in `/explorer`. Install the published `remembr[mcp]==0.2.2` package
or the current source SDK, and install LangGraph in the environment used for
`langgraph_writer.py`. Give all three agents read access to one demo space. Give LangGraph and Claude Code write access. Codex can use a read-only grant.

The graph writer reads `REMEMBR_URL`, `REMEMBR_SPACE_ID`, `REMEMBR_API_KEY`, `REMEMBR_DEMO_KEY` and `REMEMBR_DEMO_FINDING` from its environment. It saves a synthetic finding and prints only its memory ID. It does not call an LLM or persist LangGraph workflow state.

Use the two host configuration examples with **different** credentials to connect Claude Code and Codex. Ask the second host to recall the finding, then append a correction linked through `supersedes_id`. Close that host. In the third host, recall the correction and inspect its original source. Do not put the finding's content in the third host's prompt as a substitute for retrieval.

## LangGraph → Claude Code → Codex

Use [the connection guide](../../docs/agent-connections.md)
and the host configuration examples in this directory.

1. Install LangGraph in the Python environment running the writer. Set
   `REMEMBR_URL`, `REMEMBR_SPACE_ID` and the LangGraph principal's
   `REMEMBR_API_KEY`. Set `REMEMBR_DEMO_KEY` to a unique retry key and
   `REMEMBR_DEMO_FINDING` to a synthetic project decision.
2. From the repository root run
   `python examples/shared-project-memory/langgraph_writer.py`. It prints
   the saved memory ID.
3. In Claude Code, ask for the project decision and its source. Ask it to
   save a correction with the retrieved ID as `supersedes_id`, a new source
   reference and a new retry key. Wait for processing status `ready`.
4. Run `docker compose up -d --force-recreate server worker`. Once
   `/api/v1/ready` reports ready, open a fresh Codex session and ask for the
   decision and previous version. Check the corrected content, both IDs,
   and the source and author of each revision.

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

Both published 0.2.2 SDKs include these shared-space operations.
See [agent connections](../../docs/agent-connections.md) and
[shared-memory API](../../docs/shared-project-memory.md) for permissions, retry
keys, status checks and limitations.
