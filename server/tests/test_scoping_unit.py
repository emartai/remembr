"""Compatibility smoke tests for scoping module."""

from sqlalchemy.sql.elements import False_

from app.services.scoping import ScopeResolver


def test_empty_scopes_returns_false_sql_expression() -> None:
    clause = ScopeResolver.to_sql_filter([])
    assert isinstance(clause, False_)
