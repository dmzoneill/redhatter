"""
Legacy API endpoints for backward compatibility.

These endpoints maintain compatibility with older Chrome extension versions
and existing scripts. New code should use the structured API routes instead.
"""

import logging

from fastapi import APIRouter, Depends

from api.dependencies.auth import verify_token
from services.ephemeral import get_namespace_name, get_namespace_password
from services.password_store import password_store

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["legacy"],
    dependencies=[Depends(verify_token)],  # All legacy endpoints require auth
)


@router.get("/get_creds")
def get_creds(context: str = "associate", headless: bool = False):
    """
    Get credentials based on context.

    Legacy endpoint for backward compatibility with Chrome extension.

    Args:
        context: Either "associate" or "jdoeEphemeral"
        headless: Whether to use headless mode for ephemeral environments

    Returns:
        Comma-separated string: "username,password" or "Failed"
    """
    logger.debug(f"get_creds called with context={context}, headless={headless}")

    if context == "associate":
        username, password_with_otp = password_store.get_associate_credentials()

        if not username or not password_with_otp:
            logger.error("Failed to retrieve associate credentials")
            return "Failed"

        return f"{username},{password_with_otp}".strip()

    elif context == "jdoeEphemeral":
        # Ephemeral login - backwards compatibility
        # Note: New code should use /ephemeral/namespace/details endpoint
        username = password_store.get_username()
        if not username:
            logger.error("Failed to retrieve username for ephemeral context")
            return "Failed"

        try:
            namespace = get_namespace_name(username, headless)
            if not namespace:
                logger.error("Failed to retrieve namespace for ephemeral context")
                return "Failed"

            password = get_namespace_password(namespace)
            if not password:
                logger.error("Failed to retrieve password for ephemeral namespace")
                return "Failed"

            return f"jdoe,{password}"
        except Exception as e:
            logger.error(f"Failed to get ephemeral credentials: {e}")
            return "Failed"

    else:
        logger.warning(f"Unknown context requested: {context}")
        return "Failed"


@router.get("/get_associate_email")
def get_associate_email():
    """
    Get Red Hat associate email address.

    Legacy endpoint for backward compatibility.

    Returns:
        Email address string: "username@redhat.com"
    """
    logger.debug("get_associate_email called")

    username = password_store.get_username()
    if not username:
        logger.error("Failed to retrieve username for email")
        return ""

    email = f"{username}@redhat.com"
    return email.replace('"', "").strip()
