"""
Cluster configuration management utilities.

Provides CRUD operations for managing OpenShift cluster configurations
in the rhtoken.json file.
"""

import json
import logging
import os
from typing import Any, cast

logger = logging.getLogger(__name__)


class ClusterConfigManager:
    """Manages cluster configurations in rhtoken.json."""

    def __init__(self, config_path: str | None = None):
        """
        Initialize the cluster config manager.

        Args:
            config_path: Path to rhtoken.json. If None, uses default location.
        """
        if config_path is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(script_dir, "rhtoken.json")

        self.config_path = config_path

    def _load_config(self) -> dict[str, Any]:
        """Load the entire rhtoken.json configuration."""
        try:
            with open(self.config_path, encoding="utf-8") as f:
                return cast(dict[str, Any], json.load(f))
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}") from e

    def _save_config(self, config: dict[str, Any]) -> None:
        """Save configuration to rhtoken.json."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
                f.write("\n")  # Add trailing newline
        except (OSError, TypeError, ValueError) as e:
            raise OSError(f"Failed to save configuration: {e}") from e

    def list_clusters(self) -> dict[str, dict[str, Any]]:
        """
        List all cluster configurations.

        Returns:
            Dictionary of cluster ID -> cluster configuration
        """
        config = self._load_config()
        return cast(dict[str, dict[str, Any]], config.get("clusters", {}))

    def get_cluster(self, cluster_id: str) -> dict[str, Any] | None:
        """
        Get a specific cluster configuration.

        Args:
            cluster_id: The cluster identifier (e.g., 'e', 'p', 's')

        Returns:
            Cluster configuration dict or None if not found
        """
        clusters = self.list_clusters()
        return clusters.get(cluster_id)

    def search_clusters(self, query: str) -> dict[str, dict[str, Any]]:
        """
        Search clusters by name, description, or URL.

        Args:
            query: Search string (case-insensitive)

        Returns:
            Dictionary of matching cluster ID -> cluster configuration
        """
        clusters = self.list_clusters()
        query_lower = query.lower()
        results = {}

        for cluster_id, cluster_data in clusters.items():
            # Search in cluster ID, name, description, and URL
            searchable_text = " ".join(
                [
                    cluster_id,
                    cluster_data.get("name", ""),
                    cluster_data.get("description", ""),
                    cluster_data.get("url", ""),
                ]
            ).lower()

            if query_lower in searchable_text:
                results[cluster_id] = cluster_data

        return results

    def add_cluster(self, cluster_id: str, name: str, url: str, description: str = "") -> dict[str, Any]:
        """
        Add a new cluster configuration.

        Args:
            cluster_id: Unique cluster identifier
            name: Human-readable cluster name
            url: OpenShift OAuth token request URL
            description: Optional cluster description

        Returns:
            The newly created cluster configuration

        Raises:
            ValueError: If cluster_id already exists
        """
        config = self._load_config()
        clusters = config.get("clusters", {})

        if cluster_id in clusters:
            raise ValueError(f"Cluster '{cluster_id}' already exists")

        new_cluster = {"name": name, "description": description, "url": url}

        clusters[cluster_id] = new_cluster
        config["clusters"] = clusters
        self._save_config(config)

        logger.info("Added new cluster: %s - %s", cluster_id, name)
        return new_cluster

    def update_cluster(
        self,
        cluster_id: str,
        name: str | None = None,
        url: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing cluster configuration.

        Args:
            cluster_id: Cluster identifier to update
            name: New name (optional)
            url: New URL (optional)
            description: New description (optional)

        Returns:
            The updated cluster configuration

        Raises:
            ValueError: If cluster_id does not exist
        """
        config = self._load_config()
        clusters = config.get("clusters", {})

        if cluster_id not in clusters:
            raise ValueError(f"Cluster '{cluster_id}' not found")

        cluster = clusters[cluster_id]

        # Update only provided fields
        if name is not None:
            cluster["name"] = name
        if url is not None:
            cluster["url"] = url
        if description is not None:
            cluster["description"] = description

        config["clusters"] = clusters
        self._save_config(config)

        logger.info("Updated cluster: %s", cluster_id)
        return cast(dict[str, Any], cluster)

    def delete_cluster(self, cluster_id: str) -> dict[str, Any]:
        """
        Delete a cluster configuration.

        Args:
            cluster_id: Cluster identifier to delete

        Returns:
            The deleted cluster configuration

        Raises:
            ValueError: If cluster_id does not exist
        """
        config = self._load_config()
        clusters = config.get("clusters", {})

        if cluster_id not in clusters:
            raise ValueError(f"Cluster '{cluster_id}' not found")

        deleted_cluster = clusters.pop(cluster_id)
        config["clusters"] = clusters
        self._save_config(config)

        logger.info("Deleted cluster: %s", cluster_id)
        return cast(dict[str, Any], deleted_cluster)
