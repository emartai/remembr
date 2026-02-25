# Remembr Architecture

This document provides a deep technical dive into Remembr's architecture, design decisions, and implementation details.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Storage Architecture](#storage-architecture)
5. [Security & Multi-Tenancy](#security--multi-tenancy)
6. [API Design](#api-design)
7. [Framework Adapters](#framework-adapters)
8. [Performance & Scalability](#performance--scalability)
9. [Deployment Architecture](#deployment-architecture)

---

## System Overview

Remembr is a distributed memory infrastructure designed for AI agents. It provides persistent, searchable memory with multi-tenant isolation and enterprise-grade security.

### Design Principles

1. **Framework Agnostic** - Works with any AI framework via adapters
2. **Multi-Tenant by Default** - Strict data isolation at every layer
3. **Hybrid Search** - Combines semantic and symbolic retrieval
4. **Layered Memory** - Short-term (Redis) + long-term (PostgreSQL)
5. **API-First** - REST API with SDK wrappers
6. **Production Ready** - Auth, rate limiting, monitoring, compliance

---

## Component Architecture

### High-Level Components

```mermaid
graph TB
    subgraph "Client Layer"
        AGENT[AI Agent Application]
        ADAPTER[Framework Adapter]
        SDK[Remembr SDK]
    end
    
    subgraph "API Layer"
        GATEWAY[API Gateway]
        AUTH[Auth Middleware]
        RATE[Rate Limiter]
        ROUTER[Route Handlers]
    end
    
    subgraph "Service Layer"
        SESS_SVC[Session Service]
        MEM_SVC[Memory Service]
        SEARCH_SVC[Search Service]
        FORGET_SVC[Forgetting Service]
        EMBED_SVC[Embedding Service]
    end
    
    subgraph "Repository Layer"
        SESS_REPO[Session Repository]
        EP_REPO[Episode Repository]
        USER_REPO[User Repository]
        KEY_REPO[API Key Repository]
    end
    
    subgraph "Storage Layer"
        REDIS[(Redis)]
        PG[(PostgreSQL<br/>+ pgvector)]
    end
    
    subgraph "External Services"
        JINA[Jina AI API]
    end
    
    AGENT --> ADAPTER
    ADAPTER --> SDK
    SDK --> GATEWAY
    
    GATEWAY --> AUTH
    AUTH --> RATE
    RATE --> ROUTER
    
    ROUTER --> SESS_SVC
    ROUTER --> MEM_SVC
    ROUTER --> SEARCH_SVC
    ROUTER --> FORGET_SVC
    
    MEM_SVC --> EMBED_SVC
    EMBED_SVC --> JINA
    
    SESS_SVC --> SESS_REPO
    MEM_SVC --> EP_REPO
    SEARCH_SVC --> EP_REPO
    FORGET_SVC --> EP_REPO
    
    SESS_REPO --> REDIS
    SESS_REPO --> PG
    EP_REPO --> PG
    USER_REPO --> PG
    KEY_REPO --> PG
    
    style GATEWAY fill:#4A90E2
    style AUTH fill:#50C878
    style REDIS fill:#DC382D
    style PG fill:#336791
    style JINA fill:#FF6B6B
```

### Component Responsibilities

#### Client Layer
- **AI Agent**: End-user application (LangChain, CrewAI, etc.)
- **Framework Adapter**: Framework-specific integration layer
- **SDK**: HTTP client with retry logic and error handling

#### API Layer
- **API Gateway**: FastAPI application entry point
- **Auth Middleware**: JWT/API key validation and context injection
- **Rate Limiter**: Redis-backed rate limiting per API key
- **Route Handlers**: REST endpoint controllers

#### Service Layer
- **Session Service**: Session lifecycle management
- **Memory Service**: Memory storage and retrieval
- **Search Service**: Hybrid search orchestration
- **Forgetting Service**: GDPR-compliant deletion
- **Embedding Service**: Jina AI integration for vector generation

#### Repository Layer
- **Session Repository**: Session CRUD operations
- **Episode Repository**: Memory episode persistence
- **User Repository**: User and org management
- **API Key Repository**: API key lifecycle

#### Storage Layer
- **Redis**: Short-term memory cache, rate limiting, session state
- **PostgreSQL**: Long-term episodic storage with pgvector extension

---

## Data Flow

### Memory Storage Flow

```mermaid
sequenceDiagram
    participant Agent
    participant SDK
    participant API
    participant Auth
    participant MemSvc as Memory Service
    participant EmbedSvc as Embed Service
    participant Jina
    participant Redis
    participant PG as PostgreSQL

    Agent->>SDK: store(content, session_id)
    SDK->>API: POST /memory
    API->>Auth: Validate JWT/API Key
    Auth->>API: Context (org_id, user_id)
    API->>MemSvc: store_memory(content, context)
    
    par Async Operations
        MemSvc->>Redis: Cache in short-term window
        MemSvc->>PG: Insert episode record
        MemSvc->>EmbedSvc: Generate embedding
        EmbedSvc->>Jina: POST /embeddings
        Jina-->>EmbedSvc: Vector [768]
        EmbedSvc->>PG: Update episode with vector
    end
    
    MemSvc-->>API: episode_id, token_count
    API-->>SDK: 201 Created
    SDK-->>Agent: Episode object
```

### Memory Search Flow

```mermaid
sequenceDiagram
    participant Agent
    participant SDK
    participant API
    participant Auth
    participant SearchSvc as Search Service
    participant EmbedSvc as Embed Service
    participant Jina
    participant PG as PostgreSQL

    Agent->>SDK: search(query, session_id)
    SDK->>API: POST /memory/search
    API->>Auth: Validate JWT/API Key
    Auth->>API: Context (org_id, user_id)
    API->>SearchSvc: search(query, filters, context)
    
    SearchSvc->>EmbedSvc: Generate query embedding
    EmbedSvc->>Jina: POST /embeddings
    Jina-->>EmbedSvc: Query vector [768]
    
    SearchSvc->>PG: Hybrid search query
    Note over SearchSvc,PG: Vector similarity (pgvector)<br/>+ Metadata filters<br/>+ RLS enforcement
    
    PG-->>SearchSvc: Ranked results
    SearchSvc-->>API: Results with scores
    API-->>SDK: 200 OK
    SDK-->>Agent: Search results
```

### Checkpoint & Restore Flow

```mermaid
sequenceDiagram
    participant Agent
    participant API
    participant SessSvc as Session Service
    participant Redis
    participant PG as PostgreSQL

    Note over Agent,PG: Checkpoint Creation
    Agent->>API: POST /sessions/{id}/checkpoint
    API->>SessSvc: create_checkpoint(session_id)
    SessSvc->>Redis: Get short-term window
    Redis-->>SessSvc: Messages [1..N]
    SessSvc->>PG: Insert checkpoint record
    SessSvc-->>API: checkpoint_id
    API-->>Agent: 201 Created

    Note over Agent,PG: Restore from Checkpoint
    Agent->>API: POST /sessions/{id}/restore
    API->>SessSvc: restore_checkpoint(checkpoint_id)
    SessSvc->>PG: Fetch checkpoint data
    PG-->>SessSvc: Checkpoint messages
    SessSvc->>Redis: Clear current window
    SessSvc->>Redis: Load checkpoint messages
    SessSvc-->>API: restored_count
    API-->>Agent: 200 OK
```

---

## Storage Architecture

### PostgreSQL Schema

```mermaid
erDiagram
    organizations ||--o{ teams : has
    organizations ||--o{ users : has
    organizations ||--o{ api_keys : has
    teams ||--o{ users : has
    users ||--o{ sessions : creates
    users ||--o{ api_keys : owns
    sessions ||--o{ episodes : contains
    sessions ||--o{ checkpoints : has
    checkpoints ||--o{ checkpoint_messages : contains

    organizations {
        uuid id PK
        string name
        jsonb settings
        timestamp created_at
    }

    teams {
        uuid id PK
        uuid org_id FK
        string name
        timestamp created_at
    }

    users {
        uuid id PK
        uuid org_id FK
        uuid team_id FK
        string email UK
        string password_hash
        boolean is_active
        timestamp created_at
    }

    api_keys {
        uuid id PK
        uuid org_id FK
        uuid user_id FK
        uuid agent_id
        string key_hash UK
        string name
        timestamp expires_at
        timestamp created_at
    }

    sessions {
        uuid id PK
        uuid org_id FK
        uuid user_id FK
        uuid agent_id
        jsonb metadata
        timestamp created_at
    }

    episodes {
        uuid id PK
        uuid session_id FK
        uuid org_id FK
        uuid user_id FK
        string role
        text content
        vector embedding
        jsonb metadata
        string[] tags
        int token_count
        timestamp created_at
    }

    checkpoints {
        uuid id PK
        uuid session_id FK
        int message_count
        timestamp created_at
    }

    checkpoint_messages {
        uuid id PK
        uuid checkpoint_id FK
        string role
        text content
        int sequence
        timestamp created_at
    }
```

### Indexes

**Performance Indexes:**
```sql
-- Vector similarity search (pgvector)
CREATE INDEX idx_episodes_embedding ON episodes 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Session-based queries
CREATE INDEX idx_episodes_session_created ON episodes (session_id, created_at DESC);

-- User-scoped queries
CREATE INDEX idx_episodes_user_created ON episodes (user_id, created_at DESC);

-- Tag-based filtering
CREATE INDEX idx_episodes_tags ON episodes USING gin(tags);

-- Time-range queries
CREATE INDEX idx_episodes_created_at ON episodes (created_at);
```

**Security Indexes:**
```sql
-- Multi-tenant isolation
CREATE INDEX idx_episodes_org_id ON episodes (org_id);
CREATE INDEX idx_sessions_org_user ON sessions (org_id, user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys (key_hash);
```

### Row-Level Security (RLS)

```sql
-- Enable RLS on episodes table
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own org's data
CREATE POLICY episodes_org_isolation ON episodes
FOR ALL
USING (org_id = current_setting('app.current_org_id')::uuid);

-- Policy: Agent-scoped keys can only see their agent's data
CREATE POLICY episodes_agent_isolation ON episodes
FOR ALL
USING (
    agent_id IS NULL OR 
    agent_id = current_setting('app.current_agent_id')::uuid
);
```

### Redis Data Structures

```
# Short-term memory window
session:{session_id}:messages -> List[Message]
  - LPUSH for new messages
  - LRANGE for retrieval
  - TTL: 24 hours

# Rate limiting
ratelimit:{api_key}:{window} -> Counter
  - INCR for requests
  - EXPIRE for window reset
  - TTL: 60 seconds (sliding window)

# Session metadata cache
session:{session_id}:meta -> Hash
  - HSET for metadata
  - HGET for retrieval
  - TTL: 1 hour
```

---

## Security & Multi-Tenancy

### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Auth as Auth Middleware
    participant DB as PostgreSQL

    Note over Client,DB: Registration
    Client->>API: POST /auth/register
    API->>DB: Create org + user
    DB-->>API: user_id, org_id
    API-->>Client: access_token, refresh_token

    Note over Client,DB: Login
    Client->>API: POST /auth/login
    API->>DB: Verify credentials
    DB-->>API: user record
    API-->>Client: access_token, refresh_token

    Note over Client,DB: Authenticated Request
    Client->>API: GET /sessions (Bearer token)
    API->>Auth: Validate JWT
    Auth->>Auth: Decode + verify signature
    Auth->>DB: Check user is_active
    Auth->>Auth: Inject context
    Auth-->>API: Context(org_id, user_id, agent_id)
    API->>DB: Query with RLS
    DB-->>API: Scoped results
    API-->>Client: 200 OK
```

### Scoping Hierarchy

```
┌─────────────────────────────────────────┐
│         Organization Level              │
│  • Full data access                     │
│  • Compliance operations                │
│  • User management                      │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        │    Team     │
        │  • Shared   │
        │    context  │
        └──────┬──────┘
               │
        ┌──────┴──────┐
        │    User     │
        │  • Personal │
        │    sessions │
        └──────┬──────┘
               │
        ┌──────┴──────┐
        │    Agent    │
        │  • Isolated │
        │    memory   │
        └──────┬──────┘
               │
        ┌──────┴──────┐
        │   Session   │
        │  • Scoped   │
        │    episodes │
        └─────────────┘
```

### Authorization Matrix

| Scope Level | Can Read | Can Write | Can Delete | Use Case |
|-------------|----------|-----------|------------|----------|
| **Org-level** | All org data | All org data | All org data | Admin, compliance |
| **Team-level** | Team data | Team data | Team data | Shared agents |
| **User-level** | User's data | User's data | User's data | Personal agents |
| **Agent-level** | Agent's data | Agent's data | Agent's data | Isolated agents |
| **Session-level** | Session data | Session data | Session data | Conversation scope |

---

## API Design

### REST Principles

1. **Resource-Oriented**: `/sessions`, `/memory`, `/api-keys`
2. **HTTP Verbs**: GET (read), POST (create), DELETE (remove)
3. **Status Codes**: 200 (OK), 201 (Created), 400 (Bad Request), 401 (Unauthorized), 404 (Not Found)
4. **JSON Envelope**: Consistent response structure with `data` and `request_id`

### Response Envelope

```json
{
  "data": {
    "session_id": "uuid",
    "created_at": "2026-02-25T10:00:00Z"
  },
  "request_id": "req_abc123"
}
```

### Error Response

```json
{
  "message": "Session not found",
  "details": {
    "code": "SESSION_NOT_FOUND",
    "session_id": "uuid"
  },
  "request_id": "req_abc123"
}
```

### Rate Limiting

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640000000
```

**Algorithm**: Sliding window counter (Redis)
**Limits**: 1000 req/min per API key (configurable)

---

## Framework Adapters

### Adapter Architecture

```mermaid
graph LR
    subgraph "Framework Layer"
        FW[Framework<br/>LangChain/CrewAI/etc]
    end
    
    subgraph "Adapter Layer"
        IFACE[Framework Interface<br/>BaseMemory/ChatStore/etc]
        ADAPTER[Remembr Adapter<br/>Implementation]
        WRAPPER[SDK Wrapper]
    end
    
    subgraph "SDK Layer"
        SDK[Remembr SDK]
        HTTP[HTTP Client]
    end
    
    FW --> IFACE
    IFACE --> ADAPTER
    ADAPTER --> WRAPPER
    WRAPPER --> SDK
    SDK --> HTTP
    
    style ADAPTER fill:#4A90E2
    style SDK fill:#50C878
```

### Adapter Patterns

#### 1. Drop-in Replacement (LangChain)
```python
class RemembrMemory(BaseMemory):
    """Implements LangChain's BaseMemory interface"""
    
    def load_memory_variables(self, inputs):
        # Search Remembr for relevant context
        results = self.client.search(query=inputs["input"])
        return {"history": format_results(results)}
    
    def save_context(self, inputs, outputs):
        # Store conversation turn
        self.client.store(content=f"{inputs} -> {outputs}")
```

#### 2. State Integration (LangGraph)
```python
class RemembrLangGraphMemory:
    """Integrates with LangGraph state management"""
    
    def add_to_state(self, state, key, value):
        # Store in Remembr + update graph state
        self.client.store(content=value, metadata={"state_key": key})
        state[key] = value
```

#### 3. Dependency Injection (Pydantic AI)
```python
class RemembrMemoryDep:
    """Provides memory as a typed dependency"""
    
    async def __call__(self, ctx: RunContext) -> MemoryContext:
        results = await self.client.search(query=ctx.prompt)
        return MemoryContext(history=results)
```

---

## Performance & Scalability

### Performance Characteristics

| Operation | Latency (p50) | Latency (p95) | Latency (p99) |
|-----------|---------------|---------------|---------------|
| Store memory | 20ms | 50ms | 100ms |
| Search (< 1K episodes) | 50ms | 150ms | 300ms |
| Search (10K episodes) | 80ms | 200ms | 400ms |
| Search (100K episodes) | 120ms | 300ms | 600ms |
| Checkpoint create | 30ms | 80ms | 150ms |
| Checkpoint restore | 40ms | 100ms | 200ms |

### Scalability Strategies

#### Horizontal Scaling
```
┌─────────────┐
│ Load        │
│ Balancer    │
└──────┬──────┘
       │
   ┌───┴───┬───────┬───────┐
   │       │       │       │
┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐
│ API │ │ API │ │ API │ │ API │
│  1  │ │  2  │ │  3  │ │  N  │
└──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘
   │       │       │       │
   └───┬───┴───────┴───────┘
       │
   ┌───┴───┬───────┐
   │       │       │
┌──▼──┐ ┌──▼──────▼──┐
│Redis│ │ PostgreSQL │
│     │ │ (Primary)  │
└─────┘ └──────┬─────┘
               │
        ┌──────┴──────┐
        │             │
    ┌───▼───┐     ┌───▼───┐
    │Replica│     │Replica│
    │   1   │     │   2   │
    └───────┘     └───────┘
```

#### Caching Strategy
1. **L1 Cache**: In-memory LRU cache (per API instance)
2. **L2 Cache**: Redis (shared across instances)
3. **L3 Storage**: PostgreSQL (source of truth)

#### Database Optimization
- **Connection Pooling**: 20 connections per instance
- **Read Replicas**: Route search queries to replicas
- **Partitioning**: Partition episodes by `created_at` (monthly)
- **Vacuum**: Automated VACUUM ANALYZE on schedule

---

## Deployment Architecture

### Production Deployment (Kubernetes)

```mermaid
graph TB
    subgraph "Ingress Layer"
        LB[Load Balancer<br/>HTTPS/TLS]
    end
    
    subgraph "Kubernetes Cluster"
        subgraph "API Pods"
            API1[API Pod 1]
            API2[API Pod 2]
            API3[API Pod N]
        end
        
        subgraph "Worker Pods"
            WORKER1[Embedding Worker 1]
            WORKER2[Embedding Worker 2]
        end
        
        subgraph "Storage"
            REDIS_SVC[Redis Service]
            PG_SVC[PostgreSQL Service]
        end
    end
    
    subgraph "External Services"
        JINA[Jina AI API]
    end
    
    subgraph "Managed Services"
        REDIS_MANAGED[(Managed Redis<br/>ElastiCache/Upstash)]
        PG_MANAGED[(Managed PostgreSQL<br/>RDS/Supabase)]
    end
    
    LB --> API1
    LB --> API2
    LB --> API3
    
    API1 --> REDIS_SVC
    API2 --> REDIS_SVC
    API3 --> REDIS_SVC
    
    API1 --> PG_SVC
    API2 --> PG_SVC
    API3 --> PG_SVC
    
    WORKER1 --> JINA
    WORKER2 --> JINA
    
    REDIS_SVC --> REDIS_MANAGED
    PG_SVC --> PG_MANAGED
    
    style LB fill:#4A90E2
    style REDIS_MANAGED fill:#DC382D
    style PG_MANAGED fill:#336791
```

### Environment Configuration

```yaml
# Production
ENVIRONMENT: production
LOG_LEVEL: INFO
DATABASE_URL: postgresql://user:pass@postgres:5432/remembr
REDIS_URL: redis://redis:6379/0
JINA_API_KEY: ${JINA_API_KEY}
JWT_SECRET: ${JWT_SECRET}
RATE_LIMIT_ENABLED: true
RATE_LIMIT_REQUESTS: 1000
RATE_LIMIT_WINDOW: 60

# Staging
ENVIRONMENT: staging
LOG_LEVEL: DEBUG
DATABASE_URL: postgresql://user:pass@staging-postgres:5432/remembr
REDIS_URL: redis://staging-redis:6379/0
RATE_LIMIT_REQUESTS: 100

# Development
ENVIRONMENT: development
LOG_LEVEL: DEBUG
DATABASE_URL: postgresql://user:pass@localhost:5432/remembr
REDIS_URL: redis://localhost:6379/0
RATE_LIMIT_ENABLED: false
```

---

## Monitoring & Observability

### Metrics

**Application Metrics:**
- Request rate (req/s)
- Response time (p50, p95, p99)
- Error rate (%)
- Active sessions
- Memory operations (store/search/delete)

**Infrastructure Metrics:**
- CPU usage (%)
- Memory usage (MB)
- Database connections
- Redis memory usage
- Network I/O

### Logging

```json
{
  "timestamp": "2026-02-25T10:00:00Z",
  "level": "INFO",
  "request_id": "req_abc123",
  "method": "POST",
  "path": "/api/v1/memory",
  "status": 201,
  "duration_ms": 45,
  "user_id": "uuid",
  "org_id": "uuid"
}
```

### Health Checks

```bash
# Liveness probe
GET /health
Response: {"status": "healthy", "timestamp": "..."}

# Readiness probe
GET /health/ready
Response: {"status": "ready", "database": "ok", "redis": "ok"}
```

---

## Future Enhancements

### Roadmap

1. **Vector Database Support** - Pinecone, Weaviate, Qdrant integration
2. **Multi-Modal Memory** - Image, audio, video embeddings
3. **Federated Search** - Cross-org search with privacy controls
4. **Memory Compression** - Automatic summarization of old memories
5. **Real-Time Sync** - WebSocket support for live updates
6. **GraphQL API** - Alternative to REST for complex queries
7. **Memory Analytics** - Usage dashboards and insights

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL pgvector](https://github.com/pgvector/pgvector)
- [Redis Documentation](https://redis.io/docs/)
- [Jina AI Embeddings](https://jina.ai/embeddings/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

---

**Last Updated**: February 25, 2026  
**Version**: 1.0.0  
**Maintainer**: [Emmanuel Nwanguma](mailto:nwangumaemmanuel29@gmail.com)
