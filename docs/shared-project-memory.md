# Shared project memory

New users should follow [Start using Remembr](getting-started.md) for registration, credentials and the first SDK workflow. The server and Python project APIs are released in 0.2.1; TypeScript 0.2.1 is available from source while npm publication is pending.

Remembr's project API is separate from legacy private episodes. An upgrade creates empty project tables; it never copies private memories, adds grants to old credentials, or automatically shares an organization.

## Set up a project

Start the stack with `python scripts/local_setup.py`. Open [the explorer](http://localhost:8000/explorer) and sign in using an existing Remembr account. You can also register through `/api/v1/auth/register` as described in the quickstart.

1. Create a project, then a named memory space within it.
2. Create one principal credential per agent connection. Copy each `rmsp_` secret when it is shown; the database stores only its SHA256 hash.
3. Grant each principal read, write and/or delete access to the selected space. All default to false. A writer cannot read unless separately granted read. Corrections require both read and write. Delete is a separate permission.
4. Supply that agent's credential and the space UUID to its SDK or MCP process. Do not reuse the project owner's access token across agents.

Only the user who created a project can administer it. Only a principal's issuing user can revoke its credential or grant it access to their own project. Sharing across organizations is not supported. Principal labels are display names; authenticated authorship is the stable principal UUID.

Owner access tokens can create/list projects and spaces, issue/revoke principals and set grants. Legacy `rmbr_` keys do not authorize this API. New `rmsp_` credentials do not authorize legacy memory/session/export endpoints. Revocation and grant checks query PostgreSQL on every request, including retries; no cached response bypasses these checks. An operation already authorized and in flight may finish during revocation.

## API contract

All paths below start with `/api/v1/projects`. Responses use the existing `{data, request_id, timestamp}` envelope. Use a user bearer token for administration, or `X-API-Key: rmsp_...` for permitted agent operations. Do not combine credentials.

| Method/path | Purpose |
|---|---|
| `POST /` | Create project: `{name}` |
| `GET /` | List owned/permitted projects (up to 100) |
| `POST /principals` | Issue separate credential: `{name}`; secret returned once |
| `DELETE /principals/{principal_id}` | Revoke credential |
| `POST /{project_id}/spaces` | Create persistent space: `{name}` |
| `GET /{project_id}/spaces` | List permitted spaces (up to 100) |
| `PUT /spaces/{space_id}/grants/{principal_id}` | Replace `{can_read, can_write, can_delete}`; omitted permissions become false |
| `POST /spaces/{space_id}/memories` | Store or correct |
| `POST /spaces/{space_id}/search` | Browse/search permitted memories |
| `GET /spaces/{space_id}/memories/{id}` | Inspect memory and lineage |
| `GET /spaces/{space_id}/memories/{id}/status` | Processing and lifecycle state |
| `DELETE /spaces/{space_id}/memories/{id}` | Remove content/vector; retain revision tombstone |

Unknown and unauthorized spaces return the same 404. Invalid/revoked credentials return 401. A credential cannot discover ungranted spaces, search them or fetch their processing status.

Store payload:

```json
{
  "content": "We chose PostgreSQL for the project.",
  "idempotency_key": "design-decision-001",
  "source_ref": "docs/decisions/storage.md",
  "run_id": "research-run-1",
  "supersedes_id": null,
  "expires_at": null
}
```

Content is limited to 32,000 characters, sources to 2,000, run labels to 200 and retry keys to 160. Unknown fields, including client-supplied author IDs, are rejected. Sources and run labels are client declarations; Remembr authenticates the writer, not the truth of a source URL.

Idempotency is persistent per space, authenticated writer and key. An identical request returns its original memory; a different payload with the same key returns 409. Permission is checked before replay. Writes serialize briefly per space to protect retries and concurrent corrections. Correct by creating a new memory referencing the current memory's `supersedes_id`; the previous content is retained as superseded. A second correction of the same predecessor returns 409. The caller must refresh and resolve the disagreement explicitly.

Expiry is an optional future ISO8601 timestamp with a time zone. Active search excludes expired, superseded and deleted entries. Fetching a known nondeleted ID returns its lifecycle state, so callers can inspect old references. `include_inactive: true` browses expired/superseded history with an empty query; deleted content is excluded. Deleting a correction does not reactivate its predecessor. Deletion removes that record's content, vector, source and run label; other revisions must be deleted separately. Tombstones and backups are not claimed to be erased.

## Search and context limits

```json
{"query":"storage decision", "mode":"hybrid", "limit":10, "offset":0, "context_chars":12000}
```

`mode` is keyword, semantic or hybrid. An empty query browses recent memory. Limit is 1–100, offset 0–10,000 and context budget 1–64,000 characters. Budgets are characters, not model tokens. Results contain authenticated author, source, lifecycle state, embedding status, selected retrieval mode and score. Envelope request IDs support diagnosis.

Keyword ranking uses PostgreSQL English full-text `ts_rank_cd`; semantic ranking uses cosine similarity with the active embedding model/dimensions. Hybrid uses `0.7 * cosine + 0.3 * keyword/(1 + keyword)`. Scores are not probabilities or evidence of truth. Small scopes use exact vector search; large-project performance has not been benchmarked. Hybrid may return a semantically similar record with no keyword match. This first slice does not promise automatic deduplication or semantic contradiction resolution.

Search truncates returned content to the requested budget and reports per-result `content_truncated`, overall `truncated`, `context_chars_used`, `has_more` and `next_offset`. A character budget can return fewer rows than `limit`; follow `next_offset` rather than incrementing by the requested limit. The final page has `next_offset: null`. Inspect a specific memory to read its full original. Pagination is positional and may change while writers add new data.

Embedding generation is asynchronous. Poll the exact ID until `ready`, stop on `failed`, and use a bounded timeout. Keyword search can work before an embedding is ready. Provider failure during semantic/hybrid queries returns 503 instead of silently changing modes. Old model/dimension vectors require re-indexing after changing providers; they are not mixed into semantic scores.

Queue publication failure retains the raw memory with failed processing. There is no database outbox. This initial feature does not guarantee delivery through every Redis outage. Redis AOF is fsynced every second. Use operational backup/restore procedures before a production rollout.

## SDKs

Python SDK 0.2.1 (`python -m pip install "remembr==0.2.1"`):

```python
from remembr import RemembrClient

client = RemembrClient(api_key=agent_key)
saved = client.projects.store(space_id, "Decision: use PostgreSQL",
                              idempotency_key="decision-1", source_ref="design.md")
result = client.projects.search(space_id, "PostgreSQL", mode="keyword")
status = client.projects.status(space_id, saved["id"])
```

The corresponding async methods are `astore`, `asearch`, `aget`, `astatus` and `adelete`. These methods return dictionaries retaining source/status/ranking metadata. Existing private-memory methods remain unchanged.

TypeScript exposes `client.projects.store(spaceId, payload)`, `.search(spaceId, options)`, `.get`, `.status` and `.delete`, with typed responses. Credentials and space IDs come from the same owner setup flow.

## Explorer

The same-origin `/explorer` page provides account login or credential entry, project/space selection, browsing, ranking metadata, source/author/status inspection, history, correction, expiry and deletion. Owner connections can also issue credentials and replace grants. Every data operation uses the project REST API. The shell itself contains no memories. Credentials live only in page memory and clear on disconnect/reload; no browser storage or third-party scripts are used. Memory text is rendered as text rather than executable HTML.

Space-list responses include effective `permissions` (`can_read`, `can_write`, `can_delete`) for the authenticated connection. The explorer uses them to show available actions; the server still checks every operation. Write-only connections can save without browsing. A refresh reloads grants; removed access clears results, and revoked credentials return to the connection screen. Disconnect clears credentials, draft forms and pending requests. Space changes discard the current draft and prevent a delayed correction response from opening in another space.

Inspect/refresh retrieves complete content and processing status, including failure information. Correct fetches the full current record even when its search preview was truncated. A correction has a previous-version inspection action. History browsing requires an empty search query; expiry and supersession remain distinct from deletion.

### Repeat the browser checks

In an isolated test environment, install Playwright and its Chromium browser, start the local stack (including the configured embedding provider), then run from the repository root:

```sh
python -m pip install playwright==1.64.1
python -m playwright install chromium
python scripts/test_explorer_browser.py --url http://127.0.0.1:8000 --output ./browser-results
```

Use `--browser-executable /absolute/path/to/chromium` to reuse an installed browser. The suite creates a synthetic account and its own project, memories and principal, then deletes its memory content and revokes its credential. Account/project metadata and deletion tombstones remain. It writes a JSON result and screenshots without saving credential-bearing browser storage, HAR files or traces. Controlled response cases cover pending/failed rendering, a service error and delayed requests separately from the real storage/search/lifecycle flows. The 1 November 2026 local run passed 19 browser checks with Chromium 151.0.7922.34, including 320 px and 390 px layouts; other browser engines and physical mobile devices were not tested.

The explorer is an initial operational tool, not a hosted account/billing portal. Access follows the supplied credential; read-only actions cannot be elevated by enabling a button in the browser. Keep the service bound to localhost unless configuring an authenticated HTTPS deployment deliberately.
## Recover a failed embedding without duplicating memory

After restoring Ollama and the worker, a project owner or a principal with write
permission can call:

```http
POST /api/v1/projects/spaces/{space_id}/memories/{memory_id}/retry-embedding
Content-Type: application/json
X-API-Key: <this connection's rmsp_ credential>

{}
```

The response contains `id`, `queued` and `embedding_status`. Retrying a failed
embedding preserves its memory ID, author, content, source and correction chain.
A ready memory is a no-op. Read-only, revoked and ungranted credentials cannot
retry; expired, superseded and deleted memories are not retried. A write-only
credential receives status metadata, not another principal's memory content.

For a memory left `pending` after an interrupted process or a suspected lost
queue submission, explicitly send `{"retry_pending": true}`. First check that
the provider and worker are available. A pending job might still be running, so
this can enqueue duplicate work; completion is safe to repeat and a late failure
cannot demote an already-ready memory. This is operator-assisted recovery, not
an automatic database outbox or reconciliation service. Poll the existing
`GET .../memories/{memory_id}/status` endpoint for completion.

## Experimental compact ranking

For a nonempty hybrid search, send `"ranking": "rrf_mmr"` in the existing
space-search request to try the evaluated BM25/cosine rank fusion followed by
diversity reranking. The optional API path uses the same ranking functions as
the offline experiment. Weighted hybrid is the default.

This experimental path supports at most **200 ready memories matching the active
embedding model and dimensions**, after tenant/space, correction, expiry and
deletion filters. Larger candidate sets return 422; use weighted ranking for
those spaces. The context ceiling is 10,000 characters, and a smaller requested
budget is respected. Pagination remains bounded by the actual returned rows.
Scores describe rank positions, not probabilities. The evaluation covers the
first eight results; later pages are not a published quality result.

```json
{
  "query": "Which database decision did the team correct?",
  "mode": "hybrid",
  "ranking": "rrf_mmr",
  "limit": 8,
  "context_chars": 10000
}
```

Use a dedicated pilot space for comparisons. The current SDK/MCP defaults do
not request this option; it is available through the HTTP API. See the
[evaluation record](research/local-ranking-2026-11-10.md) for the measured scope.

