from typing import Any, Dict, List, get_origin, get_args
import typing
import types
from core.models import CanonicalRecord, RunConfig

class ProjectionError(Exception):
    """Raised when projection configuration is invalid or execution fails."""
    pass

class Projector:
    """
    Final view layer. Reshapes the CanonicalRecord according to RunConfig.
    Strictly read-only; never modifies the underlying business data.
    """
    
    @classmethod
    def project(cls, record: CanonicalRecord, config: RunConfig) -> Dict[str, Any]:
        """
        Projects a CanonicalRecord into a final dictionary view.
        """
        cls.validate_config(config)
        
        # Determine if we have an explicit mapping
        if not config.projection_mapping:
            # Output the entire canonical record
            exclude_none = (config.missing_value_policy == "omit")
            raw_dict = record.model_dump(exclude_none=exclude_none)
            
            if config.missing_value_policy == "error":
                # Ensure no top-level fields are missing
                for field in CanonicalRecord.model_fields:
                    if cls._is_empty(raw_dict.get(field)):
                        raise ProjectionError(f"Field '{field}' is missing (policy=error)")
            
            return cls._strip_private_fields(raw_dict, config)
            
        output = {}
        for alias, path in config.projection_mapping.items():
            val = cls._resolve_path(record, path.split('.'))
            
            # Convert models to basic dictionaries for final output serialization
            if hasattr(val, 'model_dump'):
                val = val.model_dump(exclude_none=(config.missing_value_policy == "omit"))
            elif isinstance(val, list):
                val = [
                    v.model_dump(exclude_none=(config.missing_value_policy == "omit")) 
                    if hasattr(v, 'model_dump') else v 
                    for v in val
                ]
            
            if cls._is_empty(val):
                if config.missing_value_policy == "error":
                    raise ProjectionError(f"Field '{path}' is missing for alias '{alias}'")
                elif config.missing_value_policy == "omit":
                    continue
                elif config.missing_value_policy == "null":
                    output[alias] = None
            else:
                output[alias] = cls._strip_private_fields(val, config)
                
        return output

    @classmethod
    def validate_config(cls, config: RunConfig) -> None:
        """
        Validates the projection configuration statically against the CanonicalRecord schema.
        Fails fast if invalid paths or unknown fields are configured.
        """
        if config.missing_value_policy not in ["null", "omit", "error"]:
            raise ProjectionError(f"Invalid missing_value_policy: {config.missing_value_policy}")
            
        if not config.projection_mapping:
            return
            
        for alias, path in config.projection_mapping.items():
            cls._validate_path(path)

    @classmethod
    def _validate_path(cls, path: str) -> None:
        """Statically verifies that a dot-notation path exists in the CanonicalRecord schema."""
        parts = path.split('.')
        current_type = CanonicalRecord
        
        for part in parts:
            if part.isdigit():
                continue
                
            if hasattr(current_type, 'model_fields'):
                if part not in current_type.model_fields:
                    raise ProjectionError(f"Unknown canonical field '{part}' in path '{path}'")
                    
                annotation = current_type.model_fields[part].annotation
                origin = get_origin(annotation)
                
                if origin is list:
                    args = get_args(annotation)
                    current_type = args[0] if args else Any
                elif origin is dict:
                    current_type = dict
                elif origin is getattr(types, "UnionType", None) or origin is typing.Union:
                    args = get_args(annotation)
                    # Exclude None to find the real type
                    non_none = [a for a in args if a is not type(None)]
                    current_type = non_none[0] if non_none else Any
                    
                    # If it's an optional list, unwrap the list to get the item type
                    if get_origin(current_type) is list:
                        inner_args = get_args(current_type)
                        current_type = inner_args[0] if inner_args else Any
                else:
                    current_type = annotation
            else:
                # Reached a type we cannot statically inspect (like Any or Dict keys)
                current_type = Any

    @classmethod
    def _resolve_path(cls, obj: Any, parts: List[str]) -> Any:
        """Dynamically extracts data from nested objects, lists, and dicts."""
        current = obj
        for i, part in enumerate(parts):
            if current is None:
                return None
                
            if isinstance(current, list):
                if part.isdigit():
                    idx = int(part)
                    if idx < len(current):
                        current = current[idx]
                    else:
                        return None
                else:
                    # Non-digit attribute on a list: map the remainder of the path over the list items
                    remaining_parts = parts[i:]
                    mapped = []
                    for item in current:
                        val = cls._resolve_path(item, remaining_parts)
                        if not cls._is_empty(val):
                            mapped.append(val)
                    return mapped if mapped else None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                current = getattr(current, part, None)
                
        return current

    @classmethod
    def _strip_private_fields(cls, data: Any, config: RunConfig) -> Any:
        """Recursively removes confidence and provenance metadata if disabled in config."""
        if isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                if not config.include_confidence and k in ("confidence", "overall_confidence"):
                    continue
                if not config.include_provenance and k == "provenance":
                    continue
                new_dict[k] = cls._strip_private_fields(v, config)
            return new_dict
        elif isinstance(data, list):
            return [cls._strip_private_fields(item, config) for item in data]
        else:
            return data
            
    @staticmethod
    def _is_empty(val: Any) -> bool:
        if val is None: return True
        if isinstance(val, (list, dict, str)) and len(val) == 0: return True
        return False
