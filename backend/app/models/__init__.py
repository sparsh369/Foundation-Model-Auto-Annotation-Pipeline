"""Import all models so Alembic + Base.metadata see them."""
from backend.app.models.annotation import Annotation  # noqa: F401
from backend.app.models.audit import AuditLog  # noqa: F401
from backend.app.models.dataset import Dataset  # noqa: F401
from backend.app.models.image import Image  # noqa: F401
from backend.app.models.job import Job  # noqa: F401
from backend.app.models.model_run import ModelRun  # noqa: F401
from backend.app.models.review import Review  # noqa: F401
from backend.app.models.user import User  # noqa: F401
