"""
OpenShift Token API endpoints.

Provides endpoints for retrieving OpenShift login commands
using the rhtoken script and managing cluster configurations.
"""
import json
import logging
import os
import subprocess
from enum import Enum
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies.auth import verify_token
from api.utils.cluster_config import ClusterConfigManager


def transform_oauth_to_console_url(oauth_url: str) -> str:
    """
    Transform OAuth URL to console URL.

    From: https://oauth-openshift.apps.crcs02ue1.urby.p1.openshiftapps.com/oauth/token/request
    To:   https://console-openshift-console.apps.crcs02ue1.urby.p1.openshiftapps.com/
    """
    return oauth_url.replace('oauth-openshift.apps.', 'console-openshift-console.apps.').replace('/oauth/token/request', '/')

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


# Pydantic models for cluster management
class ClusterConfig(BaseModel):
    """Cluster configuration model."""
    name: str = Field(..., description="Human-readable cluster name")
    description: str = Field(default="", description="Cluster description")
    url: str = Field(..., description="OpenShift OAuth token request URL")


class ClusterResponse(BaseModel):
    """Cluster response model."""
    cluster_id: str = Field(..., description="Cluster identifier")
    name: str = Field(..., description="Human-readable cluster name")
    description: str = Field(..., description="Cluster description")
    url: str = Field(..., description="OpenShift OAuth token request URL")


class ClusterUpdateRequest(BaseModel):
    """Cluster update request model."""
    name: Optional[str] = Field(None, description="New cluster name")
    description: Optional[str] = Field(None, description="New cluster description")
    url: Optional[str] = Field(None, description="New cluster URL")


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


# Cluster Management Endpoints

@router.get("/clusters", response_model=List[ClusterResponse])
async def list_clusters(
    _token: str = Depends(verify_token)
) -> List[ClusterResponse]:
    """
    List all configured OpenShift clusters.

    Returns:
    - List of all cluster configurations with their IDs, names, descriptions, and URLs
    """
    try:
        manager = ClusterConfigManager()
        clusters = manager.list_clusters()

        return [
            ClusterResponse(
                cluster_id=cluster_id,
                name=cluster_data.get('name', ''),
                description=cluster_data.get('description', ''),
                url=cluster_data.get('url', '')
            )
            for cluster_id, cluster_data in clusters.items()
        ]
    except Exception as e:
        logger.error(f"Error listing clusters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list clusters: {str(e)}")


@router.get("/clusters/search", response_model=List[ClusterResponse])
async def search_clusters(
    q: str = Query(..., description="Search query (searches name, description, URL, and ID)"),
    _token: str = Depends(verify_token)
) -> List[ClusterResponse]:
    """
    Search clusters by name, description, URL, or ID.

    Parameters:
    - **q**: Search query string (case-insensitive)

    Returns:
    - List of matching cluster configurations
    """
    try:
        manager = ClusterConfigManager()
        clusters = manager.search_clusters(q)

        return [
            ClusterResponse(
                cluster_id=cluster_id,
                name=cluster_data.get('name', ''),
                description=cluster_data.get('description', ''),
                url=cluster_data.get('url', '')
            )
            for cluster_id, cluster_data in clusters.items()
        ]
    except Exception as e:
        logger.error(f"Error searching clusters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search clusters: {str(e)}")


