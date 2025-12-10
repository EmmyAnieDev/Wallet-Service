import secrets
from typing import List, Optional
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB


class APIKey(SQLModel, table=True):
    """
    API Key model for service-to-service authentication and authorization.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=255)
    key: str = Field(unique=True, index=True, max_length=255)
    permissions: Optional[List[str]] = Field(
        sa_column=Column(JSONB), default=[]
    )
    expires_at: datetime = Field(index=True)
    revoked: bool = Field(default=False, index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @staticmethod
    def generate_key() -> str:
        """
        Generate a unique API key with sk_live_ prefix.
        
        Returns:
            str: Generated API key in format sk_live_<random_string>
        """
        return f"sk_live_{secrets.token_urlsafe(32)}"

    def is_valid(self) -> bool:
        """
        Check if the API key is valid (not revoked and not expired).
        
        Returns:
            bool: True if key is valid, False otherwise
        """
        now = datetime.utcnow()
        return not self.revoked and self.expires_at > now

    def has_permission(self, permission: str) -> bool:
        """
        Check if this API key has a specific permission.
        
        Args:
            permission (str): The permission to check
            
        Returns:
            bool: True if key has the permission, False otherwise
        """
        return self.permissions is not None and permission in self.permissions
