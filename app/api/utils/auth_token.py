"""
JWT token utilities for authentication.

This module provides functions for creating, verifying, and managing JWT tokens.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

from config import settings
from app.api.utils import redis_client
from app.api.utils.exceptions import (
    InvalidTokenException,
    TokenExpiredException,
    TokenRevokedException
)

logger = logging.getLogger(__name__)


def create_jwt_token(user_id: uuid.UUID, email: str, expires_in_hours: int = 48) -> str:
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

    Example:
        >>> token = create_jwt_token("user-123", "user@example.com")
        >>> len(token) > 0
        True
    """
    payload = {
        "sub": str(user_id),
        "email": email,
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
    }

    try:
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        logger.info(f"JWT token created for user: {email}")
        return token
    except Exception as e:
        logger.error(f"Failed to create JWT token: {str(e)}", exc_info=True)
        raise


async def verify_jwt_token(token: str) -> dict:
    """
    Verify and decode a JWT token.

    Checks token signature, expiration, and revocation status.

    Args:
        token (str): JWT token to verify

    Returns:
        dict: Token payload

    Raises:
        HTTPException: If token is invalid, expired, or revoked

    Example:
        >>> token = create_jwt_token("user-123", "user@example.com")
        >>> payload = await verify_jwt_token(token)
        >>> payload['sub'] == "user-123"
        True
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        jti = payload.get("jti")
        if jti:
            is_revoked = await redis_client.is_token_revoked(jti)
            if is_revoked:
                logger.warning(f"Revoked token attempted to be used: {jti}")
                raise TokenRevokedException()

        logger.debug(f"JWT token verified for user: {payload.get('email')}")
        return payload

    except JWTError as e:
        error_str = str(e).lower()

        if "expired" in error_str:
            logger.warning(f"Expired token: {str(e)}")
            raise TokenExpiredException()
        else:
            logger.warning(f"Invalid token: {str(e)}")
            raise InvalidTokenException()
    except (InvalidTokenException, TokenExpiredException, TokenRevokedException):
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}", exc_info=True)
        raise InvalidTokenException()


def decode_jwt_token(token: str) -> dict:
    """
    Decode JWT token without verification (for debugging/testing only).

    Args:
        token (str): JWT token to decode

    Returns:
        dict: Decoded token payload

    Warning:
        This function does not verify the token signature.
        Use verify_jwt_token() for production authentication.

    Example:
        >>> payload = decode_jwt_token("eyJhbGc...")
        >>> payload["email"]
        'user@example.com'
    """
    try:
        payload = jwt.decode(
            token,
            key="",
            options={"verify_signature": False}
        )
        return payload
    except Exception as e:
        logger.error(f"Failed to decode token: {str(e)}", exc_info=True)
        raise


async def revoke_jwt_token(token: str) -> dict:
    """
    Revoke a JWT token by storing its JTI in Redis.

    Stores the token's JTI in Redis with TTL matching the token's expiration.

    Args:
        token (str): JWT access token to revoke

    Returns:
        dict: Revocation response with timestamp

    Raises:
        Exception: If token is invalid or revocation fails

    Example:
        >>> result = await revoke_jwt_token("eyJhbGc...")
        >>> result["message"]
        'Successfully revoked token'
    """
    try:
        payload = decode_jwt_token(token)

        jti = payload.get("jti")
        exp = payload.get("exp")

        if not jti:
            raise Exception("Token does not contain JTI (JWT ID)")

        if not exp:
            raise Exception("Token does not contain expiration time")

        current_time = datetime.now(timezone.utc).timestamp()
        ttl = int(exp - current_time)

        if ttl <= 0:
            logger.info(f"Token already expired, skipping revocation: {jti}")
            return {
                "message": "Token already expired",
                "revoked_at": datetime.now(timezone.utc).isoformat()
            }

        await redis_client.revoke_token(jti, ttl)

        logger.info(f"Token revoked successfully: {jti}")

        return {
            "message": "Successfully revoked token",
            "revoked_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Token revocation failed: {str(e)}", exc_info=True)
        raise
