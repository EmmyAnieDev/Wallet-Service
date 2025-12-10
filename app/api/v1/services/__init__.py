"""
Wallet service layer.
"""

import logging
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.v1.models.wallet import Wallet, Transaction
from app.api.utils.exceptions import (
    WalletNotFoundException,
    InsufficientBalanceException,
    TransactionNotFoundException,
)

logger = logging.getLogger(__name__)


class WalletService:
    """Wallet service for managing wallets and transactions."""

    @staticmethod
    async def create_wallet(user_id: str, session: AsyncSession) -> Wallet:
        """Create a new wallet for a user."""
        try:
            if isinstance(user_id, str):
                user_uuid = uuid.UUID(user_id)
            else:
                user_uuid = user_id

            wallet = Wallet(
                user_id=user_uuid,
                wallet_number=Wallet.generate_wallet_number(),
                balance=Decimal("0.00"),
            )
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)
            logger.info(f"Wallet created for user: {user_id}")
            return wallet
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create wallet: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def get_wallet(user_id: str, session: AsyncSession) -> Wallet:
        """Get or create a wallet for a user."""
        try:
            if isinstance(user_id, str):
                user_uuid = uuid.UUID(user_id)
            else:
                user_uuid = user_id

            statement = select(Wallet).where(Wallet.user_id == user_uuid)
            result = await session.execute(statement)
            wallet = result.scalar_one_or_none()

            if not wallet:
                logger.info(f"Wallet not found for user {user_id}, creating new one")
                wallet = await WalletService.create_wallet(user_id, session)

            return wallet
        except Exception as e:
            logger.error(f"Failed to get wallet: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def get_balance(user_id: str, session: AsyncSession) -> Decimal:
        """Get current wallet balance."""
        try:
            wallet = await WalletService.get_wallet(user_id, session)
            logger.debug(f"Retrieved balance for user {user_id}: {wallet.balance}")
            return wallet.balance
        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def record_transaction(
        user_id: str,
        wallet_id: str,
        transaction_type: str,
        amount: Decimal,
        status: str = "pending",
        reference: str = "",
        paystack_reference: Optional[str] = None,
        payment_url: Optional[str] = None,
        recipient_wallet: Optional[str] = None,
        sender_wallet: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
        session: Optional[AsyncSession] = None,
    ) -> Transaction:
        """Record a transaction."""
        if not session:
            raise ValueError("Database session is required")

        try:
            if isinstance(user_id, str):
                user_uuid = uuid.UUID(user_id)
            else:
                user_uuid = user_id

            if isinstance(wallet_id, str):
                wallet_uuid = uuid.UUID(wallet_id)
            else:
                wallet_uuid = wallet_id

            transaction = Transaction(
                user_id=user_uuid,
                wallet_id=wallet_uuid,
                type=transaction_type,
                amount=amount,
                status=status,
                reference=reference,
                paystack_reference=paystack_reference,
                payment_url=payment_url,
                recipient_wallet_number=recipient_wallet,
                sender_wallet_number=sender_wallet,
                description=description,
                metadata=metadata,
            )
            session.add(transaction)
            await session.commit()
            await session.refresh(transaction)
            logger.info(f"Transaction recorded: {reference}")
            return transaction
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to record transaction: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def get_transaction_history(
        user_id: str,
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        """Get transaction history."""
        try:
            if isinstance(user_id, str):
                user_uuid = uuid.UUID(user_id)
            else:
                user_uuid = user_id

            statement = (
                select(Transaction)
                .where(Transaction.user_id == user_uuid)
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(statement)
            transactions = result.scalars().all()
            logger.debug(f"Retrieved {len(transactions)} transactions for user {user_id}")
            return list(transactions)
        except Exception as e:
            logger.error(f"Failed to get transaction history: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def get_transaction_by_reference(
        reference: str, session: AsyncSession
    ) -> Transaction:
        """Get a transaction by reference."""
        try:
            statement = select(Transaction).where(Transaction.reference == reference)
            result = await session.execute(statement)
            transaction = result.scalar_one_or_none()

            if not transaction:
                logger.warning(f"Transaction not found: {reference}")
                raise TransactionNotFoundException(f"Transaction {reference} not found")

            return transaction
        except Exception as e:
            logger.error(f"Failed to get transaction: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def update_wallet_balance(
        wallet_id: str,
        amount: Decimal,
        operation: str = "add",
        session: Optional[AsyncSession] = None,
    ) -> Wallet:
        """Update wallet balance."""
        if not session:
            raise ValueError("Database session is required")

        try:
            if isinstance(wallet_id, str):
                wallet_uuid = uuid.UUID(wallet_id)
            else:
                wallet_uuid = wallet_id

            wallet = await session.get(Wallet, wallet_uuid)

            if not wallet:
                raise WalletNotFoundException(f"Wallet {wallet_id} not found")

            if operation == "add":
                wallet.balance += amount
            elif operation == "subtract":
                if wallet.balance < amount:
                    raise InsufficientBalanceException(
                        f"Insufficient balance. Available: {wallet.balance}, Required: {amount}"
                    )
                wallet.balance -= amount
            else:
                raise ValueError(f"Invalid operation: {operation}")

            await session.commit()
            await session.refresh(wallet)
            logger.info(f"Wallet balance updated: {operation} {amount}")
            return wallet
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update wallet balance: {str(e)}", exc_info=True)
            raise
