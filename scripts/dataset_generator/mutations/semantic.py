import random
from typing import Dict, Any
from .base import BaseMutation

class SemanticMutation(BaseMutation):
    @property
    def mutation_type(self) -> str:
        return "semantic"
        
    def _apply_semantic_shift(self, value: Any, field: str) -> Any:
        if field == "skills" and isinstance(value, list):
            synonyms = {"Python": "Python 3", "Java": "Core Java", "Docker": "Docker Containers", "AWS": "Amazon Web Services", "Machine Learning": "ML"}
            mutated = []
            changed = False
            for s in value:
                if s in synonyms and random.random() < 0.5:
                    mutated.append(synonyms[s])
                    changed = True
                else:
                    mutated.append(s)
            return mutated if changed else value
        
        if field == "company_name" and isinstance(value, str):
            suffixes = [" Inc.", " Corp.", " LLC", " Limited"]
            if random.random() < 0.5:
                return value + random.choice(suffixes)
            else:
                return value.upper()
                
        return value

    def apply(self, record: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        mutations = {}
        if not config.get("enabled", False):
            return mutations
            
        rate = config.get("rate", 0.0)
        fields = config.get("fields", [])
        
        for field in fields:
            if random.random() < rate:
                if field == "skills" and "skills" in record:
                    original = list(record["skills"])
                    mutated = self._apply_semantic_shift(record["skills"], "skills")
                    if mutated != original:
                        record["skills"] = mutated
                        mutations["skills"] = {"original": original, "mutated": mutated}
                        
                elif field == "company_name" and "experience" in record and record["experience"]:
                    # Mutate the first experience's company
                    exp = record["experience"][0]
                    original = exp["company"]
                    mutated = self._apply_semantic_shift(original, "company_name")
                    if mutated != original:
                        exp["company"] = mutated
                        mutations["company_name"] = {"original": original, "mutated": mutated}
                        
        return mutations
