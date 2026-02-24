# Remembr

Persistent memory infrastructure for AI agents.

## Documentation Hub

Start here:

- [Quickstart](docs/quickstart.md)
- [API Reference](docs/api-reference.md)
- [Concepts](docs/concepts.md)
- [Self-hosted Setup](docs/self-hosted.md)
- [Adapter Guides](docs/adapters/)

## Adapter Comparison

| Framework | Pattern used | Best for | Install command |
|---|---|---|---|
| LangChain | `BaseChatMemory` drop-in | Existing LangChain chains/agents | `pip install remembr-langchain-adapter` |
| LangGraph | Graph state nodes + checkpointer | Stateful graph workflows with thread checkpoints | `pip install remembr-langgraph-adapter` |
| CrewAI | Shared + layered crew memory | Multi-agent crew collaboration | `pip install remembr-crewai-adapter` |
| AutoGen | Agent hook injection | ConversableAgent/group chat memory context | `pip install remembr-autogen-adapter` |
| LlamaIndex | Chat store + semantic memory buffer | Query/chat engines and RAG memory | `pip install remembr-llamaindex-adapter` |
| Pydantic AI | Typed dependency injection + tools | Structured tool-first agents | `pip install remembr-pydantic-ai-adapter` |
| OpenAI Agents SDK | `@function_tool` + lifecycle hooks | Swarm/handoff workflows | `pip install remembr-openai-agents-adapter` |
| Haystack | `@component` pipeline blocks | Pipeline-based RAG and orchestration | `pip install remembr-haystack-adapter` |

## Repository Layout

```text
remembr/
├── docs/
│   ├── quickstart.md
│   ├── api-reference.md
│   ├── concepts.md
│   ├── self-hosted.md
│   └── adapters/
├── server/
├── sdk/
└── adapters/
```

## Development

```bash
# Server
cd server
uvicorn app.main:app --reload

# Tests
pytest tests/ -v
pytest ../tests/e2e -v
```
