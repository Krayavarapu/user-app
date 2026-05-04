from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.middleware.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, and wall time (skips noisy health checks)."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        start = time.perf_counter()
        client_host = request.client.host if request.client else "?"
        logger.debug(
            "request start %s %s client=%s has_query=%s",
            request.method,
            request.url.path,
            client_host,
            bool(request.query_params),
        )
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request failed %s %s",
                request.method,
                request.url.path,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        line = (
            f"{request.method} {request.url.path} -> {response.status_code} in {elapsed_ms:.1f}ms"
        )
        if request.method == "OPTIONS":
            logger.debug(line)
        elif response.status_code >= 500:
            logger.error(line)
        elif response.status_code >= 400:
            logger.warning(line)
        else:
            logger.info(line)
        return response
