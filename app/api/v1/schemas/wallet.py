"""
Wallet request and response schemas.
"""

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class DepositRequest(BaseModel):
    """Deposit request model."""

    amount: Decimal = Field(
        ..., gt=0, decimal_places=2, description="Amount to deposit in NGN"
    )

    class Config:
        json_schema_extra = {"example": {"amount": "5000.00"}}


class DepositResponse(BaseModel):
    """Deposit response model with payment link."""

    reference: str = Field(..., description="Transaction reference ID")
    authorization_url: str = Field(..., description="Paystack payment authorization URL")
    amount: Decimal = Field(..., description="Deposit amount")
    status: str = Field(default="pending", description="Transaction status")

    class Config:
        json_schema_extra = {
            "example": {
                "reference": "TXN-1702240000-12345",
                "authorization_url": "https://checkout.paystack.com/...",
                "amount": "5000.00",
                "status": "pending",
            }
        }


class TransferRequest(BaseModel):
    """Transfer request model."""

    wallet_number: str = Field(
        ..., min_length=1, max_length=255, description="Recipient wallet number"
    )
    amount: Decimal = Field(
        ..., gt=0, decimal_places=2, description="Amount to transfer in NGN"
    )

    class Config:
        json_schema_extra = {
            "example": {"wallet_number": "WALLET-123456", "amount": "1000.00"}
        }


class TransferResponse(BaseModel):
    """Transfer response model."""

    status: str = Field(default="success", description="Transfer status")
    message: str = Field(default="Transfer completed", description="Status message")
    transaction_reference: str = Field(..., description="Transfer reference ID")
    amount: Decimal = Field(..., description="Transferred amount")
    timestamp: datetime = Field(..., description="Transfer timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Transfer completed",
                "transaction_reference": "TXN-1702240000-67890",
                "amount": "1000.00",
                "timestamp": "2025-12-10T14:30:00Z",
            }
        }


class BalanceResponse(BaseModel):
    """Balance response model."""

    balance: Decimal = Field(..., description="Current wallet balance")
    wallet_number: str = Field(..., description="Wallet number")
    user_id: str = Field(..., description="User UUID")
    currency: str = Field(default="NGN", description="Currency code")

    class Config:
        json_schema_extra = {
            "example": {
                "balance": "25000.50",
                "wallet_number": "WALLET-123456",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "currency": "NGN",
            }
        }


class TransactionResponse(BaseModel):
    """Transaction response model for history."""

    transaction_id: str = Field(..., description="Transaction UUID")
    type: str = Field(..., description="Transaction type (deposit/transfer/withdrawal)")
    amount: Decimal = Field(..., description="Transaction amount")
    status: str = Field(..., description="Transaction status (completed/pending/failed)")
    reference: str = Field(..., description="Transaction reference")
    created_at: datetime = Field(..., description="Creation timestamp")
    description: str = Field(default="", description="Transaction description")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "deposit",
                "amount": "5000.00",
                "status": "completed",
                "reference": "TXN-1702240000-12345",
                "created_at": "2025-12-10T14:30:00Z",
                "description": "Paystack deposit",
            }
        }


class PaystackWebhookRequest(BaseModel):
    """Paystack webhook request model."""

    event: str = Field(..., description="Webhook event type")
    data: dict = Field(..., description="Event data")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "charge.success",
                "data": {
                    "id": 123456,
                    "reference": "TXN-1702240000-12345",
                    "amount": 500000,
                    "customer": {"email": "user@example.com"},
                },
            }
        }


class VerifyTransactionResponse(BaseModel):
    """Paystack transaction verification response model."""

    reference: str = Field(..., description="Transaction reference")
    status: str = Field(..., description="Paystack transaction status")
    amount: Decimal = Field(..., description="Transaction amount in NGN")
    gateway_response: str = Field(..., description="Payment gateway response")
    paid_at: str = Field(None, description="Payment completion timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "reference": "TXN-1702240000-12345",
                "status": "success",
                "amount": "5000.00",
                "gateway_response": "Successful",
                "paid_at": "2025-12-10T14:30:00Z",
            }
        }
