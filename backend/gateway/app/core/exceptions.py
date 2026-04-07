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
    """Raised when client sends a bad request (400)."""
    status_code = 400
    detail = "Bad request"


# ── Global handler registration (called in main.py) ──
def register_exception_handlers(app):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
