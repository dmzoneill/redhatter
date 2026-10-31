"""Service layer for ephemeral namespace operations.

This module handles interactions with external Kubernetes instances
where ephemeral pipelines are run (bonfire/OpenShift environments).
"""

import base64
import json
import logging
import subprocess

logger = logging.getLogger(__name__)


def run_command(cmd: str) -> tuple[bool, str, str]:
    """
    Execute a shell command and return results.

    Args:
        cmd: Command to execute

    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True) as proc:
            stdout, stderr = proc.communicate()
            success = proc.returncode == 0

        logger.debug("Command: %s", cmd)
        logger.debug("Success: %s", success)
        logger.debug("Stdout: %s", stdout.strip())
        if stderr:
            logger.debug("Stderr: %s", stderr.strip())

        return success, stdout.strip(), stderr.strip()

    except (OSError, ValueError, subprocess.SubprocessError) as e:
        logger.error("Error executing command: %s", e)
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


def get_namespace_password(namespace: str) -> str | None:
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
            logger.error("Failed to set namespace to %s", namespace)
            return None

        # Get the Keycloak secret
        success, stdout, stderr = run_command(f'/usr/local/bin/kubectl get secret "env-{namespace}-keycloak" -o json')

        if not success:
            logger.error("Failed to get secret: %s", stderr)
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

    except (ValueError, TypeError, AttributeError) as e:
        logger.error("Error retrieving namespace password: %s", e)
        return None


def get_namespace_list(username: str, headless: bool = True) -> list[str] | None:
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
        success, server, _ = run_command("/usr/local/bin/oc project | awk -F'\"' '{print $4}'")

        if success and server != "https://api.c-rh-c-eph.8p0c.p1.openshiftapps.com:6443":
            # Need to login to ephemeral environment
            headless_flag = "--headless" if headless else ""
            subprocess.call(f"/usr/local/bin/rhtoken e {headless_flag}", shell=True)

        # Get namespace list from bonfire
        success, stdout, _ = run_command(f"~/.local/bin/bonfire namespace list | grep {username}")

        if not success or not stdout:
            return None

        return stdout.split()

    except (OSError, ValueError, subprocess.SubprocessError) as e:
        logger.error("Error getting namespace list: %s", e)
        return None


def get_namespace_name(username: str, headless: bool = True) -> str | None:
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


def get_namespace_expires(username: str, headless: bool = True) -> str | None:
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


def get_namespace_route(namespace: str) -> str | None:
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
            logger.error("Failed to set namespace to %s", namespace)
            return None

        # Get the route from the namespace
        success, route, _ = run_command("/usr/local/bin/kubectl get route 2>/dev/null | tail -n 1 | awk '{print $2}'")

        if success and route:
            return route

        return None

    except (OSError, ValueError, subprocess.SubprocessError) as e:
        logger.error("Error getting namespace route: %s", e)
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
        success, _, stderr = run_command(f"bonfire namespace extend {namespace} -d {duration}")

        if not success:
            logger.error("Failed to extend namespace: %s", stderr)
            return False

        logger.info("Extended namespace %s by %s", namespace, duration)
        return True

    except (OSError, ValueError, subprocess.SubprocessError) as e:
        logger.error("Error extending namespace: %s", e)
        return False
