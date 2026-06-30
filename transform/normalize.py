import unicodedata
import re
import datetime
from typing import Any, Callable
from dataclasses import dataclass
from core.registry import Registry

try:
    import phonenumbers
except ImportError:
    phonenumbers = None

try:
    from dateutil import parser
except ImportError:
    parser = None

@dataclass
class NormalizationResult:
    """Holds the result of a normalization attempt."""
    value: Any | None
    error: str | None = None

class DataCleaner:
    """Generic hygiene cleaner before specific type normalization."""
    @staticmethod
    def clean(val: Any) -> Any:
        if isinstance(val, str):
            val = unicodedata.normalize('NFC', val).strip()
            return val if val else None
        if isinstance(val, list):
            cleaned_list = [DataCleaner.clean(item) for item in val]
            return [item for item in cleaned_list if item is not None]
        if isinstance(val, dict):
            return {k: DataCleaner.clean(v) for k, v in val.items()}
        return val


normalizer_registry = Registry[Callable[..., NormalizationResult]]("Normalizers")

def normalize_name(val: Any, **kwargs) -> NormalizationResult:
    val = DataCleaner.clean(val)
    if val is None:
        return NormalizationResult(None)
    if not isinstance(val, str):
        return NormalizationResult(None, "Name must be a string")
    return NormalizationResult(val.title())

def normalize_email(val: Any, **kwargs) -> NormalizationResult:
    val = DataCleaner.clean(val)
    if val is None:
        return NormalizationResult(None)
    if not isinstance(val, str) or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", val):
        return NormalizationResult(None, "Invalid email format")
    return NormalizationResult(val.lower())

def normalize_phone(val: Any, **kwargs) -> NormalizationResult:
    val = DataCleaner.clean(val)
    if val is None:
        return NormalizationResult(None)
    if not phonenumbers:
        # Fallback if library missing during tests
        return NormalizationResult(str(val))
    try:
        default_region = kwargs.get("default_region", None)
        parsed = phonenumbers.parse(str(val), default_region)
        if not phonenumbers.is_valid_number(parsed):
            return NormalizationResult(None, "Invalid phone number")
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        return NormalizationResult(formatted)
    except phonenumbers.NumberParseException:
        # Graceful fallback for missing country codes or extensions
        # rather than returning None and dropping valid data
        return NormalizationResult(str(val))
    except Exception as e:
        return NormalizationResult(None, f"Phone parsing failed: {str(e)}")

def normalize_date(val: Any, **kwargs) -> NormalizationResult:
    val = DataCleaner.clean(val)
    if val is None:
        return NormalizationResult(None)
    if not parser:
        return NormalizationResult(str(val))
    
    val_str = str(val).strip().lower()
    if val_str in ("present", "current", "now"):
        return NormalizationResult(datetime.datetime.now().strftime("%Y-%m"))
        
    try:
        # Fixed default date ensures complete determinism independent of execution date
        default_date = datetime.datetime(2000, 1, 1)
        parsed_date = parser.parse(str(val), default=default_date, fuzzy=True)
        return NormalizationResult(parsed_date.strftime("%Y-%m"))
    except Exception as e:
        return NormalizationResult(None, f"Date parsing failed: {str(e)}")

def normalize_country(val: Any, **kwargs) -> NormalizationResult:
    val = DataCleaner.clean(val)
    if val is None:
        return NormalizationResult(None)
    if not isinstance(val, str):
        return NormalizationResult(None, "Country must be a string")
    val_upper = val.upper()
    if len(val_upper) == 2 and val_upper.isalpha():
        return NormalizationResult(val_upper)
    return NormalizationResult(None, "Country code must be ISO-3166 alpha-2")

def normalize_skill(val: Any, **kwargs) -> NormalizationResult:
    val = DataCleaner.clean(val)
    if val is None:
        return NormalizationResult(None)
    if isinstance(val, str):
        # Format as dict to align with CanonicalRecord Skill model structure
        return NormalizationResult({"name": val.lower()})
    if isinstance(val, dict) and "name" in val:
        val["name"] = str(val["name"]).lower()
        return NormalizationResult(val)
    return NormalizationResult(None, "Skill must be a string or dict with a 'name'")

def normalize_experience(val: Any, **kwargs) -> NormalizationResult:
    val = DataCleaner.clean(val)
    if val is None:
        return NormalizationResult(None)
    if not isinstance(val, list):
        return NormalizationResult(None, "Experience must be a list of dicts")
        
    normalized_exp = []
    for exp in val:
        if not isinstance(exp, dict): continue
        
        # safely map start_date / end_date from ATS JSON, or start / end from canonical
        start_val = exp.get("start") or exp.get("start_date") or exp.get("startDate")
        end_val = exp.get("end") or exp.get("end_date") or exp.get("endDate")
        
        norm_start = normalize_date(start_val).value if start_val else None
        norm_end = normalize_date(end_val).value if end_val else None
        
        norm_exp = {
            "company": str(exp.get("company")) if exp.get("company") else None,
            "title": str(exp.get("title")) if exp.get("title") else None,
            "start": norm_start,
            "end": norm_end,
            "summary": str(exp.get("summary")) if exp.get("summary") else None
        }
        # Only keep if company or title exists
        if norm_exp["company"] or norm_exp["title"]:
            normalized_exp.append(norm_exp)
            
    return NormalizationResult(normalized_exp if normalized_exp else None)

