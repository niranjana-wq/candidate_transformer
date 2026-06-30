from typing import Any, Type
from pydantic import BaseModel, ValidationError
from dataclasses import dataclass

@dataclass
class ValidationIssue:
    """Represents a single validation error on a specific field."""
    field: str
    error: str

@dataclass
class ValidationResult:
    """The complete result of a schema validation attempt."""
    is_valid: bool
    issues: list[ValidationIssue]
    validated_data: Any | None = None

class SchemaValidator:
    """
    Validates a dictionary against a provided Pydantic model (schema).
    Never modifies data. Never maps or normalizes. Purely structural and type validation.
    """
    
    @staticmethod
    def validate(data: dict[str, Any], schema_model: Type[BaseModel]) -> ValidationResult:
        """
        Validates the data against the given Pydantic schema model.
        Returns a structured result with any validation issues found.
        """
        try:
            validated = schema_model.model_validate(data)
            return ValidationResult(is_valid=True, issues=[], validated_data=validated)
        except ValidationError as e:
            issues = []
            for err in e.errors():
                loc = ".".join(str(l) for l in err["loc"])
                issues.append(ValidationIssue(field=loc, error=err["msg"]))
            return ValidationResult(is_valid=False, issues=issues)
