"""Pydantic models for ephemeral namespace operations."""

from typing import Optional

from pydantic import BaseModel, Field


class NamespaceDetails(BaseModel):
    """Details about an ephemeral namespace."""

    name: str = Field(..., description="Namespace name")
    route: Optional[str] = Field(None, description="Namespace route/URL")
    expires: Optional[str] = Field(None, description="Expiration timestamp")
    password: Optional[str] = Field(
        None, description="Namespace password (if requested)"
    )


class NamespaceExtendRequest(BaseModel):
    """Request to extend namespace duration."""

    duration: str = Field(
        default="72h", description="Duration to extend (e.g., '72h', '48h')"
    )


class NamespaceStatus(BaseModel):
    """Current namespace status."""

    exists: bool = Field(..., description="Whether namespace exists")
    name: Optional[str] = Field(None, description="Namespace name")
    expires: Optional[str] = Field(None, description="Expiration timestamp")
    details: Optional[dict] = Field(None, description="Additional namespace details")
