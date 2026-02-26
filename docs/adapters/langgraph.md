# LangGraph Adapter

## Install

```bash
pip install remembr-langgraph-adapter langgraph langchain-core remembr
```

## Graph node usage

```python
from remembr import RemembrClient
from adapters.langgraph.remembr_langgraph_memory import RemembrLangGraphMemory

client = RemembrClient(api_key="<API_KEY>", base_url="http://localhost:8000/api/v1")
adapter = RemembrLangGraphMemory(client=client)

state = {"messages": [{"role": "user", "content": "Remember my preferred chart type: bar"}]}
adapter.save_memories(state, config={"configurable": {"thread_id": "t-1"}})
loaded = adapter.load_memories({"messages": [{"role": "user", "content": "Which chart type?"}]}, config={"configurable": {"thread_id": "t-1"}})
print(loaded["remembr_context"])
```

## Checkpointer usage

```python
from adapters.langgraph.remembr_langgraph_memory import RemembrLangGraphCheckpointer

checkpointer = RemembrLangGraphCheckpointer(client=client)
config = {"configurable": {"thread_id": "t-1"}}
checkpointer.put(config, {"step": 1, "state": "draft"}, {"stage": "draft"})
print(checkpointer.get(config))
```

## StateGraph example

```python
from langgraph.graph import StateGraph
from adapters.langgraph.remembr_langgraph_memory import add_remembr_to_graph

graph = StateGraph(dict)
# ... add your app nodes/edges ...
graph = add_remembr_to_graph(graph, client=client)
```
