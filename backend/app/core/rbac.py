"""Role-based access control.

Roles are hierarchical: admin ⊃ annotator ⊃ reviewer ⊃ viewer for read, but specific
mutating actions are gated by explicit permission sets to keep checks auditable.
"""
from __future__ import annotations

import enum


class Role(str, enum.Enum):
    ADMIN = "admin"
    ANNOTATOR = "annotator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class Permission(str, enum.Enum):
    DATASET_CREATE = "dataset:create"
    DATASET_DELETE = "dataset:delete"
    JOB_CREATE = "job:create"
    JOB_CANCEL = "job:cancel"
    REVIEW_SUBMIT = "review:submit"
    EXPORT_CREATE = "export:create"
    USER_MANAGE = "user:manage"
    AUDIT_READ = "audit:read"


_ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),  # everything
    Role.ANNOTATOR: {
        Permission.DATASET_CREATE,
        Permission.JOB_CREATE,
        Permission.JOB_CANCEL,
        Permission.EXPORT_CREATE,
    },
    Role.REVIEWER: {Permission.REVIEW_SUBMIT, Permission.EXPORT_CREATE},
    Role.VIEWER: set(),
}


def has_permission(role: Role | str, permission: Permission) -> bool:
    role = Role(role)
    return permission in _ROLE_PERMISSIONS[role]


def require(role: Role | str, permission: Permission) -> None:
    """Raise PermissionError if the role lacks the permission."""
    if not has_permission(role, permission):
        raise PermissionError(f"role '{role}' lacks permission '{permission.value}'")
