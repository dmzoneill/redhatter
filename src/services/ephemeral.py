"""Service layer for ephemeral namespace operations.

This module handles interactions with external Kubernetes instances
where ephemeral pipelines are run (bonfire/OpenShift environments).
"""
import base64
import json
import logging
import subprocess
from typing import Optional, Tuple

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def run_command(cmd: str) -> Tuple[bool, str, str]:
    """
    Execute a shell command and return results.

    Args:
        cmd: Command to execute

    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )
        stdout, stderr = proc.communicate()
        success = proc.returncode == 0

        logger.debug(f"Command: {cmd}")
        logger.debug(f"Success: {success}")
        logger.debug(f"Stdout: {stdout.strip()}")
        if stderr:
            logger.debug(f"Stderr: {stderr.strip()}")

        return success, stdout.strip(), stderr.strip()

    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return False, "", str(e)


def set_namespace(namespace: str) -> bool:
    """
    Set the current namespace/project for kubectl/oc.

    Args:
        namespace: Namespace to switch to

    Returns:
        True if successful, False otherwise
    """
    success, _, _ = run_command(f"/usr/local/bin/oc project {namespace}")
    return success


def get_namespace_password(namespace: str) -> Optional[str]:
    """
    Retrieve password for the given ephemeral namespace.

    Fetches the password from the Kubernetes secret in the namespace.

    Args:
        namespace: Namespace name

    Returns:
        Password string or None if not found
    """
    try:
        # Set the namespace context
        if not set_namespace(namespace):
            logger.error(f"Failed to set namespace to {namespace}")
            return None

        # Get the Keycloak secret
        success, stdout, stderr = run_command(
            f'/usr/local/bin/kubectl get secret "env-{namespace}-keycloak" -o json'
        )

        if not success:
            logger.error(f"Failed to get secret: {stderr}")
            return None

        # Parse the secret JSON
        secret_data = json.loads(stdout)
        encoded_password = secret_data.get("data", {}).get("defaultPassword")

        if not encoded_password:
            logger.error("defaultPassword not found in secret")
            return None

        # Decode the base64-encoded password
        password = base64.b64decode(encoded_password).decode("utf-8")
        return password

    except Exception as e:
        logger.error(f"Error retrieving namespace password: {e}")
        return None


def get_namespace_list(username: str, headless: bool = True) -> Optional[list]:
    """
    Get list of namespaces for a user from bonfire.

    Args:
        username: Username to search for
        headless: Whether to use headless mode

    Returns:
        List of namespace info or None if error
    """
    try:
        # Check if we're on the correct server
        success, server, _ = run_command(
            "/usr/local/bin/oc project | awk -F'\"' '{print $4}'"
        )

        if success and server != "https://api.c-rh-c-eph.8p0c.p1.openshiftapps.com:6443":
            # Need to login to ephemeral environment
            headless_flag = "--headless" if headless else ""
            subprocess.call(f"/usr/local/bin/rhtoken e {headless_flag}", shell=True)

        # Get namespace list from bonfire
        success, stdout, _ = run_command(
            f"~/.local/bin/bonfire namespace list | grep {username}"
        )

        if not success or not stdout:
            return None

        return stdout.split()

    except Exception as e:
        logger.error(f"Error getting namespace list: {e}")
        return None


def get_namespace_name(username: str, headless: bool = True) -> Optional[str]:
    """
    Get the name of the user's namespace.

    Args:
        username: Username
        headless: Whether to use headless mode

    Returns:
        Namespace name or None
    """
    namespace_list = get_namespace_list(username, headless)
    if namespace_list and len(namespace_list) > 0:
        return namespace_list[0]
    return None


def get_namespace_expires(username: str, headless: bool = True) -> Optional[str]:
    """
    Get the expiration date of the namespace.

    Args:
        username: Username
        headless: Whether to use headless mode

    Returns:
        Expiration timestamp or None
    """
    namespace_list = get_namespace_list(username, headless)
    if namespace_list and len(namespace_list) > 6:
        return namespace_list[6]
    return None


def get_namespace_route(namespace: str) -> Optional[str]:
    """
    Get the route/URL for the namespace.

    Args:
        namespace: Namespace name

    Returns:
        Route URL or None
    """
    try:
        # Set the namespace context
        if not set_namespace(namespace):
            logger.error(f"Failed to set namespace to {namespace}")
            return None

        # Get the route from the namespace
        success, route, _ = run_command(
            "/usr/local/bin/kubectl get route 2>/dev/null | tail -n 1 | awk '{print $2}'"
        )

        if success and route:
            return route

        return None

    except Exception as e:
        logger.error(f"Error getting namespace route: {e}")
        return None


def extend_namespace(namespace: str, duration: str = "72h") -> bool:
    """
    Extend the duration of an ephemeral namespace.

    Args:
        namespace: Namespace to extend
        duration: Duration to extend (e.g., '72h', '48h')

    Returns:
        True if successful, False otherwise
    """
    try:
        success, _, stderr = run_command(
            f"bonfire namespace extend {namespace} -d {duration}"
        )

        if not success:
            logger.error(f"Failed to extend namespace: {stderr}")
            return False

        logger.info(f"Extended namespace {namespace} by {duration}")
        return True

    except Exception as e:
        logger.error(f"Error extending namespace: {e}")
        return False
