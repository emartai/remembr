"""Shared base classes and utilities for Remembr framework adapters."""

from .error_handling import with_remembr_fallback
from .remembr_adapter_base import BaseRemembrAdapter
from .utils import (
    deduplicate_episodes,
    format_messages_for_llm,
    parse_role,
    scope_from_agent_metadata,
    truncate_to_token_limit,
)

__all__ = [
    "BaseRemembrAdapter",
    "with_remembr_fallback",
    "format_messages_for_llm",
    "truncate_to_token_limit",
    "scope_from_agent_metadata",
    "deduplicate_episodes",
    "parse_role",
]
