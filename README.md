# Ceveto MCP Server

MCP (Model Context Protocol) server for AI agent access to the [Ceveto](https://ceveto.com) business management API.

## Quick Start

```bash
uvx --from git+https://github.com/Ceveto/mcp-server ceveto-mcp
```

## Claude Code Setup

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "ceveto": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Ceveto/mcp-server", "ceveto-mcp"],
      "env": {
        "CEVETO_MCP_BASE_URL": "https://api.ceveto.com",
        "CEVETO_MCP_USERNAME": "<your-api-username>",
        "CEVETO_MCP_PRIVATE_KEY": "<your-api-private-key>"
      }
    }
  }
}
```

Or install the [Ceveto Claude Plugin](https://github.com/Ceveto/claude-plugin) for automated setup.

## Getting Credentials

1. Log in to your Ceveto dashboard
2. Go to **Settings → API Keys**
3. Click **Create API Key**
4. Save the username and private key (shown once)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CEVETO_MCP_USERNAME` | Yes | — | API user username |
| `CEVETO_MCP_PRIVATE_KEY` | Yes | — | Ed25519 private key (hex) |
| `CEVETO_MCP_BASE_URL` | No | `https://api.ceveto.com` | API base URL |
| `CEVETO_MCP_DEFAULT_ACCOUNT` | No | — | Default account slug/UUID |
| `CEVETO_MCP_MODULES` | No | — | Comma-separated OpenAPI tags to filter |
| `CEVETO_MCP_TRANSPORT` | No | `stdio` | Transport: `stdio` or `sse` |
| `CEVETO_MCP_PORT` | No | `8500` | Port for SSE mode |

## How It Works

1. On startup, fetches the OpenAPI schema from the Ceveto API
2. Checks your permissions via `/company-api/me/`
3. Generates MCP tools for each permitted API endpoint
4. Tools include parameter schemas, descriptions, and permission limits

## Docker (SSE mode)

```bash
docker build -t ceveto-mcp .
docker run -p 8500:8500 \
  -e CEVETO_MCP_USERNAME=... \
  -e CEVETO_MCP_PRIVATE_KEY=... \
  -e CEVETO_MCP_BASE_URL=https://api.ceveto.com \
  ceveto-mcp
```

## Hosted Instances

| Environment | MCP Server | Backend API |
|-------------|-----------|-------------|
| Production | `https://mcp.ceveto.com` | `https://api.ceveto.com` |
| Staging | `https://mcp.ceveto.dev` | `https://api.ceveto.dev` |

Hosted mode (multi-tenant, no credentials needed on server):

```bash
ceveto-mcp --hosted --transport sse --port 8500
```

## Security

- **Ed25519 signatures** — every API request is cryptographically signed
- **OAuth 2.1** — browser-based authorization with PKCE
- **Permission-filtered tools** — only endpoints you have access to become tools
- **Method-level filtering** — read-only keys don't see write operations
- **No secrets stored** — credentials only in environment variables
