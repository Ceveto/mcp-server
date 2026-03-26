"""Entry point: python -m ceveto_mcp [--transport stdio|sse] [--hosted]."""

import argparse
import asyncio
import sys

import httpx

from ceveto_mcp.client import CevetoAPIClient
from ceveto_mcp.config import MCPConfig
from ceveto_mcp.server import create_server


async def _preload_tools(config: MCPConfig) -> dict | None:
    """Fetch OpenAPI schema + /me/ (stdio mode — needs credentials)."""
    api = CevetoAPIClient(
        config.base_url, config.username or '', config.private_key or ''
    )
    if config.default_account:
        api.set_default_account(config.default_account)
    try:
        schema = await api.get('/api/openapi.json')
        me = await api.get('/company-api/me/')
        return {'schema': schema, 'me': me}
    except Exception as e:
        print(f'Warning: Could not preload: {e}', file=sys.stderr)
        return None


async def _preload_schema(base_url: str) -> dict | None:
    """Fetch only OpenAPI schema (hosted mode — no auth needed)."""
    try:
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f'{base_url}/api/openapi.json')
            resp.raise_for_status()
            return {'schema': resp.json()}
    except Exception as e:
        print(f'Warning: Could not preload schema: {e}', file=sys.stderr)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description='Ceveto MCP Server')
    parser.add_argument(
        '--transport',
        choices=['stdio', 'sse', 'streamable-http'],
        default=None,
    )
    parser.add_argument('--port', type=int, default=None)
    parser.add_argument(
        '--hosted',
        action='store_true',
        help='Multi-tenant hosted mode (no credentials needed)',
    )
    args = parser.parse_args()

    config = MCPConfig(hosted_mode=args.hosted)  # type: ignore[call-arg]

    if args.hosted:
        transport = args.transport or 'sse'
        preloaded = asyncio.run(_preload_schema(config.base_url))
    else:
        config.validate_credentials()
        transport = args.transport or config.transport
        preloaded = asyncio.run(_preload_tools(config))

    port = args.port or config.port
    server = create_server(config, preloaded=preloaded)

    if transport == 'streamable-http':
        server.run(transport='streamable-http')
    elif transport == 'sse':
        server.run(transport='sse', host='0.0.0.0', port=port)  # type: ignore[call-arg]
    else:
        server.run(transport='stdio')


if __name__ == '__main__':
    main()
