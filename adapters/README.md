# Remembr Framework Adapters

## Comparison

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

## When to use each

- **LangChain**: You already use memory abstractions like `ConversationBufferMemory`.
- **LangGraph**: You want durable graph-state and checkpoint replay.
- **CrewAI**: You need short-term private + long-term shared team memory.
- **AutoGen**: You want message-hook based contextual injection.
- **LlamaIndex**: You need semantic memory retrieval inside query/chat engines.
- **Pydantic AI**: You prefer typed deps + explicit tools and prompt composition.
- **OpenAI Agents SDK**: You need tools/handoffs with non-blocking lifecycle logging.
- **Haystack**: You build component pipelines and want memory as pipeline components.

## Common patterns and gotchas

- All adapters rely on shared utilities in `adapters/base/utils.py`.
- All Remembr calls should be protected via `with_remembr_fallback` to avoid crashing host frameworks.
- Role normalization is done via `parse_role(...)` to avoid framework-specific role drift.
- Prefer passing an explicit `session_id` for continuity across runs.
- For multi-agent systems, include `agent_id`/`team_id` metadata for better scoping.

## Migration guide

1. **Keep the same session_id** when moving frameworks.
2. Replace framework-specific memory wiring with the corresponding adapter factory:
   - `create_langchain_memory(...)`
   - `create_langgraph_memory(...)`
   - `create_crewai_memory(...)`
   - `create_autogen_memory(...)`
   - `create_llamaindex_memory(...)`
   - `create_pydantic_ai_memory(...)`
   - `create_openai_agents_memory(...)`
   - `create_haystack_memory(...)`
3. Keep tool prompts stable and reuse existing tags/metadata conventions.
4. Validate role mapping and context formatting after migration.
