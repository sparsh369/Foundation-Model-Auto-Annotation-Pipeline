# API Reference

Base URL: `{{host}}/api/v1` · Auth: `Authorization: Bearer <access_token>` · Live docs: `/docs`.

## Auth
| Method | Path                | Body                          | Notes                          |
|--------|---------------------|-------------------------------|--------------------------------|
| POST   | `/auth/register`    | `{email,password,role?}`      | Admin-only for non-`viewer`.   |
| POST   | `/auth/login`       | `{username,password}` (form)  | Returns access + refresh JWT.  |
| POST   | `/auth/refresh`     | `{refresh_token}`             | Rotates access token.          |
| GET    | `/auth/me`          | —                             | Current principal.             |

## Datasets
| Method | Path                       | Notes                                  |
|--------|----------------------------|----------------------------------------|
| POST   | `/datasets`                | Create dataset.                        |
| GET    | `/datasets`                | List (paginated).                      |
| GET    | `/datasets/{id}`           | Detail + counts.                       |
| POST   | `/datasets/{id}/images:presign` | Presigned S3 upload URLs (batch). |
| POST   | `/datasets/{id}/images:register`| Register uploaded objects.        |
| DELETE | `/datasets/{id}`           | Admin/owner only.                      |

## Jobs
| Method | Path                  | Notes                                            |
|--------|-----------------------|--------------------------------------------------|
| POST   | `/jobs`               | `{dataset_id,type,params}` → enqueues pipeline.  |
| GET    | `/jobs/{id}`          | Status + progress (total/processed/failed).      |
| POST   | `/jobs/{id}:cancel`   | Revoke pending tasks.                            |
| POST   | `/jobs/{id}:resume`   | Re-enqueue only PENDING images.                  |

## Annotations & Reviews (HITL)
| Method | Path                              | Notes                              |
|--------|-----------------------------------|------------------------------------|
| GET    | `/annotations?image_id=&status=`  | Versioned annotations.             |
| GET    | `/reviews/queue`                  | Reviewer's NEEDS_REVIEW queue.     |
| POST   | `/reviews/{annotation_id}`        | `{decision,corrected_payload?}`.   |
| POST   | `/exports`                        | `{dataset_id,format}` → export job.|

## Admin / Ops
| Method | Path            | Notes                          |
|--------|-----------------|--------------------------------|
| GET    | `/health`       | Liveness.                      |
| GET    | `/health/ready` | Readiness (DB + Redis + S3).   |
| GET    | `/metrics`      | Prometheus exposition.         |
| GET    | `/admin/audit`  | Audit log (admin only).        |
