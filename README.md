# Foundation-Model Auto-Annotation Pipeline

An enterprise-grade, horizontally-scalable auto-labeling platform that combines modern
vision foundation models (**Grounding DINO**, **SAM 2**, **CLIP**, and a pluggable
**VLM** such as GPT-4V) with a **human-in-the-loop** review workflow to automatically
generate bounding boxes, segmentation masks, labels, and captions for datasets ranging
from **10K to 1M+ images** — reducing manual annotation effort by **80–90%**.

```
            ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  image ──▶ │ Grounding    │──▶│   SAM 2      │──▶│    CLIP      │──▶│  VLM (GPT-4V)│──▶ confidence
            │ DINO (boxes) │   │  (masks)     │   │ (validation) │   │ (captions)   │      engine
            └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘        │
                                                                                              ▼
                                                       auto-approve ◀── route ──▶ human review (CVAT / Label Studio)
```

## Repository layout

| Path           | Purpose                                                                 |
|----------------|-------------------------------------------------------------------------|
| `backend/`     | FastAPI control plane: auth/RBAC, datasets, jobs, reviews, exports.     |
| `ml/`          | Foundation-model wrappers, pipeline orchestrator, confidence engine, exporters, active learning. |
| `workers/`     | Celery distributed GPU inference workers.                               |
| `frontend/`    | Next.js + TypeScript + Tailwind operator console.                       |
| `infra/`       | Terraform (AWS/GCP/Azure), shared infra modules.                        |
| `k8s/`         | Raw Kubernetes manifests.                                               |
| `helm/`        | Helm chart for the full stack.                                          |
| `monitoring/`  | Prometheus, Grafana dashboards, OTel collector config.                  |
| `tests/`       | Unit + integration tests.                                               |
| `docs/`        | Architecture, API, and operations documentation.                        |

## Quick start (local, CPU-friendly control plane)

```bash
cp .env.example .env                 # fill in secrets
docker compose up -d postgres redis minio      # data stores
docker compose up -d api worker                # control plane + a worker
# API docs:    http://localhost:8000/docs
# Flower:      http://localhost:5555
# MinIO:       http://localhost:9001
# Grafana:     http://localhost:3001
```

> **GPU note:** the model wrappers in `ml/models/` contain real inference code against
> Grounding DINO / SAM 2 / CLIP. Running them requires a CUDA GPU and downloaded weights
> (see `ml/README.md`). On a CPU-only box, set `PIPELINE_MOCK_MODELS=true` to exercise the
> full control plane / queueing / export / review flow with deterministic stub detections.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — HLD, LLD, data/queue/GPU flow, DB schema, scaling, DR.
- [docs/API.md](docs/API.md) — REST surface (also live at `/docs` via OpenAPI).
- [ml/README.md](ml/README.md) — model weights, batching & GPU-memory strategy.

## License

Internal / proprietary reference implementation.
