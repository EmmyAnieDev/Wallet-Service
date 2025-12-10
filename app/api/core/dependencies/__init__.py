"""
Core dependencies for FastAPI routes.

This package provides dependency injection functions for authentication,
authorization, and other cross-cutting concerns.
"""

from app.api.core.dependencies.auth import get_current_user

__all__ = ["get_current_user"]
