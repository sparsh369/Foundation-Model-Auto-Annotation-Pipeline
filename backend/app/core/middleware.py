"""Cross-cutting middleware: request-id binding + Prometheus metrics."""
from __future__ import annotations

import time
import uuid

import structlog
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex)
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        elapsed = time.perf_counter() - start

        # Use route template (not raw path) to keep label cardinality bounded.
        route = request.scope.get("route")
        path_tmpl = getattr(route, "path", request.url.path)
        REQUEST_COUNT.labels(request.method, path_tmpl, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, path_tmpl).observe(elapsed)
        response.headers["x-request-id"] = request_id
        return response