def normalize_education(val: Any, **kwargs) -> NormalizationResult:
    val = DataCleaner.clean(val)
    if val is None:
        return NormalizationResult(None)
    if not isinstance(val, list):
        return NormalizationResult(None, "Education must be a list of dicts")
        
    degree_prefixes = [
        "b.e", "b.tech", "b.sc", "b.s", "b.a", "bs", "ba", "bachelor",
        "m.e", "m.tech", "m.sc", "m.s", "m.a", "ms", "ma", "master",
        "mba", "phd", "ph.d", "doctorate"
    ]
        
    normalized_edu = []
    for edu in val:
        if not isinstance(edu, dict): continue
        
        inst = edu.get("institution") or edu.get("school")
        deg = edu.get("degree")
        field = edu.get("field")
        end_year = edu.get("end_year") or edu.get("graduation_year") or edu.get("endDate")
        
        if end_year:
            end_year = normalize_date(end_year).value
            if end_year and "-" in end_year:
                end_year = end_year.split("-")[0] # Extract just year for education
                
        # Smart extraction from degree if field is missing
        if deg and not field and isinstance(deg, str):
            deg_lower = deg.lower()
            for prefix in degree_prefixes:
                if deg_lower.startswith(prefix) or deg_lower.startswith(prefix.replace(".", "")):
                    # Try to split on common delimiters
                    parts = re.split(r' in | of |, |\s-\s', deg, maxsplit=1, flags=re.IGNORECASE)
                    if len(parts) == 2:
                        deg = parts[0].strip()
                        field = parts[1].strip()
                    else:
                        # Fallback space split
                        parts = deg.split(" ", 1)
                        if len(parts) == 2:
                            deg = parts[0].strip()
                            field = parts[1].strip()
                    break
                    
        norm_edu = {
            "institution": str(inst) if inst else None,
            "degree": str(deg) if deg else None,
            "field": str(field) if field else None,
            "end_year": str(end_year) if end_year else None
        }
        
        if norm_edu["institution"] or norm_edu["degree"]:
            normalized_edu.append(norm_edu)
            
    return NormalizationResult(normalized_edu if normalized_edu else None)

def enrich_years_experience(exp_list: Any) -> float | None:
    """Helper to calculate years of experience purely from normalized experience array."""
    if not exp_list or not isinstance(exp_list, list):
        return None
        
    total_months = 0
    intervals = []
    
    for exp in exp_list:
        if not isinstance(exp, dict): continue
        start_str = exp.get("start")
        end_str = exp.get("end")
        
        if not start_str:
            continue
            
        try:
            start_date = datetime.datetime.strptime(start_str, "%Y-%m")
            end_date = datetime.datetime.strptime(end_str, "%Y-%m") if end_str else datetime.datetime.now()
            
            # Simple month difference (could overlap, but for this basic calculation it's sufficient)
            diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            if diff > 0:
                intervals.append((start_date, end_date))
        except Exception:
            continue
            
    if not intervals:
        return None
        
    # Sort and merge intervals to prevent double counting overlapping jobs
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for current in intervals[1:]:
        prev = merged[-1]
        if current[0] <= prev[1]:
            # Overlap: extend end date if necessary
            merged[-1] = (prev[0], max(prev[1], current[1]))
        else:
            merged.append(current)
            
    total_months = sum((i[1].year - i[0].year) * 12 + (i[1].month - i[0].month) for i in merged)
    return round(total_months / 12.0, 1) if total_months > 0 else None

# Register all normalizers
normalizer_registry.register("name", normalize_name)
normalizer_registry.register("email", normalize_email)
normalizer_registry.register("phone", normalize_phone)
normalizer_registry.register("date", normalize_date)
normalizer_registry.register("country", normalize_country)
normalizer_registry.register("skill", normalize_skill)
normalizer_registry.register("experience", normalize_experience)
normalizer_registry.register("education", normalize_education)

class FieldNormalizer:
    """
    Applies registered normalization functions to specific fields.
    """
    @staticmethod
    def normalize_field(normalizer_key: str, value: Any, **kwargs) -> NormalizationResult:
        try:
            normalizer_func = normalizer_registry.get(normalizer_key)
            return normalizer_func(value, **kwargs)
        except Exception:
            # If no specific normalizer is registered for this key, just return the cleaned value.
            return NormalizationResult(DataCleaner.clean(value))
