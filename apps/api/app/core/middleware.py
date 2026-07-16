"""HTTP middleware."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("vayu.access")

RequestResponseCall = Callable[[Request], Awaitable[Response]]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log one structured line per request.

    Records the endpoint, latency, and response code required by the platform's
    observability baseline, plus a correlation id echoed back as
    `X-Request-ID` so a user-reported error can be traced to a log line.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseCall) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Log the failure with timing, then re-raise so the exception
            # handlers own the response shape.
            logger.exception(
                "request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    "status_code": 500,
                },
            )
            raise

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "endpoint": request.url.path,
                "latency_ms": latency_ms,
                "status_code": response.status_code,
            },
        )
        return response
