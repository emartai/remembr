# Concepts

## Memory scoping

Remembr applies strict scope boundaries so data visibility follows org/team/user/agent context.

```text
Organization (org_id)
└── Team (team_id)
    └── User (user_id)
        └── Agent (agent_id)
            └── Session (session_id)
                ├── Short-term window (Redis + checkpointing)
                └── Episodic memories (Postgres/pgvector)
```

### Scope rules
- Reads and writes are resolved from request auth context.
- Agent-scoped keys should not read sibling-agent private memories.
- Org-level keys can perform compliance operations (for example `DELETE /memory/user/{user_id}`).

## Memory layers

### 1) Short-term memory
- Optimized conversation window for immediate context.
- Backed by Redis cache behavior + server-side token accounting.
- Supports checkpoints and restore.

### 2) Episodic memory
- Durable long-term storage in Postgres.
- Indexed with vectors (`pgvector`) + metadata/tags.
- Queried via semantic/hybrid/filter pathways.

## Hybrid search (Jina embeddings)

Hybrid retrieval combines:
1. Vector similarity from Jina embeddings.
2. Symbolic filters (`session_id`, `role`, `tags`, time range).
3. Ranking into result list with scores.

Why hybrid matters:
- Semantic understanding for paraphrased queries.
- Deterministic filtering for compliance and precision.

## Forgetting API and GDPR

Forgetting endpoints implement targeted deletion:
- `DELETE /memory/{episode_id}` → specific record deletion.
- `DELETE /memory/session/{session_id}` → session wipe.
- `DELETE /memory/user/{user_id}` → user-wide erase request.

Operationally this supports:
- Right to erasure workflows.
- Incident response cleanup.
- Controlled retention policies by scope.

Recommended compliance workflow:
1. Authenticate with org-level authority.
2. Execute the narrowest delete endpoint needed.
3. Log request + `request_id` for audit traceability.
