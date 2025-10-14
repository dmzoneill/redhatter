"""
OpenShift Token API endpoints.

Provides endpoints for retrieving OpenShift login commands
using the rhtoken script.
"""
import json
import logging
import os
import subprocess
from enum import Enum
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/token", tags=["token"])


class Environment(str, Enum):
    """OpenShift environment options."""
    EPHEMERAL = "e"
    PROD = "p"
    STAGE = "s"
    APP_PROD = "ap"
    APP_STAGE = "cp"
    STONE_PROD = "k"


@router.get("/oc-login")
async def get_oc_login_command(
    env: Environment = Query(..., description="Environment: e|p|s|ap|cp|k"),
    headless: bool = Query(True, description="Run in headless mode"),
    _token: str = Depends(verify_token)
) -> Dict[str, str]:
    """
    Get OpenShift login command for specified environment.

    Runs the rhtoken script with --query flag to retrieve the
    oc login command without executing it.

    Parameters:
    - **env**: Environment (e=ephemeral, p=prod, s=stage, ap=app-prod, cp=app-stage, k=stone-prod)
    - **headless**: Run browser in headless mode (default: true)

    Returns:
    - command: The oc login command string
    - environment: The environment requested
    """
    logger.info(f"Getting oc login command for environment: {env.value}")

    # Build command
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rhtoken_path = os.path.join(script_dir, "rhtoken")

    if not os.path.exists(rhtoken_path):
        logger.error(f"rhtoken script not found at: {rhtoken_path}")
        raise HTTPException(status_code=500, detail="rhtoken script not found")

    cmd = [rhtoken_path, env.value, "--query"]
    if headless:
        cmd.append("--headless")

    logger.info(f"Executing command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Extract the oc login command from output
        output = result.stdout.strip()

        # The command should be in the output
        # Filter out any [INFO] or other log messages
        lines = output.split('\n')
        oc_command = None
        for line in lines:
            if line.startswith('oc login'):
                oc_command = line
                break

        if not oc_command:
            # If no line starts with 'oc login', use the last non-empty line
            for line in reversed(lines):
                if line.strip() and not line.startswith('['):
                    oc_command = line.strip()
                    break

        if not oc_command:
            logger.error(f"Could not extract oc login command from output: {output}")
            raise HTTPException(
                status_code=500,
                detail="Could not extract oc login command from rhtoken output"
            )

        logger.info(f"Successfully retrieved oc login command for {env.value}")

        return {
            "command": oc_command,
            "environment": env.value,
            "environment_name": _get_env_name(env.value)
        }

    except subprocess.TimeoutExpired:
        logger.error(f"rhtoken script timed out for environment: {env.value}")
        raise HTTPException(
            status_code=504,
            detail="Request timed out - rhtoken script took too long to execute"
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"rhtoken script failed: {e.stderr}")
        raise HTTPException(
            status_code=500,
            detail=f"rhtoken script failed: {e.stderr}"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting oc login command: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


def _get_env_name(env: str) -> str:
    """Get human-readable environment name from rhtoken.json config."""
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(script_dir, "rhtoken.json")

        with open(config_path, 'r') as f:
            config = json.load(f)
            clusters = config.get('clusters', {})
            cluster = clusters.get(env, {})
            return cluster.get('name', 'Unknown')
    except Exception as e:
        logger.error(f"Error loading environment name from config: {e}")
        return "Unknown"
