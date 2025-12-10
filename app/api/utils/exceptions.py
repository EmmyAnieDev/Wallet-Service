"""
Custom exception classes for the Wallet Service API.

This module defines all custom exceptions used throughout the application
for consistent error handling and logging.
"""

from typing import Any, Optional
from fastapi import status


class WalletServiceException(Exception):
    """
    Base exception class for all Wallet Service exceptions.
    
    Attributes:
        message (str): Error message
        status_code (int): HTTP status code
        error_code (str): Application-specific error code
        details (dict): Additional error details
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize WalletServiceException.

        Args:
            message (str): Error message
            status_code (int): HTTP status code (default: 500)
            error_code (str): Application-specific error code (default: INTERNAL_ERROR)
            details (dict, optional): Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class InvalidCredentialsException(WalletServiceException):
    """
    Raised when user provides invalid credentials during authentication.

    Examples:
        >>> raise InvalidCredentialsException("Wrong password provided")
    """

    def __init__(self, message: str = "Invalid credentials provided", details: Optional[dict] = None):
        """Initialize InvalidCredentialsException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_CREDENTIALS",
            details=details,
        )


class UserNotFoundException(WalletServiceException):
    """
    Raised when a user account is not found.

    Examples:
        >>> raise UserNotFoundException("User with email not found")
    """

    def __init__(self, message: str = "User not found", details: Optional[dict] = None):
        """Initialize UserNotFoundException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="USER_NOT_FOUND",
            details=details,
        )


class EmailAlreadyInUseException(WalletServiceException):
    """
    Raised when attempting to register with an email already in use.

    Examples:
        >>> raise EmailAlreadyInUseException("Email already registered")
    """

    def __init__(self, message: str = "Email is already in use", details: Optional[dict] = None):
        """Initialize EmailAlreadyInUseException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="EMAIL_IN_USE",
            details=details,
        )


class WeakPasswordException(WalletServiceException):
    """
    Raised when a password does not meet security requirements.

    Examples:
        >>> raise WeakPasswordException("Password must be at least 8 characters")
    """

    def __init__(self, message: str = "Password does not meet security requirements", details: Optional[dict] = None):
        """Initialize WeakPasswordException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="WEAK_PASSWORD",
            details=details,
        )


class TokenExpiredException(WalletServiceException):
    """
    Raised when an authentication token has expired.

    Examples:
        >>> raise TokenExpiredException("JWT token has expired")
    """

    def __init__(self, message: str = "Token has expired", details: Optional[dict] = None):
        """Initialize TokenExpiredException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_EXPIRED",
            details=details,
        )


class InvalidTokenException(WalletServiceException):
    """
    Raised when a token is invalid or malformed.

    Examples:
        >>> raise InvalidTokenException("Invalid token signature")
    """

    def __init__(self, message: str = "Invalid token", details: Optional[dict] = None):
        """Initialize InvalidTokenException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_TOKEN",
            details=details,
        )


class TokenRevokedException(WalletServiceException):
    """
    Raised when a token has been revoked.

    Examples:
        >>> raise TokenRevokedException("Token has been revoked")
    """

    def __init__(self, message: str = "Token has been revoked", details: Optional[dict] = None):
        """Initialize TokenRevokedException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_REVOKED",
            details=details,
        )


class MissingAuthorizationException(WalletServiceException):
    """
    Raised when authorization header is missing.

    Examples:
        >>> raise MissingAuthorizationException("Missing authorization header")
    """

    def __init__(self, message: str = "Missing or invalid authorization header", details: Optional[dict] = None):
        """Initialize MissingAuthorizationException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="MISSING_AUTHORIZATION",
            details=details,
        )


class NetworkException(WalletServiceException):
    """
    Raised when a network request fails (e.g., to external services like Paystack).

    Examples:
        >>> raise NetworkException("Failed to reach Paystack API")
    """

    def __init__(self, message: str = "Network request failed", details: Optional[dict] = None):
        """Initialize NetworkException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="NETWORK_ERROR",
            details=details,
        )


class InsufficientBalanceException(WalletServiceException):
    """
    Raised when attempting to transfer more funds than available in wallet.

    Examples:
        >>> raise InsufficientBalanceException("Insufficient wallet balance")
    """

    def __init__(self, message: str = "Insufficient balance", details: Optional[dict] = None):
        """Initialize InsufficientBalanceException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INSUFFICIENT_BALANCE",
            details=details,
        )


class InvalidAPIKeyException(WalletServiceException):
    """
    Raised when an API key is invalid, expired, or revoked.

    Examples:
        >>> raise InvalidAPIKeyException("API key has expired")
    """

    def __init__(self, message: str = "Invalid API key", details: Optional[dict] = None):
        """Initialize InvalidAPIKeyException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_API_KEY",
            details=details,
        )


class InsufficientPermissionsException(WalletServiceException):
    """
    Raised when an API key or user lacks required permissions for an action.

    Examples:
        >>> raise InsufficientPermissionsException("API key lacks 'transfer' permission")
    """

    def __init__(self, message: str = "Insufficient permissions", details: Optional[dict] = None):
        """Initialize InsufficientPermissionsException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="INSUFFICIENT_PERMISSIONS",
            details=details,
        )


class PaymentProcessingException(WalletServiceException):
    """
    Raised when payment processing through Paystack fails.

    Examples:
        >>> raise PaymentProcessingException("Paystack payment initialization failed")
    """

    def __init__(self, message: str = "Payment processing failed", details: Optional[dict] = None):
        """Initialize PaymentProcessingException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="PAYMENT_FAILED",
            details=details,
        )


class TransactionNotFoundException(WalletServiceException):
    """
    Raised when a transaction is not found in the database.

    Examples:
        >>> raise TransactionNotFoundException("Transaction reference not found")
    """

    def __init__(self, message: str = "Transaction not found", details: Optional[dict] = None):
        """Initialize TransactionNotFoundException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TRANSACTION_NOT_FOUND",
            details=details,
        )


class WalletNotFoundException(WalletServiceException):
    """
    Raised when a wallet is not found.

    Examples:
        >>> raise WalletNotFoundException("User wallet not found")
    """

    def __init__(self, message: str = "Wallet not found", details: Optional[dict] = None):
        """Initialize WalletNotFoundException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="WALLET_NOT_FOUND",
            details=details,
        )


class APIKeyNotFoundException(WalletServiceException):
    """
    Raised when an API key is not found in the database.

    Examples:
        >>> raise APIKeyNotFoundException("API key not found")
    """

    def __init__(self, message: str = "API key not found", details: Optional[dict] = None):
        """Initialize APIKeyNotFoundException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="API_KEY_NOT_FOUND",
            details=details,
        )


class APIKeyLimitException(WalletServiceException):
    """
    Raised when user attempts to create more API keys than the maximum allowed.

    Examples:
        >>> raise APIKeyLimitException("Maximum 5 API keys allowed per user")
    """

    def __init__(self, message: str = "API key limit exceeded", details: Optional[dict] = None):
        """Initialize APIKeyLimitException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="API_KEY_LIMIT_EXCEEDED",
            details=details,
        )


class DuplicateTransactionException(WalletServiceException):
    """
    Raised when a duplicate transaction is detected.

    Examples:
        >>> raise DuplicateTransactionException("Transaction reference already exists")
    """

    def __init__(self, message: str = "Duplicate transaction", details: Optional[dict] = None):
        """Initialize DuplicateTransactionException."""
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="DUPLICATE_TRANSACTION",
            details=details,
        )
