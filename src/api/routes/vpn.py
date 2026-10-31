"""VPN-related API routes."""

import logging
import subprocess
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException

from api.dependencies.auth import verify_token as get_verify_token
from api.models.vpn import (
    VPNDefaultInfo,
    VPNProfile,
    VPNSetDefaultRequest,
    VPNStatus,
)
from services.password_store import password_store
from services.vpn import (
    find_profile_by_id,
    find_profile_by_uuid,
    get_default_vpn_uuid,
    get_global_profile,
    get_vpn_connection_status,
    load_vpn_profiles,
    set_default_vpn_uuid,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vpn", tags=["vpn"])

# Errors the VPN helpers can raise; mapped to HTTP 500 with the error message.
_VPN_ERRORS = (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError, yaml.YAMLError)


@router.get("/profiles", response_model=list[VPNProfile], dependencies=[Depends(get_verify_token)])
def list_vpn_profiles():
    """List all configured VPN profiles."""
    try:
        config = load_vpn_profiles()
        profiles = config.get("profiles", [])
        return profiles
    except _VPN_ERRORS as e:
        logger.error("Error loading VPN profiles: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/profiles/{profile_id}", response_model=VPNProfile, dependencies=[Depends(get_verify_token)])
def get_vpn_profile(profile_id: str):
    """Get details for a specific VPN profile."""
    try:
        config = load_vpn_profiles()
        profiles = config.get("profiles", [])

        profile = find_profile_by_id(profiles, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

        return profile
    except HTTPException:
        raise
    except _VPN_ERRORS as e:
        logger.error("Error getting VPN profile: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/default", response_model=VPNDefaultInfo, dependencies=[Depends(get_verify_token)])
def get_default_vpn():
    """
    Get the default VPN profile information.

    Returns the UUID from password store and attempts to match it with a profile from profiles.yaml.
    If nm-uuid doesn't exist, initializes it to the GLOBAL profile.
    """
    try:
        # Try to get default UUID from password store
        uuid = get_default_vpn_uuid(password_store)

        # If no UUID found, initialize to GLOBAL profile
        if not uuid:
            logger.info("No default VPN UUID found, initializing to GLOBAL profile")
            config = load_vpn_profiles()
            profiles = config.get("profiles", [])
            global_profile = get_global_profile(profiles)

            if not global_profile:
                raise HTTPException(status_code=404, detail="GLOBAL profile not found in profiles.yaml")

            if not global_profile.get("uuid"):
                raise HTTPException(
                    status_code=500,
                    detail="GLOBAL profile does not have a UUID configured",
                )

            uuid = global_profile["uuid"]

            # Save it to password store
            if not set_default_vpn_uuid(password_store, uuid):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to initialize default VPN UUID in password store",
                )

            return VPNDefaultInfo(
                uuid=uuid,
                profile_id=global_profile["id"],
                profile_name=global_profile["name"],
                source="password_store (initialized)",
            )

        # UUID exists, try to find matching profile
        config = load_vpn_profiles()
        profiles = config.get("profiles", [])
        profile = find_profile_by_uuid(profiles, uuid)

        if profile:
            return VPNDefaultInfo(
                uuid=uuid,
                profile_id=profile["id"],
                profile_name=profile["name"],
                source="password_store",
            )
        # UUID exists but doesn't match any profile
        logger.warning("Default VPN UUID %s does not match any known profile", uuid)
        return VPNDefaultInfo(uuid=uuid, profile_id=None, profile_name=None, source="password_store")

    except HTTPException:
        raise
    except _VPN_ERRORS as e:
        logger.error("Error getting default VPN: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/default", dependencies=[Depends(get_verify_token)])
def set_default_vpn(request: VPNSetDefaultRequest):
    """
    Set the default VPN profile.

    Accepts either profile_id or uuid. If profile_id is provided, it takes precedence
    and the UUID is looked up from profiles.yaml. Updates the nm-uuid in password store.
    """
    try:
        config = load_vpn_profiles()
        profiles = config.get("profiles", [])

        target_uuid = None

        # Prefer profile_id if provided
        if request.profile_id:
            profile = find_profile_by_id(profiles, request.profile_id)
            if not profile:
                raise HTTPException(status_code=404, detail=f"Profile '{request.profile_id}' not found")

            if not profile.get("uuid"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Profile '{request.profile_id}' does not have a UUID configured",
                )

            target_uuid = profile["uuid"]
            profile_name = profile["name"]

        elif request.uuid:
            target_uuid = request.uuid
            # Try to find profile by UUID for response info
            profile = find_profile_by_uuid(profiles, request.uuid)
            profile_name = profile["name"] if profile else None

        else:
            raise HTTPException(status_code=400, detail="Either profile_id or uuid must be provided")

        # Update password store
        if not set_default_vpn_uuid(password_store, target_uuid):
            raise HTTPException(
                status_code=500,
                detail="Failed to update default VPN UUID in password store",
            )

        logger.info("Default VPN set to UUID: %s", target_uuid)

        return {
            "success": True,
            "message": f"Default VPN set to {profile_name if profile_name else target_uuid}",
            "uuid": target_uuid,
            "profile_name": profile_name,
        }

    except HTTPException:
        raise
    except _VPN_ERRORS as e:
        logger.error("Error setting default VPN: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/connect/default", dependencies=[Depends(get_verify_token)])
def connect_vpn_default():
    """
    Connect to the default VPN using the vpn-connect script.

    This calls vpn-connect without a UUID parameter, so the script will
    fetch the default UUID from the password store.
    """
    try:
        # Find the vpn-connect script (relative to this file)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # src/api/routes -> src

        script_paths = [
            project_root / "vpn-connect",
            Path.home() / "src" / "rh-otp-auto-connect" / "src" / "vpn-connect",
            Path("/usr/local/bin/vpn-connect"),
            Path("/usr/bin/vpn-connect"),
        ]

        script_path = None
        for path in script_paths:
            if path.exists() and path.is_file():
                script_path = path
                break

        if not script_path:
            raise HTTPException(status_code=404, detail="vpn-connect script not found")

        # Execute the script without UUID parameter (uses default from password store)
        result = subprocess.run([str(script_path)], capture_output=True, text=True, timeout=60, check=False)

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Connection failed"
            logger.error("Default VPN connect failed: %s", error_msg)
            raise HTTPException(status_code=500, detail=f"Failed to connect: {error_msg}")

        logger.info("Connected to default VPN")
        return {
            "success": True,
            "message": "Connected to default VPN",
            "method": "default",
        }

    except subprocess.TimeoutExpired as exc:
        logger.error("Default VPN connect timeout")
        raise HTTPException(status_code=504, detail="Connection timeout") from exc
    except _VPN_ERRORS as e:
        logger.error("Error connecting to default VPN: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/connect/standard", dependencies=[Depends(get_verify_token)])
def connect_vpn_standard():
    """
    Connect to VPN using the standard vpn-connect script.

    DEPRECATED: Use /vpn/connect/default instead.
    This endpoint is kept for backward compatibility.
    """
    return connect_vpn_default()


@router.post("/connect/shuttle", dependencies=[Depends(get_verify_token)])
def connect_vpn_shuttle():
    """Connect to VPN using the shuttle vpn-connect-shuttle script."""
    try:
        # Find the vpn-connect-shuttle script (relative to this file)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # src/api/routes -> src

        script_paths = [
            project_root / "vpn-connect-shuttle",
            Path.home() / "src" / "rh-otp-auto-connect" / "src" / "vpn-connect-shuttle",
            Path("/usr/local/bin/vpn-connect-shuttle"),
            Path("/usr/bin/vpn-connect-shuttle"),
        ]

        script_path = None
        for path in script_paths:
            if path.exists() and path.is_file():
                script_path = path
                break

        if not script_path:
            raise HTTPException(status_code=404, detail="vpn-connect-shuttle script not found")

        # Execute the script
        result = subprocess.run([str(script_path)], capture_output=True, text=True, timeout=60, check=False)

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Connection failed"
            logger.error("VPN shuttle connect failed: %s", error_msg)
            raise HTTPException(status_code=500, detail=f"Failed to connect: {error_msg}")

        logger.info("Connected to VPN via shuttle method")
        return {
            "success": True,
            "message": "Connected to VPN (shuttle)",
            "method": "shuttle",
        }

    except subprocess.TimeoutExpired as exc:
        logger.error("VPN shuttle connect timeout")
        raise HTTPException(status_code=504, detail="Connection timeout") from exc
    except _VPN_ERRORS as e:
        logger.error("Error connecting VPN (shuttle): %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/connect/{profile_id}", dependencies=[Depends(get_verify_token)])
def connect_vpn_profile(profile_id: str):
    """Connect to a specific VPN profile using the vpn-connect script."""
    try:
        config = load_vpn_profiles()
        profiles = config.get("profiles", [])

        # Find profile by ID (case-insensitive)
        target_profile = find_profile_by_id(profiles, profile_id)

        if not target_profile:
            raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

        # Get UUID from the profile
        profile_uuid = target_profile.get("uuid")
        profile_name = target_profile.get("name")

        if not profile_uuid:
            raise HTTPException(
                status_code=400,
                detail=f"Profile '{profile_id}' does not have a UUID configured",
            )

        # Find the vpn-connect script (relative to this file)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # src/api/routes -> src

        script_paths = [
            project_root / "vpn-connect",
            Path.home() / "src" / "rh-otp-auto-connect" / "src" / "vpn-connect",
            Path("/usr/local/bin/vpn-connect"),
            Path("/usr/bin/vpn-connect"),
        ]

        script_path = None
        for path in script_paths:
            if path.exists() and path.is_file():
                script_path = path
                break

        if not script_path:
            raise HTTPException(status_code=404, detail="vpn-connect script not found")

        # Execute vpn-connect script with the UUID
        result = subprocess.run(
            [str(script_path), "--uuid", profile_uuid],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Connection failed"
            logger.error("Failed to connect to VPN: %s", error_msg)
            raise HTTPException(status_code=500, detail=f"Failed to connect: {error_msg}")

        logger.info("Connected to VPN profile: %s (UUID: %s)", profile_name, profile_uuid)
        return {
            "success": True,
            "message": f"Connected to {profile_name}",
            "profile_id": profile_id,
            "profile_name": profile_name,
            "uuid": profile_uuid,
        }

    except HTTPException:
        raise
    except subprocess.TimeoutExpired as exc:
        logger.error("VPN connect timeout for profile %s", profile_id)
        raise HTTPException(status_code=504, detail="Connection timeout") from exc
    except _VPN_ERRORS as e:
        logger.error("Error connecting to VPN: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/disconnect", dependencies=[Depends(get_verify_token)])
def disconnect_vpn():
    """Disconnect active VPN connection."""
    try:
        # Get current VPN status
        status = get_vpn_connection_status()

        if not status.get("connected"):
            return {
                "success": True,
                "message": "No active VPN connection",
                "was_connected": False,
            }

        # Disconnect using connection name
        conn_name = status.get("profile_name")
        if not conn_name:
            raise HTTPException(status_code=500, detail="Could not determine VPN connection name")

        result = subprocess.run(
            ["nmcli", "connection", "down", "id", str(conn_name)],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            logger.error("Failed to disconnect VPN: %s", error_msg)
            raise HTTPException(status_code=500, detail=f"Failed to disconnect: {error_msg}")

        logger.info("Disconnected VPN: %s", conn_name)
        return {
            "success": True,
            "message": f"Disconnected from {conn_name}",
            "was_connected": True,
        }

    except HTTPException:
        raise
    except _VPN_ERRORS as e:
        logger.error("Error disconnecting VPN: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/status", response_model=VPNStatus, dependencies=[Depends(get_verify_token)])
def get_vpn_status():
    """Get current VPN connection status."""
    try:
        status = get_vpn_connection_status()

        # If connected, try to find matching profile
        profile_id = None
        if status.get("connected"):
            config = load_vpn_profiles()
            profiles = config.get("profiles", [])
            conn_name = status.get("profile_name", "")

            # Try to match by name or UUID
            for profile in profiles:
                if profile.get("name") == conn_name or profile.get("uuid") == status.get("connection_uuid"):
                    profile_id = profile["id"]
                    break

        return VPNStatus(
            connected=status.get("connected", False),
            profile_name=status.get("profile_name"),
            profile_id=profile_id,
            connection_details=status,
        )

    except _VPN_ERRORS as e:
        logger.error("Error getting VPN status: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
