"""Per-session state for multi-tenant hosted mode."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ceveto_mcp.client import CevetoAPIClient


@dataclass
class SessionState:
    api_client: CevetoAPIClient
    permissions: dict
    is_owner: bool


_session_state: ContextVar[SessionState | None] = ContextVar(
    'session_state', default=None
)


def set_session_state(state: SessionState) -> None:
    _session_state.set(state)


def get_session_state() -> SessionState | None:
    return _session_state.get()


def get_session_client() -> CevetoAPIClient:
    """Get API client for current session. Raises if not set."""
    state = get_session_state()
    if not state:
        raise RuntimeError('No session state — not authenticated')
    return state.api_client
