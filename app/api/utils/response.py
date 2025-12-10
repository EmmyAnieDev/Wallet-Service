"""
Response payload utilities for consistent API response formatting.

Provides standardized response structures for success and error cases
with proper HTTP status codes and data formatting.
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """
    Standard success response wrapper.

    Used for all successful API responses to ensure consistency.
    Includes metadata for pagination when applicable.

    Args:
        status (str): Always "success" for successful responses
        message (str): Human-readable success message
        data (T): Response data payload (generic type)
        meta (dict, optional): Additional metadata (pagination, etc.)
        code (int): HTTP status code

    Examples:
        >>> response = SuccessResponse(
        ...     message="User created successfully",
        ...     data={"user_id": "123", "email": "user@example.com"},
        ...     code=201
        ... )
        >>> response.status
        'success'
    """

    status: str = Field(default="success", description="Response status")
    message: str = Field(..., description="Human-readable message")
    data: T = Field(..., description="Response payload")
    meta: Optional[dict[str, Any]] = Field(default=None, description="Metadata (pagination, etc.)")
    code: int = Field(default=200, description="HTTP status code")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {"id": "123", "name": "Example"},
                "meta": None,
                "code": 200,
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response wrapper.

    Used for all error API responses to ensure consistency.
    Includes error code for programmatic handling.

    Args:
        status (str): Always "error" for error responses
        message (str): Human-readable error message
        error_code (str): Application-specific error code
        details (dict, optional): Additional error details
        code (int): HTTP status code

    Examples:
        >>> response = ErrorResponse(
        ...     message="Insufficient balance",
        ...     error_code="INSUFFICIENT_BALANCE",
        ...     code=400
        ... )
        >>> response.status
        'error'
    """

    status: str = Field(default="error", description="Response status")
    message: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Application-specific error code")
    details: Optional[dict[str, Any]] = Field(default=None, description="Additional error details")
    code: int = Field(default=500, description="HTTP status code")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "An error occurred",
                "error_code": "INTERNAL_ERROR",
                "details": None,
                "code": 500,
            }
        }


class ResponsePayload:
    """
    Helper class for creating standardized response payloads.

    Provides static methods to create success and error responses
    with consistent formatting across the application.
    """

    @staticmethod
    def success(
        message: str,
        data: Any = None,
        meta: Optional[dict[str, Any]] = None,
        code: int = 200,
    ) -> dict[str, Any]:
        """
        Create a success response payload.

        Args:
            message (str): Success message to display
            data (Any, optional): Response data payload
            meta (dict, optional): Additional metadata (pagination, totals, etc.)
            code (int): HTTP status code (default: 200)

        Returns:
            dict: Formatted success response

        Examples:
            >>> payload = ResponsePayload.success(
            ...     message="User created",
            ...     data={"user_id": "123"},
            ...     code=201
            ... )
            >>> payload["status"]
            'success'
        """
        return {
            "status": "success",
            "message": message,
            "data": data,
            "meta": meta,
            "code": code,
        }

    @staticmethod
    def error(
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[dict[str, Any]] = None,
        code: int = 500,
    ) -> dict[str, Any]:
        """
        Create an error response payload.

        Args:
            message (str): Error message to display
            error_code (str): Application-specific error code (default: INTERNAL_ERROR)
            details (dict, optional): Additional error details for debugging
            code (int): HTTP status code (default: 500)

        Returns:
            dict: Formatted error response

        Examples:
            >>> payload = ResponsePayload.error(
            ...     message="User not found",
            ...     error_code="USER_NOT_FOUND",
            ...     code=404
            ... )
            >>> payload["error_code"]
            'USER_NOT_FOUND'
        """
        return {
            "status": "error",
            "message": message,
            "error_code": error_code,
            "details": details,
            "code": code,
        }

    @staticmethod
    def paginated(
        message: str,
        data: list[Any],
        total: int,
        limit: int,
        offset: int,
        code: int = 200,
    ) -> dict[str, Any]:
        """
        Create a paginated success response.

        Args:
            message (str): Success message
            data (list): List of items
            total (int): Total number of items available
            limit (int): Items per page
            offset (int): Current offset
            code (int): HTTP status code (default: 200)

        Returns:
            dict: Formatted paginated response

        Examples:
            >>> payload = ResponsePayload.paginated(
            ...     message="Transactions retrieved",
            ...     data=[{"id": "1"}, {"id": "2"}],
            ...     total=100,
            ...     limit=10,
            ...     offset=0
            ... )
            >>> payload["meta"]["total"]
            100
        """
        meta = {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(data),
        }
        return {
            "status": "success",
            "message": message,
            "data": data,
            "meta": meta,
            "code": code,
        }

    @staticmethod
    def exception_to_error(exception: Exception) -> dict[str, Any]:
        """
        Convert a WalletServiceException to error response.

        Args:
            exception (Exception): Exception instance

        Returns:
            dict: Formatted error response

        Examples:
            >>> from app.api.utils.exceptions import InvalidAPIKeyException
            >>> exc = InvalidAPIKeyException("Key expired")
            >>> payload = ResponsePayload.exception_to_error(exc)
            >>> payload["code"]
            401
        """
        from app.api.utils.exceptions import WalletServiceException

        if isinstance(exception, WalletServiceException):
            return ResponsePayload.error(
                message=exception.message,
                error_code=exception.error_code,
                details=exception.details,
                code=exception.status_code,
            )
        
        # Generic exception
        return ResponsePayload.error(
            message=str(exception),
            error_code="INTERNAL_ERROR",
            code=500,
        )
