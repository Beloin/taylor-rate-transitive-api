from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse  # keep single import
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.simulation.errors import ERROR_HEADER, InjectedError, build_error_body

logger = logging.getLogger(__name__)


def _organic_body(request: Request, message: str) -> dict[str, Any]:
    return build_error_body("ORGANIC_ERROR", message, request).model_dump()


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if isinstance(exc, InjectedError):
            headers = {ERROR_HEADER: exc.kind.value}
            if exc.kind.value == "RATE_LIMIT":
                headers["Retry-After"] = "5"
            return JSONResponse(
                content=build_error_body(
                    exc.kind.value, exc.detail, request
                ).model_dump(),
                status_code=exc.status_code,
                headers=headers,
            )
        message = str(exc.detail) if exc.detail else "HTTP error"
        return JSONResponse(
            content=_organic_body(request, message),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            content=_organic_body(request, "Validation error: invalid input"),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            content=_organic_body(request, "An unexpected error occurred"),
            status_code=500,
        )