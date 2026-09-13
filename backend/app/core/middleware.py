"""Application middleware for correlation IDs and standard error handling."""

import re
from collections.abc import Callable

from backend.app.common.types import uuid7
from backend.app.core.constants import HEADER_REQUEST_ID
from backend.app.core.exceptions import DomainException
from backend.app.core.logging import get_logger, request_id_ctx_var
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = get_logger(__name__)

# Valid request ID pattern: alphanumeric, hyphen, underscore, 1 to 128 chars
REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9\-_]{1,128}$")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing and propagating correlation request IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming_id = request.headers.get(HEADER_REQUEST_ID)
        if incoming_id and REQUEST_ID_REGEX.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = str(uuid7())

        # Set context variable for structured logging
        token = request_id_ctx_var.set(request_id)
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            response.headers[HEADER_REQUEST_ID] = request_id
            return response
        finally:
            request_id_ctx_var.reset(token)


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers formatting into standard envelopes."""

    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", request_id_ctx_var.get() or "-")
        logger.warning(f"Domain exception: [{exc.code}] {exc.message} (Status: {exc.status_code})")
        return JSONResponse(
            status_code=exc.status_code,
            headers={HEADER_REQUEST_ID: request_id},
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", request_id_ctx_var.get() or "-")
        errors = []
        for err in exc.errors():
            field = ".".join(str(loc) for loc in err["loc"] if loc != "body")
            errors.append({"field": field, "message": err["msg"]})

        logger.warning(f"Validation error on {request.url.path}: {errors}")
        return JSONResponse(
            status_code=getattr(
                status,
                "HTTP_422_UNPROCESSABLE_CONTENT",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ),
            headers={HEADER_REQUEST_ID: request_id},
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request payload failed input schema validation.",
                    "details": {"errors": errors},
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", request_id_ctx_var.get() or "-")
        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        # Never expose Python tracebacks or SQL syntax to clients
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers={HEADER_REQUEST_ID: request_id},
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": (
                        "An unexpected server error occurred. Please contact the administrator."
                    ),
                    "details": {},
                    "request_id": request_id,
                }
            },
        )
