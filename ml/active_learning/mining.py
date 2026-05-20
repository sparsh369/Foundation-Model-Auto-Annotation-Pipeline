"""Hard-sample mining & uncertainty ranking for active learning.

Surfaces the images most worth a human's time: low overall confidence, high internal
disagreement, or empty detections on a non-trivial prompt set.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Candidate:
    image_id: str
    confidence: float
    n_detections: int
    weakest: float
    reason: str
    priority: float  # higher = more valuable to label next


def score_candidates(
    rows: list[dict], *, review_high: float = 0.85
) -> list[Candidate]:
    """`rows` are confidence dicts persisted by the pipeline (one per annotation)."""
    out: list[Candidate] = []
    for r in rows:
        overall = float(r.get("overall", 0.0))
        weakest = float(r.get("weakest", overall))
        n = int(r.get("n_detections", 0))

        if n == 0:
            reason, priority = "no_detections", 1.0
        elif overall < 0.4:
            reason, priority = "low_confidence", 0.9 - overall
        elif (overall - weakest) > 0.3:
            reason, priority = "internal_disagreement", 0.6 + (overall - weakest)
        elif overall < review_high:
            reason, priority = "borderline", review_high - overall
        else:
            continue  # confident — skip

        out.append(
            Candidate(
                image_id=r["image_id"],
                confidence=overall,
                n_detections=n,
                weakest=weakest,
                reason=reason,
                priority=round(priority, 4),
            )
        )
    out.sort(key=lambda c: c.priority, reverse=True)
    return out
