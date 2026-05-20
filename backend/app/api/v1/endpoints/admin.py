from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_session, require_permission
from backend.app.core.rbac import Permission
from backend.app.models.audit import AuditLog
from backend.app.models.user import User

router = APIRouter()


@router.get("/audit")
async def audit_log(
    entity_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.AUDIT_READ)),
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(r.id),
            "actor_id": str(r.actor_id) if r.actor_id else None,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "meta": r.meta,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
