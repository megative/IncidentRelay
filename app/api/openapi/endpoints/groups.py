def path_param(name, description):
    """
    Build an integer path parameter.
    """
    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": {"type": "integer", "minimum": 1},
    }


def json_body(description, schema, required=True):
    """
    Build a JSON request body.
    """
    return {
        "required": required,
        "description": description,
        "content": {
            "application/json": {
                "schema": schema
            }
        },
    }


def response(description, schema=None):
    """
    Build a JSON response.
    """
    item = {"description": description}

    if schema:
        item["content"] = {
            "application/json": {
                "schema": schema
            }
        }

    return item


GROUP_SCHEMA = {
    "type": "object",
    "required": ["slug", "name"],
    "properties": {
        "id": {"type": "integer", "readOnly": True, "example": 1},
        "slug": {
            "type": "string",
            "example": "infra",
            "description": "Stable group slug.",
        },
        "name": {
            "type": "string",
            "example": "Infrastructure",
            "description": "Human-readable group name.",
        },
        "description": {
            "type": "string",
            "nullable": True,
            "example": "Infrastructure access boundary.",
        },
        "active": {
            "type": "boolean",
            "default": True,
            "description": "Whether the group is active.",
        },
    },
}


GROUP_DELETE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "deleted": {"type": "boolean", "example": True},
        "id": {"type": "integer", "example": 1},
        "slug": {"type": "string", "example": "infra"},
        "name": {"type": "string", "example": "Infrastructure"},
    },
}


def tags():
    """
    Return OpenAPI tags.
    """
    return [
        {
            "name": "groups",
            "description": (
                "Access boundaries for teams, users, routes, rotations, "
                "notification channels and silences."
            ),
        }
    ]


def paths():
    """
    Return OpenAPI paths for group endpoints.
    """
    return {
        "/api/groups": {
            "get": {
                "tags": ["groups"],
                "summary": "List groups",
                "description": (
                    "Returns groups visible to the current user. "
                    "Admins see all active groups."
                ),
                "operationId": "listGroups",
                "responses": {
                    "200": response(
                        "List of groups.",
                        {"type": "array", "items": GROUP_SCHEMA},
                    ),
                },
            },
            "post": {
                "tags": ["groups"],
                "summary": "Create group",
                "description": "Creates a new group. Admin permission is required.",
                "operationId": "createGroup",
                "requestBody": json_body("Group properties.", GROUP_SCHEMA),
                "responses": {
                    "201": response("Group created.", GROUP_SCHEMA),
                    "400": response("Validation error."),
                    "403": response("Admin permission is required."),
                },
            },
        },
        "/api/groups/{group_id}": {
            "put": {
                "tags": ["groups"],
                "summary": "Update group",
                "description": (
                    "Updates group properties. Admin or RW access to the group is required."
                ),
                "operationId": "updateGroup",
                "parameters": [path_param("group_id", "Group id.")],
                "requestBody": json_body("Updated group properties.", GROUP_SCHEMA),
                "responses": {
                    "200": response("Group updated.", GROUP_SCHEMA),
                    "400": response("Validation error."),
                    "403": response("Access denied."),
                    "404": response("Group not found."),
                },
            },
            "delete": {
                "tags": ["groups"],
                "summary": "Delete group",
                "description": (
                    "Soft-deletes a group and disables resources under it: "
                    "teams, rotations, routes, notification channels, silences, "
                    "memberships and related API tokens. Historical alerts are preserved. "
                    "Admin permission is required."
                ),
                "operationId": "deleteGroup",
                "parameters": [path_param("group_id", "Group id.")],
                "responses": {
                    "200": response("Group deleted.", GROUP_DELETE_RESPONSE_SCHEMA),
                    "403": response("Admin permission is required."),
                    "404": response("Group not found."),
                },
            },
        },
    }
