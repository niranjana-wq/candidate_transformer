from typing import Any
from core.registry import Registry

# Registry to hold field mappings for different source types.
# Key: source_type, Value: dict mapping native field name to canonical field path.
mapping_registry = Registry[dict[str, str]]("FieldMapping")

class SchemaMapper:
    """
    Translates source-specific field names to canonical field paths.
    Only performs field-name translation. Never modifies or normalizes values.
    Unknown fields are ignored.
    """
    
    @staticmethod
    def map_record(source_type: str, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Maps flat or nested raw data to a canonical dictionary structure based on the registered mapping.
        """
        try:
            field_map = mapping_registry.get(source_type)
        except Exception:
            # If no mapping exists for this source, we cannot safely map anything.
            return {}
            
        mapped_data: dict[str, Any] = {}
        
        for native_key, canonical_path in field_map.items():
            native_value = SchemaMapper._get_nested_value(raw_data, native_key)
            if native_value not in (None, "", []):
                SchemaMapper._set_nested_value(mapped_data, canonical_path, native_value)
                
        # Special fallback for names split into first/last in source data
        if "full_name" not in mapped_data:
            first = SchemaMapper._get_nested_value(raw_data, "personal.first_name")
            last = SchemaMapper._get_nested_value(raw_data, "personal.last_name")
            if first or last:
                mapped_data["full_name"] = f"{first or ''} {last or ''}".strip()
                
        return mapped_data

    @staticmethod
    def _get_nested_value(d: dict[str, Any], path: str) -> Any:
        import re
        parts = []
        for part in path.split('.'):
            match = re.match(r'(.+)\[(\d+)\]', part)
            if match:
                parts.append((match.group(1), int(match.group(2))))
            else:
                parts.append((part, None))
                
        current = d
        for key, idx in parts:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
            if idx is not None:
                if not isinstance(current, list) or len(current) <= idx:
                    return None
                current = current[idx]
        return current

    @staticmethod
    def _set_nested_value(d: dict[str, Any], path: str, value: Any) -> None:
        """Helper to set a value in a nested dictionary/list using dot and bracket notation."""
        import re
        parts = []
        for part in path.split('.'):
            match = re.match(r'(.+)\[(\d+)\]', part)
            if match:
                parts.append((match.group(1), int(match.group(2))))
            else:
                parts.append((part, None))
                
        current = d
        for i, (key, idx) in enumerate(parts[:-1]):
            if idx is not None:
                if key not in current or not isinstance(current[key], list):
                    current[key] = [{}] * (idx + 1)
                elif len(current[key]) <= idx:
                    current[key].extend([{} for _ in range(idx - len(current[key]) + 1)])
                current = current[key][idx]
            else:
                if key not in current:
                    current[key] = {}
                current = current[key]
                
        last_key, last_idx = parts[-1]
        if last_idx is not None:
            if last_key not in current or not isinstance(current[key], list):
                current[last_key] = [{}] * (last_idx + 1)
            elif len(current[last_key]) <= last_idx:
                current[last_key].extend([{} for _ in range(last_idx - len(current[last_key]) + 1)])
            current[last_key][last_idx] = value
        else:
            current[last_key] = value
