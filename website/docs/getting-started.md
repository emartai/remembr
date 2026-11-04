# Start using Remembr

Remembr 0.2.1 is released on GitHub and PyPI. The TypeScript 0.2.1 source is available, but its npm publication is pending. Remembr currently runs on your own machine or server; a hosted Remembr Cloud service is planned and is not yet available.

## 1. Start the memory server

You need Python 3.11+, Docker Compose v2, a running Linux container engine and internet access for the first image/model downloads. Installing the SDK alone does not start the server.

```sh
git clone --branch v0.2.1 https://github.com/emartai/remembr.git
cd remembr
python scripts/local_setup.py
python scripts/smoke_test.py
```

Use `python3` if that is your Python command. Initial downloads can take several minutes. Open `http://localhost:8000/api/v1/ready` and confirm `status` is `ready`. The smoke test checks a synthetic private-memory workflow; its accounts are not your dashboard login. See [local setup](local-setup.md) for ports, model choices and troubleshooting.

## 2. Create your account

Open `http://localhost:8000/docs`. Expand **POST /api/v1/auth/register**, click **Try it out**, and enter your own email, a password and an organization name:

```json
{"email":"you@example.com","password":"replace-with-your-own-password","org_name":"My workspace"}
```

Execute once. A successful response is HTTP 201. If that email already exists, sign in instead of registering again. Keep the returned tokens private. Open `http://localhost:8000/explorer` and sign in with the same email and password.

## 3. Choose the memory you need

| Use case | Credential | Client API |
| --- | --- | --- |
| Several agents sharing project decisions across runs | One `rmsp_` principal credential per agent, explicitly granted a space | `client.projects` or the MCP bridge |
| An application's private conversations and session context | A legacy `rmbr_` API key created by the account owner | Session and memory methods; existing framework adapters |

These APIs have separate authorization. Creating a project does not share existing private conversations. A session ID is not a shared-space ID. For shared agent memory, continue below.

## 4. Connect your first agent

In the explorer, create a project, create a space inside it, and create an agent connection/principal. Copy its credential when shown; it cannot be recovered later. Grant that principal **read** and **write** access to the space. Copy the space UUID. Create another principal for each additional agent; use read-only access where appropriate.

Install the published Python SDK in your application's virtual environment:

```sh
python -m pip install "remembr==0.2.1"
```

Set `REMEMBR_API_KEY` to the agent's `rmsp_` credential and `REMEMBR_SPACE_ID` to the space UUID in the environment of your application. The example reads both without hardcoding them:

```python
import os
import time

from remembr import RemembrClient

client = RemembrClient(
    api_key=os.environ["REMEMBR_API_KEY"],
    base_url=os.getenv("REMEMBR_URL", "http://localhost:8000").rstrip("/") + "/api/v1",
)
space = os.environ["REMEMBR_SPACE_ID"]
saved = client.projects.store(
    space,
    "The project uses PostgreSQL for persistent storage.",
    source_ref="first-agent-demo",
    idempotency_key="first-agent-storage-decision-v1",
)
deadline = time.monotonic() + 120
while True:
    status = client.projects.status(space, saved["id"])
    if status["embedding_status"] == "ready":
        break
    if status["embedding_status"] == "failed":
        raise RuntimeError("Embedding failed; inspect the worker and provider")
    if time.monotonic() >= deadline:
        raise TimeoutError("Memory processing timed out")
    time.sleep(2)
print(client.projects.search(space, "Which database does the project use?", mode="hybrid"))
```

Return to the explorer to inspect the content, source, authenticated author and processing status. Another agent with its own read grant to the same space can retrieve this decision. Corrections create a new revision; they do not silently overwrite the original.

## 5. Connect an MCP client or TypeScript app

For MCP-capable clients, install the published extra and follow [agent connections](agent-connections.md):

```sh
python -m pip install "remembr[mcp]==0.2.1"
```

The client launches `remembr-mcp` or `python -m remembr.mcp`. Supply `REMEMBR_URL=http://localhost:8000`, the space UUID and that client's own principal credential. The bridge exposes store, search, get and processing-status tools. Installing it does not automatically enable memory inside a host.

TypeScript shared-space APIs require the 0.2.1 source package while npm publication is pending. From the repository root:

```sh
cd sdk/typescript
npm ci
npm run build
npm pack
```

In your application directory, install the resulting archive with `npm install /absolute/path/to/remembr-sdk-0.2.1.tgz`. The older npm 0.2.0 package does not include `client.projects`. See [shared project memory](shared-project-memory.md) for its TypeScript methods and permission rules.

## Private/session memory instead

Use the registration/login access token to create a key through **POST /api/v1/api-keys** in `/docs`, with a body such as `{"name":"my-private-app"}`. Authorize the API request with that owner's bearer token. Copy the returned `rmbr_` secret and pass it to `RemembrClient`; use the session/store/search examples in the SDK guides. Wait for each memory's processing status before semantic retrieval. These keys cannot access shared spaces.

## Stop and resume

Run `docker compose --profile ollama down` to stop the local stack while retaining its data and downloaded model. Run `python scripts/local_setup.py` to resume and verify readiness. Do not delete the volumes unless you intend to erase that installation's data.

See [verification](verification.md) and [compatibility](compatibility.md) for tested behavior and limits.
