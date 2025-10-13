"""VPN-related business logic and services."""
import logging
import subprocess
from pathlib import Path
from typing import Optional

import yaml
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def load_vpn_profiles():
    """Load VPN profiles from profiles.yaml."""
    profiles_file = Path(__file__).parent.parent / "vpn-profiles" / "profiles.yaml"

    if not profiles_file.exists():
        raise HTTPException(
            status_code=404,
            detail="VPN profiles configuration not found. Run: make vpn-profiles-scan"
        )

    with open(profiles_file) as f:
        config = yaml.safe_load(f)

    return config


def get_vpn_connection_status():
    """Get current VPN connection status using nmcli."""
    try:
        result = subprocess.run(
            ["nmcli", "connection", "show", "--active"],
            capture_output=True,
            text=True,
            check=True
        )

        # Look for active VPN connections
        for line in result.stdout.splitlines():
            parts = line.split()
            # Check if this is a VPN connection (type field contains 'vpn')
            if len(parts) >= 4 and 'vpn' in parts[-2].lower():
                conn_name = ' '.join(parts[:-3])  # Name is everything except last 3 fields (uuid, type, device)
                conn_uuid = parts[-3]

                return {
                    "connected": True,
                    "profile_name": conn_name,
                    "connection_uuid": conn_uuid
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
            return uuid.strip()
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
        return password_store_service.update_store("nm-uuid", uuid)
    except Exception as e:
        logger.error(f"Error setting default VPN UUID: {e}")
        return False


def find_profile_by_uuid(profiles: list, uuid: str) -> Optional[dict]:
    """
    Find a VPN profile by its UUID.

    Args:
        profiles: List of VPN profile dictionaries
        uuid: UUID to search for

    Returns:
        Profile dictionary if found, None otherwise
    """
    for profile in profiles:
        if profile.get('uuid') == uuid:
            return profile
    return None


def find_profile_by_id(profiles: list, profile_id: str) -> Optional[dict]:
    """
    Find a VPN profile by its ID (case-insensitive).

    Args:
        profiles: List of VPN profile dictionaries
        profile_id: Profile ID to search for

    Returns:
        Profile dictionary if found, None otherwise
    """
    for profile in profiles:
        if profile['id'].upper() == profile_id.upper():
            return profile
    return None


def get_global_profile(profiles: list) -> Optional[dict]:
    """
    Get the GLOBAL VPN profile.

    Args:
        profiles: List of VPN profile dictionaries

    Returns:
        GLOBAL profile dictionary if found, None otherwise
    """
    return find_profile_by_id(profiles, "GLOBAL")
