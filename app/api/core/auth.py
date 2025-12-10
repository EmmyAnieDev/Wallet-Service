"""
Authentication and authorization middleware for the Wallet Service API.

This module provides JWT token validation, API key verification, and
context extraction for authenticated requests.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.db.database import get_db
from app.api.utils.exceptions import (
    UserNotFoundException,
    MissingAuthorizationException,
    InsufficientPermissionsException
)

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


class AuthContext:
    """
    Context object containing authentication and authorization information.
    
    Attributes:
        user_id: UUID of the authenticated user
        email: Email of the authenticated user
        auth_type: Type of authentication (jwt or api_key)
        permissions: List of permissions (for API keys)
    """

    def __init__(
        self,
        user_id: UUID,
        email: str,
        auth_type: str = "jwt",
        permissions: Optional[list[str]] = None,
    ):
        """
        Initialize AuthContext.
        
        Args:
            user_id (UUID): UUID of the user
            email (str): User email address
            auth_type (str): Type of authentication (jwt or api_key)
            permissions (list, optional): List of permissions
        """
        self.user_id = user_id
        self.email = email
        self.auth_type = auth_type
        self.permissions = permissions or []

    def has_permission(self, permission: str) -> bool:
        """
        Check if user/API key has a specific permission.
        
        Args:
            permission (str): Permission to check
            
        Returns:
            bool: True if permission is granted
        """
        if self.auth_type == "jwt":
            return True
        return permission in self.permissions


class JWTHandler:
    """
    Handles JWT token creation, validation, and payload extraction.

    This class provides a wrapper around JWT token utilities for backward compatibility.
    """

    @staticmethod
    def create_token(user_id: UUID, email: str, expires_in_hours: int = 48) -> str:
        """
        Create a JWT token for a user.

        Args:
            user_id (UUID): User UUID
            email (str): User email
            expires_in_hours (int): Token expiration time in hours

        Returns:
            str: Encoded JWT token

        Raises:
            Exception: If token creation fails
        """
        from app.api.utils.auth_token import create_jwt_token
        return create_jwt_token(user_id, email, expires_in_hours)

    @staticmethod
    async def verify_token(token: str) -> dict:
        """
        Verify and decode a JWT token.

        Checks token signature, expiration, and revocation status.

        Args:
            token (str): JWT token to verify

        Returns:
            dict: Token payload

        Raises:
            HTTPException: If token is invalid, expired, or revoked
        """
        from app.api.utils.auth_token import verify_jwt_token
        return await verify_jwt_token(token)


class APIKeyHandler:
    """
    Handles API key validation and permission verification.
    """

    @staticmethod
    async def verify_api_key(key: str, session: AsyncSession) -> tuple[str, list[str]]:
        """
        Verify an API key and return user_id and permissions.
        
        Args:
            key (str): API key to verify
            session (AsyncSession): Database session
            
        Returns:
            tuple: (user_id, permissions)
            
        Raises:
            HTTPException: If key is invalid, expired, or revoked

        """
        from app.api.v1.models.api_key import APIKey
        from app.api.utils.exceptions import InvalidAPIKeyException

        try:
            statement = select(APIKey).where(APIKey.key == key)
            result = await session.execute(statement)
            api_key = result.scalar_one_or_none()

            if not api_key:
                logger.warning(f"API key not found: {key[:10]}...")
                raise InvalidAPIKeyException("API key not found")

            if not api_key.is_valid():
                logger.warning(f"API key invalid/expired: {key[:10]}...")
                raise InvalidAPIKeyException("API key is expired or revoked")

            logger.debug(f"API key verified for user: {api_key.user_id}")
            return str(api_key.user_id), api_key.permissions or []

        except InvalidAPIKeyException:
            raise
        except Exception as e:
            logger.error(f"API key verification failed: {str(e)}", exc_info=True)
            raise InvalidAPIKeyException("Invalid API key")


async def get_auth_context(
    request: Request,
    session: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthContext:
    """
    Extract authentication context from request.

    Checks for JWT token in Authorization header or API key in x-api-key header.

    Args:
        request (Request): FastAPI request object
        session (AsyncSession): Database session
        credentials (HTTPAuthorizationCredentials, optional): Bearer token credentials

    Returns:
        AuthContext: Authenticated user context

    Raises:
        HTTPException: If authentication fails
    """
    api_key_header = request.headers.get("x-api-key")

    if credentials:
        token = credentials.credentials
        payload = await JWTHandler.verify_token(token)
        return AuthContext(
            user_id=payload["sub"],
            email=payload["email"],
            auth_type="jwt",
        )

    if api_key_header:
        user_id, permissions = await APIKeyHandler.verify_api_key(api_key_header, session)

        from app.api.v1.models.user import User
        user = await session.get(User, user_id)
        if not user:
            raise UserNotFoundException(f"User not found for ID: {user_id}")

        return AuthContext(
            user_id=UUID(user_id),
            email=user.email,
            auth_type="api_key",
            permissions=permissions,
        )

    logger.warning("No valid authentication found in request")
    raise MissingAuthorizationException()


def require_permission(permission: str):
    """
    Dependency to require a specific permission for an endpoint.
    
    Args:
        permission (str): Required permission
        
    Returns:
        Callable: Decorator function
    """
    from fastapi import Depends

    async def check_permission(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        """
        Check if user has required permission.
        
        Args:
            auth (AuthContext): Authentication context
            
        Returns:
            AuthContext: Authenticated context if permission granted
            
        Raises:
            HTTPException: If permission is denied
        """
        if not auth.has_permission(permission):
            logger.warning(f"Permission denied for user {auth.user_id}: {permission}")
            raise InsufficientPermissionsException(f"Permission '{permission}' required")
        return auth

    return check_permission
