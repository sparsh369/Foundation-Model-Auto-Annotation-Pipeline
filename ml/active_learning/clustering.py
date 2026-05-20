"""Embedding clustering for dataset balancing & diverse sampling.

Clusters image/crop embeddings (e.g., CLIP) with KMeans and selects samples that maximize
coverage — avoids spending review budget on near-duplicates.
"""
from __future__ import annotations

import numpy as np


def cluster_embeddings(embeddings: np.ndarray, n_clusters: int = 16) -> np.ndarray:
    from sklearn.cluster import KMeans

    n_clusters = min(n_clusters, len(embeddings))
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    return km.fit_predict(embeddings)


def diverse_sample(
    embeddings: np.ndarray, image_ids: list[str], budget: int, n_clusters: int = 16
) -> list[str]:
    """Round-robin across clusters, picking the point nearest each cluster centroid first,
    so the returned set is spread across the dataset's modes."""
    from sklearn.cluster import KMeans

    n_clusters = min(n_clusters, len(embeddings))
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit(embeddings)
    labels = km.labels_

    # rank points within each cluster by distance to centroid
    buckets: dict[int, list[tuple[float, str]]] = {c: [] for c in range(n_clusters)}
    for emb, iid, c in zip(embeddings, image_ids, labels, strict=False):
        dist = float(np.linalg.norm(emb - km.cluster_centers_[c]))
        buckets[int(c)].append((dist, iid))
    for c in buckets:
        buckets[c].sort()

    selected: list[str] = []
    while len(selected) < budget and any(buckets.values()):
        for c in range(n_clusters):
            if buckets[c]:
                selected.append(buckets[c].pop(0)[1])
                if len(selected) >= budget:
                    break
    return selected
