import random
from typing import Dict, Any
from .base import BaseMutation

class ConflictingMutation(BaseMutation):
    @property
    def mutation_type(self) -> str:
        return "conflicting"

    def apply(self, record: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        mutations = {}
        if not config.get("enabled", False):
            return mutations
            
        rate = config.get("rate", 0.0)
        
        # Conflict: Change phone number completely to simulate a shared profile or false merge
        if "phone" in record and random.random() < rate:
            original = record["phone"]
            record["phone"] = "+1-555-000-9999"
            mutations["phone"] = {"original": original, "mutated": "+1-555-000-9999", "reason": "conflicting_data"}
            
        return mutations
