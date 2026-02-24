# Haystack Adapter

## Install

```bash
pip install remembr-haystack-adapter farm-haystack remembr
```

## Component usage

```python
from remembr import RemembrClient
from adapters.haystack.remembr_haystack_memory import RemembrMemoryRetriever, RemembrMemoryWriter

client = RemembrClient(api_key="<API_KEY>", base_url="https://api.remembr.dev/api/v1")
writer = RemembrMemoryWriter(client=client, default_session_id="session-id")
retriever = RemembrMemoryRetriever(client=client, default_session_id="session-id")

writer.run(content="Escalate on-call immediately for P1")
print(retriever.run(query="P1 on-call"))
```

## Pipeline factory

```python
from adapters.haystack.remembr_haystack_memory import build_remembr_rag_pipeline

pipeline = build_remembr_rag_pipeline(client=client, llm_component=my_llm)
```

## RAG pipeline example

```python
result = pipeline.run(
    {
        "memory_retriever": {"query": "incident handling"},
        "prompt_builder": {"query": "What is our P1 process?"},
    }
)
print(result)
```
