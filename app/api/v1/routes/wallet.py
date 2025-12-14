"""
Wallet management routes.

This module provides endpoints for wallet operations including deposits, transfers, and balance checks.
"""

import logging
from fastapi import APIRouter, Depends, Request, Query, status
from fastapi.responses import JSONResponse
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
from app.api.v1.schemas.response import SuccessResponseModel
from app.api.v1.services.wallet import WalletService
from app.api.v1.services.paystack import PaystackService
from app.api.utils.response import success_response, error_response
from app.api.utils.pagination import PaginationParams, PaginatedResponse
from app.api.utils.exceptions import (
    WalletNotFoundException,
    InsufficientBalanceException,
    TransactionNotFoundException,
    PaymentProcessingException,
    NetworkException,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.post(
    "/deposit",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponseModel[DepositResponse]
)
async def deposit(
    request: DepositRequest,
    auth: AuthContext = Depends(require_permission("deposit")),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
        JSONResponse: Payment link and transaction reference
    """
    try:
        result = await WalletService.initialize_deposit(
            user_id=auth.user_id,
            amount=request.amount,
            email=auth.email,
            session=session,
        )

        logger.info(f"Deposit initialized for user {auth.email}: {result['reference']}")

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Deposit initialized successfully",
            data=DepositResponse(
                reference=result["reference"],
                authorization_url=result["authorization_url"],
                amount=result["amount"],
                status="pending"
            ).model_dump()
        )
    except WalletNotFoundException:
        logger.error(f"Wallet not found for user {auth.user_id}")
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            detail="WALLET_NOT_FOUND"
        )
    except PaymentProcessingException:
        logger.error(f"Payment processing failed for user {auth.email}")
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to initialize payment",
            detail="PAYMENT_PROCESSING_ERROR"
        )
    except NetworkException:
        logger.error("Network error connecting to payment gateway")
        return error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Payment service temporarily unavailable",
            detail="NETWORK_ERROR"
        )
    except Exception as e:
        logger.error(f"Deposit initialization failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            detail="INTERNAL_SERVER_ERROR"
        )


@router.post("/paystack/webhook", status_code=status.HTTP_200_OK)
async def paystack_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Handle Paystack webhook notifications.

    This endpoint is called by Paystack when a transaction status changes.
    It verifies the webhook signature and credits the user's wallet.

    IMPORTANT: This is the ONLY endpoint that credits wallets.

    Args:
        request (Request): Webhook request from Paystack
        session (AsyncSession): Database session

    Returns:
        JSONResponse: Success acknowledgment
    """
    try:
        body = await request.body()
        signature = request.headers.get("x-paystack-signature", "")

        if not PaystackService.verify_webhook_signature(signature, body):
            logger.warning("Invalid Paystack webhook signature")
            return error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid signature",
                detail="INVALID_SIGNATURE"
            )

        import json
        data = json.loads(body)

        event = data.get("event")
        payload = data.get("data", {})

        logger.info(f"Paystack webhook received: {event}")

        if event != "charge.success":
            logger.info(f"Ignoring webhook event: {event}")
            return success_response(
                status_code=status.HTTP_200_OK,
                message="Event ignored",
                data={"status": True}
            )

        reference = payload.get("reference")
        paystack_status = payload.get("status")

        await WalletService.process_webhook(
            reference=reference,
            status=paystack_status,
            session=session,
        )

        logger.info(f"Webhook processed successfully: {reference}")

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Webhook processed",
            data={"status": True}
        )
    except TransactionNotFoundException:
        logger.error("Transaction not found in webhook processing")
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transaction not found",
            detail="TRANSACTION_NOT_FOUND"
        )
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Webhook processing failed",
            detail="WEBHOOK_ERROR"
        )


