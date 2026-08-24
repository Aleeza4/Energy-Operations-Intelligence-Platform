"""
Unit tests for EOIP database session management.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from eoip.database.session import create_session_factory, session_scope


def test_create_session_factory() -> None:
    """Verify that the session factory uses the expected settings."""
    engine = Mock()

    factory = create_session_factory(engine)

    assert factory.kw["bind"] is engine
    assert factory.class_.__name__ == Session.__name__
    assert factory.class_.__module__ == Session.__module__
    assert factory.kw["autoflush"] is False
    assert factory.kw["expire_on_commit"] is False


def test_session_scope_commits_and_closes_on_success() -> None:
    """Verify successful sessions are committed and closed."""
    session = Mock(spec=Session)
    session_factory = Mock(return_value=session)

    with session_scope(session_factory) as yielded_session:
        assert yielded_session is session

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()


def test_session_scope_rolls_back_and_closes_on_error() -> None:
    """Verify failed sessions are rolled back and closed."""
    session = Mock(spec=Session)
    session_factory = Mock(return_value=session)

    with (
        pytest.raises(RuntimeError, match="database failure"),
        session_scope(session_factory),
    ):
        raise RuntimeError("database failure")

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()


def test_session_scope_returns_new_session_from_factory() -> None:
    """Verify the context manager obtains a session from the factory."""
    session = Mock(spec=Session)
    session_factory = Mock(return_value=session)

    with session_scope(session_factory):
        pass

    session_factory.assert_called_once_with()
