"""
Generic response schemas for API endpoints.

Provides standardized response wrappers for success and error cases.
"""

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponseModel(BaseModel, Generic[T]):
    """Generic success response wrapper for API endpoints."""

    status_code: int = Field(..., description="HTTP status code")
    success: bool = Field(default=True, description="Success status")
    message: str = Field(..., description="Success message")
    data: T = Field(..., description="Response data")

    class Config:
        json_schema_extra = {
            "example": {
                "status_code": 200,
                "success": True,
                "message": "Operation completed successfully",
                "data": {}
            }
        }


class ErrorResponseModel(BaseModel):
    """Error response model for API endpoints."""

    status_code: int = Field(..., description="HTTP status code")
    status: bool = Field(default=False, description="Error status (always false)")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error detail code")

    class Config:
        json_schema_extra = {
            "example": {
                "status_code": 400,
                "status": False,
                "message": "An error occurred",
                "detail": "ERROR_CODE"
            }
        }
