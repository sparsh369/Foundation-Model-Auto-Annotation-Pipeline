"""Stage 4 — Vision-Language Model (GPT-4V / pluggable) captioning & tagging.

The VLM is the most expensive per-image call, so the pipeline gates it (see pipeline.py):
it runs only when requested and ideally only on ambiguous images. Provider is swappable
via VLM_PROVIDER (openai | azure | mock).
"""
from __future__ import annotations

import base64
import json

import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

log = get_logger(__name__)

_PROMPT = (
    "You are an annotation assistant. Given an image and a list of detected object labels, "
    "return strict JSON: {\"caption\": str, \"tags\": [str], \"corrections\": [str]}. "
    "caption: one factual sentence. tags: 3-8 salient concepts. corrections: labels that "
    "appear wrong or missing. No prose outside the JSON."
)


class VLMCaptioner:
    version = f"vlm-{settings.vlm_provider}-{settings.vlm_model}"

    def __init__(self) -> None:
        self.mock = settings.pipeline_mock_models or settings.vlm_provider == "mock"
        if self.mock:
            return
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.openai_api_key)

    def caption(self, image: np.ndarray, labels: list[str]) -> dict:
        if self.mock:
            return self._mock_caption(labels)

        import cv2

        ok, buf = cv2.imencode(".jpg", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if not ok:
            return {"caption": None, "tags": [], "corrections": []}
        b64 = base64.b64encode(buf.tobytes()).decode()

        resp = self.client.chat.completions.create(
            model=settings.vlm_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Detected labels: {labels}"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                    ],
                },
            ],
            max_tokens=400,
            temperature=0.0,
        )
        try:
            return json.loads(resp.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            log.warning("vlm_non_json_response")
            return {"caption": None, "tags": [], "corrections": []}

    def _mock_caption(self, labels: list[str]) -> dict:
        uniq = list(dict.fromkeys(labels))
        cap = (
            f"An image containing {', '.join(uniq)}." if uniq else "An image with no salient objects."
        )
        return {"caption": cap, "tags": uniq[:8], "corrections": []}
