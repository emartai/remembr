# Embeddings and Vector Search

## Overview

Remembr uses PostgreSQL with the pgvector extension for efficient vector similarity search. Embeddings are generated using Jina AI's embedding API and stored with HNSW (Hierarchical Navigable Small World) indexes for fast approximate nearest neighbor search.

## Architecture

```
Text Content
    ↓
Jina AI API (jina-embeddings-v3)
    ↓
Vector Embedding (1024 dimensions)
    ↓
PostgreSQL + pgvector
    ↓
HNSW Index (Cosine Similarity)
    ↓
Fast Similarity Search
```

## Embeddings Table

### Schema

| Column          | Type         | Description                    |
|-----------------|--------------|--------------------------------|
| id              | UUID         | Primary key                    |
| org_id          | UUID         | Organization ID (multi-tenant) |
| episode_id      | UUID         | Optional episode reference     |
| memory_fact_id  | UUID         | Optional memory fact reference |
| content         | TEXT         | Original text content          |
| model           | VARCHAR(100) | Model name (e.g., jina-embeddings-v3) |
| dimensions      | INTEGER      | Vector dimensions              |
| vector          | FLOAT[]      | Embedding vector               |
| created_at      | TIMESTAMPTZ  | Creation timestamp             |
| updated_at      | TIMESTAMPTZ  | Last update timestamp          |

### Indexes

- **B-tree indexes**: org_id, episode_id, memory_fact_id, model
- **HNSW index**: vector (for cosine similarity search)

## pgvector Extension

### Installation

The pgvector extension is automatically enabled in the migration:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Vector Operations

pgvector provides three distance operators:

1. **Cosine Distance** (`<=>`) - Used by Remembr
   - Range: 0 (identical) to 2 (opposite)
   - Best for normalized vectors
   - Formula: 1 - cosine_similarity

2. **L2 Distance** (`<->`)
   - Euclidean distance
   - Good for absolute magnitude

3. **Inner Product** (`<#>`)
   - Dot product
   - Good for unnormalized vectors

## HNSW Index

### What is HNSW?

Hierarchical Navigable Small World (HNSW) is a graph-based algorithm for approximate nearest neighbor search:

- **Fast**: O(log n) search complexity
- **Accurate**: High recall rates (>95%)
- **Memory efficient**: Stores graph structure
- **Scalable**: Works well with millions of vectors

### Index Configuration

```sql
CREATE INDEX ix_embeddings_vector_cosine ON embeddings 
USING hnsw (vector vector_cosine_ops);
```

### Performance Characteristics

- **Build time**: Slower than IVFFlat (but only done once)
- **Query time**: Faster than IVFFlat
- **Accuracy**: Better than IVFFlat
- **Memory**: Moderate overhead

## Jina AI Integration

### Model: jina-embeddings-v3

- **Dimensions**: 1024
- **Max input**: 8192 tokens
- **Languages**: Multilingual (100+ languages)
- **Performance**: State-of-the-art on MTEB benchmark

### API Usage

```python
from app.services import EmbeddingService

service = EmbeddingService()

# Single text
vector, dimensions = await service.generate_embedding("Hello world")

# Batch processing
texts = ["Text 1", "Text 2", "Text 3"]
results = await service.generate_embeddings_batch(texts)
```

### Rate Limits

- Free tier: 1M tokens/month
- Paid tier: Custom limits
- Batch size: Up to 100 texts per request

## Similarity Search

### Basic Search

```python
from app.repositories import EmbeddingRepository

repo = EmbeddingRepository(db)

# Generate query embedding
query_vector, _ = await embedding_service.generate_embedding("search query")

# Find similar embeddings
results = await repo.similarity_search(
    org_id=org_id,
    query_vector=query_vector,
    limit=10,
    threshold=0.7,
)

for embedding, similarity in results:
    print(f"Similarity: {similarity:.2f} - {embedding.content}")
```

### Similarity Scores

Cosine similarity is converted to a 0-1 scale:

- **1.0**: Identical vectors
- **0.9-1.0**: Very similar
- **0.7-0.9**: Similar
- **0.5-0.7**: Somewhat similar
- **<0.5**: Not similar

### Threshold Selection

Choose threshold based on use case:

- **0.9+**: Near-duplicate detection
- **0.8+**: High precision search
- **0.7+**: Balanced precision/recall (recommended)
- **0.6+**: High recall search
- **0.5+**: Exploratory search

## Query Patterns

### Search Episodes

```python
# Find similar episodes
query_vector, _ = await embedding_service.generate_embedding(
    "What did we discuss about pricing?"
)

results = await repo.similarity_search(
    org_id=org_id,
    query_vector=query_vector,
    limit=5,
    threshold=0.75,
)

# Get episode details
for embedding, score in results:
    if embedding.episode_id:
        episode = await db.get(Episode, embedding.episode_id)
        print(f"Score: {score:.2f} - {episode.content}")
```

### Search Memory Facts

