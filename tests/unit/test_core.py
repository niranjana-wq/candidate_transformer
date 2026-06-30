import pytest
from core.models import RawRecord, CanonicalRecord, RunConfig, ProvenanceEntry
from core.registry import Registry, RegistryError
from core.context import PipelineContext
from pydantic import ValidationError

def test_raw_record_validation():
    # Valid
    record = RawRecord(source_type="csv", source_identifier="file.csv", record_index=1, raw_data={"name": "John"})
    assert record.source_type == "csv"
    assert record.record_index == 1

    # Invalid (missing required)
    with pytest.raises(ValidationError):
        RawRecord(source_type="csv")

def test_canonical_record_validation():
    # Valid
    record = CanonicalRecord(full_name="John Doe", emails=["john@example.com"])
    assert record.full_name == "John Doe"
    assert len(record.emails) == 1
    
    # Invalid email list type
    with pytest.raises(ValidationError):
        CanonicalRecord(emails="not-a-list")

def test_run_config_validation():
    config = RunConfig(include_confidence=False, missing_value_policy="omit")
    assert not config.include_confidence
    assert config.missing_value_policy == "omit"
    
    from projection.projector import Projector, ProjectionError
    with pytest.raises(ProjectionError):
        config_invalid = RunConfig(missing_value_policy="invalid_policy")
        Projector.validate_config(config_invalid)

def test_registry():
    reg = Registry("test_reg")
    reg.register("key1", 100)
    assert reg.get("key1") == 100
    
    with pytest.raises(RegistryError):
        reg.register("key1", 200)
        
    with pytest.raises(RegistryError):
        reg.get("missing_key")
        
    all_items = reg.get_all()
    assert "key1" in all_items
    
def test_pipeline_context():
    config = RunConfig()
    ctx = PipelineContext(config=config)
    
    assert ctx.config == config
    
    entry = ProvenanceEntry(field="emails", source="json", method="priority")
    ctx.add_provenance("cand_1", entry)
    
    prov = ctx.get_provenance("cand_1")
    assert len(prov) == 1
    assert prov[0].source == "json"
    
    assert ctx.finalize_provenance("cand_1") == prov
    assert ctx.get_provenance("missing") == []
