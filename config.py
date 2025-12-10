"""
Configuration settings for the Wallet Service API.

Load settings from environment variables.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # Application Configuration
    APP_NAME: str = os.getenv("APP_NAME", "Wallet Service")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    SERVER_NAME: str = os.getenv("SERVER_NAME", "_")
    
    # URLs
    APP_URL: str = os.getenv("APP_URL", "https://api.wallet.com")
    DEV_URL: str = os.getenv("DEV_URL", "http://localhost:3000")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Database Configuration
    DB_TYPE: str = os.getenv("DB_TYPE", "postgresql")
    DB_HOST: str = os.getenv("DB_HOST", "db")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "wallet_user")
    DB_PASS: str = os.getenv("DB_PASS", "wallet_password")
    DB_NAME: str = os.getenv("DB_NAME", "wallet_db")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://wallet_user:wallet_password@db:5432/wallet_db"
    )
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    REDIS_TTL: int = int(os.getenv("REDIS_TTL", "900"))
    
    # JWT Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-jwt-super-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRY_HOURS: int = int(os.getenv("JWT_EXPIRY_HOURS", "48"))
    JWT_REFRESH_EXPIRY_DAYS: int = int(os.getenv("JWT_REFRESH_EXPIRY_DAYS", "30"))
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/auth/google/callback"
    )
    
    # Paystack
    PAYSTACK_SECRET_KEY: str = os.getenv("PAYSTACK_SECRET_KEY", "")
    PAYSTACK_PUBLIC_KEY: str = os.getenv("PAYSTACK_PUBLIC_KEY", "")
    PAYSTACK_WEBHOOK_SECRET: str = os.getenv("PAYSTACK_WEBHOOK_SECRET", "")
    PAYSTACK_API_URL: str = os.getenv("PAYSTACK_API_URL", "https://api.paystack.co")
    PAYSTACK_TIMEOUT: int = int(os.getenv("PAYSTACK_TIMEOUT", "30"))
    
    # API Keys Configuration
    API_KEY_MAX_PER_USER: int = int(os.getenv("API_KEY_MAX_PER_USER", "5"))
    MAX_API_KEYS_PER_USER: int = int(os.getenv("API_KEY_MAX_PER_USER", "5"))  # Alias for compatibility
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = APP_NAME
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()


# Validation: Ensure critical settings are provided in production
if settings.ENVIRONMENT == "production":
    required_settings = [
        ("GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID),
        ("GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET),
        ("PAYSTACK_SECRET_KEY", settings.PAYSTACK_SECRET_KEY),
        ("JWT_SECRET", settings.JWT_SECRET),
        ("SECRET_KEY", settings.SECRET_KEY),
    ]
    
    missing_settings = [name for name, value in required_settings if not value]
    
    if missing_settings:
        raise ValueError(
            f"Missing required production settings: {', '.join(missing_settings)}"
        )

# Validate JWT_SECRET is changed from default in production
if settings.ENVIRONMENT == "production":
    if "change-in-production" in settings.JWT_SECRET.lower() or \
       "change-in-production" in settings.SECRET_KEY.lower():
        raise ValueError(
            "JWT_SECRET and SECRET_KEY must be changed from default values in production"
        )