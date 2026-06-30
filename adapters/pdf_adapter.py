import io
from typing import Any
from core.models import RawRecord
from adapters.base import BaseAdapter, ExtractionError, adapter_registry

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

class PdfAdapter(BaseAdapter):
    def extract(self, source_identifier: str, source_content: Any) -> list[RawRecord]:
        if PdfReader is None:
            raise ExtractionError(source_identifier, "pypdf library not installed")

        if not isinstance(source_content, bytes):
            raise ExtractionError(source_identifier, "PDF source_content must be bytes")

        try:
            reader = PdfReader(io.BytesIO(source_content))
            if reader.is_encrypted:
                raise ExtractionError(source_identifier, "PDF is password protected")

            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            full_text = "\n".join(text_parts).strip()
            
            if not full_text:
                raise ExtractionError(source_identifier, "No text layer, OCR not supported")

            import re
            raw_data = {"extracted_text": full_text}
            
            # 1. First pass: strict colon-delimited extraction
            for line in full_text.split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    raw_data[k.strip().lower()] = v.strip()
                    
            # 2. Second pass: regex fallback for unstructured pipe-delimited or plain text
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            if "name" not in raw_data and lines:
                raw_data["name"] = lines[0]
                
            if "headline" not in raw_data and len(lines) > 1:
                potential_headline = lines[1]
                # If it doesn't look like an email or phone, assume it's a headline
                if len(potential_headline) < 100 and "@" not in potential_headline and not re.search(r'\d{3}', potential_headline):
                    raw_data["headline"] = potential_headline

            if "email" not in raw_data:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', full_text)
                if email_match:
                    raw_data["email"] = email_match.group(0)
                    
            if "phone" not in raw_data:
                # Basic phone regex catching international formats and extensions
                phone_match = re.search(r'\(?\+?[0-9]{1,3}\)?\s?-?\.?[0-9]{3}\s?-?\.?[0-9]{3,4}\s?-?\.?[0-9]{0,4}(?:x[0-9]+)?', full_text)
                if phone_match:
                    raw_data["phone"] = phone_match.group(0)
                    
            if "github" not in raw_data:
                github_match = re.search(r'github\.com/[a-zA-Z0-9-]+', full_text)
                if github_match:
                    raw_data["github"] = github_match.group(0)
                    
            if "linkedin" not in raw_data:
                linkedin_match = re.search(r'linkedin\.com/in/[a-zA-Z0-9-]+', full_text)
                if linkedin_match:
                    raw_data["linkedin"] = linkedin_match.group(0)
                    
            # 3. Third pass: Section-based unstructured extraction
            sections = {"experience": [], "education": [], "skills": []}
            current_section = None
            
            for line in lines:
                line_lower = line.lower().strip()
                if line_lower in ["experience", "work experience", "employment history", "professional experience"]:
                    current_section = "experience"
                    continue
                elif line_lower in ["education", "academic background", "education & training"]:
                    current_section = "education"
                    continue
                elif line_lower in ["skills", "technical skills", "core competencies"]:
                    current_section = "skills"
                    continue
                elif len(line) < 30 and line.isupper() and not any(char.isdigit() for char in line):
                    current_section = None # Avoid bleeding into unknown sections
                    continue
                    
                if current_section:
                    sections[current_section].append(line)
                    
            if "experience" not in raw_data and sections["experience"]:
                exp_list = []
                current_exp = {}
                for exp_line in sections["experience"]:
                    # Robust date regex
                    date_match = re.search(r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?[a-z]*\s*(?:19|20)\d{2})\s*(?:-|to)\s*((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?[a-z]*\s*(?:19|20)\d{2}|present|current|now)', exp_line, re.IGNORECASE)
                    if date_match:
                        if current_exp:
                            exp_list.append(current_exp)
                        current_exp = {"start_date": date_match.group(1), "end_date": date_match.group(2)}
                        clean_line = exp_line[:date_match.start()] + exp_line[date_match.end():]
                        clean_line = clean_line.strip(' -|,')
                        if clean_line:
                            current_exp["company"] = clean_line
                    else:
                        if current_exp:
                            current_exp["summary"] = current_exp.get("summary", "") + " " + exp_line
                        else:
                            current_exp = {"company": exp_line}
                if current_exp:
                    exp_list.append(current_exp)
                if exp_list:
                    raw_data["experience"] = exp_list
                    
            if "education" not in raw_data and sections["education"]:
                edu_list = []
                for edu_line in sections["education"]:
                    date_match = re.search(r'(?:19|20)\d{2}', edu_line)
                    end_year = date_match.group(0) if date_match else None
                    edu_list.append({
                        "degree": edu_line,
                        "end_year": end_year
                    })
                if edu_list:
                    raw_data["education"] = edu_list
            
            return [RawRecord(
                source_type="pdf",
                source_identifier=source_identifier,
                record_index=0,
                raw_data=raw_data
            )]

        except Exception as e:
            raise ExtractionError(source_identifier, "Failed to read PDF", {"error": str(e)})

adapter_registry.register("pdf", PdfAdapter())
