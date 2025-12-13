import secrets
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel
from typing import Optional
import uuid
from datetime import datetime
from decimal import Decimal


class Wallet(SQLModel, table=True):
    """Wallet model for storing user wallet balances."""

    __tablename__ = "wallets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    wallet_number: str = Field(unique=True, index=True, max_length=20)
    balance: Decimal = Field(default=Decimal("0.00"), max_digits=15, decimal_places=2)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @staticmethod
    def generate_wallet_number() -> str:
        """Generate unique wallet number."""
        return f"{secrets.randbelow(10**13):013d}"

    class Config:
        json_schema_extra = {
            "example": {
                "wallet_number": "1234567890123",
                "balance": "5000.00",
            }
        }


class Transaction(SQLModel, table=True):
    """Transaction model for tracking all wallet transactions."""

    __tablename__ = "transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    wallet_id: uuid.UUID = Field(foreign_key="wallets.id", index=True)

    type: str = Field(max_length=20)
    amount: Decimal = Field(max_digits=15, decimal_places=2)
    status: str = Field(default="pending", max_length=20)
    reference: str = Field(unique=True, index=True, max_length=255)

    recipient_wallet_number: Optional[str] = Field(default=None, max_length=20)
    sender_wallet_number: Optional[str] = Field(default=None, max_length=20)

    paystack_reference: Optional[str] = Field(default=None, max_length=255)
    payment_url: Optional[str] = Field(default=None)

    description: Optional[str] = Field(default=None, max_length=500)
    extra_data: Optional[dict] = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "type": "deposit",
                "amount": "5000.00",
                "status": "success",
                "reference": "TXN_123456",
            }
        }
