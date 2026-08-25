import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return _correlation_id.get()


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        return json.dumps(payload)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonLogFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Reads/generates X-Correlation-Id and binds it via contextvars so every
    log line emitted while handling a request carries the same id (research.md §7)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._logger = logging.getLogger("concierge.request")

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        token = _correlation_id.set(correlation_id)
        start = time.monotonic()
        try:
            self._logger.info("request.start %s %s", request.method, request.url.path)
            response = await call_next(request)
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            self._logger.info(
                "request.end %s %s duration_ms=%.1f", request.method, request.url.path, duration_ms
            )
            _correlation_id.reset(token)
        response.headers["X-Correlation-Id"] = correlation_id
        return response
