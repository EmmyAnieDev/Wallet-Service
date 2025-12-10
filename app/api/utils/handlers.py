"""
Exception handlers for the Wallet Service API.

This module provides global exception handlers for FastAPI application.
"""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.utils.exceptions import WalletServiceException
from app.api.utils.response import ResponsePayload

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

    return JSONResponse(
        status_code=exc.status_code,
        content=ResponsePayload.error(
            message=exc.message,
            error_code=exc.error_code,
            code=exc.status_code
        )
    )
