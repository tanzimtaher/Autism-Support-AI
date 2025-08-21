"""
Knowledge Adapter for Autism Support App
Provides stable API over structured_mongo.json for both chat and browse UX.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

class KnowledgeAdapter:
    """Stable API over structured_mongo.json for both chat and browse UX."""
    
    def __init__(self, json_path: str = "knowledge/structured_mongo.json"):
        try:
            self.data = json.loads(Path(json_path).read_text())
            self.version = self.data.get("schema_version", "1.x")
            print(f"✅ Loaded knowledge base version: {self.version}")
        except Exception as e:
            print(f"❌ Error loading knowledge base: {e}")
            self.data = {}
            self.version = "error"

    # Router gates
    def get_safety_rules(self) -> Dict:
        """Get safety rules for critical terms."""
        return self.data.get("router", {}).get("safety_rules", {})
    
    def get_role_gate(self) -> List[str]:
        """Get available roles."""
        return self.data.get("router", {}).get("role_gate", [])
    
    def get_status_gate(self) -> List[str]:
        """Get diagnosis status options."""
        return self.data.get("router", {}).get("status_gate", [])
    
    def get_age_bands(self) -> List[str]:
        """Get available age bands."""
        return self.data.get("router", {}).get("age_bands", [])

    # Flows
    def get_undiagnosed_flow(self) -> Dict:
        """Get flow for undiagnosed children."""
        dn = self.data.get("diagnosed_no", {})
        return {
            "entry_point": dn.get("entry_point", {}),
            "monitor_vs_screen": dn.get("monitor_vs_screen", {}),
            "screening_options": dn.get("screening_options", {}).get("options", {}),
            "interpretation_routes": dn.get("interpretation_routes", {}).get("routes", {}),
            "not_yet_evaluated": dn.get("not_yet_evaluated", {}),
            "no_dx_but_concerns": dn.get("no_dx_but_concerns", {}).get("branches", {}),
            "at_home_resources": dn.get("at_home_resources", {}),
            "legal_emergency_intro": dn.get("legal_emergency_intro", {})
        }

    def get_diagnosed_flow(self) -> Dict:
        """Get flow for diagnosed children."""
        dy = self.data.get("diagnosed_yes", {})
        return {
            "support_affording": dy.get("support_affording", {}),
            "find_resources": dy.get("find_resources", {}),
            "legal_and_emergency": dy.get("legal_and_emergency", {})
        }

    def get_node(self, dotted_path: str) -> Optional[Dict]:
        """Get a specific node by dotted path."""
        try:
            cur = self.data
            for part in dotted_path.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return None
            return cur
        except Exception as e:
            print(f"❌ Error getting node {dotted_path}: {e}")
            return None

    def get_available_paths(self, context_path: str) -> List[str]:
        """Get available conversation paths from current context."""
        try:
            content = self.get_node(context_path)
            if not content:
                return []
            
            available_paths = []
            
            # Handle routes
            routes = content.get("routes") or content.get("interpretation_routes", {}).get("routes", {})
            if isinstance(routes, dict):
                for key, route in routes.items():
                    path = route.get("next_path") if isinstance(route, dict) else None
                    if not path:
                        path = f"{context_path}.routes.{key}"
                    available_paths.append(path)
            
            # Handle branches
            branches = content.get("branches") or content.get("no_dx_but_concerns", {}).get("branches", {})
            if isinstance(branches, dict):
                for key, branch in branches.items():
                    path = branch.get("path") if isinstance(branch, dict) else None
                    if not path:
                        path = f"{context_path}.branches.{key}"
                    available_paths.append(path)
            
            # Handle options
            options = content.get("options", {})
            if isinstance(options, dict):
                for key, option in options.items():
                    path = option.get("next_path") if isinstance(option, dict) else None
                    if not path:
                        path = f"{context_path}.options.{key}"
                    available_paths.append(path)
            
            # Filter out empty paths
            return [path for path in available_paths if path]
            
        except Exception as e:
            print(f"❌ Error getting available paths: {e}")
            return []

    def get_initial_context(self, user_profile: Dict) -> str:
        """Determine initial context based on user profile."""
        role = user_profile.get("role", "parent_caregiver")
        status = user_profile.get("diagnosis_status", "diagnosed_no")
        
        if role == "parent_caregiver":
            if status == "diagnosed_no":
                return "diagnosed_no.entry_point"
            else:
                return "diagnosed_yes.support_affording"
        else:
            if status == "diagnosed_no":
                return "adult_self.diagnosed_no.education"
            else:
                return "adult_self.diagnosed_yes.care_navigation"
