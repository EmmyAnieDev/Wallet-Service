"""
Wallet service layer.

This module provides business logic for wallet operations.
"""

import logging
import secrets
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlmodel import select, desc

from app.api.v1.models.wallet import Wallet, Transaction
from app.api.v1.services.paystack import PaystackService
from app.api.utils.exceptions import (
    WalletNotFoundException,
    InsufficientBalanceException,
    TransactionNotFoundException,
    DuplicateTransactionException,
)

logger = logging.getLogger(__name__)


class WalletService:
    """Service class for wallet management operations."""

    @staticmethod
    async def create_wallet(user_id: UUID, session: AsyncSession) -> Wallet:
        """
        Create a wallet for a user.

        Args:
            user_id (UUID): User UUID
            session (AsyncSession): Database session

        Returns:
            Wallet: Created wallet

        Raises:
            Exception: If wallet creation fails
        """
        statement = select(Wallet).where(Wallet.user_id == user_id)
        result = await session.execute(statement)
        existing_wallet = result.scalar_one_or_none()

        if existing_wallet:
            logger.info(f"Wallet already exists for user {user_id}")
            return existing_wallet

        wallet = Wallet(
            user_id=user_id,
            wallet_number=Wallet.generate_wallet_number(),
            balance=Decimal("0.00")
        )

        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)

        logger.info(f"Wallet created for user {user_id}: {wallet.wallet_number}")
        return wallet

    @staticmethod
    async def get_wallet_by_user_id(user_id: UUID, session: AsyncSession) -> Wallet:
        """
        Get wallet by user ID.

        Args:
            user_id (UUID): User UUID
            session (AsyncSession): Database session

        Returns:
            Wallet: User's wallet

        Raises:
            WalletNotFoundException: If wallet not found
        """
        statement = select(Wallet).where(Wallet.user_id == user_id)
        result = await session.execute(statement)
        wallet = result.scalar_one_or_none()

        if not wallet:
            logger.warning(f"Wallet not found for user {user_id}")
            raise WalletNotFoundException(f"Wallet not found for user {user_id}")

        return wallet

    @staticmethod
    async def get_wallet_by_number(wallet_number: str, session: AsyncSession) -> Wallet:
        """
        Get wallet by wallet number.

        Args:
            wallet_number (str): Wallet number
            session (AsyncSession): Database session

        Returns:
            Wallet: Wallet

        Raises:
            WalletNotFoundException: If wallet not found
        """
        statement = select(Wallet).where(Wallet.wallet_number == wallet_number)
        result = await session.execute(statement)
        wallet = result.scalar_one_or_none()

        if not wallet:
            logger.warning(f"Wallet not found: {wallet_number}")
            raise WalletNotFoundException(f"Wallet number {wallet_number} not found")

        return wallet

    @staticmethod
    async def initialize_deposit(
        user_id: UUID,
        amount: Decimal,
        email: str,
        session: AsyncSession,
    ) -> dict:
        """
        Initialize deposit transaction with Paystack.

        Args:
            user_id (UUID): User UUID
            amount (Decimal): Amount to deposit
            email (str): User email
            session (AsyncSession): Database session

        Returns:
            dict: Transaction details with payment URL

        Raises:
            WalletNotFoundException: If wallet not found
        """
        wallet = await WalletService.get_wallet_by_user_id(user_id, session)

        reference = f"TXN_{int(datetime.utcnow().timestamp())}_{secrets.token_hex(4)}"

        statement = select(Transaction).where(Transaction.reference == reference)
        result = await session.execute(statement)
        if result.scalar_one_or_none():
            raise DuplicateTransactionException("Transaction reference already exists")

        amount_in_kobo = int(amount * 100)
        paystack_data = await PaystackService.initialize_transaction(
            email=email,
            amount=amount_in_kobo,
            reference=reference
        )

        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type="deposit",
            amount=amount,
            status="pending",
            reference=reference,
            paystack_reference=reference,
            payment_url=paystack_data["authorization_url"],
            description="Paystack deposit"
        )

        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)

        logger.info(f"Deposit initialized for user {user_id}: {reference}")

        return {
            "reference": reference,
            "authorization_url": paystack_data["authorization_url"],
            "amount": amount
        }

    @staticmethod
    async def process_webhook(
        reference: str,
        status: str,
        session: AsyncSession,
    ) -> Transaction:
        """
        Process Paystack webhook and credit wallet.

        Args:
            reference (str): Transaction reference
            status (str): Transaction status from Paystack
            session (AsyncSession): Database session

        Returns:
            Transaction: Updated transaction

        Raises:
            TransactionNotFoundException: If transaction not found
        """
        statement = select(Transaction).where(Transaction.reference == reference)
        result = await session.execute(statement)
        transaction = result.scalar_one_or_none()

        if not transaction:
            logger.error(f"Transaction not found: {reference}")
            raise TransactionNotFoundException(f"Transaction {reference} not found")

        if transaction.status == "success":
            logger.info(f"Transaction already processed: {reference}")
            return transaction

        logger.info(f"Processing webhook for transaction {reference}: {status}")

        if status == "success":
            transaction.status = "success"
            transaction.updated_at = datetime.utcnow()

            wallet = await session.get(Wallet, transaction.wallet_id)
            if wallet:
                old_balance = wallet.balance
                wallet.balance += transaction.amount
                wallet.updated_at = datetime.utcnow()
                logger.info(
                    f"Wallet {wallet.wallet_number} credited: "
                    f"{old_balance} -> {wallet.balance} (+{transaction.amount})"
                )
        else:
            transaction.status = "failed"
            transaction.updated_at = datetime.utcnow()
            logger.warning(f"Transaction failed: {reference}")

        await session.commit()
        await session.refresh(transaction)

        return transaction

    @staticmethod
    async def transfer(
        sender_user_id: UUID,
        recipient_wallet_number: str,
        amount: Decimal,
        session: AsyncSession,
    ) -> Transaction:
        """
        Transfer funds between wallets.

        Args:
            sender_user_id (UUID): Sender user UUID
            recipient_wallet_number (str): Recipient wallet number
            amount (Decimal): Amount to transfer
            session: AsyncSession): Database session

        Returns:
            Transaction: Transfer transaction

        Raises:
            WalletNotFoundException: If wallet not found
            InsufficientBalanceException: If sender has insufficient balance
        """
        sender_wallet = await WalletService.get_wallet_by_user_id(sender_user_id, session)

        recipient_wallet = await WalletService.get_wallet_by_number(
            recipient_wallet_number, session
        )

        if sender_wallet.balance < amount:
            logger.warning(
                f"Insufficient balance for transfer: "
                f"{sender_wallet.wallet_number} (balance: {sender_wallet.balance}, required: {amount})"
            )
            raise InsufficientBalanceException(
                f"Insufficient balance. Available: {sender_wallet.balance}"
            )

        if sender_wallet.id == recipient_wallet.id:
            raise WalletNotFoundException("Cannot transfer to your own wallet")

        logger.info(
            f"Transfer: {sender_wallet.wallet_number} -> {recipient_wallet.wallet_number} "
            f"Amount: {amount}"
        )

        reference = f"TFR_{int(datetime.utcnow().timestamp())}_{secrets.token_hex(4)}"

        transaction = Transaction(
            user_id=sender_user_id,
            wallet_id=sender_wallet.id,
            type="transfer",
            amount=amount,
            status="success",
            reference=reference,
            sender_wallet_number=sender_wallet.wallet_number,
            recipient_wallet_number=recipient_wallet.wallet_number,
            description=f"Transfer to {recipient_wallet.wallet_number}"
        )

        old_sender_balance = sender_wallet.balance
        sender_wallet.balance -= amount
        sender_wallet.updated_at = datetime.utcnow()

        old_recipient_balance = recipient_wallet.balance
        recipient_wallet.balance += amount
        recipient_wallet.updated_at = datetime.utcnow()

        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)

        logger.info(
            f"Transfer completed: {reference} | "
            f"Sender: {old_sender_balance} -> {sender_wallet.balance} | "
            f"Recipient: {old_recipient_balance} -> {recipient_wallet.balance}"
        )

        return transaction

    @staticmethod
    async def get_transaction_by_reference(
        reference: str, session: AsyncSession
    ) -> Transaction:
        """
        Get transaction by reference.

        Args:
            reference (str): Transaction reference
            session (AsyncSession): Database session

        Returns:
            Transaction: Transaction

        Raises:
            TransactionNotFoundException: If transaction not found
        """
        statement = select(Transaction).where(Transaction.reference == reference)
        result = await session.execute(statement)
        transaction = result.scalar_one_or_none()

        if not transaction:
            logger.warning(f"Transaction not found: {reference}")
            raise TransactionNotFoundException(f"Transaction {reference} not found")

        return transaction

    @staticmethod
    async def get_user_transactions(
        user_id: UUID,
        session: AsyncSession,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[list[Transaction], int]:
        """
        Get user transaction history with pagination.

        Args:
            user_id (UUID): User UUID
            session (AsyncSession): Database session
            offset (int): Number of records to skip
            limit (int): Maximum number of records to return

        Returns:
            tuple[list[Transaction], int]: Tuple of (transactions list, total count)
        """
        count_statement = (
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.user_id == user_id)
        )
        count_result = await session.execute(count_statement)
        total = count_result.scalar() or 0

        statement = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(desc(Transaction.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(statement)
        transactions = result.scalars().all()

        logger.info(f"Retrieved {len(transactions)} of {total} transactions for user {user_id}")
        return list(transactions), total
