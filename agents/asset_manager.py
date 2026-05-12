import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("AssetManager")

class OracleAssets:
    """
    Loads all Oracle prompts, SOPs, and tools from assets directory.
    Handles large JSON files and multiple tool libraries gracefully.
    """
    
    ASSET_ROOT = Path(os.getenv("SWARM_ASSETS_DIR", Path(__file__).resolve().parents[2] / "assets"))
    
    def __init__(self):
        self.prompts = {}
        self.sops = {}
        self.tools = {}
        self.registry = {}
        self._load_all()
    
    def _load_all(self):
        """Load all assets on initialization"""
        logger.info("Loading Oracle Assets...")
        
        # Load prompts from assets/prompts/
        prompts_dir = self.ASSET_ROOT / "prompts"
        if prompts_dir.exists():
            for prompt_file in prompts_dir.glob("*.txt"):
                try:
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        self.prompts[prompt_file.stem] = f.read()
                except Exception as e:
                    logger.error(f"Failed to load prompt {prompt_file.stem}: {e}")
        
        # Load SOPs from assets/sops/
        sops_dir = self.ASSET_ROOT / "sops"
        if sops_dir.exists():
            for sop_file in sops_dir.glob("*.md"):
                try:
                    with open(sop_file, 'r', encoding='utf-8') as f:
                        self.sops[sop_file.stem] = f.read()
                except Exception as e:
                    logger.error(f"Failed to load SOP {sop_file.stem}: {e}")
        
        # Load tools from assets/tools/ (multiple JSON libraries)
        tools_dir = self.ASSET_ROOT / "tools"
        if tools_dir.exists():
            for tool_file in tools_dir.glob("*.json"):
                try:
                    with open(tool_file, 'r', encoding='utf-8') as f:
                        tools_data = json.load(f)
                        # Merge all tools into single dict
                        if isinstance(tools_data, dict):
                            self.tools.update(tools_data)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON syntax error in {tool_file.name}, skipping: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Failed to load tools {tool_file.stem}: {e}")
        
        logger.info(f"✅ Assets loaded: {len(self.prompts)} prompts, {len(self.sops)} SOPs, {len(self.tools)} tools")
    
    def get_prompt_for_role(self, role: str) -> Optional[str]:
        """Get best-matching prompt for a role"""
        role_lower = role.lower()
        
        # Try exact match first
        for name, prompt in self.prompts.items():
            if role_lower == name.lower():
                return prompt
        
        # Try partial matches
        for name, prompt in self.prompts.items():
            if role_lower in name.lower() or name.lower() in role_lower:
                return prompt
        
        # Fallback to generic prompts
        for fallback_name in ["Enterprise Prompt", "System Prompt", "Master Prompt"]:
            if fallback_name in self.prompts:
                return self.prompts[fallback_name]
        
        # Last resort: return first available prompt
        if self.prompts:
            return next(iter(self.prompts.values()))
        
        return None
    
    def get_sops_for_role(self, role: str) -> List[Dict[str, str]]:
        """Get SOPs relevant to a role"""
        relevant = []
        role_lower = role.lower()
        
        for sop_name, sop_content in self.sops.items():
            sop_name_lower = sop_name.lower()
            
            # Match if role is in SOP name or SOP mentions role
            if (role_lower in sop_name_lower or 
                role_lower in sop_content[:500].lower()):
                relevant.append({
                    "name": sop_name,
                    "content": sop_content[:2000] + "..." if len(sop_content) > 2000 else sop_content
                })
        
        return relevant[:5]  # Top 5 SOPs
    
    def get_tools_for_role(self, role: str) -> List[Dict[str, Any]]:
        """Get tools relevant to a role"""
        relevant = []
        role_lower = role.lower()
        
        # Role-to-tool category mapping
        role_categories = {
            "cto": ["architecture", "security", "devops", "backend"],
            "security": ["security", "auth", "permissions", "encryption"],
            "devops": ["deploy", "docker", "infrastructure", "ci", "cd"],
            "marketing": ["content", "social", "analytics", "email"],
            "outreach": ["email", "social", "contact", "crm"],
            "database": ["database", "sql", "query", "schema"],
            "testing": ["test", "qa", "quality", "coverage"],
        }
        
        categories = role_categories.get(role_lower, [])
        
        for tool_name, tool_config in self.tools.items():
            tool_name_lower = tool_name.lower()
            
            # Match if tool name or categories align
            if (role_lower in tool_name_lower or
                any(cat in tool_name_lower for cat in categories)):
                relevant.append(tool_config if isinstance(tool_config, dict) else {"name": tool_name, "config": tool_config})
        
        return relevant[:10]  # Top 10 tools
    
    def build_agent_context(self, role: str) -> Dict[str, Any]:
        """Build complete context dict for an agent initialization"""
        sops = self.get_sops_for_role(role)
        tools = self.get_tools_for_role(role)
        prompt = self.get_prompt_for_role(role)
        
        return {
            "role": role,
            "prompt": prompt,
            "sops": sops,
            "tools": tools,
            "has_prompt": prompt is not None,
            "has_sops": len(sops) > 0,
            "has_tools": len(tools) > 0,
            "num_sops": len(sops),
            "num_tools": len(tools)
        }

# Initialize on module import
# Lazy singleton to avoid import-time IO
_ORACLE = None

def get_oracle_assets():
    global _ORACLE
    if _ORACLE is None:
        _ORACLE = OracleAssets()
    return _ORACLE