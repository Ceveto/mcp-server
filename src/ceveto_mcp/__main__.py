"""Entry point: python -m ceveto_mcp [--transport stdio|sse]."""

import argparse
import asyncio
import logging
import sys

from ceveto_mcp.client import CevetoAPIClient
from ceveto_mcp.config import MCPConfig
from ceveto_mcp.server import create_server

logger = logging.getLogger(__name__)


async def _preload_tools(config: MCPConfig) -> dict | None:
    """Fetch OpenAPI schema and /me/ before server starts."""
    api = CevetoAPIClient(
        config.base_url, config.username, config.private_key
    )
    if config.default_account:
        api.set_default_account(config.default_account)

    try:
        schema = await api.get('/api/openapi.json')
        me = await api.get('/company-api/me/')
        return {'schema': schema, 'me': me}
    except Exception as e:
        print(f'Warning: Could not preload API tools: {e}', file=sys.stderr)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description='Ceveto MCP Server')
    parser.add_argument(
        '--transport',
        choices=['stdio', 'sse'],
        default=None,
    )
    parser.add_argument('--port', type=int, default=None)
    args = parser.parse_args()

    config = MCPConfig()  # type: ignore[call-arg]
    transport = args.transport or config.transport
    port = args.port or config.port

    # Preload OpenAPI schema + permissions before creating server
    preloaded = asyncio.run(_preload_tools(config))

    server = create_server(config, preloaded=preloaded)

    if transport == 'sse':
        server.run(transport='sse', host='0.0.0.0', port=port)  # type: ignore[call-arg]
    else:
        server.run(transport='stdio')


if __name__ == '__main__':
    main()
