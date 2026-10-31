"""Ephemeral namespace API routes.

These routes interact with external Kubernetes instances where
ephemeral pipelines are run (bonfire/OpenShift environments).
"""

import logging
import subprocess

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies.auth import verify_token as get_verify_token
from api.models.ephemeral import (
    NamespaceDetails,
    NamespaceExtendRequest,
    NamespaceStatus,
)
from services.ephemeral import extend_namespace as extend_namespace_service
from services.ephemeral import (
    get_namespace_expires,
    get_namespace_list,
    get_namespace_name,
    get_namespace_password,
    get_namespace_route,
)
from services.password_store import password_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ephemeral", tags=["ephemeral"])

# Errors the ephemeral helpers can raise; mapped to HTTP 500 with the error message.
_EPHEMERAL_ERRORS = (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError)


@router.get("/namespace/details", response_model=NamespaceDetails, dependencies=[Depends(get_verify_token)])
def get_namespace_details(
    headless: bool = Query(default=False, description="Use headless mode for authentication"),
    include_password: bool = Query(default=False, description="Include namespace password in response"),
):
    """
    Get details about the user's ephemeral namespace.

    This endpoint fetches information about the current ephemeral environment
    including the namespace name, route, and expiration date.
    """
    try:
        # Get username from password store
        username = password_store.get_from_store("username")
        if not username:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve username from password store",
            )

        username = username.strip()

        # Get namespace details
        namespace_name = get_namespace_name(username, headless)
        if not namespace_name:
            raise HTTPException(
                status_code=404,
                detail="No visible namespace reservation found for user",
            )

        # Get additional details
        route = get_namespace_route(namespace_name)
        expires = get_namespace_expires(username, headless)

        # Optionally get password
        password = None
        if include_password:
            password = get_namespace_password(namespace_name)

        return NamespaceDetails(name=namespace_name, route=route, expires=expires, password=password)

    except HTTPException:
        raise
    except _EPHEMERAL_ERRORS as e:
        logger.error("Error getting namespace details: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/namespace/status", response_model=NamespaceStatus, dependencies=[Depends(get_verify_token)])
def get_namespace_status(
    headless: bool = Query(default=False, description="Use headless mode for authentication"),
):
    """
    Get the status of the user's ephemeral namespace.

    Returns information about whether a namespace exists and its current state.
    """
    try:
        # Get username from password store
        username = password_store.get_from_store("username")
        if not username:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve username from password store",
            )

        username = username.strip()

        # Get namespace list
        namespace_list = get_namespace_list(username, headless)

        if not namespace_list or len(namespace_list) == 0:
            return NamespaceStatus(exists=False, name=None, expires=None, details=None)

        # Namespace exists
        namespace_name = namespace_list[0] if len(namespace_list) > 0 else None
        expires = namespace_list[6] if len(namespace_list) > 6 else None

        return NamespaceStatus(
            exists=True,
            name=namespace_name,
            expires=expires,
            details={"full_info": namespace_list},
        )

    except HTTPException:
        raise
    except _EPHEMERAL_ERRORS as e:
        logger.error("Error getting namespace status: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/namespace/extend", dependencies=[Depends(get_verify_token)])
def extend_namespace(
    request: NamespaceExtendRequest | None = None,
    headless: bool = Query(default=False, description="Use headless mode for authentication"),
):
    """
    Extend the duration of the user's ephemeral namespace.

    This extends the namespace reservation to prevent it from being cleaned up.
    """
    try:
        # Get username from password store
        username = password_store.get_from_store("username")
        if not username:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve username from password store",
            )

        username = username.strip()

        # Get namespace name
        namespace_name = get_namespace_name(username, headless)
        if not namespace_name:
            raise HTTPException(
                status_code=404,
                detail="No visible namespace reservation found for user",
            )

        # Get duration from request or use default
        duration = "72h"
        if request and request.duration:
            duration = request.duration

        # Extend the namespace
        success = extend_namespace_service(namespace_name, duration)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to extend namespace {namespace_name}")

        # Get updated namespace info
        namespace_list = get_namespace_list(username, headless)
        expires = get_namespace_expires(username, headless)

        logger.info("Extended namespace %s by %s", namespace_name, duration)

        return {
            "success": True,
            "message": f"Namespace {namespace_name} extended by {duration}",
            "namespace": namespace_name,
            "duration": duration,
            "new_expiration": expires,
            "details": namespace_list,
        }

    except HTTPException:
        raise
    except _EPHEMERAL_ERRORS as e:
        logger.error("Error extending namespace: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/namespace/clear-cache", dependencies=[Depends(get_verify_token)])
def clear_namespace_cache(
    headless: bool = Query(default=False, description="Use headless mode for authentication"),
):
    """
    Clear the namespace cache and refresh data.

    This forces a fresh lookup of namespace information from bonfire.
    Note: The current implementation doesn't use a cache at the service layer,
    so this endpoint mainly serves for compatibility with the old API.
    """
    try:
        # Get username from password store
        username = password_store.get_from_store("username")
        if not username:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve username from password store",
            )

        username = username.strip()

        # Get fresh namespace info
        namespace_list = get_namespace_list(username, headless)

        if not namespace_list:
            raise HTTPException(
                status_code=404,
                detail="No visible namespace reservation found for user",
            )

        return {
            "success": True,
            "message": "Cache cleared and namespace info refreshed",
            "namespace_info": namespace_list,
        }

    except HTTPException:
        raise
    except _EPHEMERAL_ERRORS as e:
        logger.error("Error clearing namespace cache: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
