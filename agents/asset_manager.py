"""
Asset Manager - Centralized access to prompts, SOPs, and agent tools.
Wires in the 'amazing' assets to increase agent intelligence.
"""

import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("AssetManager")


class AssetManager:
    """
    Manages access to project assets:
    - SOPs (Standard Operating Procedures)
    - Prompts (System and specialized)
    - Tools (Agent tool definitions)
    """

    def __init__(self, base_path: str = "assets"):
        self.base_path = base_path
        self.prompts_path = os.path.join(base_path, "prompts")
        self.sops_path = os.path.join(base_path, "sops")
        self.tools_path = os.path.join(base_path, "tools")
        self.registry_path = os.path.join(base_path, "registry.json")

        # Load registry if exists
        self.registry = {}
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    self.registry = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load asset registry: {e}")

    def get_prompt(self, name: str) -> str:
        """Retrieve a prompt by name"""
        # Try exact match, then with .txt, then with .md
        for ext in ["", ".txt", ".md"]:
            path = os.path.join(self.prompts_path, f"{name}{ext}")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()

        logger.warning(f"Prompt not found: {name}")
        return ""

    def get_sop(self, name: str) -> str:
        """Retrieve an SOP by name"""
        for ext in ["", ".md", ".txt"]:
            path = os.path.join(self.sops_path, f"{name}{ext}")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()

        logger.warning(f"SOP not found: {name}")
        return ""

    def get_tools(self, name: str) -> List[Dict[str, Any]]:
        """Retrieve agent tool definitions by name"""
        for ext in ["", ".json"]:
            path = os.path.join(self.tools_path, f"{name}{ext}")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)

        logger.warning(f"Tools not found: {name}")
        return []

    def list_assets(self) -> Dict[str, List[str]]:
        """List all available assets"""
        return {
            "prompts": os.listdir(self.prompts_path) if os.path.exists(self.prompts_path) else [],
            "sops": os.listdir(self.sops_path) if os.path.exists(self.sops_path) else [],
            "tools": os.listdir(self.tools_path) if os.path.exists(self.tools_path) else [],
        }


# Global instance
asset_manager = AssetManager()
