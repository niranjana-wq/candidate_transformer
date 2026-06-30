import random
from typing import Dict, Any
from .base import BaseMutation

class FormattingMutation(BaseMutation):
    @property
    def mutation_type(self) -> str:
        return "formatting"
        
    def apply(self, record: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        mutations = {}
        
        # Phone formatting
        if config.get("phone_format_mix") and record.get("phone"):
            original = record["phone"]
            fmt = random.choice(["E164", "US_LOCAL", "DASHES", "DOTS"])
            # Strip non-digits
            digits = ''.join(c for c in original if c.isdigit())
            if digits:
                if fmt == "E164":
                    new_phone = "+" + digits
                elif fmt == "US_LOCAL":
                    if len(digits) >= 10:
                        new_phone = f"({digits[-10:-7]}) {digits[-7:-4]}-{digits[-4:]}"
                    else:
                        new_phone = original
                elif fmt == "DASHES":
                    if len(digits) >= 10:
                        new_phone = f"{digits[-10:-7]}-{digits[-7:-4]}-{digits[-4:]}"
                    else:
                        new_phone = original
                elif fmt == "DOTS":
                    if len(digits) >= 10:
                        new_phone = f"{digits[-10:-7]}.{digits[-7:-4]}.{digits[-4:]}"
                    else:
                        new_phone = original
                else:
                    new_phone = original
                    
                if new_phone != original:
                    record["phone"] = new_phone
                    mutations["phone"] = {"original": original, "mutated": new_phone}
                    
        # Name combining
        if config.get("combine_names") and record.get("first_name") and record.get("last_name"):
            full = f"{record['first_name']} {record['last_name']}"
            record["full_name"] = full
            del record["first_name"]
            del record["last_name"]
            mutations["name"] = {"original": "split_names", "mutated": "full_name"}
            
        return mutations
