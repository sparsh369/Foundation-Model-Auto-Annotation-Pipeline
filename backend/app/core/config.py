"""Centralised, type-safe application configuration.

All settings are sourced from environment variables (12-factor) with sensible local
defaults. Derived DSNs keep the rest of the codebase from string-building connection URLs.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = "Foundation-Model Auto-Annotation Pipeline"
    environment: Literal["local", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = True

    # ── Security ─────────────────────────────────────────────────
    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 43_200
    jwt_algorithm: str = "HS256"
    rate_limit_per_minute: int = 120

    # ── Database ─────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "annotator"
    postgres_password: str = "annotator"
    postgres_db: str = "annotation"
    database_url: str | None = None  # explicit override wins

    # ── Redis / broker ───────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Object storage ───────────────────────────────────────────
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "annotations"
    s3_use_ssl: bool = False

    # ── ML / pipeline ────────────────────────────────────────────
    pipeline_mock_models: bool = True
    device: Literal["cuda", "cpu", "mps"] = "cuda"
    gdino_config_path: str = "/weights/groundingdino/config.py"
    gdino_weights_path: str = "/weights/groundingdino/groundingdino_swint_ogc.pth"
    sam2_config: str = "sam2_hiera_l.yaml"
    sam2_checkpoint: str = "/weights/sam2/sam2_hiera_large.pt"
    clip_model: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"
    vlm_provider: Literal["openai", "azure", "mock"] = "mock"
    openai_api_key: str | None = None
    vlm_model: str = "gpt-4o"
    inference_batch_size: int = 8
    max_detections_per_image: int = 100

    # ── Confidence thresholds ────────────────────────────────────
    conf_auto_approve: float = 0.85
    conf_human_review: float = 0.50
    conf_reject: float = 0.20

    # ── Integrations ─────────────────────────────────────────────
    cvat_url: str | None = None
    cvat_token: str | None = None
    label_studio_url: str | None = None
    label_studio_token: str | None = None

    # ── MLOps / observability ────────────────────────────────────
    mlflow_tracking_uri: str | None = None
    wandb_api_key: str | None = None
    otel_exporter_otlp_endpoint: str | None = None
    prometheus_enabled: bool = True

    # ── Derived DSNs ─────────────────────────────────────────────
    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Sync DSN for Alembic + Celery workers (which use a sync session)."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
