# OpenAI Agents Adapter

## Install

```bash
pip install remembr-openai-agents-adapter openai-agents remembr
```

## Tools usage

```python
from remembr import RemembrClient
from adapters.openai_agents.remembr_openai_memory import RemembrMemoryTools

client = RemembrClient(api_key="<API_KEY>", base_url="http://localhost:8000/api/v1")
RemembrMemoryTools.configure(client)

print(RemembrMemoryTools.store_memory("Remember this", "session-id"))
print(RemembrMemoryTools.search_memory("remember", "session-id"))
```

## Hooks usage

```python
from adapters.openai_agents.remembr_openai_memory import RemembrAgentHooks

hooks = RemembrAgentHooks(client=client, session_id="session-id")
# Attach hooks when creating your Agent
```

## Handoff memory example

```python
from adapters.openai_agents.remembr_openai_memory import RemembrHandoffMemory

handoff_memory = RemembrHandoffMemory(client=client, session_id="session-id")
handoff_memory.store_before_handoff("Planner", "Need rollback plan details")
print(handoff_memory.inject_after_handoff("Executor"))
```
