import json
from pathlib import Path
from typing import List, Dict, Any

class AtsEmitter:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        
    def emit(self, records: List[Dict[str, Any]]):
        output_data = []
        for r in records:
            # Map canonical to ATS JSON format
            ats_record = {
                "candidate_id": f"MASTER-{r['uuid'][:8].upper()}",
                "personal": {
                    "first_name": r.get("first_name", ""),
                    "middle_name": "",
                    "last_name": r.get("last_name", ""),
                    "gender": "Unknown",
                    "dob": "1990-01-01"
                },
                "contact": {
                    "primary_email": r.get("email"),
                    "alternate_emails": [],
                    "primary_phone": r.get("phone"),
                    "alternate_phone": None
                },
                "location": r.get("location", {}),
                "social": {
                    "github": r.get("github"),
                    "linkedin": r.get("linkedin"),
                    "portfolio": r.get("portfolio")
                },
                "education": r.get("education", []),
                "experience": r.get("experience", []),
                "skills": [{"name": s, "level": "Advanced"} for s in r.get("skills", [])]
            }
            output_data.append(ats_record)
            
        out_path = self.output_dir / "ATS_info.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
