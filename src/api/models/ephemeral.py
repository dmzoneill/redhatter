"""Pydantic models for ephemeral namespace operations."""

from pydantic import BaseModel, Field


class NamespaceDetails(BaseModel):
    """Details about an ephemeral namespace."""

    name: str = Field(..., description="Namespace name")
    route: str | None = Field(None, description="Namespace route/URL")
    expires: str | None = Field(None, description="Expiration timestamp")
    password: str | None = Field(None, description="Namespace password (if requested)")


class NamespaceExtendRequest(BaseModel):
    """Request to extend namespace duration."""

    duration: str = Field(default="72h", description="Duration to extend (e.g., '72h', '48h')")


class NamespaceStatus(BaseModel):
    """Current namespace status."""

    exists: bool = Field(..., description="Whether namespace exists")
    name: str | None = Field(None, description="Namespace name")
    expires: str | None = Field(None, description="Expiration timestamp")
    details: dict | None = Field(None, description="Additional namespace details")
