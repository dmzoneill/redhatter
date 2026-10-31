"""VPN-related business logic and services."""

import logging
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import yaml
from fastapi import HTTPException

logger = logging.getLogger(__name__)


# Cache profiles config to avoid repeated YAML parsing
_profiles_cache = None
_profiles_cache_mtime = None


def load_vpn_profiles(use_cache: bool = True) -> Dict[str, Any]:
    """
    Load VPN profiles from profiles.yaml with optional caching.

    Args:
        use_cache: If True, use cached profiles if file hasn't changed

    Returns:
        Dictionary containing VPN profiles configuration

    Raises:
        HTTPException: If profiles file not found
    """
    global _profiles_cache, _profiles_cache_mtime

    profiles_file = Path(__file__).parent.parent / "vpn-profiles" / "profiles.yaml"

    if not profiles_file.exists():
        raise HTTPException(
            status_code=404,
            detail="VPN profiles configuration not found. Run: make vpn-profiles-scan",
        )

    # Check if we can use cache
    if use_cache and _profiles_cache is not None:
        current_mtime = profiles_file.stat().st_mtime
        if current_mtime == _profiles_cache_mtime:
            logger.debug("Using cached VPN profiles")
            return cast(Dict[str, Any], _profiles_cache)

    # Load from file
    with open(profiles_file) as f:
        config = cast(Dict[str, Any], yaml.safe_load(f))

    # Update cache
    if use_cache:
        _profiles_cache = config
        _profiles_cache_mtime = profiles_file.stat().st_mtime
        logger.debug("VPN profiles loaded and cached")

    return config


def get_vpn_connection_status() -> Dict[str, Any]:
    """Get current VPN connection status using nmcli."""
    try:
        result = subprocess.run(
            ["nmcli", "connection", "show", "--active"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Look for active VPN connections
        for line in result.stdout.splitlines():
            parts = line.split()
            # Check if this is a VPN connection (type field contains 'vpn')
            if len(parts) >= 4 and "vpn" in parts[-2].lower():
                conn_name = " ".join(
                    parts[:-3]
                )  # Name is everything except last 3 fields (uuid, type, device)
                conn_uuid = parts[-3]

                return {
                    "connected": True,
                    "profile_name": conn_name,
                    "connection_uuid": conn_uuid,
                }

        return {"connected": False}

    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking VPN status: {e}")
        return {"connected": False, "error": str(e)}


def get_default_vpn_uuid(password_store_service) -> Optional[str]:
    """
    Get the default VPN UUID from password store.

    Args:
        password_store_service: Service for accessing password store

    Returns:
        UUID string or None if not found
    """
    try:
        uuid = password_store_service.get_from_store("nm-uuid")
        if uuid and isinstance(uuid, str):
            return cast(str, uuid.strip())
        return None
    except Exception as e:
        logger.error(f"Error retrieving default VPN UUID: {e}")
        return None


def set_default_vpn_uuid(password_store_service, uuid: str) -> bool:
    """
    Set the default VPN UUID in password store.

    Args:
        password_store_service: Service for accessing password store
        uuid: UUID to set as default

    Returns:
        True if successful, False otherwise
    """
    try:
        result = password_store_service.update_store("nm-uuid", uuid)
        return cast(bool, result)
    except Exception as e:
        logger.error(f"Error setting default VPN UUID: {e}")
        return False


def find_profile_by_uuid(
    profiles: List[Dict[str, Any]], uuid: str
) -> Optional[Dict[str, Any]]:
    """
    Find a VPN profile by its UUID.

    Args:
        profiles: List of VPN profile dictionaries
        uuid: UUID to search for

    Returns:
        Profile dictionary if found, None otherwise
    """
    for profile in profiles:
        if profile.get("uuid") == uuid:
            return profile
    return None


def find_profile_by_id(
    profiles: List[Dict[str, Any]], profile_id: str
) -> Optional[Dict[str, Any]]:
    """
    Find a VPN profile by its ID (case-insensitive).

    Args:
        profiles: List of VPN profile dictionaries
        profile_id: Profile ID to search for

    Returns:
        Profile dictionary if found, None otherwise
    """
    for profile in profiles:
        if profile["id"].upper() == profile_id.upper():
            return profile
    return None


def get_global_profile(profiles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Get the GLOBAL VPN profile.

    Args:
        profiles: List of VPN profile dictionaries

    Returns:
        GLOBAL profile dictionary if found, None otherwise
    """
    return find_profile_by_id(profiles, "GLOBAL")
