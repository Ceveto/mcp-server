"""Permission-based tool filtering for MCP server."""

from __future__ import annotations

# Map OpenAPI tags to permission module names from PERMISSION_MODULES.
# Tags not listed here are always allowed (no permission check).
TAG_TO_MODULE: dict[str, str] = {
    'Contacts': 'contacts',
    'Locations': 'locations',
    'Tasks': 'tasks',
    'Task Approvals': 'tasks',
    'Task Automation': 'tasks',
    'Task Calendar': 'tasks',
    'Task Categories': 'tasks',
    'Task Comments': 'tasks',
    'Task Completion Gates': 'tasks',
    'Task Events': 'tasks',
    'Task Forms': 'tasks',
    'Task Inspection Runs': 'tasks',
    'Task Inspection Steps': 'tasks',
    'Task Inspection Templates': 'tasks',
    'Task Participants': 'tasks',
    'Task Recurring': 'tasks',
    'Task Signatures': 'tasks',
    'Task Time Entries': 'tasks',
    'Task Types': 'tasks',
    'Task Workflows': 'tasks',
    'CMMS': 'cmms',
    'CMMS - Assets': 'cmms',
    'CMMS - Categories': 'cmms',
    'CMMS - Measurements': 'cmms',
    'CMMS - Parts': 'cmms',
    'Tags': 'tags',
    'Teams': 'teams',
    'Skills': 'skills',
    'Orders': 'payments',
    'Payments': 'payments',
    'Currencies': 'payments',
    'Traksy': 'traksy',
    'Traksy - Schedules': 'traksy',
    'Traksy - Time Entries': 'traksy',
    'Traksy - Work Units': 'traksy',
    'Documents': 'documents',
    'Account Accesses': 'account_accesses',
    'Invites': 'account_accesses',
    'Manufacturers': 'cmms',
    'Suppliers': 'cmms',
    'Audit': 'audit',
    'Webhooks': 'webhooks',
    'API Keys': 'account_accesses',
    'My API Key': 'account_accesses',
    'Subscriptions': 'subscriptions',
}

# Tags that are always allowed regardless of permissions
ALWAYS_ALLOWED_TAGS = {
    'Me', 'Accounts', 'Reports', 'Dashboard',
    'health', 'meta', 'Calculator', 'Permissions',
}


# HTTP method to permission action mapping
METHOD_TO_ACTION: dict[str, str] = {
    'get': 'read',
    'post': 'write',
    'put': 'write',
    'patch': 'write',
    'delete': 'write',
}


def get_allowed_tags(
    permissions: dict, is_owner: bool = False
) -> set[str] | None:
    """Determine which OpenAPI tags this user can access.

    Args:
        permissions: User's permissions dict from /me/.
        is_owner: Whether the user is an account owner.

    Returns:
        Set of allowed tag names, or None if all allowed (owner).
    """
    if is_owner:
        return None

    accessible_modules = {
        module
        for module, actions in permissions.items()
        if isinstance(actions, dict) and actions
    }

    allowed = set(ALWAYS_ALLOWED_TAGS)
    for tag, module in TAG_TO_MODULE.items():
        if module in accessible_modules:
            allowed.add(tag)

    return allowed


def is_method_allowed(
    permissions: dict,
    is_owner: bool,
    tags: list[str],
    method: str,
) -> bool:
    """Check if a specific HTTP method is allowed for an operation's tags.

    Args:
        permissions: User's permissions dict.
        is_owner: Whether the user is an account owner.
        tags: OpenAPI tags for the operation.
        method: HTTP method (get, post, put, patch, delete).

    Returns:
        True if the method is allowed.
    """
    if is_owner:
        return True

    required_action = METHOD_TO_ACTION.get(method, 'read')

    for tag in tags:
        module = TAG_TO_MODULE.get(tag)
        if not module:
            continue  # Unmapped tags are always allowed

        module_perms = permissions.get(module, {})
        if not isinstance(module_perms, dict):
            return False

        # Check direct action
        if required_action in module_perms:
            return True

        # Check hierarchy (admin implies write implies read)
        if required_action == 'read' and (
            'write' in module_perms or 'admin' in module_perms
        ):
            return True
        if required_action == 'write' and 'admin' in module_perms:
            return True

        return False

    return True  # No mapped tags = always allowed


def get_conditions_for_method(
    permissions: dict,
    tags: list[str],
    method: str,
) -> dict[str, str]:
    """Get condition limits applicable to an operation.

    Returns a dict of human-readable limits, e.g.
    {"max_amount": "5000"}.
    """
    action = METHOD_TO_ACTION.get(method, 'read')
    if action == 'read':
        return {}

    for tag in tags:
        module = TAG_TO_MODULE.get(tag)
        if not module:
            continue
        module_perms = permissions.get(module, {})
        if not isinstance(module_perms, dict):
            continue
        action_data = module_perms.get(action, {})
        if isinstance(action_data, dict) and action_data:
            return {k: str(v) for k, v in action_data.items()}

    return {}
