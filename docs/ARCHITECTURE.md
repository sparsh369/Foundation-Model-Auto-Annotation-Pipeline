# System Architecture — Foundation-Model Auto-Annotation Pipeline

> Target scale: **10K – 1M+ images per dataset**, throughput bound by GPU fleet size,
> control-plane designed to be stateless and horizontally scalable.

---

## 1. High-Level Architecture (HLD)

```
                               ┌────────────────────────────────────────────┐
                               │                Operators                    │
                               │   Next.js console  ·  CVAT  ·  Label Studio  │
                               └───────────────┬──────────────┬───────────────┘
                                               │ HTTPS/JWT     │ webhooks
                                               ▼              ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              CONTROL PLANE (stateless)                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐             │
│  │  FastAPI     │   │  FastAPI     │ … │  FastAPI     │   │  FastAPI     │  (N replicas)│
│  │  Auth/RBAC   │   │  Datasets    │   │  Jobs        │   │  Reviews     │             │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘             │
│         └──────────────────┴─────────┬────────┴──────────────────┘                      │
└───────────────────────────────────────┼────────────────────────────────────────────────┘
                                         │
        ┌────────────────────┬───────────┼────────────────────┬─────────────────────┐
        ▼                    ▼           ▼                    ▼                     ▼
 ┌────────────┐      ┌────────────┐ ┌────────────┐    ┌────────────┐        ┌────────────┐
 │ PostgreSQL │      │   Redis    │ │  Broker    │    │  S3/MinIO  │        │  MLflow    │
 │ (metadata) │      │ (cache/    │ │ (Redis or  │    │ (images,   │        │ (registry/ │
 │            │      │  rate-lim) │ │  Kafka)    │    │  masks)    │        │  metrics)  │
 └────────────┘      └────────────┘ └─────┬──────┘    └────────────┘        └────────────┘
                                          │ tasks
                ┌─────────────────────────┴──────────────────────────┐
                ▼                                                     ▼
     ┌────────────────────────┐                          ┌────────────────────────┐
     │   GPU WORKER POOL       │   (KEDA / HPA autoscale) │   CPU WORKER POOL        │
     │  Celery · CUDA          │                          │  Celery                  │
     │  ┌──────────────────┐   │                          │  - exports (COCO/YOLO…)  │
     │  │ Stage1 GDINO     │   │                          │  - active-learning jobs  │
     │  │ Stage2 SAM2      │   │                          │  - webhook fan-out       │
     │  │ Stage3 CLIP      │   │                          └────────────────────────┘
     │  │ Stage4 VLM       │   │
     │  │ Stage5 Confidence│   │
     │  └──────────────────┘   │
     └────────────────────────┘
```

**Plane separation.** The *control plane* (FastAPI) owns metadata, auth, routing and is
stateless → trivially horizontally scaled behind an ALB/Ingress. The *data plane* (GPU
workers) is the expensive, autoscaled tier. They communicate **only** through the broker
and object storage — never direct RPC — so a worker crash never takes down the API and
vice-versa.

---

## 2. Tech-Stack Justification

| Concern            | Choice                     | Why                                                                 |
|--------------------|----------------------------|---------------------------------------------------------------------|
| API framework      | FastAPI + Pydantic v2      | Async I/O, automatic OpenAPI, fast serialization, type safety.      |
| Async DB           | SQLAlchemy 2 + asyncpg     | Non-blocking metadata access; mature migrations via Alembic.        |
| Task queue         | Celery (Redis broker)      | Battle-tested, priority queues, retries, visibility into in-flight. |
| Alt. broker        | Kafka (optional)           | At-scale (>100K img/run) durable log + replay + back-pressure.      |
| Object store       | S3 / MinIO                 | Cheap, infinite, presigned URLs keep images off the control plane.  |
| Models             | Grounding DINO/SAM2/CLIP/VLM | Open-vocabulary detection + promptable segmentation + validation.  |
| Frontend           | Next.js + TS + Tailwind    | SSR dashboards, type-safe API client, component velocity.           |
| Orchestration      | Kubernetes + Helm + KEDA   | GPU scheduling, queue-length autoscaling, declarative deploys.      |
| Observability      | Prometheus/Grafana/OTel    | Metrics + traces; per-stage latency and GPU utilization.            |

---

## 3. Service-to-service communication

1. **Client → API** — HTTPS, JWT bearer. Mutations validated by Pydantic + RBAC.
2. **API → Postgres** — async pool; metadata only (no image bytes).
3. **API → S3** — issues *presigned* upload/download URLs; bytes never transit the API.
4. **API → Broker** — enqueues `Job` → fan-out of per-image (or per-shard) tasks.
5. **Worker → S3** — pulls image, writes masks/crops/overlays.
6. **Worker → Postgres** — writes `Annotation` rows + `Job` progress (via a thin results API or direct session).
7. **Worker → MLflow** — logs run params, per-stage latency, confidence histograms.
8. **API → CVAT / Label Studio** — pushes review tasks; receives corrections via webhook.

---

## 4. End-to-end data flow

```
upload ──▶ Image(PENDING) ──▶ enqueue Job ──▶ shard into tasks
   │                                              │
   │                          ┌───────────────────┴───────────────────┐
   │                          ▼ (per image, on GPU worker)             │
   │              Stage1 boxes → Stage2 masks → Stage3 CLIP → Stage4 VLM
   │                          │                                        │
   │                          ▼ Stage5 confidence routing              │
   │        ┌─────────────────┼──────────────────┐                     │
   │        ▼                 ▼                  ▼                      │
   │   AUTO_APPROVED    NEEDS_REVIEW          REJECTED ──▶ reprocess    │
   │        │                 │                                        │
   │        │                 ▼                                        │
   │        │      push to CVAT / Label Studio ──▶ human correction    │
   │        │                 │                                        │
   │        ▼                 ▼                                        │
   └──▶ Annotation(version n) ──▶ export (COCO/YOLO/VOC/CVAT/LS) ──────┘
                              │
                              ▼
                  active learning: mine hard/uncertain samples → re-annotate / retrain hooks
```

