from __future__ import annotations

import pytest

from backend.app.core.rbac import Permission, Role, has_permission, require
from backend.app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_roundtrip():
    h = hash_password("hunter2pass")
    assert verify_password("hunter2pass", h)
    assert not verify_password("wrong", h)


def test_access_token_carries_role():
    token = create_access_token("user-123", Role.ANNOTATOR.value)
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-123"
    assert payload["role"] == "annotator"
    assert payload["type"] == "access"


def test_rbac_matrix():
    assert has_permission(Role.ADMIN, Permission.USER_MANAGE)
    assert has_permission(Role.ANNOTATOR, Permission.JOB_CREATE)
    assert not has_permission(Role.REVIEWER, Permission.JOB_CREATE)
    assert not has_permission(Role.VIEWER, Permission.DATASET_CREATE)
    assert has_permission(Role.REVIEWER, Permission.REVIEW_SUBMIT)


def test_require_raises_for_missing_permission():
    with pytest.raises(PermissionError):
        require(Role.VIEWER, Permission.DATASET_DELETE)
