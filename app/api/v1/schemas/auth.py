from pydantic import BaseModel, Field

class GoogleLoginResponse(BaseModel):
    """Google login response with JWT token."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user_id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGc...",
                "token_type": "Bearer",
                "expires_in": 86400,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
            }
        }


class LogoutResponse(BaseModel):
    """Logout response schema."""

    message: str = Field(..., description="Logout status message")
    revoked_at: str = Field(..., description="ISO timestamp of revocation")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Successfully revoked token",
                "revoked_at": "2025-12-11T10:30:00Z",
            }
        }
