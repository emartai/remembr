# LlamaIndex Adapter

## Install

```bash
pip install remembr-llamaindex-adapter llama-index remembr
```

## ChatEngine usage

```python
from remembr import RemembrClient
from adapters.llamaindex.remembr_llamaindex_memory import RemembrMemoryBuffer

client = RemembrClient(api_key="<API_KEY>", base_url="https://api.remembr.dev/api/v1")

memory = RemembrMemoryBuffer(client=client, token_limit=256)
memory.put("Prefer weekly digests")
print(memory.get(input="How often should digests be sent?"))
```

## RAG-style retrieval example

```python
from adapters.llamaindex.remembr_llamaindex_memory import RemembrSemanticMemory

semantic = RemembrSemanticMemory.from_client(client)
semantic.save_context({"input": "Project Orion ships in May"}, {"output": "Stored"})
retriever = semantic.as_retriever()
print(retriever.retrieve("When does Orion ship?"))
```
