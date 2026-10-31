"""Common dependencies and utilities for API routes."""

import logging
from pathlib import Path
from typing import Callable, Optional, cast

from fastapi import HTTPException

from services.password_store import password_store

logger = logging.getLogger(__name__)


def get_username_from_store() -> str:
    """
    Get username from password store.

    Returns:
        Username string

    Raises:
        HTTPException: If username cannot be retrieved
    """
    username = password_store.get_from_store("username")
    if not username:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve username from password store"
        )
    return cast(str, username.strip())


def find_script_path(
    script_name: str, search_paths: Optional[list[Path]] = None
) -> Path:
    """
    Find a script in common locations.

    Args:
        script_name: Name of script to find (e.g., "vpn-connect")
        search_paths: Optional custom search paths

    Returns:
        Path to script

    Raises:
        HTTPException: If script not found
    """
    if search_paths is None:
        # Default search paths relative to project
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # src/api/dependencies -> src

        search_paths = [
            project_root / script_name,
            Path.home() / "src" / "rh-otp-auto-connect" / "src" / script_name,
            Path(f"/usr/local/bin/{script_name}"),
            Path(f"/usr/bin/{script_name}"),
        ]

    for path in search_paths:
        if path.exists() and path.is_file():
            logger.debug(f"Found script {script_name} at {path}")
            return path

    raise HTTPException(
        status_code=404,
        detail=f"{script_name} script not found in any of the expected locations",
    )


def handle_api_errors(func: Callable):
    """
    Decorator to handle common API error patterns.

    Wraps endpoint functions with try/except to handle HTTPException
    and general exceptions consistently.

    Usage:
        @router.get("/endpoint")
        @handle_api_errors
        def my_endpoint():
            # Implementation
            pass
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Preserve function metadata for FastAPI
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__annotations__ = func.__annotations__

    return wrapper
