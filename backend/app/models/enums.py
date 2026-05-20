"""Shared enum types persisted as native Postgres enums."""
from __future__ import annotations

import enum


class DatasetStatus(str, enum.Enum):
    CREATED = "created"
    INGESTING = "ingesting"
    READY = "ready"
    ARCHIVED = "archived"


class ImageStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ANNOTATED = "annotated"
    FAILED = "failed"


class JobType(str, enum.Enum):
    AUTO_ANNOTATE = "auto_annotate"
    EXPORT = "export"
    ACTIVE_LEARNING = "active_learning"
    REANNOTATE = "reannotate"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnnotationStatus(str, enum.Enum):
    AUTO_APPROVED = "auto_approved"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    HUMAN_APPROVED = "human_approved"
    HUMAN_CORRECTED = "human_corrected"


class AnnotationSource(str, enum.Enum):
    PIPELINE = "pipeline"
    HUMAN = "human"


class ReviewDecision(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    CORRECT = "correct"


class ExportFormat(str, enum.Enum):
    COCO = "coco"
    YOLO = "yolo"
    PASCAL_VOC = "pascal_voc"
    CVAT_XML = "cvat_xml"
    LABEL_STUDIO = "label_studio"
