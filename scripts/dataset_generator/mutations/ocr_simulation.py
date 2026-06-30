import random
from typing import Dict, Any
from .base import BaseMutation

class OcrSimulationMutation(BaseMutation):
    @property
    def mutation_type(self) -> str:
        return "ocr_simulation"
        
    def _apply_ocr_typos(self, text: str) -> str:
        # Realistic OCR confusion patterns
        confusion = {
            'l': '1', '1': 'l', 'O': '0', '0': 'O', 'm': 'rn', 'rn': 'm', 
            'c': 'e', 'e': 'c', 'I': 'l', 'B': '8', '8': 'B', 'S': '5', '5': 'S',
            'Z': '2', '2': 'Z'
        }
        chars = list(text)
        # Apply up to 2 OCR errors
        num_errors = random.randint(1, 2)
        for _ in range(num_errors):
            idx = random.randint(0, len(chars)-1)
            char = chars[idx]
            if char in confusion:
                chars[idx] = confusion[char]
            else:
                # If no mapping, just swap a random mapping somewhere else
                for i, c in enumerate(chars):
                    if c in confusion:
                        chars[i] = confusion[c]
                        break
        return "".join(chars)

    def apply(self, record: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        mutations = {}
        if not config.get("enabled", False):
            return mutations
            
        rate = config.get("rate", 0.0)
        fields = config.get("fields", [])
        
        for field in fields:
            if field in record and isinstance(record[field], str) and random.random() < rate:
                original = record[field]
                mutated = self._apply_ocr_typos(original)
                if mutated != original:
                    record[field] = mutated
                    mutations[field] = {"original": original, "mutated": mutated}
                    
        return mutations
