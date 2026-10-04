from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request
from pydantic import BaseModel


class ErrorKind(str, enum.Enum):
    RATE_LIMIT = "RATE_LIMIT"
    API_IS_NOT_AVAILABLE = "API_IS_NOT_AVAILABLE"
    UKNOWN_ERROR = "UKNOWN_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    I_AM_NOT_TAYLOR_ERROR = "I_AM_NOT_TAYLOR_ERROR"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"


BEFORE_KINDS = [ErrorKind.RATE_LIMIT, ErrorKind.API_IS_NOT_AVAILABLE]
AFTER_KINDS = [
    ErrorKind.UKNOWN_ERROR,
    ErrorKind.INTERNAL_ERROR,
    ErrorKind.I_AM_NOT_TAYLOR_ERROR,
]

KIND_STATUS: dict[ErrorKind, int] = {
    ErrorKind.RATE_LIMIT: 429,
    ErrorKind.API_IS_NOT_AVAILABLE: 503,
    ErrorKind.UKNOWN_ERROR: 500,
    ErrorKind.INTERNAL_ERROR: 500,
    ErrorKind.I_AM_NOT_TAYLOR_ERROR: 403,
    ErrorKind.MALFORMED_RESPONSE: 200,
}

ORGANIC_KIND = "ORGANIC_ERROR"
ERROR_HEADER = "x-taylor-api-error"


class ErrorBody(BaseModel):
    kind: str
    message: str
    request_id: str
    timestamp: str


def build_error_body(kind: str, message: str, request: Request) -> ErrorBody:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    return ErrorBody(
        kind=kind,
        message=message,
        request_id=request_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


class InjectedError(HTTPException):
    """Error raised by the simulation layer, carries its ErrorKind."""

    def __init__(self, kind: ErrorKind, message: str):
        self.kind = kind
        super().__init__(status_code=KIND_STATUS[kind], detail=message)


KIND_MESSAGES: dict[ErrorKind, str] = {
    ErrorKind.RATE_LIMIT: "Too many requests, chill out swiftie",
    ErrorKind.API_IS_NOT_AVAILABLE: "API is not available right now, try later",
    ErrorKind.UKNOWN_ERROR: "An unknown error happened, who knows",
    ErrorKind.INTERNAL_ERROR: "An internal error happened, our bad",
    ErrorKind.I_AM_NOT_TAYLOR_ERROR: "You are not Taylor, so you cannot do that",
    ErrorKind.MALFORMED_RESPONSE: "Response was malformed on purpose",
}