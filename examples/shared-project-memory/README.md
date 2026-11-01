# Shared memory across independent processes

Start Remembr, then create a project, space and separate credentials in `/explorer`. Install the repository Python SDK with its MCP extra, and install LangGraph in the environment used for `langgraph_writer.py`.

The graph writer reads `REMEMBR_URL`, `REMEMBR_SPACE_ID`, `REMEMBR_API_KEY`, `REMEMBR_DEMO_KEY` and `REMEMBR_DEMO_FINDING` from its environment. It saves a synthetic finding and prints only its memory ID. It does not call an LLM or persist LangGraph workflow state.

Use the two host configuration examples with **different** credentials to connect Claude Code and Codex. Ask the second host to recall the finding, then append a correction linked through `supersedes_id`. Close that host. In the third host, recall the correction and inspect its original source. Do not put the finding's content in the third host's prompt as a substitute for retrieval.

See [agent connections](../../docs/agent-connections.md) and [shared-memory API](../../docs/shared-project-memory.md) for permissions, retry keys, status checks and limitations. These source changes are local; an already published package does not contain them until a release is explicitly prepared and published.
