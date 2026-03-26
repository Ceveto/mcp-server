"""Dynamic MCP tool generation from OpenAPI schema."""

from __future__ import annotations

import json
import re

from mcp.server.fastmcp import FastMCP

from ceveto_mcp.client import CevetoAPIClient


# Endpoints to skip
SKIP_PATTERNS = (
    '/health/',
    '/meta/',
    '/openapi.json',
    '/docs',
    '/auth/',
    '/filter-options/',
    '/branding/',
    '/whitelabel/',
    '/permissions/',
    '/calculator/',
    '/archived/',
    '/bulk/',
    '/export/',
    '/csv/',
    '/qr/',
    '/checkout/',
    '/stripe/',
    '/electric/',
    '/signup/',
    '/profile-image/',
    '/subscriptions/',
    '/tiers/',
    '/billing/',
    '/session-status/',
    '/reorder/',
)

# Only include these HTTP methods as tools
ALLOWED_METHODS = {'get', 'post', 'put', 'patch', 'delete'}


def _sanitize_operation_id(op_id: str) -> str:
    """Convert operationId to a clean tool name.

    'contacts_api_routers_contacts_list_contacts' -> 'list_contacts'
    'tasks_api_routers_tasks_create_task' -> 'create_task'
    """
    # Take the last meaningful part after the module path
    parts = op_id.split('_')
    # Find the action word (list, get, create, update, delete, etc.)
    action_words = {
        'list', 'get', 'create', 'update', 'delete', 'archive',
        'restore', 'transition', 'approve', 'reject', 'duplicate',
    }
    for i, part in enumerate(parts):
        if part in action_words:
            return '_'.join(parts[i:])
    # Fallback: use last 2-3 parts
    return '_'.join(parts[-3:]) if len(parts) > 3 else '_'.join(parts)


def _resolve_ref(ref: str, components: dict) -> dict:
    """Resolve a $ref to its schema definition."""
    if not ref.startswith('#/components/schemas/'):
        return {}
    name = ref.split('/')[-1]
    return components.get(name, {})


def _build_input_schema(
    operation: dict, components: dict
) -> dict:
    """Build MCP tool inputSchema from OpenAPI parameters + requestBody."""
    properties: dict = {}
    required: list = []

    # Query/path parameters
    for param in operation.get('parameters', []):
        name = param['name']
        schema = param.get('schema', {})

        # Flatten anyOf [type, null] to just the type
        if 'anyOf' in schema:
            for variant in schema['anyOf']:
                if variant.get('type') != 'null':
                    schema = variant
                    break

        prop: dict = {}
        if 'type' in schema:
            prop['type'] = schema['type']
        if 'title' in schema:
            prop['description'] = schema['title']
        if 'default' in schema:
            prop['default'] = schema['default']
        if 'enum' in schema:
            prop['enum'] = schema['enum']

        properties[name] = prop
        if param.get('required'):
            required.append(name)

    # Request body
    body_content = (
        operation.get('requestBody', {}).get('content', {})
    )
    for mime, spec in body_content.items():
        body_schema = spec.get('schema', {})
        if '$ref' in body_schema:
            body_schema = _resolve_ref(
                body_schema['$ref'], components
            )

        for name, field in body_schema.get('properties', {}).items():
            prop = {}
            if '$ref' in field:
                resolved = _resolve_ref(field['$ref'], components)
                prop['type'] = 'object'
                if 'description' in resolved:
                    prop['description'] = resolved['description']
            elif 'anyOf' in field:
                for variant in field['anyOf']:
                    if variant.get('type') != 'null':
                        prop = dict(variant)
                        break
            else:
                prop = dict(field)

            # Clean up
            prop.pop('title', None)
            if not prop.get('type'):
                prop['type'] = 'string'

            properties[name] = prop

        for req_name in body_schema.get('required', []):
            if req_name not in required:
                required.append(req_name)
        break  # Only first content type

    result: dict = {
        'type': 'object',
        'properties': properties,
    }
    if required:
        result['required'] = required
    return result


def _build_description(
    method: str,
    path: str,
    operation: dict,
    conditions: dict[str, str] | None = None,
) -> str:
    """Build tool description from OpenAPI operation."""
    summary = operation.get('summary', '')
    desc = operation.get('description', '')
    text = desc or summary or f'{method.upper()} {path}'

    # Add parameter hints
    params = operation.get('parameters', [])
    if params:
        param_lines = []
        for p in params:
            name = p['name']
            schema = p.get('schema', {})
            p_type = schema.get('type', '')
            if 'anyOf' in schema:
                for v in schema['anyOf']:
                    if v.get('type') != 'null':
                        p_type = v.get('type', '')
                        break
            required = ' (required)' if p.get('required') else ''
            param_lines.append(f'  {name}: {p_type}{required}')
        if param_lines:
            text += '\n\nParameters:\n' + '\n'.join(param_lines)

    # Add permission condition limits
    if conditions:
        limits = ', '.join(
            f'{k} = {v}' for k, v in conditions.items()
        )
        text += f'\n\nLimits: {limits}'

    return text


