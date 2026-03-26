"""Ceveto MCP server — dual mode: stdio (single-user) and hosted (multi-tenant)."""

from __future__ import annotations

import json
import sys

from mcp.server.fastmcp import FastMCP

from ceveto_mcp.client import CevetoAPIClient
from ceveto_mcp.config import MCPConfig
from ceveto_mcp.openapi_tools import register_openapi_tools
from ceveto_mcp.permissions import get_allowed_tags


def create_server(
    config: MCPConfig,
    preloaded: dict | None = None,
) -> FastMCP:
    """Create MCP server in stdio or hosted mode."""
    if config.hosted_mode:
        return _create_hosted_server(config, preloaded)
    return _create_stdio_server(config, preloaded)


# ---------------------------------------------------------------------------
# Stdio mode (single user, credentials from env)
# ---------------------------------------------------------------------------


def _create_stdio_server(
    config: MCPConfig, preloaded: dict | None
) -> FastMCP:
    api = CevetoAPIClient(
        config.base_url, config.username or '', config.private_key or ''
    )
    if config.default_account:
        api.set_default_account(config.default_account)

    server = FastMCP(name='ceveto-api')
    _register_meta_tools(server, static_api=api)

    if preloaded:
        _register_stdio_tools(server, api, config, preloaded)
    else:
        print(
            'Warning: No preloaded schema — only meta tools.',
            file=sys.stderr,
        )

    return server


def _register_stdio_tools(
    server: FastMCP,
    api: CevetoAPIClient,
    config: MCPConfig,
    preloaded: dict,
) -> None:
    schema = preloaded['schema']
    me = preloaded['me']

    permissions = me.get('permissions', {})
    is_owner = me.get('is_owner', False)
    permitted_tags = get_allowed_tags(permissions, is_owner=is_owner)

    allowed_tags = None
    if config.modules:
        allowed_tags = {
            t.strip() for t in config.modules.split(',') if t.strip()
        }
        if permitted_tags is not None:
            allowed_tags = allowed_tags & permitted_tags
    elif permitted_tags is not None:
        allowed_tags = permitted_tags

    count = register_openapi_tools(
        server,
        schema,
        api=api,
        prefix='/api/',
        allowed_tags=allowed_tags,
        permissions=permissions,
        is_owner=is_owner,
    )
    print(f'Registered {count} API tools.', file=sys.stderr)


# ---------------------------------------------------------------------------
# Hosted mode (multi-tenant, per-session credentials)
# ---------------------------------------------------------------------------


def _create_hosted_server(
    config: MCPConfig, preloaded: dict | None
) -> FastMCP:
    server = FastMCP(name='ceveto-api')
    _register_meta_tools(server, static_api=None)

    if preloaded and 'schema' in preloaded:
        # Register all tools without static api — client resolved per-session
        count = register_openapi_tools(
            server,
            preloaded['schema'],
            api=None,
            prefix='/api/',
        )
        print(
            f'Hosted mode: registered {count} tools (auth per-session).',
            file=sys.stderr,
        )

    return server


# ---------------------------------------------------------------------------
# Meta tools (work in both modes)
# ---------------------------------------------------------------------------


def _register_meta_tools(
    server: FastMCP,
    static_api: CevetoAPIClient | None = None,
) -> None:
    def _resolve_api() -> CevetoAPIClient | None:
        from ceveto_mcp.session import get_session_state

        state = get_session_state()
        return state.api_client if state else static_api

    @server.tool()
    async def whoami() -> str:
        """Show the current API user's identity, active account, and permissions.

        Use this first to understand which account you're operating on
        and what permissions are available.
        """
        api = _resolve_api()
        if not api:
            return json.dumps({'error': 'Not authenticated'})
        return json.dumps(
            await api.get('/company-api/me/'), indent=2, default=str
        )

    @server.tool()
    async def list_accounts() -> str:
        """List all accounts this API key has access to.

        Each entry includes the account id, name, slug, and whether
        the API user is an owner.
        """
        api = _resolve_api()
        if not api:
            return json.dumps({'error': 'Not authenticated'})
        return json.dumps(
            await api.get('/company-api/me/accounts/'),
            indent=2,
            default=str,
        )

    @server.tool()
    async def switch_default_account(account: str) -> str:
        """Switch the active account for all subsequent tool calls.

        Args:
            account: Account slug (e.g. "acme-corp") or UUID.
        """
        api = _resolve_api()
        if not api:
            return json.dumps({'error': 'Not authenticated'})
        api.set_default_account(account)
        return f'Default account set to: {account}'
