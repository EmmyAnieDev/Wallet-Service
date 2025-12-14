"""
API key management service layer.

This module provides business logic for creating, revoking, and managing API keys.
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.v1.models.api_key import APIKey
from app.api.utils.exceptions import (
    APIKeyLimitException,
    InvalidAPIKeyException,
    APIKeyNotFoundException
)
from app.api.utils.api_key_utils import parse_expiry
from config import settings

logger = logging.getLogger(__name__)


class APIKeyService:
    """Service class for API key management operations."""

    @staticmethod
    async def create_api_key(
        user_id: UUID,
        name: str,
        permissions: list[str],
        expiry_duration: str,
        session: AsyncSession,
    ) -> APIKey:
        """
        Create new API key for user.

        Args:
            user_id (UUID): User UUID
            name (str): API key name/label
            permissions (list[str]): List of permission scopes
            expiry_duration (str): Expiry duration (e.g., "1D", "1Y")
            session (AsyncSession): Database session

        Returns:
            APIKey: Created API key

        Raises:
            APIKeyLimitException: If user has reached max API keys
        """
        statement = select(APIKey).where(
            APIKey.user_id == user_id,
            APIKey.revoked == False,
            APIKey.expires_at > datetime.utcnow()
        )
        result = await session.execute(statement)
        active_keys = result.scalars().all()

        logger.info(f"User {user_id} has {len(active_keys)} active (non-expired, non-revoked) API keys (max: {settings.API_KEY_MAX_PER_USER})")

        if len(active_keys) >= settings.API_KEY_MAX_PER_USER:
            logger.warning(f"API key limit reached for user {user_id}: {len(active_keys)}/{settings.API_KEY_MAX_PER_USER}")
            raise APIKeyLimitException(
                f"Maximum {settings.API_KEY_MAX_PER_USER} API keys allowed"
            )

        api_key = APIKey(
            user_id=user_id,
            name=name,
            key=APIKey.generate_key(),
            permissions=permissions,
            expires_at=parse_expiry(expiry_duration)
        )

        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)

        logger.info(f"API key created successfully for user {user_id}: {api_key.id}")
        return api_key

    @staticmethod
    async def rollover_api_key(
        user_id: UUID,
        expired_key_id: UUID,
        expiry_duration: str,
        session: AsyncSession,
    ) -> tuple[UUID, APIKey]:
        """
        Rollover an expired API key with a new one.

        Args:
            user_id (UUID): User UUID
            expired_key_id (UUID): ID of expired key to rollover
            expiry_duration (str): New expiry duration
            session (AsyncSession): Database session

        Returns:
            tuple[UUID, APIKey]: (old_key_id, new_api_key)

        Raises:
            APIKeyNotFoundException: If key not found or not owned by user
            InvalidAPIKeyException: If key is not expired yet
        """
        old_key = await session.get(APIKey, expired_key_id)

        if not old_key or old_key.user_id != user_id:
            logger.warning(f"Rollover failed: API key {expired_key_id} not found for user {user_id}")
            raise APIKeyNotFoundException("API key not found")

        if old_key.expires_at > datetime.utcnow():
            logger.warning(f"Rollover failed: API key {expired_key_id} is not expired yet")
            raise InvalidAPIKeyException("API key must be expired to rollover")

        logger.info(f"Rolling over expired API key {expired_key_id} for user {user_id}")

        old_key.revoked = True
        old_key.updated_at = datetime.utcnow()

        statement = select(APIKey).where(
            APIKey.user_id == user_id,
            APIKey.revoked == False,
            APIKey.expires_at > datetime.utcnow()
        )
        result = await session.execute(statement)
        active_keys = result.scalars().all()

        logger.info(f"After revoking old key, user {user_id} has {len(active_keys)} active keys")

        if len(active_keys) >= settings.API_KEY_MAX_PER_USER:
            logger.warning(f"Rollover failed: User {user_id} already has {len(active_keys)} active keys")
            raise APIKeyLimitException(
                f"Maximum {settings.API_KEY_MAX_PER_USER} API keys allowed. Revoke an active key first."
            )

        new_key = APIKey(
            user_id=user_id,
            name=f"{old_key.name} (rolled over)",
            key=APIKey.generate_key(),
            permissions=old_key.permissions,
            expires_at=parse_expiry(expiry_duration),
        )

        session.add(new_key)
        await session.commit()
        await session.refresh(new_key)

        logger.info(f"API key rolled over successfully: {expired_key_id} -> {new_key.id}")
        return old_key.id, new_key

    @staticmethod
    async def revoke_api_key(
        user_id: UUID,
        key_id: str,
        session: AsyncSession,
    ) -> APIKey:
        """
        Revoke an API key.

        Args:
            user_id (UUID): User UUID
            key_id (str): API key UUID to revoke
            session (AsyncSession): Database session

        Returns:
            APIKey: Revoked API key

        Raises:
            APIKeyNotFoundException: If key not found or not owned by user
            InvalidAPIKeyException: If key is already revoked
        """
        api_key = await session.get(APIKey, key_id)

        if not api_key or api_key.user_id != user_id:
            logger.warning(f"Revoke failed: API key {key_id} not found for user {user_id}")
            raise APIKeyNotFoundException("API key not found")

        if api_key.revoked:
            logger.warning(f"Revoke failed: API key {key_id} already revoked")
            raise InvalidAPIKeyException("API key already revoked")

        logger.info(f"Revoking API key {key_id} for user {user_id}")

        api_key.revoked = True
        api_key.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(api_key)

        logger.info(f"API key revoked successfully: {key_id}")
        return api_key

    @staticmethod
    async def get_user_api_keys(
        user_id: UUID,
        session: AsyncSession,
    ) -> list[APIKey]:
        """
        Get all API keys for a user.

        Args:
            user_id (UUID): User UUID
            session (AsyncSession): Database session

        Returns:
            list[APIKey]: List of user's API keys (both active and revoked)
        """
        statement = select(APIKey).where(APIKey.user_id == user_id)
        result = await session.execute(statement)
        api_keys = result.scalars().all()

        logger.info(f"Retrieved {len(api_keys)} API keys for user {user_id}")
        return list(api_keys)

    @staticmethod
    async def get_api_key(
        user_id: UUID,
        key_id: str,
        session: AsyncSession,
    ) -> APIKey:
        """
        Get a specific API key for a user.

        Args:
            user_id (UUID): User UUID
            key_id (str): API key UUID
            session (AsyncSession): Database session

        Returns:
            APIKey: The API key

        Raises:
            APIKeyNotFoundException: If key not found or not owned by user
        """
        api_key = await session.get(APIKey, key_id)

        if not api_key or api_key.user_id != user_id:
            logger.warning(f"API key {key_id} not found for user {user_id}")
            raise APIKeyNotFoundException("API key not found")

        logger.debug(f"Retrieved API key {key_id} for user {user_id}")
        return api_key

    @staticmethod
    async def delete_api_key(
        user_id: UUID,
        key_id: str,
        session: AsyncSession,
    ) -> UUID:
        """
        Permanently delete an API key from the database.

        Args:
            user_id (UUID): User UUID
            key_id (str): API key UUID to delete
            session (AsyncSession): Database session

        Returns:
            UUID: Deleted API key ID

        Raises:
            APIKeyNotFoundException: If key not found or not owned by user
        """
        api_key = await session.get(APIKey, key_id)

        if not api_key or api_key.user_id != user_id:
            logger.warning(f"Delete failed: API key {key_id} not found for user {user_id}")
            raise APIKeyNotFoundException("API key not found")

        logger.info(f"Deleting API key {key_id} for user {user_id}")

        deleted_key_id = api_key.id
        await session.delete(api_key)
        await session.commit()

        logger.info(f"API key deleted successfully: {key_id}")
        return deleted_key_id