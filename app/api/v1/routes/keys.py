"""
API Key management routes.

This module provides endpoints for managing API keys used for service-to-service authentication.
"""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.core.dependencies import get_current_user
from app.api.db.database import get_db
from app.api.v1.models.user import User
from app.api.v1.schemas.keys import (
    CreateAPIKeyRequest,
    RolloverAPIKeyRequest,
    APIKeyResponse,
    APIKeyListItemResponse,
    RolloverAPIKeyResponse,
    RevokeAPIKeyResponse,
)
from app.api.v1.services.keys import APIKeyService
from app.api.utils.response import ResponsePayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.get("", status_code=status.HTTP_200_OK)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    List all API keys for the authenticated user.

    Returns a list of all API keys (both active and revoked) for the user.
    For security reasons, the actual key values are not returned.

    Args:
        current_user (User): Authenticated user
        session (AsyncSession): Database session

    Returns:
        dict: Response with list of API keys
    """
    from datetime import datetime

    api_keys = await APIKeyService.get_user_api_keys(
        user_id=current_user.id,
        session=session,
    )

    logger.info(f"Retrieved {len(api_keys)} API keys for user {current_user.email}")

    key_list = [
        APIKeyListItemResponse(
            id=key.id,
            name=key.name,
            permissions=key.permissions or [],
            expires_at=key.expires_at,
            created_at=key.created_at,
            is_active=not key.revoked,
            is_expired=key.expires_at < datetime.utcnow(),
        ).model_dump()
        for key in api_keys
    ]

    return ResponsePayload.success(
        message="API keys retrieved successfully",
        data=key_list,
        code=status.HTTP_200_OK
    )


@router.get("/{key_id}", status_code=status.HTTP_200_OK)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get a specific API key by ID.

    Returns details of a specific API key. For security reasons,
    the actual key value is not returned.

    Args:
        key_id (str): UUID of the API key
        current_user (User): Authenticated user
        session (AsyncSession): Database session

    Returns:
        dict: Response with API key details

    Raises:
        APIKeyNotFoundException: If key not found or not owned by user
    """
    from datetime import datetime

    api_key = await APIKeyService.get_api_key(
        user_id=current_user.id,
        key_id=key_id,
        session=session,
    )

    logger.info(f"Retrieved API key {key_id} for user {current_user.email}")

    return ResponsePayload.success(
        message="API key retrieved successfully",
        data=APIKeyListItemResponse(
            id=api_key.id,
            name=api_key.name,
            permissions=api_key.permissions or [],
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            is_active=not api_key.revoked,
            is_expired=api_key.expires_at < datetime.utcnow(),
        ).model_dump(),
        code=status.HTTP_200_OK
    )


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create a new API key for the authenticated user.

    Generates a new API key with specified permissions and expiration.
    Users can have a maximum of 5 active API keys.

    Args:
        request (CreateAPIKeyRequest): API key creation details
        current_user (User): Authenticated user
        session (AsyncSession): Database session

    Returns:
        dict: Response with created API key details

    Raises:
        APIKeyLimitException: If user has reached maximum API key limit
    """
    api_key = await APIKeyService.create_api_key(
        user_id=current_user.id,
        name=request.name,
        permissions=request.permissions,
        expiry_duration=request.expiry,
        session=session,
    )

    logger.info(f"API key created for user {current_user.email}")

    return ResponsePayload.success(
        message="API key created successfully",
        data=APIKeyResponse(
            id=api_key.id,
            api_key=api_key.key,
            name=api_key.name,
            permissions=api_key.permissions or [],
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            is_active=not api_key.revoked,
        ).model_dump(),
        code=status.HTTP_201_CREATED
    )


@router.post("/rollover")
async def rollover_api_key(
    request: RolloverAPIKeyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Rollover an expired API key with a new one.

    Creates a new API key with the same permissions as the expired key and revokes the old one.
    This is useful when an API key has expired but you want to maintain the same permissions.

    Args:
        request (RolloverAPIKeyRequest): Rollover request with expired key ID and new expiry
        current_user (User): Authenticated user
        session (AsyncSession): Database session

    Returns:
        dict: Response with old key ID and new API key details

    Raises:
        APIKeyNotFoundException: If expired key not found or not owned by user
        InvalidAPIKeyException: If key is not expired yet
    """
    old_key_id, new_key = await APIKeyService.rollover_api_key(
        user_id=current_user.id,
        expired_key_id=request.expired_key_id,
        expiry_duration=request.expiry,
        session=session,
    )

    logger.info(f"API key rolled over for user {current_user.email}: {old_key_id} -> {new_key.id}")

    return ResponsePayload.success(
        message="API key rolled over successfully",
        data=RolloverAPIKeyResponse(
            old_key_id=old_key_id,
            new_key=APIKeyResponse(
                id=new_key.id,
                api_key=new_key.key,
                name=new_key.name,
                permissions=new_key.permissions or [],
                expires_at=new_key.expires_at,
                created_at=new_key.created_at,
                is_active=not new_key.revoked,
            ),
        ).model_dump(),
        code=status.HTTP_200_OK
    )


@router.post("/revoke/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Revoke an API key.

    Permanently revokes an active API key, preventing its further use for authentication.
    Revoked keys cannot be restored and must be replaced with new keys if needed.

    Args:
        key_id (str): UUID of the API key to revoke
        current_user (User): Authenticated user
        session (AsyncSession): Database session

    Returns:
        dict: Response with revoked API key details

    Raises:
        APIKeyNotFoundException: If key not found or not owned by user
        InvalidAPIKeyException: If key is already revoked
    """
    api_key = await APIKeyService.revoke_api_key(
        user_id=current_user.id,
        key_id=key_id,
        session=session,
    )

    logger.info(f"API key revoked for user {current_user.email}: {key_id}")

    return ResponsePayload.success(
        message="API key revoked successfully",
        data=RevokeAPIKeyResponse(
            key_id=api_key.id,
            revoked_at=api_key.updated_at,
        ).model_dump(),
        code=status.HTTP_200_OK
    )


@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete an API key permanently.

    Permanently deletes an API key from the database.
    This is different from revoking - the key is completely removed.

    Args:
        key_id (str): UUID of the API key to delete
        current_user (User): Authenticated user
        session (AsyncSession): Database session

    Returns:
        dict: Response with confirmation

    Raises:
        APIKeyNotFoundException: If key not found or not owned by user
    """
    deleted_key_id = await APIKeyService.delete_api_key(
        user_id=current_user.id,
        key_id=key_id,
        session=session,
    )

    logger.info(f"API key deleted permanently for user {current_user.email}: {key_id}")

    return ResponsePayload.success(
        message="API key deleted successfully",
        data={
            "key_id": str(deleted_key_id),
            "status": "deleted"
        },
        code=status.HTTP_200_OK
    )
