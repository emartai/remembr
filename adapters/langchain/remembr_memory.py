"""LangChain memory adapter backed by Remembr."""

from __future__ import annotations

from typing import Any

from langchain_core.memory import BaseMemory
from langchain_core.messages import AIMessage, HumanMessage

from adapters.base.error_handling import with_remembr_fallback
from adapters.base.remembr_adapter_base import BaseRemembrAdapter
from adapters.base.utils import parse_role


class RemembrMemory(BaseMemory, BaseRemembrAdapter):
    """Drop-in memory class compatible with LangChain 1.x memory APIs."""

    memory_key: str = "history"
    return_messages: bool = True

    def __init__(
        self,
        client: Any,
        session_id: str | None = None,
        scope_metadata: dict[str, Any] = {},
        return_messages: bool = True,
        **kwargs: Any,
    ) -> None:
        # Initialize BaseMemory
        super().__init__(**kwargs)
        
        # Initialize BaseRemembrAdapter
        BaseRemembrAdapter.__init__(
            self,
            client=client,
            session_id=session_id,
            scope_metadata=scope_metadata,
        )
        
        self.return_messages = return_messages

    @property
    def memory_variables(self) -> list[str]:
        """Return list of memory variable keys."""
        return [self.memory_key]

    @with_remembr_fallback()
    def save_context(self, inputs: dict[str, Any], outputs: dict[str, Any]) -> None:
        """Save context from this conversation turn to Remembr.
        
        Args:
            inputs: Dictionary containing user input (typically with 'input' key)
            outputs: Dictionary containing AI output (typically with 'output' key)
        """
        user_input = str(inputs.get("input", "")).strip()
        ai_output = str(outputs.get("output", "")).strip()

        if user_input:
            self._store(user_input, role="user")
        if ai_output:
            self._store(ai_output, role="assistant")

    @with_remembr_fallback(default_value={"history": []})
    def load_memory_variables(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Load memory variables from Remembr based on the current input.
        
        Args:
            inputs: Dictionary containing the current input (typically with 'input' key)
            
        Returns:
            Dictionary with memory_key mapped to conversation history
        """
        query = str(inputs.get("input", "")).strip()
        if not query:
            return {self.memory_key: []}

        # Search Remembr for relevant context
        results = self._search(query=query, limit=10)
        
        if self.return_messages:
            # Return as LangChain message objects
            messages = []
            for item in results.results:
                if parse_role(item.role) == "assistant":
                    messages.append(AIMessage(content=item.content))
                else:
                    messages.append(HumanMessage(content=item.content))
            return {self.memory_key: messages}
        else:
            # Return as formatted string
            context_lines = []
            for item in results.results:
                role = "AI" if parse_role(item.role) == "assistant" else "Human"
                context_lines.append(f"{role}: {item.content}")
            return {self.memory_key: "\n".join(context_lines)}

    @with_remembr_fallback()
    def clear(self) -> None:
        """Clear all memories for this session from Remembr."""
        self._run(self.client.forget_session(self.session_id))
