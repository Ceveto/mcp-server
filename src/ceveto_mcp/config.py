"""MCP server configuration."""

from pydantic_settings import BaseSettings


class MCPConfig(BaseSettings):
    base_url: str = 'https://app.ceveto.com'
    username: str  # API user username (X-API-Key value)
    private_key: str  # Ed25519 private key, hex-encoded (64 chars)
    default_account: str = ''  # Optional slug/UUID for default account
    transport: str = 'stdio'  # stdio or sse
    port: int = 8500  # SSE mode port
    # Comma-separated list of OpenAPI tags to include as tools.
    # Empty = all tags. Example: "Contacts,Tasks,Locations"
    modules: str = ''

    model_config = {'env_prefix': 'CEVETO_MCP_'}
