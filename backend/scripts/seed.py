"""Idempotently seed an initial admin user. Safe to run on every boot."""
from __future__ import annotations

from sqlalchemy import select

from backend.app.core.logging import configure_logging, get_logger
from backend.app.core.rbac import Role
from backend.app.core.security import hash_password
from backend.app.db.session import SyncSessionLocal
from backend.app.models.user import User

configure_logging()
log = get_logger(__name__)

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin12345"  # override in real deploys via a Secret-backed bootstrap


def main() -> None:
    with SyncSessionLocal() as db:
        exists = db.execute(select(User).where(User.email == ADMIN_EMAIL)).scalar_one_or_none()
        if exists:
            log.info("admin already present", email=ADMIN_EMAIL)
            return
        db.add(
            User(
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                full_name="Bootstrap Admin",
                role=Role.ADMIN,
            )
        )
        db.commit()
        log.info("seeded admin", email=ADMIN_EMAIL)


if __name__ == "__main__":
    main()
