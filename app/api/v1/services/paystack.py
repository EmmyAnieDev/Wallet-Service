"""
Paystack payment service.
"""

import logging
import hmac
import hashlib
import httpx

from app.api.utils.exceptions import PaymentProcessingException, NetworkException
from config import settings

logger = logging.getLogger(__name__)


class PaystackService:
    """Service for Paystack payment integration."""

    @staticmethod
    async def initialize_transaction(
        email: str, amount: int, reference: str
    ) -> dict:
        """
        Initialize Paystack transaction.

        Args:
            email (str): Customer email
            amount (int): Amount in kobo (NGN * 100)
            reference (str): Unique transaction reference

        Returns:
            dict: Authorization URL and access code

        Raises:
            PaymentProcessingException: If Paystack API fails
        """
        try:
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "email": email,
                "amount": amount,
                "reference": reference,
            }

            async with httpx.AsyncClient(timeout=settings.PAYSTACK_TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.PAYSTACK_API_URL}/transaction/initialize",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    raise PaymentProcessingException(
                        "Paystack initialization failed"
                    )
                data = resp.json()
                return data["data"]

        except httpx.HTTPError as e:
            logger.error(f"Paystack API error: {str(e)}", exc_info=True)
            raise NetworkException("Failed to reach Paystack API")
        except Exception as e:
            logger.error(f"Transaction initialization failed: {str(e)}", exc_info=True)
            raise PaymentProcessingException("Failed to initialize transaction")

    @staticmethod
    async def verify_transaction(reference: str) -> dict:
        """
        Verify Paystack transaction status.

        Args:
            reference (str): Transaction reference

        Returns:
            dict: Transaction status and amount

        Raises:
            PaymentProcessingException: If verification fails
        """
        try:
            headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

            async with httpx.AsyncClient(timeout=settings.PAYSTACK_TIMEOUT) as client:
                resp = await client.get(
                    f"{settings.PAYSTACK_API_URL}/transaction/verify/{reference}",
                    headers=headers,
                )
                if resp.status_code != 200:
                    raise PaymentProcessingException("Verification failed")
                data = resp.json()
                return data["data"]

        except Exception as e:
            logger.error(f"Transaction verification failed: {str(e)}", exc_info=True)
            raise PaymentProcessingException("Failed to verify transaction")

    @staticmethod
    def verify_webhook_signature(signature: str, payload: bytes) -> bool:
        """
        Verify Paystack webhook signature.

        Args:
            signature (str): X-Paystack-Signature header
            payload (bytes): Raw request body

        Returns:
            bool: Signature is valid
        """
        try:
            expected = hmac.new(
                settings.PAYSTACK_SECRET_KEY.encode(),
                payload,
                hashlib.sha512,
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False
