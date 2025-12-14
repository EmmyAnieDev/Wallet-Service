"""
Exception handlers for the Wallet Service API.

This module provides global exception handlers for FastAPI application.
"""

import logging
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError

from app.api.utils.exceptions import WalletServiceException
from app.api.utils.response import error_response

logger = logging.getLogger(__name__)


async def wallet_service_exception_handler(request: Request, exc: WalletServiceException):
    """
    Global exception handler for all WalletServiceException and subclasses.

    Args:
        request (Request): The request that caused the exception
        exc (WalletServiceException): The exception instance

    Returns:
        JSONResponse: Formatted error response
    """
    logger.warning(f"{exc.error_code}: {exc.message}")

    return error_response(
        status_code=exc.status_code,
        message=exc.message,
        detail=exc.error_code
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Global exception handler for request validation errors (422).

    Args:
        request (Request): The request that caused the exception
        exc (RequestValidationError): The validation exception

    Returns:
        JSONResponse: Formatted error response
    """
    errors = exc.errors()
    error_messages = []

    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")

    logger.warning(f"Validation error: {error_messages}")

    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation error",
        detail="; ".join(error_messages)
    )
