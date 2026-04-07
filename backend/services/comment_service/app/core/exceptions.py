"""
Custom Exceptions — replaces scattered HTTPException calls.

1. Routes raise custom exceptions:     raise NotFoundException("User not found")
2. Global handler catches them:         app.add_exception_handler(...)
3. Handler converts to HTTP response:   {"detail": "User not found"} with 404 status

Why: Single place to define error behavior. DRY. Easy to add logging, metrics, etc.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


# ── Base exception (all custom exceptions inherit from this) ──
class AppException(Exception):
    """Base class for all custom exceptions."""
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


# ── Specific exceptions ──
class NotFoundException(AppException):
    """Raised when a resource is not found (404)."""
    status_code = 404
    detail = "Resource not found"


class DuplicateException(AppException):
    """Raised when trying to create a duplicate resource (409)."""
    status_code = 409
    detail = "Resource already exists"


class NotAuthorizedException(AppException):
    """Raised when user is not authenticated (401)."""
    status_code = 401
    detail = "Not authenticated"


class ForbiddenException(AppException):
    """Raised when user lacks permission (403)."""
    status_code = 403
    detail = "Insufficient permissions"


class BadRequestException(AppException):
    """Raised for invalid input or business rule violation (400)."""
    status_code = 400
    detail = "Bad request"


# ── Global exception handler — register this on the FastAPI app ──
async def app_exception_handler(request: Request, exc: AppException):
    """Converts any AppException into a JSON response automatically."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
