FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml ./
COPY src/ src/
RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV CEVETO_MCP_TRANSPORT=sse

EXPOSE 8500

ENTRYPOINT ["ceveto-mcp"]
