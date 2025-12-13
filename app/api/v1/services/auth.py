import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.v1.models.user import User
from app.api.utils.exceptions import UserNotFoundException

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and user management."""

    @staticmethod
    async def get_or_create_google_user(
        email: str,
        name: str,
        provider_user_id: str,
        profile_picture_url: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> User:
        """
        Get existing user or create new one from Google OAuth.

        Args:
            email (str): User email from Google
            name (str): User name from Google
            provider_user_id (str): Google account ID
            profile_picture_url (str, optional): User profile picture URL
            session (AsyncSession, optional): Database session

        Returns:
            User: Existing or newly created user
        """
        if not session:
            raise ValueError("Database session is required")

        try:
            try:
                user = await AuthService.get_user_by_email(email, session)
                logger.info(f"Existing user found: {email}")

                # Ensure user has a wallet
                from app.api.v1.services.wallet import WalletService
                try:
                    await WalletService.get_wallet_by_user_id(user.id, session)
                except:
                    # Create wallet if it doesn't exist
                    await WalletService.create_wallet(user.id, session)
                    logger.info(f"Wallet created for existing user: {email}")

                return user
            except UserNotFoundException:
                logger.info(f"User not found, creating new user: {email}")

                user = User(
                    email=email,
                    name=name,
                    provider_user_id=provider_user_id,
                    profile_picture_url=profile_picture_url,
                    auth_provider="google",
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info(f"New user created successfully: {email}")

                # Create wallet for new user
                from app.api.v1.services.wallet import WalletService
                await WalletService.create_wallet(user.id, session)
                logger.info(f"Wallet created for new user: {email}")

                return user

        except UserNotFoundException:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to get or create user: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def get_user_by_email(email: str, session: AsyncSession) -> User:
        """
        Get user by email.

        Args:
            email (str): User email
            session (AsyncSession): Database session

        Returns:
            User: User object

        Raises:
            UserNotFoundException: If user not found
        """
        try:
            statement = select(User).where(User.email == email)
            result = await session.execute(statement)
            user = result.scalar_one_or_none()

            if not user:
                raise UserNotFoundException(f"User {email} not found")

            return user
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to get user by email: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def get_user_by_id(user_id: str, session: AsyncSession) -> User:
        """
        Get user by ID.

        Args:
            user_id (str): User UUID
            session (AsyncSession): Database session

        Returns:
            User: User object

        Raises:
            UserNotFoundException: If user not found
        """
        try:
            user = await session.get(User, user_id)

            if not user:
                raise UserNotFoundException(f"User {user_id} not found")

            return user
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to get user by ID: {str(e)}", exc_info=True)
            raise

