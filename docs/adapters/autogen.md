# AutoGen Adapter

## Install

```bash
pip install remembr-autogen-adapter pyautogen remembr
```

## ConversableAgent usage

```python
from remembr import RemembrClient
from adapters.autogen.remembr_autogen_memory import RemembrAutoGenMemory

client = RemembrClient(api_key="<API_KEY>", base_url="https://api.remembr.dev/api/v1")
memory = RemembrAutoGenMemory(client=client)

memory.save_context({"message": "Customer locale is fr-FR"}, {"response": "Stored"})
print(memory.inject_context_into_message("Draft a follow-up email"))
```

## GroupChat example

```python
# group_chat is an AutoGen GroupChat instance
# memory.attach_to_group_chat(group_chat)
# memory.query_agent_memory("Planner", "rollback")
```
