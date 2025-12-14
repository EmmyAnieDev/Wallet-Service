"""
Response payload utilities for consistent API response formatting.

Provides standardized response structures for success and error cases
with proper HTTP status codes and data formatting.
"""

from typing import Optional
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(status_code: int, message: str, data: Optional[dict] = None) -> JSONResponse:
    """
    Returns a JSON response for success responses.

    Args:
        status_code (int): HTTP status code
        message (str): Success message
        data (dict, optional): Response data payload

    Returns:
        JSONResponse: Formatted success response
    """
    response_data = {"status_code": status_code, "success": True, "message": message}

    if data is not None:
        response_data["data"] = data

    return JSONResponse(
        status_code=status_code, content=jsonable_encoder(response_data)
    )


def error_response(
    status_code: int,
    message: str = "An error occurred",
    detail: Optional[str] = None
) -> JSONResponse:
    """
    Generate a standardized error response.

    Args:
        status_code (int): HTTP status code
        message (str): Error message
        detail (str, optional): Additional error details

    Returns:
        JSONResponse: Formatted error response
    """
    content = {
        "status_code": status_code,
        "status": False,
        "message": message,
    }
    if detail is not None:
        content["detail"] = detail

    return JSONResponse(
        status_code=status_code,
        content=content
    )
