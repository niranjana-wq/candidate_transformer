from pydantic import BaseModel, Field, ConfigDict
from typing import Any

class RawRecord(BaseModel):
    """
    Represents a raw record extracted from a single source before any cleaning or normalization.
    """
    source_type: str = Field(description="The type of source (e.g., 'resume', 'csv', 'json', 'linkedin', 'github')")
    source_identifier: str = Field(description="The unique identifier for the source (e.g., filename or URL)")
    record_index: int | None = Field(default=None, description="For bulk sources like CSV/JSON, tracks the row or index for auditing")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="The raw, unmapped data fields from the source")


class Location(BaseModel):
    """
    Represents a candidate's location.
    Country should ideally be normalized to ISO-3166 alpha-2 format.
    """
    city: str | None = None
    region: str | None = None
    country: str | None = None


class Links(BaseModel):
    """
    Represents a candidate's online presence and links.
    """
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    other: list[str] = Field(default_factory=list)


class Skill(BaseModel):
    """
    Represents a specific skill and the confidence in its extraction.
    """
    name: str
    confidence: float | None = None
    sources: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    """
    Represents a single professional experience entry.
    Dates are normalized to YYYY-MM.
    """
    company: str | None = None
    title: str | None = None
    start: str | None = None
    end: str | None = None
    summary: str | None = None


class Education(BaseModel):
    """
    Represents a single education entry.
    """
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    end_year: str | None = None


class ProvenanceEntry(BaseModel):
    """
    Records the origin of a specific canonical field's value.
    """
    field: str = Field(description="The canonical field path (e.g., 'full_name', 'experience')")
    source: str = Field(description="The winning source identifier or type")
    method: str = Field(description="The method by which the value was chosen (e.g., 'priority', 'agreement')")
    confidence: float | None = Field(default=None, description="The field's calculated confidence score")
    source_priority: int | None = Field(default=None, description="The priority level of the winning source (lower is better)")
    agreement_count: int | None = Field(default=None, description="Number of independent sources that agreed on this value")


class CanonicalRecord(BaseModel):
    """
    The internal, fixed-schema representation of a candidate.
    This schema is immutable during projection. Missing fields are strictly None, never invented.
    """
    model_config = ConfigDict(extra='forbid')
    
    candidate_id: str | None = Field(default=None, description="Deterministic hash ID generated post-resolution")
    full_name: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list, description="E.164 normalized phone numbers")
    location: Location | None = None
    links: Links | None = None
    headline: str | None = None
    years_experience: float | None = None
    skills: list[Skill] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    overall_confidence: float | None = Field(default=None, ge=0.10, le=1.00)


class RunConfig(BaseModel):
    """
    Configuration parameters for a single pipeline run, specifically driving projection.
    """
    model_config = ConfigDict(extra='forbid')
    
    projection_mapping: dict[str, Any] = Field(default_factory=dict, description="Path remapping for the output JSON")
    include_confidence: bool = Field(default=True, description="Whether to include confidence scores in the output")
    include_provenance: bool = Field(default=True, description="Whether to include provenance trails in the output")
    missing_value_policy: str = Field(default="null", description="Policy for missing fields: 'null', 'omit', or 'error'")
    
    # Business rules (Defaults match previous hardcoded values)
    priority_order: list[str] = Field(
        default_factory=lambda: ["resume", "pdf", "txt", "json", "csv", "linkedin", "github"]
    )
    reliability: dict[str, float] = Field(
        default_factory=lambda: {
            "resume": 0.95, "pdf": 0.95, "txt": 0.95,
            "json": 0.92, "csv": 0.88,
            "linkedin": 0.85, "github": 0.82
        }
    )
    penalties: dict[int, float] = Field(
        default_factory=lambda: {1: 0.15, 2: 0.08, 3: 0.03}
    )
    
    # Matcher configurations
    match_threshold: float = Field(default=0.65, description="Threshold for fuzzy matching to accept a merge")
    match_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "email": 0.35,
            "phone": 0.25,
            "name": 0.20,
            "company": 0.10,
            "education": 0.05,
            "location": 0.05
        }
    )
    dynamic_weights: bool = Field(default=False, description="Whether to dynamically redistribute weights for missing fields")
    
    # Confidence configurations
    confidence_field_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "full_name": 1.0,
            "emails": 1.5,
            "phones": 1.5,
            "experience": 2.0,
            "education": 1.5,
            "skills": 1.0,
            "location": 0.5,
            "headline": 0.5,
            "links": 0.5
        }
    )
    confidence_conflict_penalties: dict[str, float] = Field(
        default_factory=lambda: {
            "full_name": 0.2,
            "emails": 0.3,
            "phones": 0.3,
            "experience": 0.15,
            "education": 0.15,
            "skills": 0.05,
            "location": 0.05,
            "headline": 0.05,
            "links": 0.05
        }
    )


class AuditEntry(BaseModel):
    """
    A single entry for the structured audit log.
    """
    timestamp: str
    level: str = Field(description="Log level: 'INFO', 'WARNING', 'ERROR'")
    action: str = Field(description="Action categorized (e.g., 'quarantine', 'merge_conflict', 'validation_failure')")
    candidate_id: str | None = None
    source: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
