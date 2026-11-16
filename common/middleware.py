import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from common.metrics import REQUEST_COUNT, REQUEST_LATENCY

log = structlog.get_logger()


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        request.state.trace_id = trace_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            service=self.service_name,
        )

        start = time.time()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration = time.time() - start
            REQUEST_COUNT.labels(
                self.service_name, request.method, request.url.path, 500
            ).inc()
            REQUEST_LATENCY.labels(
                self.service_name, request.method, request.url.path
            ).observe(duration)
            log.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
            )
            raise

        duration = time.time() - start
        REQUEST_COUNT.labels(
            self.service_name, request.method, request.url.path, response.status_code
        ).inc()
        REQUEST_LATENCY.labels(
            self.service_name, request.method, request.url.path
        ).observe(duration)
        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        response.headers["x-trace-id"] = trace_id
        return response
