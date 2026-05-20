# ML Pipeline

Five-stage open-vocabulary auto-annotation. See [`pipeline.py`](pipeline.py).

| Stage | Model          | Module                         | Output                          |
|-------|----------------|--------------------------------|---------------------------------|
| 1     | Grounding DINO | `models/grounding_dino.py`     | boxes + labels (open-vocab)     |
| 2     | SAM 2          | `models/sam2.py`               | masks + polygons + mask quality |
| 3     | CLIP           | `models/clip_validator.py`     | crop↔label cosine similarity    |
| 4     | VLM (GPT-4V)   | `models/vlm.py`                | caption, tags, corrections      |
| 5     | Confidence     | `confidence/engine.py`         | fused score + routing decision  |

## Running without a GPU

Set `PIPELINE_MOCK_MODELS=true` (default in `.env.example`). Every wrapper has a
deterministic mock path, so the **entire** control plane, queueing, confidence routing,
HITL, and export flow are exercisable on a laptop. Flip to `false` on a CUDA box.

## Weights

| Model          | Where to get it                                                        |
|----------------|------------------------------------------------------------------------|
| Grounding DINO | HF `IDEA-Research/grounding-dino-tiny` (auto-downloaded by transformers). |
| SAM 2          | `facebookresearch/sam2` checkpoints → set `SAM2_CHECKPOINT`/`SAM2_CONFIG`. |
| CLIP           | `open_clip` `ViT-B-32 / laion2b_s34b_b79k` (auto-downloaded).           |
| VLM            | OpenAI API key in `OPENAI_API_KEY`, or `VLM_PROVIDER=mock`.             |

## GPU memory & batching strategy

- **One resident copy per worker** (`ml/registry.py`): models load once, pinned to a device.
- **SAM 2**: image encoder runs once; all boxes prompt the cached embedding (the big win).
- **CLIP**: crops batched into a single forward pass.
- **fp16 autocast** + `torch.inference_mode()`; `empty_cache()` after large SAM 2 batches.
- `MAX_DETECTIONS_PER_IMAGE` caps SAM 2 prompt fan-out to bound VRAM.
- **VLM gating**: GPT-4V only fires when image confidence is *ambiguous* — the costly call
  is skipped for clearly-good and clearly-bad images.

## Confidence engine

Transparent linear ensemble of detection score, CLIP similarity, mask quality, box↔mask
consistency, and cross-model agreement, multiplied by an entropy penalty that punishes
signal disagreement. Routes to `auto_approve` / `needs_review` / `reject`. Fully auditable —
the per-signal breakdown is persisted on every annotation.
