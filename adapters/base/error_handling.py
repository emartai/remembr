"""Shared fallback error handling for adapter methods."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable

try:
    from remembr.exceptions import RemembrError
except Exception:  # pragma: no cover
    class RemembrError(Exception):
        pass


def _fallback_for_annotation(annotation: Any) -> Any:
    if annotation in (dict, "dict", "dict[str, Any]"):
        return {}
    if annotation in (list, "list", "list[Any]", "list[str]"):
        return []
    if annotation in (str, "str"):
        return ""
    return None


def with_remembr_fallback(default_value: Any = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except RemembrError as err:
                adapter_name = args[0].__class__.__name__ if args else "UnknownAdapter"
                logging.getLogger(__name__).warning(
                    "[%s.%s] Remembr fallback triggered: %s",
                    adapter_name,
                    fn.__name__,
                    err,
                )
                if callable(default_value):
                    return default_value()
                if default_value is not None:
                    return default_value
                return _fallback_for_annotation(fn.__annotations__.get("return"))

        return wrapper

    return decorator
