from __future__ import annotations

from ml.pipeline import PipelineConfig, pipeline


def test_pipeline_runs_end_to_end_in_mock_mode(png_bytes):
    cfg = PipelineConfig(prompts=["cat", "dog", "car"])
    ann, conf = pipeline.run("img-1", png_bytes, cfg)

    assert conf["routing"] in {"auto_approve", "needs_review", "reject"}
    assert conf["n_detections"] == len(ann.detections)
    assert "timings" in conf and "detect" in conf["timings"]
    for d in ann.detections:
        assert d.label in {"cat", "dog", "car"}
        assert 0.0 <= d.confidence <= 1.0
        assert d.mask is not None  # segmentation ran
        assert d.clip_score is not None  # CLIP ran


def test_pipeline_is_deterministic_for_same_image(png_bytes):
    cfg = PipelineConfig(prompts=["cat"])
    a, _ = pipeline.run("img-1", png_bytes, cfg)
    b, _ = pipeline.run("img-1", png_bytes, cfg)
    assert len(a.detections) == len(b.detections)
