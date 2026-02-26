# Pydantic AI Adapter

## Install

```bash
pip install remembr-pydantic-ai-adapter pydantic-ai remembr
```

## Dependency injection pattern

```python
from remembr import RemembrClient
from adapters.pydantic_ai.remembr_pydantic_memory import RemembrMemoryDep

client = RemembrClient(api_key="<API_KEY>", base_url="http://localhost:8000/api/v1")
deps = RemembrMemoryDep(client=client, session_id="session-id")
```

## Tools usage

```python
from adapters.pydantic_ai.remembr_pydantic_memory import RemembrMemoryTools

class Ctx:
    def __init__(self, deps):
        self.deps = deps

ctx = Ctx(deps)
print(RemembrMemoryTools.store_memory(ctx, "Always include acceptance criteria"))
print(RemembrMemoryTools.search_memory(ctx, "acceptance criteria"))
```

## Factory function

```python
from adapters.pydantic_ai.remembr_pydantic_memory import create_remembr_agent

agent = create_remembr_agent(
    model="openai:gpt-4o-mini",
    system_prompt="You are a pragmatic engineering assistant.",
    api_key="<API_KEY>",
)
```
