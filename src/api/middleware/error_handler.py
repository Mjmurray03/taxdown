from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
from typing import Union

logger = logging.getLogger(__name__)


# Custom exception classes
class TaxdownException(Exception):
    """Base exception for Taxdown API"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class PropertyNotFoundError(TaxdownException):
    def __init__(self, property_id: str):
        super().__init__(
            message=f"Property not found: {property_id}",
            code="PROPERTY_NOT_FOUND",
            status_code=404
        )


class PortfolioNotFoundError(TaxdownException):
    def __init__(self, portfolio_id: str):
        super().__init__(
            message=f"Portfolio not found: {portfolio_id}",
            code="PORTFOLIO_NOT_FOUND",
            status_code=404
        )


class AnalysisError(TaxdownException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="ANALYSIS_ERROR",
            status_code=422
        )


class ValidationError(TaxdownException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400
        )


class AuthorizationError(TaxdownException):
    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=403
        )


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict = None
) -> JSONResponse:
    """Create standardized error response."""
    content = {
        "status": "error",
        "error": {
            "code": code,
            "message": message
        }
    }

    if details:
        content["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=content)


async def taxdown_exception_handler(request: Request, exc: TaxdownException):
    """Handle custom Taxdown exceptions."""
    logger.warning(f"TaxdownException: {exc.code} - {exc.message}")
    return create_error_response(exc.status_code, exc.code, exc.message)


async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")

    # Map status codes to error codes
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }

    code = code_map.get(exc.status_code, "ERROR")

    return create_error_response(exc.status_code, code, str(exc.detail))


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    errors = exc.errors()

    # Format validation errors
    formatted_errors = []
    for error in errors:
        loc = " -> ".join(str(l) for l in error["loc"])
        formatted_errors.append({
            "field": loc,
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(f"Validation error: {formatted_errors}")

    return create_error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": formatted_errors}
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    # Log full traceback
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Don't expose internal details in production
    return create_error_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later."
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(TaxdownException, taxdown_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