def register_openapi_tools(
    server: FastMCP,
    schema: dict,
    *,
    api: CevetoAPIClient | None = None,
    prefix: str = '/api/',
    allowed_tags: set[str] | None = None,
    permissions: dict | None = None,
    is_owner: bool = False,
) -> int:
    """Register MCP tools dynamically from an OpenAPI schema.

    Args:
        server: FastMCP server instance.
        api: Signed HTTP client.
        schema: Parsed OpenAPI schema dict.
        prefix: Only include paths starting with this prefix.
        allowed_tags: If set, only include operations with these tags.
            Tags are case-insensitive. None = include all.
        permissions: User's permissions dict for method-level filtering.
            If set, GET-only for read, POST/PUT/PATCH/DELETE for write.
        is_owner: If True, skip method-level permission checks.

    Returns:
        Number of tools registered.
    """
    paths = schema.get('paths', {})
    components = schema.get('components', {}).get('schemas', {})
    count = 0
    seen_names: set[str] = set()

    # Normalize allowed tags to lowercase
    if allowed_tags:
        allowed_tags = {t.lower().strip() for t in allowed_tags}

    for path, methods in sorted(paths.items()):
        if not path.startswith(prefix):
            continue
        if any(skip in path for skip in SKIP_PATTERNS):
            continue

        for method, operation in methods.items():
            if method not in ALLOWED_METHODS:
                continue

            op_id = operation.get('operationId', '')
            if not op_id:
                continue

            op_tags_raw = operation.get('tags', [])

            # Filter by tags if configured
            if allowed_tags:
                op_tags_lower = {t.lower() for t in op_tags_raw}
                if not op_tags_lower & allowed_tags:
                    continue

            # Filter by method-level permissions (read vs write)
            if permissions is not None and not is_owner:
                from ceveto_mcp.permissions import is_method_allowed

                if not is_method_allowed(
                    permissions, is_owner, op_tags_raw, method
                ):
                    continue

            tool_name = _sanitize_operation_id(op_id)

            # Deduplicate names
            if tool_name in seen_names:
                # Append method prefix
                tool_name = f'{method}_{tool_name}'
            if tool_name in seen_names:
                continue
            seen_names.add(tool_name)

            # Get condition limits for this operation
            conditions = None
            if permissions is not None and not is_owner:
                from ceveto_mcp.permissions import get_conditions_for_method

                conditions = get_conditions_for_method(
                    permissions, op_tags_raw, method
                )

            description = _build_description(
                method, path, operation, conditions or None
            )
            input_schema = _build_input_schema(operation, components)

            # Extract path parameters
            path_params = re.findall(r'\{(\w+)\}', path)

            # Register the tool
            _register_dynamic_tool(
                server=server,
                tool_name=tool_name,
                description=description,
                input_schema=input_schema,
                method=method,
                path_template=path,
                path_params=path_params,
                static_api=api,
            )
            count += 1

    return count


def _register_dynamic_tool(
    *,
    server: FastMCP,
    tool_name: str,
    description: str,
    input_schema: dict,
    method: str,
    path_template: str,
    path_params: list[str],
    static_api: CevetoAPIClient | None = None,
) -> None:
    """Register a single dynamic tool on the MCP server.

    In stdio mode, static_api is set. In hosted mode, the client
    is resolved per-session from session state.
    """

    @server.tool(name=tool_name, description=description)
    async def dynamic_tool(**kwargs: str) -> str:
        from ceveto_mcp.session import get_session_state

        # Resolve client: session state (hosted) or static (stdio)
        state = get_session_state()
        api = state.api_client if state else static_api
        if not api:
            return json.dumps({'error': 'Not authenticated'})

        # FastMCP may pass all args as a single "kwargs" JSON string
        if 'kwargs' in kwargs and len(kwargs) == 1:
            raw = kwargs['kwargs']
            if isinstance(raw, str):
                try:
                    kwargs = json.loads(raw)
                except json.JSONDecodeError:
                    pass

        # Build path with path parameters
        path = path_template
        for pp in path_params:
            if pp in kwargs:
                path = path.replace(f'{{{pp}}}', str(kwargs.pop(pp)))

        # Clean None values
        params = {k: v for k, v in kwargs.items() if v is not None}

        result: dict
        if method == 'get':
            result = await api.get(path, params or None)
        elif method == 'delete':
            result = await api.delete(path)
        elif method == 'post':
            result = await api.post(path, params)
        elif method == 'put':
            result = await api.put(path, params)
        elif method == 'patch':
            result = await api.patch(path, params)
        else:
            result = {'error': f'Unsupported method: {method}'}

        return json.dumps(result, indent=2, default=str)
