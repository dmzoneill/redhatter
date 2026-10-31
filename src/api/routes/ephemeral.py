"""Ephemeral namespace API routes.

These routes interact with external Kubernetes instances where
ephemeral pipelines are run (bonfire/OpenShift environments).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

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


# Import verify_token from main - we'll use a dependency function
# Import verify_token from auth dependencies
from api.dependencies.auth import verify_token as get_verify_token


@router.get("/namespace/details", response_model=NamespaceDetails)
def get_namespace_details(
    headless: bool = Query(
        default=False, description="Use headless mode for authentication"
    ),
    include_password: bool = Query(
        default=False, description="Include namespace password in response"
    ),
    token: str = Depends(get_verify_token),
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

        return NamespaceDetails(
            name=namespace_name, route=route, expires=expires, password=password
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting namespace details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/namespace/status", response_model=NamespaceStatus)
def get_namespace_status(
    headless: bool = Query(
        default=False, description="Use headless mode for authentication"
    ),
    token: str = Depends(get_verify_token),
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
    except Exception as e:
        logger.error(f"Error getting namespace status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/namespace/extend")
def extend_namespace(
    request: Optional[NamespaceExtendRequest] = None,
    headless: bool = Query(
        default=False, description="Use headless mode for authentication"
    ),
    token: str = Depends(get_verify_token),
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
            raise HTTPException(
                status_code=500, detail=f"Failed to extend namespace {namespace_name}"
            )

        # Get updated namespace info
        namespace_list = get_namespace_list(username, headless)
        expires = get_namespace_expires(username, headless)

        logger.info(f"Extended namespace {namespace_name} by {duration}")

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
    except Exception as e:
        logger.error(f"Error extending namespace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/namespace/clear-cache")
def clear_namespace_cache(
    headless: bool = Query(
        default=False, description="Use headless mode for authentication"
    ),
    token: str = Depends(get_verify_token),
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
    except Exception as e:
        logger.error(f"Error clearing namespace cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))
