import csv
from pathlib import Path
from typing import List, Dict, Any

class CsvEmitter:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        
    def emit(self, records: List[Dict[str, Any]]):
        output_data = []
        for r in records:
            # Full name might have been mutated, or we combine it here
            full_name = r.get("full_name")
            if not full_name:
                first = r.get("first_name", "")
                last = r.get("last_name", "")
                full_name = f"{first} {last}".strip()
                
            loc = r.get("location", {})
            location_str = f"{loc.get('city', '')}, {loc.get('country', '')}".strip(", ")
            
            skills_str = ", ".join(r.get("skills", []))
            
            exp_str = ""
            if r.get("experience"):
                exp = r["experience"][0]
                exp_str = f"{exp.get('title')} at {exp.get('company')}"
                
            csv_record = {
                "candidate_id": f"CAND-{r.get('uuid', '')[:8].upper()}" if r.get('uuid') else "",
                "full_name": full_name,
                "emails": r.get("email", ""),
                "phones": r.get("phone", ""),
                "github_url": r.get("github", ""),
                "linkedin_url": r.get("linkedin", ""),
                "current_company": r.get("experience")[0].get("company") if r.get("experience") else "",
                "job_title": r.get("experience")[0].get("title") if r.get("experience") else "",
                "location": location_str,
                "years_experience": "3",
                "education": r.get("education")[0].get("degree") if r.get("education") else "",
                "skills": skills_str,
                "source": "recruiter_csv"
            }
            output_data.append(csv_record)
            
        out_path = self.output_dir / "recruiter_csv.csv"
        if output_data:
            keys = output_data[0].keys()
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(output_data)