```python
# Find related facts
query_vector, _ = await embedding_service.generate_embedding(
    "customer preferences"
)

results = await repo.similarity_search(
    org_id=org_id,
    query_vector=query_vector,
    limit=10,
    threshold=0.7,
)

# Filter for memory facts only
fact_results = [
    (emb, score) for emb, score in results 
    if emb.memory_fact_id is not None
]
```

### Hybrid Search

Combine vector search with filters:

```python
# Search with SQL filters
query = text("""
    SELECT 
        e.*,
        1 - (e.vector <=> :query_vector::vector) as similarity
    FROM embeddings e
    JOIN episodes ep ON e.episode_id = ep.id
    WHERE e.org_id = :org_id
        AND ep.role = 'user'
        AND ep.created_at >= :since
        AND 1 - (e.vector <=> :query_vector::vector) >= :threshold
    ORDER BY e.vector <=> :query_vector::vector
    LIMIT :limit
""")
```

## Performance Optimization

### Batch Embedding Generation

Always use batch API for multiple texts:

```python
# Good: Batch processing
texts = [episode.content for episode in episodes]
embeddings = await service.generate_embeddings_batch(texts)

# Bad: Sequential processing
embeddings = []
for episode in episodes:
    emb, _ = await service.generate_embedding(episode.content)
    embeddings.append(emb)
```

### Index Maintenance

HNSW indexes are automatically maintained, but you can optimize:

```sql
-- Rebuild index if needed
REINDEX INDEX ix_embeddings_vector_cosine;

-- Vacuum to reclaim space
VACUUM ANALYZE embeddings;
```

### Query Optimization

1. **Always filter by org_id** for multi-tenancy
2. **Use appropriate threshold** to limit results
3. **Set reasonable limit** (10-50 typical)
4. **Consider caching** for frequent queries

## Monitoring

### Index Statistics

```sql
-- Index size
SELECT pg_size_pretty(pg_relation_size('ix_embeddings_vector_cosine'));

-- Index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read
FROM pg_stat_user_indexes
WHERE indexname = 'ix_embeddings_vector_cosine';
```

### Query Performance

```sql
-- Explain query plan
EXPLAIN ANALYZE
SELECT *
FROM embeddings
WHERE org_id = 'uuid-here'
ORDER BY vector <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

## Best Practices

### 1. Normalize Text

Clean text before embedding:

```python
def normalize_text(text: str) -> str:
    # Remove extra whitespace
    text = " ".join(text.split())
    # Truncate to max length
    max_length = 8000  # Leave room for tokens
    if len(text) > max_length:
        text = text[:max_length]
    return text
```

### 2. Store Original Content

Always store the original text with the embedding:

- Enables re-embedding with new models
- Provides context for results
- Supports debugging

### 3. Version Embeddings

Track the model used:

```python
embedding = Embedding(
    content=text,
    vector=vector,
    model="jina-embeddings-v3",  # Track model version
    dimensions=len(vector),
)
```

### 4. Handle Errors

Implement retry logic for API calls:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def generate_with_retry(text: str):
    return await embedding_service.generate_embedding(text)
```

### 5. Monitor Costs

Track API usage:

```python
from loguru import logger

async def generate_embedding(text: str):
    token_count = len(text.split())  # Rough estimate
    logger.info("Generating embedding", tokens=token_count)
    
    vector, dims = await service.generate_embedding(text)
    
    # Track in metrics system
    metrics.increment("embeddings.generated", tokens=token_count)
    
    return vector, dims
```

## Troubleshooting

### Slow Queries

If similarity search is slow:

1. Check index exists: `\d embeddings`
2. Verify index is being used: `EXPLAIN ANALYZE ...`
3. Reduce limit or increase threshold
4. Consider adding more filters (org_id, created_at)

### Low Recall

If not finding relevant results:

1. Lower threshold (try 0.6 or 0.5)
2. Increase limit
3. Check embedding quality
4. Verify text normalization

### High Memory Usage

If pgvector uses too much memory:

1. Reduce HNSW index parameters (requires rebuild)
2. Consider IVFFlat index instead
3. Partition embeddings table by org_id

## Migration from Other Models

To re-embed with a new model:

```python
async def migrate_embeddings(org_id: uuid.UUID):
    # Get all embeddings for org
    result = await db.execute(
        select(Embedding).where(Embedding.org_id == org_id)
    )
    embeddings = result.scalars().all()
    
    # Batch re-embed
    texts = [emb.content for emb in embeddings]
    new_vectors = await service.generate_embeddings_batch(texts)
    
    # Update embeddings
    for embedding, (vector, dims) in zip(embeddings, new_vectors):
        embedding.vector = vector
        embedding.model = "new-model-name"
        embedding.dimensions = dims
    
    await db.commit()
```

## Resources

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Jina AI Embeddings](https://jina.ai/embeddings/)
- [HNSW Paper](https://arxiv.org/abs/1603.09320)
- [Vector Search Best Practices](https://www.pinecone.io/learn/vector-search/)
