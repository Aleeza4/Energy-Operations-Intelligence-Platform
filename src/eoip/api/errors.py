"""Central API errors and exception handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

LOGGER = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """Stable public error detail."""

    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    """Stable EOIP API error envelope."""

    error: ErrorDetail


class APIError(Exception):
    """Expected API boundary error."""

    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def register_exception_handlers(app: FastAPI) -> None:
    """Register safe, consistent exception mappings."""

    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, error: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": error.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {
                "location": list(item["loc"]),
                "message": item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "request_validation_error",
                    "message": "The request parameters are invalid.",
                    "details": details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        LOGGER.exception("Unhandled API error for %s", request.url.path, exc_info=error)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected server error occurred.",
                }
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        request: Request,
        error: SQLAlchemyError,
    ) -> JSONResponse:
        LOGGER.error("Database unavailable for %s: %s", request.url.path, error)
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "data_source_unavailable",
                    "message": "The EOIP data source is temporarily unavailable.",
                }
            },
        )
