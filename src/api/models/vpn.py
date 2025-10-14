"""VPN-related Pydantic models."""

from typing import Optional

from pydantic import BaseModel


class VPNProfile(BaseModel):
    """VPN Profile model."""

    id: str
    name: str
    remote: str
    uuid: Optional[str] = None
    port: Optional[int] = None
    proto_tcp: Optional[bool] = None
    tunnel_mtu: Optional[int] = None
    dns_search: Optional[str] = None
    route_table: Optional[int] = None


class VPNStatus(BaseModel):
    """VPN connection status model."""

    connected: bool
    profile_name: Optional[str] = None
    profile_id: Optional[str] = None
    connection_details: Optional[dict] = None


class VPNDefaultInfo(BaseModel):
    """VPN default profile information model."""

    uuid: str
    profile_id: Optional[str] = None
    profile_name: Optional[str] = None
    source: str = "password_store"


class VPNSetDefaultRequest(BaseModel):
    """Request model for setting default VPN profile."""

    profile_id: Optional[str] = None
    uuid: Optional[str] = None
