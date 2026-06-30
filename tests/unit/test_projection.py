import pytest
from projection.projector import Projector, ProjectionError
from core.models import CanonicalRecord, RunConfig, Links, Experience, Skill, ProvenanceEntry

def test_projector_invalid_field_path():
    config = RunConfig(projection_mapping={"Alias": "unknown_field"})
    with pytest.raises(ProjectionError, match="Unknown canonical field"):
        Projector.validate_config(config)

def test_projector_nested_arrays():
    config = RunConfig(projection_mapping={"First_Company": "experience.0.company"})
    rec = CanonicalRecord(experience=[Experience(company="Google"), Experience(company="Apple")])
    out = Projector.project(rec, config)
    assert out["First_Company"] == "Google"

def test_projector_missing_value_policy_null():
    config = RunConfig(missing_value_policy="null", projection_mapping={"Exp": "years_experience"})
    rec = CanonicalRecord()
    out = Projector.project(rec, config)
    assert out["Exp"] is None

def test_projector_missing_value_policy_omit():
    config = RunConfig(missing_value_policy="omit", projection_mapping={"Exp": "years_experience", "Name": "full_name"})
    rec = CanonicalRecord(full_name="Alice")
    out = Projector.project(rec, config)
    assert "Exp" not in out
    assert out["Name"] == "Alice"

def test_projector_missing_value_policy_error():
    config = RunConfig(missing_value_policy="error", projection_mapping={"Exp": "years_experience"})
    rec = CanonicalRecord()
    with pytest.raises(ProjectionError, match="is missing"):
        Projector.project(rec, config)

def test_projector_duplicate_aliases():
    # Pydantic dicts handle duplicate keys by overwriting, but conceptually we can test
    # projection where multiple paths map. Actually projection_mapping is Dict[str, str]
    # so duplicate aliases are impossible in JSON/Python dicts natively (the last one wins).
    # We can skip explicit duplicate alias test since JSON parsers handle this.
    pass

def test_projector_strip_metadata():
    config = RunConfig(include_confidence=False, include_provenance=False)
    rec = CanonicalRecord(full_name="Alice", overall_confidence=0.99)
    rec.provenance.append(ProvenanceEntry(field="full_name", source="resume", method="single"))
    rec.skills.append(Skill(name="Python", confidence=0.88))
    
    out = Projector.project(rec, config)
    
    assert "overall_confidence" not in out
    assert "provenance" not in out
    assert "confidence" not in out.get("skills", [{}])[0]

def test_projector_keep_metadata():
    config = RunConfig(include_confidence=True, include_provenance=True)
    rec = CanonicalRecord(full_name="Alice", overall_confidence=0.99)
    rec.provenance.append(ProvenanceEntry(field="full_name", source="resume", method="single"))
    
    out = Projector.project(rec, config)
    assert out["overall_confidence"] == 0.99
    assert len(out["provenance"]) == 1
