from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test_secret_key_min_32_chars_0123456789ab")
os.environ.setdefault("PIPELINE_MOCK_MODELS", "true")
os.environ.setdefault("DEVICE", "cpu")
os.environ.setdefault("VLM_PROVIDER", "mock")

import numpy as np
import pytest


@pytest.fixture
def rgb_image() -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.integers(0, 255, size=(256, 256, 3), dtype=np.uint8)


@pytest.fixture
def png_bytes(rgb_image) -> bytes:
    import io

    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.fromarray(rgb_image).save(buf, format="PNG")
    return buf.getvalue()
