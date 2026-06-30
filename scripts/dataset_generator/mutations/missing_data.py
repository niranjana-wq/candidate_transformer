import random
from typing import Dict, Any
from .base import BaseMutation

class MissingDataMutation(BaseMutation):
    @property
    def mutation_type(self) -> str:
        return "missing_data"
        
    def apply(self, record: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        mutations = {}
        
        # Check explicit drops
        drops = [
            ("drop_email", "email"),
            ("drop_phone", "phone"),
            ("drop_github", "github"),
            ("drop_portfolio", "portfolio"),
            ("drop_id", "uuid"),
            ("drop_location", "location")
        ]
        
        for config_key, field_key in drops:
            rate = config.get(config_key, 0.0)
            if rate > 0 and random.random() < rate:
                if field_key in record:
                    original = record[field_key]
                    del record[field_key]
                    mutations[field_key] = {"original": original, "mutated": None}
                    
        return mutations
