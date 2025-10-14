"""Authentication dependencies for FastAPI routes."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)

# Authentication token cache
_auth_token = None


def get_or_create_auth_token() -> str:
    """
    Get or create the authentication token.

    The token is generated once and stored in ~/.cache/rhotp/auth_token
    for use by the Chrome extension and other clients.
    """
    global _auth_token

    if _auth_token:
        return _auth_token

    token_dir = Path.home() / ".cache" / "rhotp"
    token_file = token_dir / "auth_token"

    # Create directory if it doesn't exist
    token_dir.mkdir(parents=True, exist_ok=True)

    # Try to read existing token
    if token_file.exists():
        try:
            _auth_token = token_file.read_text().strip()
            if _auth_token:
                logger.info("Loaded existing authentication token")
                return _auth_token
        except Exception as e:
            logger.error(f"Error reading auth token: {e}")

    # Generate new token
    import secrets

    _auth_token = secrets.token_urlsafe(32)

    # Save token to file
    try:
        token_file.write_text(_auth_token)
        token_file.chmod(0o600)  # Restrict permissions
        logger.info(f"Generated new authentication token and saved to {token_file}")
    except Exception as e:
        logger.error(f"Error saving auth token: {e}")

    return _auth_token


def verify_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify the Bearer token from the Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        The verified token

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if it's a Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    expected_token = get_or_create_auth_token()

    if token != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
