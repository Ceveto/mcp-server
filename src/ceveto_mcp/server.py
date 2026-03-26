"""Ceveto MCP server — dynamic tools from OpenAPI schema."""

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
    """Create MCP server with tools from OpenAPI schema.

    Args:
        config: MCP configuration.
        preloaded: Optional dict with 'schema' and 'me' keys,
            fetched before server starts. If None, only meta tools
            are available (dynamic loading still works via load_api_tools).
    """
    api = CevetoAPIClient(
        config.base_url, config.username, config.private_key
    )
    if config.default_account:
        api.set_default_account(config.default_account)

    server = FastMCP(name='ceveto-api')

    _register_meta_tools(server, api)

    # Register API tools from preloaded OpenAPI schema
    if preloaded:
        _register_preloaded_tools(
            server, api, config, preloaded
        )
    else:
        print(
            'Warning: No preloaded schema — only meta tools available.',
            file=sys.stderr,
        )

    return server


def _register_preloaded_tools(
    server: FastMCP,
    api: CevetoAPIClient,
    config: MCPConfig,
    preloaded: dict,
) -> None:
    """Register API tools from preloaded OpenAPI schema + permissions."""
    schema = preloaded['schema']
    me = preloaded['me']

    permissions = me.get('permissions', {})
    is_owner = me.get('is_owner', False)

    # Determine allowed tags from permissions
    permitted_tags = get_allowed_tags(permissions, is_owner=is_owner)

    # Filter by configured modules
    allowed_tags = None
    if config.modules:
        allowed_tags = {
            t.strip()
            for t in config.modules.split(',')
            if t.strip()
        }
        # Intersect with permitted tags
        if permitted_tags is not None:
            allowed_tags = allowed_tags & permitted_tags
    elif permitted_tags is not None:
        allowed_tags = permitted_tags

    count = register_openapi_tools(
        server,
        api,
        schema,
        prefix='/api/',
        allowed_tags=allowed_tags,
        permissions=permissions,
        is_owner=is_owner,
    )

    print(f'Registered {count} API tools from OpenAPI schema.', file=sys.stderr)


def _register_meta_tools(
    server: FastMCP, api: CevetoAPIClient
) -> None:
    @server.tool()
    async def whoami() -> str:
        """Show the current API user's identity, active account, and permissions.

        Use this first to understand which account you're operating on
        and what permissions are available.
        """
        return json.dumps(
            await api.get('/company-api/me/'), indent=2, default=str
        )

    @server.tool()
    async def list_accounts() -> str:
        """List all accounts this API key has access to.

        Each entry includes the account id, name, slug, and whether
        the API user is an owner.
        """
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
        api.set_default_account(account)
        return f'Default account set to: {account}'
