from pathlib import Path
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import random

class PdfEmitter:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        
    def emit(self, records: List[Dict[str, Any]]):
        pdf_dir = self.output_dir / "resume" / "pdf"
        
        for r in records:
            name_str = r.get("full_name") or f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
            # Clean filename
            safe_name = name_str.replace(" ", "_").replace("/", "").replace("\\", "")
            filename = f"{safe_name}_Resume_{r['uuid'][:4]}.pdf"
            
            c = canvas.Canvas(str(pdf_dir / filename), pagesize=letter)
            
            # Simple layout variation
            template = random.choice(["ats", "modern", "classic"])
            
            c.setFont("Helvetica-Bold", 16 if template == "modern" else 14)
            c.drawString(72, 750, name_str)
            
            c.setFont("Helvetica", 10)
            y = 730
            
            # Contact block
            contact_parts = []
            if r.get("email"): contact_parts.append(r["email"])
            if r.get("phone"): contact_parts.append(r["phone"])
            if r.get("github"): contact_parts.append(r["github"])
            if r.get("linkedin"): contact_parts.append(r["linkedin"])
            
            c.drawString(72, y, " | ".join(contact_parts))
            y -= 30
            
            # Experience
            c.setFont("Helvetica-Bold", 12)
            c.drawString(72, y, "Experience")
            y -= 20
            c.setFont("Helvetica", 10)
            
            for exp in r.get("experience", []):
                title = f"{exp.get('title')} at {exp.get('company')}"
                dates = f"{exp.get('start_date', '')} to {exp.get('end_date', '')}"
                c.drawString(72, y, f"{title} ({dates})")
                y -= 20
                if y < 100:
                    c.showPage()
                    y = 750
            
            # Education
            y -= 10
            c.setFont("Helvetica-Bold", 12)
            c.drawString(72, y, "Education")
            y -= 20
            c.setFont("Helvetica", 10)
            for edu in r.get("education", []):
                c.drawString(72, y, f"{edu.get('degree')} - {edu.get('institution')}, {edu.get('end_year')}")
                y -= 20
                
            # Skills
            y -= 10
            c.setFont("Helvetica-Bold", 12)
            c.drawString(72, y, "Skills")
            y -= 20
            c.setFont("Helvetica", 10)
            c.drawString(72, y, ", ".join(r.get("skills", [])))
            
            c.save()
            r["pdf_filename"] = filename
