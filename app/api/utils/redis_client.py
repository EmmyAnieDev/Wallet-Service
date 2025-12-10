"""
Redis utilities for token revocation and caching.

This module provides Redis connection management and token revocation functions.
"""

import logging
from typing import Optional
import redis.asyncio as redis
from config import settings

logger = logging.getLogger(__name__)

_redis_instance: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance.

    Returns:
        redis.Redis: Redis client instance

    Example:
        >>> client = await get_redis_client()
        >>> await client.ping()
        True
    """
    global _redis_instance

    if _redis_instance is None:
        try:
            _redis_instance = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await _redis_instance.ping()
            logger.info("Redis client connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}", exc_info=True)
            raise

    return _redis_instance


async def close_redis_client():
    """
    Close Redis connection.

    Example:
        >>> await close_redis_client()
    """
    global _redis_instance

    if _redis_instance:
        await _redis_instance.close()
        _redis_instance = None
        logger.info("Redis client closed")


async def revoke_token(jti: str, ttl: int):
    """
    Revoke a JWT token by storing its JTI in Redis.

    Args:
        jti (str): JWT ID (jti claim from token)
        ttl (int): Time to live in seconds (should match token expiry)

    Example:
        >>> await revoke_token("unique-jti-123", 172800)
    """
    try:
        client = await get_redis_client()
        key = f"revoked_token:{jti}"
        await client.setex(key, ttl, "revoked")
        logger.info(f"Token revoked: {jti} (TTL: {ttl}s)")
    except Exception as e:
        logger.error(f"Failed to revoke token: {str(e)}", exc_info=True)
        raise


async def is_token_revoked(jti: str) -> bool:
    """
    Check if a token is revoked.

    Args:
        jti (str): JWT ID to check

    Returns:
        bool: True if token is revoked, False otherwise

    Example:
        >>> is_revoked = await is_token_revoked("unique-jti-123")
        >>> is_revoked
        True
    """
    try:
        client = await get_redis_client()
        key = f"revoked_token:{jti}"
        result = await client.exists(key)
        return bool(result)
    except Exception as e:
        logger.error(f"Failed to check token revocation: {str(e)}", exc_info=True)
        return False
