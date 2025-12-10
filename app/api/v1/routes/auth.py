import logging
from typing import Optional
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.core.auth import JWTHandler
from app.api.core.dependencies import get_current_user
from app.api.db.database import get_db
from app.api.v1.services.auth import AuthService
from app.api.v1.models.user import User
from app.api.utils.response import ResponsePayload
from app.api.v1.schemas.auth import GoogleLoginResponse, LogoutResponse
from app.api.utils.auth_token import revoke_jwt_token
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/google", response_model=None)
async def google_login():
    """
    Initiate Google OAuth login.
    
    Triggers Google sign-in flow by redirecting to Google's OAuth consent screen.
    
    Returns:
        RedirectResponse: Redirect to Google OAuth URL
    """
    try:
        params = {
            "response_type": "code",
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        
        google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        logger.info("Redirecting to Google OAuth")
        
        return RedirectResponse(url=google_auth_url)

    except Exception as e:
        logger.error(f"Google login failed: {str(e)}", exc_info=True)
        return ResponsePayload.error(
            message="Failed to initiate Google login",
            error_code="GOOGLE_OAUTH_INIT_FAILED",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Handle Google OAuth callback.
    
    Logs in the user, creates the user if not existing, and returns a JWT token.
    
    Args:
        code (str): Authorization code from Google
        state (str, optional): State parameter for CSRF protection
        session (AsyncSession): Database session
        
    Returns:
        dict: Response with JWT token and user info
    """
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )

            if token_response.status_code != status.HTTP_200_OK:
                logger.error(f"Token exchange failed: {token_response.text}")
                return ResponsePayload.error(
                    message="Failed to exchange authorization code",
                    error_code="GOOGLE_TOKEN_EXCHANGE_FAILED",
                    code=status.HTTP_400_BAD_REQUEST
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if user_info_response.status_code != status.HTTP_200_OK:
                logger.error(f"Failed to get user info: {user_info_response.text}")
                return ResponsePayload.error(
                    message="Failed to retrieve user information",
                    error_code="GOOGLE_USERINFO_FAILED",
                    code=status.HTTP_400_BAD_REQUEST
                )

            user_info = user_info_response.json()

        email = user_info.get("email")
        name = user_info.get("name")
        google_id = user_info.get("id")
        picture = user_info.get("picture")

        if not email or not google_id:
            logger.error("Missing required user info from Google")
            return ResponsePayload.error(
                message="Invalid user information from Google",
                error_code="GOOGLE_USERINFO_INVALID",
                code=status.HTTP_400_BAD_REQUEST
            )

        user = await AuthService.get_or_create_google_user(
            email=email,
            name=name or email.split("@")[0],
            provider_user_id=google_id,
            profile_picture_url=picture,
            session=session,
        )

        jwt_token = JWTHandler.create_token(
            user_id=user.id,
            email=user.email,

            expires_in_hours=settings.JWT_EXPIRY_HOURS
        )

        logger.info(f"User {user.email} logged in successfully")

        return ResponsePayload.success(
            message="Login successful",
            data=GoogleLoginResponse(
                access_token=jwt_token,
                token_type="Bearer",
                expires_in=settings.JWT_EXPIRY_HOURS * 3600,
                user_id=str(user.id),
                email=user.email,
            ).model_dump()
        )

    except Exception as e:
        logger.error(f"Google callback failed: {str(e)}", exc_info=True)
        return ResponsePayload.error(
            message="Authentication failed",
            error_code="GOOGLE_AUTH_FAILED",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/logout", response_model=None)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Logout user by revoking their JWT token.

    Revokes the JWT token from the Authorization header by storing its JTI (JWT ID) in Redis with TTL.
    After logout, the token cannot be used for authentication even if not expired.

    Args:
        request (Request): FastAPI request object
        current_user (User): Authenticated user from JWT token

    Returns:
        dict: Response with logout confirmation

    Raises:
        HTTPException: If token is invalid or revocation fails
    """
    from app.api.utils.exceptions import MissingAuthorizationException

    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise MissingAuthorizationException()

        token = auth_header.split(" ")[1]

        result = await revoke_jwt_token(token)

        logger.info(f"User {current_user.email} logged out successfully")

        return ResponsePayload.success(
            message="Successfully logged out",
            data=LogoutResponse(
                message=result["message"],
                revoked_at=result["revoked_at"]
            ).model_dump()
        )

    except Exception as e:
        logger.error(f"Logout failed: {str(e)}", exc_info=True)
        return ResponsePayload.error(
            message="Logout failed",
            error_code="LOGOUT_FAILED",
            code=status.HTTP_400_BAD_REQUEST
        )