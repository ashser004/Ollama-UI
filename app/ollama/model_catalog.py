"""
model_catalog.py — Load, filter, and manage the models.json catalog.

Provides model discovery, filtering by capability, and
comparison with locally installed models.
"""

import json
import os
from app import config


class ModelCatalog:
    """Manages the bundled model catalog."""

    def __init__(self):
        self._models: list[dict] = []
        self._load()

    def _load(self):
        """Load models from models.json."""
        path = config.get_models_json_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._models = data.get("models", [])
            except (json.JSONDecodeError, IOError):
                self._models = []

    def reload(self):
        """Reload the catalog from disk."""
        self._load()

    @property
    def all_models(self) -> list[dict]:
        """Get all models in the catalog."""
        return self._models.copy()

    def get_capabilities(self) -> list[str]:
        """Get a sorted list of all unique capabilities."""
        caps = set()
        for model in self._models:
            for cap in model.get("capabilities", []):
                caps.add(cap)
        return sorted(caps)

    def filter_models(
        self,
        capability: str = None,
        search_query: str = None,
        available_disk_gb: float = None,
        available_ram_gb: float = None,
        installed_tags: list[str] = None,
        show_installed: bool = True
    ) -> list[dict]:
        """
        Filter models based on criteria.
        Returns a list of model dicts with an added 'is_installed' and
        'can_install' field.
        """
        results = []
        installed = set(installed_tags or [])

        for model in self._models:
            # Capability filter
            if capability and capability.lower() != "all":
                if capability.lower() not in [c.lower() for c in model.get("capabilities", [])]:
                    continue

            # Search filter
            if search_query:
                q = search_query.lower()
                name_match = q in model.get("name", "").lower()
                tag_match = q in model.get("tag", "").lower()
                desc_match = q in model.get("description", "").lower()
                cap_match = any(q in c.lower() for c in model.get("capabilities", []))
                if not (name_match or tag_match or desc_match or cap_match):
                    continue

            # Mark installed
            is_installed = model.get("tag", "") in installed
            if not show_installed and is_installed:
                continue

            # Check compatibility
            can_install = True
            install_warning = ""

            if available_disk_gb is not None:
                if model.get("size_gb", 0) > available_disk_gb:
                    can_install = False
                    install_warning = "Not enough disk space"

            if available_ram_gb is not None:
                if model.get("min_ram_gb", 0) > available_ram_gb:
                    can_install = False
                    install_warning = "Not enough RAM"

            result = model.copy()
            result["is_installed"] = is_installed
            result["can_install"] = can_install
            result["install_warning"] = install_warning
            results.append(result)

        return results

    def get_model_by_tag(self, tag: str) -> dict | None:
        """Get a specific model by its Ollama tag."""
        for model in self._models:
            if model.get("tag") == tag:
                return model.copy()
        return None

    def get_model_by_name(self, name: str) -> dict | None:
        """Get a specific model by display name."""
        for model in self._models:
            if model.get("name", "").lower() == name.lower():
                return model.copy()
        return None
