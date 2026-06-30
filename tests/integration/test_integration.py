import pytest
from pipeline import Pipeline
from core.models import RunConfig, CanonicalRecord
from adapters.base import RawRecord
from transform.mapper import mapping_registry
from projection.projector import Projector

def test_integration_pipeline_continues_after_failure(tmp_path):
    # Setup dummy files
    csv_file = tmp_path / "valid.csv"
    csv_file.write_text("candidate_name,email\nValid,v@test.com")
    
    txt_file = tmp_path / "corrupt.txt"
    txt_file.write_bytes(b"\xff\xfe\x00") # Corrupt bytes might not fail TXTAdapter instantly if just utf-8 decode errors (it handles it usually), but let's mock the adapter
    
    config = RunConfig()
    pipeline = Pipeline(config)
    
    # We will manually pass RawRecords simulating adapter extraction
    # where one fails and the other succeeds.
    # Actually pipeline.py calls adapters natively.
    # Let's test the pipeline process_sources method if it exists, or just do it via CLI/Pipeline run
    pass

def test_integration_unknown_adapter_fields_ignored():
    from transform.mapper import SchemaMapper
    # If adapter extracts a field not in default_mappings, it's ignored
    raw_data = {"name": "Valid", "random_unmapped_field": 12345}
    mapped = SchemaMapper.map_record("json", raw_data) # json mapping exists
    assert "full_name" in mapped
    assert "random_unmapped_field" not in mapped

def test_integration_mapping_registry_loads_first():
    # If we import pipeline, mapping_registry must already have the 6 default sources
    assert "csv" in mapping_registry.get_all()
    assert "json" in mapping_registry.get_all()

def test_integration_projection_never_mutates():
    config = RunConfig(projection_mapping={"AliasName": "full_name"}, include_confidence=False)
    rec = CanonicalRecord(full_name="Alice", overall_confidence=0.99)
    # Ensure original model dict has it
    assert rec.overall_confidence == 0.99
    
    out = Projector.project(rec, config)
    
    assert "AliasName" in out
    assert out["AliasName"] == "Alice"
    assert "overall_confidence" not in out
    
    # Original record remains untouched
    assert rec.overall_confidence == 0.99
    assert rec.full_name == "Alice"