@router.get("/clusters/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: str,
    _token: str = Depends(verify_token)
) -> ClusterResponse:
    """
    Get a specific cluster configuration by ID.

    Parameters:
    - **cluster_id**: Cluster identifier (e.g., 'e', 'p', 's', 'ap', 'cp', 'k')

    Returns:
    - Cluster configuration details
    """
    try:
        manager = ClusterConfigManager()
        cluster = manager.get_cluster(cluster_id)

        if cluster is None:
            raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' not found")

        return ClusterResponse(
            cluster_id=cluster_id,
            name=cluster.get('name', ''),
            description=cluster.get('description', ''),
            url=cluster.get('url', '')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cluster {cluster_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cluster: {str(e)}")


@router.post("/clusters/{cluster_id}", response_model=ClusterResponse, status_code=201)
async def add_cluster(
    cluster_id: str,
    cluster_config: ClusterConfig,
    _token: str = Depends(verify_token)
) -> ClusterResponse:
    """
    Add a new cluster configuration.

    Parameters:
    - **cluster_id**: Unique cluster identifier (e.g., 'dev', 'test')
    - **cluster_config**: Cluster configuration (name, description, url)

    Returns:
    - The newly created cluster configuration
    """
    try:
        manager = ClusterConfigManager()
        manager.add_cluster(
            cluster_id=cluster_id,
            name=cluster_config.name,
            url=cluster_config.url,
            description=cluster_config.description
        )

        return ClusterResponse(
            cluster_id=cluster_id,
            name=cluster_config.name,
            description=cluster_config.description,
            url=cluster_config.url
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding cluster {cluster_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add cluster: {str(e)}")


@router.put("/clusters/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(
    cluster_id: str,
    update_request: ClusterUpdateRequest,
    _token: str = Depends(verify_token)
) -> ClusterResponse:
    """
    Update an existing cluster configuration.

    Parameters:
    - **cluster_id**: Cluster identifier to update
    - **update_request**: Fields to update (name, description, url)

    Returns:
    - The updated cluster configuration
    """
    try:
        manager = ClusterConfigManager()
        updated_cluster = manager.update_cluster(
            cluster_id=cluster_id,
            name=update_request.name,
            url=update_request.url,
            description=update_request.description
        )

        return ClusterResponse(
            cluster_id=cluster_id,
            name=updated_cluster.get('name', ''),
            description=updated_cluster.get('description', ''),
            url=updated_cluster.get('url', '')
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating cluster {cluster_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update cluster: {str(e)}")


@router.delete("/clusters/{cluster_id}", response_model=ClusterResponse)
async def delete_cluster(
    cluster_id: str,
    _token: str = Depends(verify_token)
) -> ClusterResponse:
    """
    Delete a cluster configuration.

    Parameters:
    - **cluster_id**: Cluster identifier to delete

    Returns:
    - The deleted cluster configuration
    """
    try:
        manager = ClusterConfigManager()
        deleted_cluster = manager.delete_cluster(cluster_id)

        return ClusterResponse(
            cluster_id=cluster_id,
            name=deleted_cluster.get('name', ''),
            description=deleted_cluster.get('description', ''),
            url=deleted_cluster.get('url', '')
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting cluster {cluster_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete cluster: {str(e)}")


# Cluster Terminal and Web Console Endpoints

@router.post("/clusters/{cluster_id}/open-terminal")
async def open_cluster_terminal(
    cluster_id: str,
    _token: str = Depends(verify_token)
) -> Dict[str, str]:
    """
    Open a terminal window and execute oc login for the specified cluster.

    Parameters:
    - **cluster_id**: Cluster identifier (e.g., 'e', 'p', 's', 'ap', 'cp', 'k')

    Returns:
    - success: Boolean indicating if terminal was opened
    - message: Status message
    """
    logger.info(f"[open-terminal] Starting request for cluster: {cluster_id}")

    try:
        # Get the oc login command
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        rhtoken_path = os.path.join(script_dir, "rhtoken")

        logger.debug(f"[open-terminal] Script directory: {script_dir}")
        logger.debug(f"[open-terminal] rhtoken path: {rhtoken_path}")

        if not os.path.exists(rhtoken_path):
            logger.error(f"[open-terminal] rhtoken script not found at: {rhtoken_path}")
            raise HTTPException(status_code=500, detail="rhtoken script not found")

        # Instead of getting the oc login command first (which requires full auth),
        # just run rhtoken directly in the terminal to let it authenticate interactively
        logger.info(f"[open-terminal] Opening terminal to run rhtoken for cluster: {cluster_id}")

        # Open terminal with rhtoken command (no --query flag, so it will authenticate and execute)
        terminal_command = [
            'gnome-terminal',
            '--',
            'bash',
            '-c',
            f'{rhtoken_path} {cluster_id}; echo ""; echo "Press Enter to close..."; read'
        ]

        logger.info(f"[open-terminal] Opening terminal with command: gnome-terminal -- bash -c 'rhtoken {cluster_id}...'")
        logger.debug(f"[open-terminal] Full terminal command: {terminal_command}")

        # Start the process and immediately return (don't wait for it)
        process = subprocess.Popen(
            terminal_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        logger.info(f"[open-terminal] Terminal process started with PID: {process.pid}")
        logger.info(f"[open-terminal] Successfully opened terminal for cluster {cluster_id}")

        return {
            "success": True,
            "message": f"Terminal opened for cluster {cluster_id}"
        }

    except Exception as e:
        logger.error(f"[open-terminal] Unexpected error for cluster {cluster_id}: {str(e)}")
        logger.exception("[open-terminal] Full exception traceback:")
        raise HTTPException(status_code=500, detail=f"Failed to open terminal: {str(e)}")


@router.post("/clusters/{cluster_id}/open-web")
async def open_cluster_web(
    cluster_id: str,
    _token: str = Depends(verify_token)
) -> Dict[str, str]:
    """
    Open the cluster web console in the default browser.

    Parameters:
    - **cluster_id**: Cluster identifier (e.g., 'e', 'p', 's', 'ap', 'cp', 'k')

    Returns:
    - success: Boolean indicating if browser was opened
    - message: Status message
    - url: The console URL that was opened
    """
    try:
        # Get cluster configuration
        manager = ClusterConfigManager()
        cluster = manager.get_cluster(cluster_id)

        if cluster is None:
            raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' not found")

        # Transform OAuth URL to console URL
        oauth_url = cluster.get('url', '')
        console_url = transform_oauth_to_console_url(oauth_url)

        # Open URL in browser
        subprocess.Popen(
            ['xdg-open', console_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        logger.info(f"Opened web console for cluster {cluster_id}: {console_url}")

        return {
            "success": True,
            "message": f"Web console opened for cluster {cluster_id}",
            "url": console_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error opening web console for cluster {cluster_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to open web console: {str(e)}")
