"""
Wallet management routes.

This module provides endpoints for wallet operations including deposits, transfers, and balance checks.
"""

import logging
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.core.auth import require_permission, AuthContext
from app.api.db.database import get_db
from app.api.v1.schemas.wallet import (
    DepositRequest,
    DepositResponse,
    TransferRequest,
    TransferResponse,
    BalanceResponse,
    TransactionResponse,
    VerifyTransactionResponse,
)
from app.api.v1.services.wallet import WalletService
from app.api.v1.services.paystack import PaystackService
from app.api.utils.response import ResponsePayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.post("/deposit", status_code=status.HTTP_200_OK)
async def deposit(
    request: DepositRequest,
    auth: AuthContext = Depends(require_permission("deposit")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Initialize a deposit transaction via Paystack.

    Requires either:
    - JWT authentication (from Google sign-in)
    - API key with 'deposit' permission

    Args:
        request (DepositRequest): Deposit amount
        auth (AuthContext): Authentication context
        session (AsyncSession): Database session

    Returns:
        dict: Payment link and transaction reference

    Raises:
        WalletNotFoundException: If user wallet not found
    """
    result = await WalletService.initialize_deposit(
        user_id=auth.user_id,
        amount=request.amount,
        email=auth.email,
        session=session,
    )

    logger.info(f"Deposit initialized for user {auth.email}: {result['reference']}")

    return ResponsePayload.success(
        message="Deposit initialized successfully",
        data=DepositResponse(
            reference=result["reference"],
            authorization_url=result["authorization_url"],
            amount=result["amount"],
            status="pending"
        ).model_dump(),
        code=status.HTTP_200_OK
    )


@router.post("/paystack/webhook", status_code=status.HTTP_200_OK)
async def paystack_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Handle Paystack webhook notifications.

    This endpoint is called by Paystack when a transaction status changes.
    It verifies the webhook signature and credits the user's wallet.

    IMPORTANT: This is the ONLY endpoint that credits wallets.

    Args:
        request (Request): Webhook request from Paystack
        session (AsyncSession): Database session

    Returns:
        dict: Success acknowledgment
    """
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if not PaystackService.verify_webhook_signature(signature, body):
        logger.warning("Invalid Paystack webhook signature")
        return ResponsePayload.error(
            message="Invalid signature",
            error_code="INVALID_SIGNATURE",
            code=status.HTTP_401_UNAUTHORIZED
        )

    import json
    data = json.loads(body)

    event = data.get("event")
    payload = data.get("data", {})

    logger.info(f"Paystack webhook received: {event}")

    if event != "charge.success":
        logger.info(f"Ignoring webhook event: {event}")
        return ResponsePayload.success(
            message="Event ignored",
            data={"status": True},
            code=status.HTTP_200_OK
        )

    reference = payload.get("reference")
    paystack_status = payload.get("status")

    await WalletService.process_webhook(
        reference=reference,
        status=paystack_status,
        session=session,
    )

    logger.info(f"Webhook processed successfully: {reference}")

    return ResponsePayload.success(
        message="Webhook processed",
        data={"status": True},
        code=status.HTTP_200_OK
    )


@router.get("/verify/{reference}", status_code=status.HTTP_200_OK)
async def verify_transaction(
    reference: str,
    auth: AuthContext = Depends(require_permission("read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Verify transaction status.

    Checks local database first. If transaction is pending, verifies with Paystack API.
    This endpoint does NOT credit wallets - only the webhook does that.

    Args:
        reference (str): Transaction reference
        auth (AuthContext): Authentication context
        session (AsyncSession): Database session

    Returns:
        dict: Transaction verification data

    Raises:
        TransactionNotFoundException: If transaction not found
        PaymentProcessingException: If Paystack verification fails
    """
    transaction = await WalletService.get_transaction_by_reference(reference, session)

    if transaction.status == "pending":
        paystack_data = await PaystackService.verify_transaction(reference)

        amount_in_ngn = paystack_data.get("amount", 0) / 100

        logger.info(f"Transaction verified via Paystack: {reference} - {paystack_data.get('status')}")

        return ResponsePayload.success(
            message="Transaction verified with Paystack",
            data=VerifyTransactionResponse(
                reference=paystack_data.get("reference", ""),
                status=paystack_data.get("status", "unknown"),
                amount=amount_in_ngn,
                gateway_response=paystack_data.get("gateway_response", ""),
                paid_at=paystack_data.get("paid_at", "")
            ).model_dump(),
            code=status.HTTP_200_OK
        )

    logger.info(f"Transaction status from database: {reference} - {transaction.status}")

    return ResponsePayload.success(
        message="Transaction status retrieved",
        data=VerifyTransactionResponse(
            reference=transaction.reference,
            status=transaction.status,
            amount=transaction.amount,
            gateway_response="Transaction already processed",
            paid_at=str(transaction.updated_at) if transaction.status == "success" else ""
        ).model_dump(),
        code=status.HTTP_200_OK
    )


@router.get("/balance", status_code=status.HTTP_200_OK)
async def get_balance(
    auth: AuthContext = Depends(require_permission("read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get current wallet balance.

    Requires either:
    - JWT authentication
    - API key with 'read' permission

    Args:
        auth (AuthContext): Authentication context
        session (AsyncSession): Database session

    Returns:
        dict: Current wallet balance

    Raises:
        WalletNotFoundException: If wallet not found
    """
    wallet = await WalletService.get_wallet_by_user_id(auth.user_id, session)

    logger.info(f"Balance retrieved for user {auth.email}: {wallet.balance}")

    return ResponsePayload.success(
        message="Balance retrieved successfully",
        data=BalanceResponse(
            balance=wallet.balance,
            wallet_number=wallet.wallet_number,
            user_id=str(wallet.user_id),
            currency="NGN"
        ).model_dump(),
        code=status.HTTP_200_OK
    )


@router.post("/transfer", status_code=status.HTTP_200_OK)
async def transfer(
    request: TransferRequest,
    auth: AuthContext = Depends(require_permission("transfer")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Transfer funds to another wallet.

    Requires either:
    - JWT authentication
    - API key with 'transfer' permission

    Args:
        request (TransferRequest): Transfer details
        auth (AuthContext): Authentication context
        session (AsyncSession): Database session

    Returns:
        dict: Transfer confirmation

    Raises:
        WalletNotFoundException: If wallet not found
        InsufficientBalanceException: If insufficient balance
    """
    transaction = await WalletService.transfer(
        sender_user_id=auth.user_id,
        recipient_wallet_number=request.wallet_number,
        amount=request.amount,
        session=session,
    )

    logger.info(
        f"Transfer completed: {auth.email} -> {request.wallet_number} "
        f"Amount: {request.amount}, Reference: {transaction.reference}"
    )

    return ResponsePayload.success(
        message="Transfer completed successfully",
        data=TransferResponse(
            status="success",
            message="Transfer completed",
            transaction_reference=transaction.reference,
            amount=transaction.amount,
            timestamp=transaction.created_at
        ).model_dump(),
        code=status.HTTP_200_OK
    )


@router.get("/transactions", status_code=status.HTTP_200_OK)
async def get_transactions(
    auth: AuthContext = Depends(require_permission("read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get transaction history for the authenticated user.

    Requires either:
    - JWT authentication
    - API key with 'read' permission

    Args:
        auth (AuthContext): Authentication context
        session (AsyncSession): Database session

    Returns:
        dict: List of transactions
    """
    transactions = await WalletService.get_user_transactions(auth.user_id, session)

    logger.info(f"Retrieved {len(transactions)} transactions for user {auth.email}")

    transaction_list = [
        TransactionResponse(
            transaction_id=str(txn.id),
            type=txn.type,
            amount=txn.amount,
            status=txn.status,
            reference=txn.reference,
            created_at=txn.created_at,
            description=txn.description or ""
        ).model_dump()
        for txn in transactions
    ]

    return ResponsePayload.success(
        message="Transactions retrieved successfully",
        data=transaction_list,
        code=status.HTTP_200_OK
    )
