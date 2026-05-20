from __future__ import annotations

import numpy as np

from ml.active_learning.drift import detect_drift
from ml.active_learning.mining import score_candidates


def test_mining_ranks_empty_and_low_confidence_first():
    rows = [
        {"image_id": "a", "overall": 0.95, "weakest": 0.9, "n_detections": 3},
        {"image_id": "b", "overall": 0.0, "weakest": 0.0, "n_detections": 0},
        {"image_id": "c", "overall": 0.3, "weakest": 0.3, "n_detections": 2},
    ]
    ranked = score_candidates(rows)
    ids = [c.image_id for c in ranked]
    assert "a" not in ids  # confident → skipped
    assert ids[0] == "b"  # no detections → top priority


def test_drift_detects_distribution_shift():
    rng = np.random.default_rng(0)
    reference = rng.normal(0, 1, size=(500, 8))
    shifted = rng.normal(3, 1, size=(500, 8))
    result = detect_drift(reference, shifted)
    assert result["drift_detected"] is True
    assert result["mean_psi"] > 0.2


def test_no_drift_for_same_distribution():
    rng = np.random.default_rng(1)
    a = rng.normal(0, 1, size=(500, 8))
    b = rng.normal(0, 1, size=(500, 8))
    assert detect_drift(a, b)["drift_detected"] is False