@router.get(
    "/verify/{reference}",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponseModel[VerifyTransactionResponse]
)
async def verify_transaction(
    reference: str,
    auth: AuthContext = Depends(require_permission("read")),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Verify transaction status.

    Checks local database first. If transaction is pending, verifies with Paystack API.
    This endpoint does NOT credit wallets - only the webhook does that.

    Args:
        reference (str): Transaction reference
        auth (AuthContext): Authentication context
        session (AsyncSession): Database session

    Returns:
        JSONResponse: Transaction verification data
    """
    try:
        transaction = await WalletService.get_transaction_by_reference(reference, session)

        if transaction.status == "pending":
            paystack_data = await PaystackService.verify_transaction(reference)

            amount_in_ngn = paystack_data.get("amount", 0) / 100

            logger.info(f"Transaction verified via Paystack: {reference} - {paystack_data.get('status')}")

            return success_response(
                status_code=status.HTTP_200_OK,
                message="Transaction verified with Paystack",
                data=VerifyTransactionResponse(
                    reference=paystack_data.get("reference", ""),
                    status=paystack_data.get("status", "unknown"),
                    amount=amount_in_ngn,
                    gateway_response=paystack_data.get("gateway_response", ""),
                    paid_at=paystack_data.get("paid_at")
                ).model_dump()
            )

        logger.info(f"Transaction status from database: {reference} - {transaction.status}")

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Transaction status retrieved",
            data=VerifyTransactionResponse(
                reference=transaction.reference,
                status=transaction.status,
                amount=transaction.amount,
                gateway_response="Transaction already processed",
                paid_at=str(transaction.updated_at) if transaction.status == "success" else None
            ).model_dump()
        )
    except TransactionNotFoundException:
        logger.error(f"Transaction not found: {reference}")
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transaction not found",
            detail="TRANSACTION_NOT_FOUND"
        )
    except PaymentProcessingException:
        logger.error(f"Payment verification failed for transaction: {reference}")
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to verify transaction",
            detail="VERIFICATION_FAILED"
        )
    except Exception as e:
        logger.error(f"Transaction verification failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            detail="INTERNAL_SERVER_ERROR"
        )


@router.get(
    "/balance",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponseModel[BalanceResponse]
)
async def get_balance(
    auth: AuthContext = Depends(require_permission("read")),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get current wallet balance.

    Requires either:
    - JWT authentication
    - API key with 'read' permission

    Args:
        auth (AuthContext): Authentication context
        session (AsyncSession): Database session

    Returns:
        JSONResponse: Current wallet balance
    """
    try:
        wallet = await WalletService.get_wallet_by_user_id(auth.user_id, session)

        logger.info(f"Balance retrieved for user {auth.email}: {wallet.balance}")

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Balance retrieved successfully",
            data=BalanceResponse(
                balance=wallet.balance,
                wallet_number=wallet.wallet_number,
                user_id=str(wallet.user_id),
                currency="NGN"
            ).model_dump()
        )
    except WalletNotFoundException:
        logger.error(f"Wallet not found for user {auth.user_id}")
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            detail="WALLET_NOT_FOUND"
        )
    except Exception as e:
        logger.error(f"Balance retrieval failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            detail="INTERNAL_SERVER_ERROR"
        )


@router.post(
    "/transfer",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponseModel[TransferResponse]
)
async def transfer(
    request: TransferRequest,
    auth: AuthContext = Depends(require_permission("transfer")),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
        JSONResponse: Transfer confirmation
    """
    try:
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

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Transfer completed successfully",
            data=TransferResponse(
                status="success",
                message="Transfer completed",
                transaction_reference=transaction.reference,
                amount=transaction.amount,
                timestamp=transaction.created_at
            ).model_dump()
        )
    except WalletNotFoundException:
        logger.error("Wallet not found in transfer")
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            detail="WALLET_NOT_FOUND"
        )
    except InsufficientBalanceException:
        logger.error(f"Insufficient balance for transfer by user {auth.email}")
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Insufficient balance",
            detail="INSUFFICIENT_BALANCE"
        )
    except Exception as e:
        logger.error(f"Transfer failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            detail="INTERNAL_SERVER_ERROR"
        )


@router.get(
    "/transactions",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponseModel[PaginatedResponse[TransactionResponse]]
)
async def get_transactions(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    auth: AuthContext = Depends(require_permission("read")),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get paginated transaction history for the authenticated user.

    Requires either:
    - JWT authentication
    - API key with 'read' permission

    Args:
        page (int): Page number (default: 1)
        page_size (int): Items per page (default: 20, max: 100)
        auth (AuthContext): Authentication context
        session (AsyncSession): Database session

    Returns:
        JSONResponse: Paginated list of transactions
    """
    try:
        pagination = PaginationParams(page=page, page_size=page_size)

        transactions, total = await WalletService.get_user_transactions(
            auth.user_id,
            session,
            offset=pagination.offset,
            limit=pagination.limit
        )

        logger.info(f"Retrieved {len(transactions)} of {total} transactions for user {auth.email}")

        transaction_list = [
            TransactionResponse(
                transaction_id=str(txn.id),
                type=txn.type,
                amount=txn.amount,
                status=txn.status,
                reference=txn.reference,
                created_at=txn.created_at,
                description=txn.description or ""
            )
            for txn in transactions
        ]

        paginated_data = PaginatedResponse.create(
            items=transaction_list,
            total=total,
            page=page,
            page_size=page_size
        )

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Transactions retrieved successfully",
            data=paginated_data.model_dump()
        )
    except Exception as e:
        logger.error(f"Transaction retrieval failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            detail="INTERNAL_SERVER_ERROR"
        )
