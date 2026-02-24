# LangChain Adapter

## Install

```bash
pip install remembr-langchain-adapter langchain langchain-core remembr
```

## Basic usage

```python
from remembr import RemembrClient
from adapters.langchain.remembr_memory import RemembrMemory

client = RemembrClient(api_key="<API_KEY>", base_url="https://api.remembr.dev/api/v1")
memory = RemembrMemory(client=client)

memory.save_context({"input": "I prefer concise answers."}, {"output": "Noted."})
context = memory.load_memory_variables({"input": "How should you respond?"})
print(context["history"])
```

## ConversationChain example

```python
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
chain = ConversationChain(llm=llm, memory=memory, verbose=True)

chain.predict(input="Remember: my timezone is UTC+1")
print(chain.predict(input="What timezone am I in?"))
```

## Advanced scoping

```python
memory = RemembrMemory(
    client=client,
    session_id="existing-session-id",
    scope_metadata={"team_id": "team-42", "agent_id": "planner"},
)
```
