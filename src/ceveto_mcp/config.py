"""MCP server configuration."""

from pydantic_settings import BaseSettings


class MCPConfig(BaseSettings):
    base_url: str = 'https://api.ceveto.com'
    username: str | None = None  # Optional for hosted mode
    private_key: str | None = None  # Optional for hosted mode
    default_account: str = ''
    transport: str = 'stdio'  # stdio, sse, or streamable-http
    port: int = 8500
    modules: str = ''  # Comma-separated OpenAPI tags
    hosted_mode: bool = False  # Multi-tenant per-session auth

    model_config = {'env_prefix': 'CEVETO_MCP_'}

    def validate_credentials(self) -> None:
        """Raise if credentials missing in stdio mode."""
        if not self.hosted_mode and (not self.username or not self.private_key):
            raise ValueError(
                'CEVETO_MCP_USERNAME and CEVETO_MCP_PRIVATE_KEY '
                'are required for stdio mode'
            )