---

## 5. Database schema (logical)

```
users(id, email, hashed_password, role, is_active, created_at)
datasets(id, name, description, owner_id→users, image_count, status, created_at)
images(id, dataset_id→datasets, s3_key, width, height, sha256, status, created_at)
jobs(id, dataset_id→datasets, type, status, total, processed, failed,
     params(jsonb), created_by→users, created_at, finished_at)
annotations(id, image_id→images, job_id→jobs, version, status, source,
            label, bbox(jsonb), segmentation(jsonb), caption, tags(jsonb),
            confidence(jsonb), created_at)            -- (image_id, version) unique
reviews(id, annotation_id→annotations, reviewer_id→users, decision,
        corrected_payload(jsonb), notes, created_at)
audit_logs(id, actor_id→users, action, entity_type, entity_id, meta(jsonb), created_at)
model_runs(id, job_id→jobs, model_versions(jsonb), metrics(jsonb), mlflow_run_id, created_at)
```

Indices: `images(dataset_id, status)`, `annotations(image_id, version)`,
`jobs(status)`, `reviews(annotation_id)`, `audit_logs(entity_type, entity_id)`.
`annotations` is the natural partition candidate (by `dataset_id` hash) at >50M rows.

---

## 6. Queue architecture

- **Queues**: `inference` (GPU, high prio), `export` (CPU), `active_learning` (CPU, low prio).
- **Sharding**: a `Job` for N images is split into tasks of `INFERENCE_BATCH_SIZE` so each
  task is right-sized for one GPU forward pass and bounded in runtime (good for retries).
- **Idempotency**: task key = `(job_id, image_id)`; results upsert on `(image_id, version)`.
- **Retries**: exponential backoff, max 3; poison messages → dead-letter + `Job.failed++`.
- **Back-pressure**: at very large scale switch broker to Kafka; consumer lag drives KEDA.

---

## 7. GPU worker architecture & memory strategy

- **Lazy singletons**: each worker process loads each model **once** (`ml/registry.py`),
  pinned to one GPU. Models stay resident across tasks → amortize multi-second load cost.
- **Batching**: Grounding DINO + CLIP run on micro-batches (`INFERENCE_BATCH_SIZE`); SAM 2
  reuses a single image embedding to prompt many boxes (the expensive encoder runs once).
- **Memory guards**: `torch.inference_mode()`, `autocast(fp16)`, explicit
  `torch.cuda.empty_cache()` between oversized batches; `MAX_DETECTIONS_PER_IMAGE` caps
  SAM 2 prompt fan-out to bound VRAM.
- **Isolation**: one model-set per worker replica; concurrency=1 per GPU to avoid OOM from
  interleaved peaks. Scale by adding replicas, not threads.

---

## 8. Inference orchestration

`ml/pipeline.py` is a deterministic 5-stage DAG with typed dataclasses passed between
stages. Each stage is independently mockable (`PIPELINE_MOCK_MODELS`) so the control plane
and queueing can be exercised without GPUs. Cross-stage agreement (DINO ∩ CLIP ∩ VLM) feeds
the confidence engine (§ confidence in `ml/confidence/engine.py`).

---

## 9. Scaling strategy

- **Control plane**: HPA on CPU/RPS; stateless, so scale 2→50 pods freely.
- **GPU workers**: **KEDA** scaler on broker queue length (`inference`), `1 pod : 1 GPU`.
  `maxReplicaCount` = node-pool size; cluster-autoscaler adds GPU nodes on pending pods.
- **DB**: read replicas for analytics dashboards; PgBouncer for connection multiplexing.
- **Storage**: S3 scales infinitely; use prefix sharding (`{dataset}/{sha[:2]}/…`).

---

## 10. Cost optimization

- GPU nodes on **spot/preemptible** with checkpointed per-image idempotency → safe to evict.
- Scale GPU pool to **zero** when `inference` queue is empty (KEDA `minReplicaCount: 0`).
- VLM (GPT-4V) is the most expensive per-call stage → only invoke when DINO/CLIP agreement
  is *ambiguous* (configurable gate), not on every image.
- Mixed precision + batching reduces GPU-seconds per image ~2–3×.

---

## 11. Failure recovery

| Failure                 | Mitigation                                                            |
|-------------------------|-----------------------------------------------------------------------|
| Worker OOM / evict      | Task retried on another worker; idempotent upsert prevents dupes.     |
| Poison image            | 3 retries → dead-letter queue, `Job.failed++`, surfaced in UI.        |
| API pod crash           | Stateless; LB reroutes; in-flight requests retried by client.         |
| DB failover             | Multi-AZ Postgres; app retries on transient `OperationalError`.       |
| Broker outage           | Kafka durable log replays; Redis → AOF persistence + replica.         |
| Partial job             | `Job` tracks processed/failed; "resume" re-enqueues only PENDING imgs.|

---

## 12. Disaster recovery

- **RPO ≈ 5 min**: Postgres PITR (WAL archiving to S3) + automated snapshots.
- **RTO ≈ 30 min**: infra is Terraform + Helm → rebuild cluster from code; S3 is the
  durable source of truth for images/masks; metadata restored from latest snapshot.
- Cross-region S3 replication for the artifact bucket; MLflow registry backed by S3 + DB.
- Quarterly game-days: restore snapshot into an isolated namespace and replay a sample job.
