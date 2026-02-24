"""LangChain memory adapter backed by Remembr."""

from __future__ import annotations

from typing import Any

from langchain.memory.chat_memory import BaseChatMemory
from langchain_core.messages import AIMessage, HumanMessage

from adapters.base.error_handling import with_remembr_fallback
from adapters.base.remembr_adapter_base import BaseRemembrAdapter
from adapters.base.utils import parse_role


class RemembrMemory(BaseChatMemory, BaseRemembrAdapter):
    """Drop-in memory class compatible with LangChain conversation memory APIs."""

    memory_key: str = "history"

    def __init__(
        self,
        client: Any,
        session_id: str | None = None,
        scope_metadata: dict[str, Any] = {},
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        BaseRemembrAdapter.__init__(
            self,
            client=client,
            session_id=session_id,
            scope_metadata=scope_metadata,
        )

    @property
    def memory_variables(self) -> list[str]:
        return [self.memory_key]

    @with_remembr_fallback()
    def save_context(self, inputs: dict[str, Any], outputs: dict[str, Any]) -> None:
        user_input = str(inputs.get("input", "")).strip()
        ai_output = str(outputs.get("output", "")).strip()

        if user_input:
            self._store(user_input, role="user")
        if ai_output:
            self._store(ai_output, role="assistant")

    def load_context(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return self.load_memory_variables(inputs)

    @with_remembr_fallback(default_value={"history": []})
    def load_memory_variables(self, inputs: dict[str, Any]) -> dict[str, Any]:
        query = str(inputs.get("input", "")).strip()
        if not query:
            return {self.memory_key: []}

        results = self._search(query=query)
        messages = []
        for item in results.results:
            if parse_role(item.role) == "assistant":
                messages.append(AIMessage(content=item.content))
            else:
                messages.append(HumanMessage(content=item.content))

        return {self.memory_key: messages}

    @with_remembr_fallback()
    def clear(self) -> None:
        self._run(self.client.forget_session(self.session_id))
