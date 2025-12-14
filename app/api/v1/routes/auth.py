import logging
from typing import Optional
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.core.auth import JWTHandler
from app.api.core.dependencies import get_current_user
from app.api.db.database import get_db
from app.api.v1.services.auth import AuthService
from app.api.v1.models.user import User
from app.api.utils.response import success_response, error_response
from app.api.v1.schemas.auth import GoogleLoginResponse, LogoutResponse
from app.api.v1.schemas.response import SuccessResponseModel
from app.api.utils.auth_token import revoke_jwt_token
from app.api.utils.exceptions import MissingAuthorizationException
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/google")
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
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to initiate Google login",
            detail="GOOGLE_OAUTH_INIT_FAILED"
        )


@router.get(
    "/google/callback",
    response_model=SuccessResponseModel[GoogleLoginResponse]
)
async def google_callback(
    code: str,
    state: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Handle Google OAuth callback.

    Logs in the user, creates the user if not existing, and returns a JWT token.

    Args:
        code (str): Authorization code from Google
        state (str, optional): State parameter for CSRF protection
        session (AsyncSession): Database session

    Returns:
        JSONResponse: Response with JWT token and user info
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
                return error_response(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Failed to exchange authorization code",
                    detail="GOOGLE_TOKEN_EXCHANGE_FAILED"
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if user_info_response.status_code != status.HTTP_200_OK:
                logger.error(f"Failed to get user info: {user_info_response.text}")
                return error_response(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Failed to retrieve user information",
                    detail="GOOGLE_USERINFO_FAILED"
                )

            user_info = user_info_response.json()

        email = user_info.get("email")
        name = user_info.get("name")
        google_id = user_info.get("id")
        picture = user_info.get("picture")

        if not email or not google_id:
            logger.error("Missing required user info from Google")
            return error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid user information from Google",
                detail="GOOGLE_USERINFO_INVALID"
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

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Login successful",
            data=GoogleLoginResponse(
                access_token=jwt_token,
                token_type="Bearer",
                expires_in=settings.JWT_EXPIRY_HOURS * 3600,
                user_id=str(user.id),
                email=user.email,
            ).model_dump()
        )

    except httpx.HTTPError as e:
        logger.error(f"HTTP error during Google callback: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Failed to connect to Google services",
            detail="GOOGLE_SERVICE_UNAVAILABLE"
        )
    except Exception as e:
        logger.error(f"Google callback failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Authentication failed",
            detail="GOOGLE_AUTH_FAILED"
        )


@router.post(
    "/logout",
    response_model=SuccessResponseModel[LogoutResponse]
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    Logout user by revoking their JWT token.

    Revokes the JWT token from the Authorization header by storing its JTI (JWT ID) in Redis with TTL.
    After logout, the token cannot be used for authentication even if not expired.

    Args:
        request (Request): FastAPI request object
        current_user (User): Authenticated user from JWT token

    Returns:
        JSONResponse: Response with logout confirmation
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise MissingAuthorizationException()

        token = auth_header.split(" ")[1]

        result = await revoke_jwt_token(token)

        logger.info(f"User {current_user.email} logged out successfully")

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Successfully logged out",
            data=LogoutResponse(
                message=result["message"],
                revoked_at=result["revoked_at"]
            ).model_dump()
        )

    except MissingAuthorizationException:
        logger.error("Missing authorization header in logout request")
        return error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Missing authorization header",
            detail="MISSING_AUTHORIZATION"
        )
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Logout failed",
            detail="LOGOUT_FAILED"
        )
