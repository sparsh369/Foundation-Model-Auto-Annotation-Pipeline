"""Data drift detection between a reference and a current embedding distribution.

Uses Population Stability Index (PSI) per principal component as a lightweight,
explainable drift signal that triggers re-annotation / retraining hooks.
"""
from __future__ import annotations

import numpy as np


def _psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.quantile(reference, quantiles)
    edges[0], edges[-1] = -np.inf, np.inf
    ref_hist = np.histogram(reference, bins=edges)[0] / max(len(reference), 1)
    cur_hist = np.histogram(current, bins=edges)[0] / max(len(current), 1)
    ref_hist = np.clip(ref_hist, 1e-6, None)
    cur_hist = np.clip(cur_hist, 1e-6, None)
    return float(np.sum((cur_hist - ref_hist) * np.log(cur_hist / ref_hist)))


def detect_drift(
    reference: np.ndarray, current: np.ndarray, threshold: float = 0.2
) -> dict:
    """Returns mean PSI across feature dims + a boolean trigger.
    PSI < 0.1 ≈ no shift, 0.1–0.2 ≈ moderate, > 0.2 ≈ significant."""
    dims = min(reference.shape[1], current.shape[1])
    psis = [_psi(reference[:, d], current[:, d]) for d in range(dims)]
    mean_psi = float(np.mean(psis))
    return {
        "mean_psi": round(mean_psi, 4),
        "max_psi": round(float(np.max(psis)), 4),
        "drift_detected": mean_psi > threshold,
        "threshold": threshold,
    }
