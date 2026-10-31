"""VPN-related business logic and services."""

import logging
import subprocess
from pathlib import Path
from typing import Any, cast

import yaml
from fastapi import HTTPException

logger = logging.getLogger(__name__)


# Cache profiles config to avoid repeated YAML parsing. A single dict container
# keeps the mutable state without a module-level ``global`` statement.
_PROFILES_CACHE: dict[str, Any] = {"config": None, "mtime": None}


def load_vpn_profiles(use_cache: bool = True) -> dict[str, Any]:
    """
    Load VPN profiles from profiles.yaml with optional caching.

    Args:
        use_cache: If True, use cached profiles if file hasn't changed

    Returns:
        Dictionary containing VPN profiles configuration

    Raises:
        HTTPException: If profiles file not found
    """
    profiles_file = Path(__file__).parent.parent / "vpn-profiles" / "profiles.yaml"

    if not profiles_file.exists():
        raise HTTPException(
            status_code=404,
            detail="VPN profiles configuration not found. Run: make vpn-profiles-scan",
        )

    # Check if we can use cache
    if use_cache and _PROFILES_CACHE["config"] is not None:
        current_mtime = profiles_file.stat().st_mtime
        if current_mtime == _PROFILES_CACHE["mtime"]:
            logger.debug("Using cached VPN profiles")
            return cast(dict[str, Any], _PROFILES_CACHE["config"])

    # Load from file
    with open(profiles_file, encoding="utf-8") as f:
        config = cast(dict[str, Any], yaml.safe_load(f))

    # Update cache
    if use_cache:
        _PROFILES_CACHE["config"] = config
        _PROFILES_CACHE["mtime"] = profiles_file.stat().st_mtime
        logger.debug("VPN profiles loaded and cached")

    return config


def get_vpn_connection_status() -> dict[str, Any]:
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
                conn_name = " ".join(parts[:-3])  # Name is everything except last 3 fields (uuid, type, device)
                conn_uuid = parts[-3]

                return {
                    "connected": True,
                    "profile_name": conn_name,
                    "connection_uuid": conn_uuid,
                }

        return {"connected": False}

    except subprocess.CalledProcessError as e:
        logger.error("Error checking VPN status: %s", e)
        return {"connected": False, "error": str(e)}


def get_default_vpn_uuid(password_store_service) -> str | None:
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
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as e:
        logger.error("Error retrieving default VPN UUID: %s", e)
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
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as e:
        logger.error("Error setting default VPN UUID: %s", e)
        return False


def find_profile_by_uuid(profiles: list[dict[str, Any]], uuid: str) -> dict[str, Any] | None:
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


def find_profile_by_id(profiles: list[dict[str, Any]], profile_id: str) -> dict[str, Any] | None:
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


def get_global_profile(profiles: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Get the GLOBAL VPN profile.

    Args:
        profiles: List of VPN profile dictionaries

    Returns:
        GLOBAL profile dictionary if found, None otherwise
    """
    return find_profile_by_id(profiles, "GLOBAL")
