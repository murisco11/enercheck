import logging
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.logger = logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request_id_context.set(request_id)
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        self.logger.info("request.completed", extra={"request_id": request_id})
        return response
