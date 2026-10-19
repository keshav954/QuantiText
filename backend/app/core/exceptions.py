"""
Custom exception classes and FastAPI exception handlers.
Centralised so all error responses have a consistent shape.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base exception for application-level errors."""

    def __init__(self, message: str, status_code: int = 400, detail: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} '{resource_id}' not found",
            status_code=404,
            detail={"resource": resource, "id": resource_id},
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=403)


class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=409)


class ValidationError(AppException):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message=message, status_code=422, detail=detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach custom exception handlers to the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail if isinstance(exc.detail, str) else "HTTP error",
                "detail": exc.detail if isinstance(exc.detail, dict) else {},
            },
        )
