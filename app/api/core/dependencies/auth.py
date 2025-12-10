"""
Authentication dependencies for FastAPI routes.

This module provides dependency functions for route protection and user authentication.
"""

import logging
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.db.database import get_db
from app.api.utils.auth_token import verify_jwt_token
from app.api.v1.models.user import User
from app.api.utils.exceptions import InvalidTokenException, UserNotFoundException

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.

    Extracts and verifies the JWT token from the Authorization header,
    then retrieves the corresponding user from the database.

    Args:
        credentials (HTTPAuthorizationCredentials): Bearer token credentials
        session (AsyncSession): Database session

    Returns:
        User: Authenticated user object

    Raises:
        HTTPException: If token is invalid or user not found

    Example:
        >>> # In a route:
        >>> @router.get("/me")
        >>> async def get_me(current_user: User = Depends(get_current_user)):
        ...     return {"email": current_user.email}
    """
    try:
        token = credentials.credentials
        payload = await verify_jwt_token(token)

        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token missing user ID (sub claim)")
            raise InvalidTokenException("Invalid token: missing user ID")

        user = await session.get(User, user_id)
        if not user:
            logger.warning(f"User not found for ID: {user_id}")
            raise UserNotFoundException(f"User not found for ID: {user_id}")

        logger.debug(f"User authenticated: {user.email}")
        return user

    except (InvalidTokenException, UserNotFoundException):
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}", exc_info=True)
        raise InvalidTokenException("Authentication failed")
