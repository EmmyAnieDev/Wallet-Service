"""
API Key management request and response schemas.
"""

from datetime import datetime
from typing import List
from uuid import UUID
from pydantic import BaseModel, Field


class CreateAPIKeyRequest(BaseModel):
    """API key creation request model."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="API key name/label"
    )
    permissions: list[str] = Field(..., description="List of permission scopes")
    expiry: str = Field(
        ...,
        pattern="^[0-9]+(Min|H|D|M|Y)$",
        description='Expiry duration (e.g., "1Min", "1H", "7D", "1Y")',
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Production API Key",
                "permissions": ["deposit", "transfer", "read"],
                "expiry": "1Min",
            }
        }


class APIKeyListItemResponse(BaseModel):
    """API key list item response model (without exposing the actual key value)."""

    id: UUID = Field(..., description="API key UUID")
    name: str = Field(..., description="API key name")
    permissions: List[str] = Field(..., description="Permission scopes")
    expires_at: datetime = Field(..., description="Key expiration datetime")
    created_at: datetime = Field(..., description="Key creation datetime")
    is_active: bool = Field(default=True, description="Key active status")
    is_expired: bool = Field(default=False, description="Whether key is expired")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Production API Key",
                "permissions": ["deposit", "transfer", "read"],
                "expires_at": "2026-12-10T14:30:00Z",
                "created_at": "2025-12-10T14:30:00Z",
                "is_active": True,
                "is_expired": False,
            }
        }


class APIKeyResponse(BaseModel):
    """API key response model."""

    id: UUID = Field(..., description="API key UUID")
    api_key: str = Field(..., description="Generated API key string (sk_...)")
    name: str = Field(..., description="API key name")
    permissions: List[str] = Field(..., description="Permission scopes")
    expires_at: datetime = Field(..., description="Key expiration datetime")
    created_at: datetime = Field(..., description="Key creation datetime")
    is_active: bool = Field(default=True, description="Key active status")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "api_key": "sk_live_abcdef123456...",
                "name": "Production API Key",
                "permissions": ["deposit", "transfer", "read"],
                "expires_at": "2026-12-10T14:30:00Z",
                "created_at": "2025-12-10T14:30:00Z",
                "is_active": True,
            }
        }


class RolloverAPIKeyRequest(BaseModel):
    """Request model for rolling over an expired API key."""

    expired_key_id: UUID = Field(..., description="UUID of expired key to rollover")
    expiry: str = Field(
        ...,
        pattern="^[0-9]+(Min|H|D|M|Y)$",
        description='New expiry duration (e.g., "1Min", "1H", "7D", "1Y")',
    )

    class Config:
        json_schema_extra = {
            "example": {
                "expired_key_id": "550e8400-e29b-41d4-a716-446655440000",
                "expiry": "1Min",
            }
        }


class RolloverAPIKeyResponse(BaseModel):
    """Response model for rolled over API key."""

    old_key_id: UUID = Field(..., description="ID of revoked expired key")
    new_key: "APIKeyResponse" = Field(..., description="New API key details")

    class Config:
        json_schema_extra = {
            "example": {
                "old_key_id": "550e8400-e29b-41d4-a716-446655440000",
                "new_key": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "api_key": "sk_live_newkey123456...",
                    "name": "Production API Key (rolled over)",
                    "permissions": ["deposit", "transfer", "read"],
                    "expires_at": "2026-12-10T14:30:00Z",
                    "created_at": "2025-12-10T14:30:00Z",
                    "is_active": True,
                },
            }
        }


class RevokeAPIKeyResponse(BaseModel):
    """Response model for revoked API key."""

    key_id: UUID = Field(..., description="ID of revoked key")
    status: str = Field(default="revoked", description="Revocation status")
    message: str = Field(default="API key revoked successfully")
    revoked_at: datetime = Field(..., description="Revocation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "revoked",
                "message": "API key revoked successfully",
                "revoked_at": "2025-12-10T14:35:00Z",
            }
        }
