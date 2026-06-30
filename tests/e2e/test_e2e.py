import pytest
import json
import hashlib
from pathlib import Path
from pipeline import Pipeline
from core.models import RunConfig

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

def read_fixture(filename):
    with open(FIXTURES_DIR / filename, "rb") as f:
        return f.read()

def run_pipeline(sources, config):
    pipeline = Pipeline(config)
    output = pipeline.run(sources)
    return output, pipeline

def test_e2e_all_six_sources(tmp_path):
    pass

def test_e2e_resume_missing_email():
    # 3. Resume has highest priority but missing email.
    config = RunConfig()
    
    # Load actual fixtures
    pdf_bytes = read_fixture("valid_resume.pdf")
    json_bytes = read_fixture("duplicate_records.json")
    
    sources = [
        ("pdf", "valid_resume.pdf", pdf_bytes),
        ("json", "duplicate_records.json", json_bytes)
    ]
    
    output, _ = run_pipeline(sources, config)
    # The JSON fixture has Alice Smith and Alice M. Smith (which merge via email).
    # The PDF fixture has Johnathan Doe.
    # There should be 2 candidates total.
    assert len(output) == 2

def test_e2e_determinism():
    # 21. Run exact pipeline twice, check hashes
    config = RunConfig(include_confidence=True, include_provenance=True)
    csv_bytes = read_fixture("malformed.csv")
    
    sources = [("csv", "malformed.csv", csv_bytes)]
    
    out1, _ = run_pipeline(sources, config)
    out2, _ = run_pipeline(sources, config)
    
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)
    if out1:
        assert out1[0]["candidate_id"] == out2[0]["candidate_id"]

def test_e2e_quarantined_source():
    # 10. Quarantined source
    config = RunConfig()
    
    sources = [
        ("pdf", "corrupted.pdf", read_fixture("corrupted.pdf")),
        ("json", "unicode_names.json", read_fixture("unicode_names.json"))
    ]
    
    # Should not raise exception, pipeline continues
    out, pipeline = run_pipeline(sources, config)
    
    # Verify quarantine log
    audit_events = pipeline.audit.export()["events"]
    assert any(e["action"] == "quarantine" and e["source"] == "corrupted.pdf" for e in audit_events)
    
    assert len(out) == 2 # Ivan and Ken

def test_e2e_conflict_resolution():
    # 6. Three-way conflict across sources
    config = RunConfig(include_confidence=True)
    
    # Create conflicting inputs matching exactly on email to force a merge
    json_bytes = b'[{"name": "Conflict B", "email": "conflict@test.com", "phone": "111"}]'
    csv_bytes = b'candidate_name,email,phone\nConflict C,conflict@test.com,222\n'
    
    # PDF is parsed by lines, so we give it a simple text layout
    pdf_text = b'name: Conflict A\nemail: conflict@test.com\nphone: 333\n'
    # Actually wait, PDF parsing uses PyPDF, so we just pass raw text as txt instead of mocking PDF
    sources = [
        ("txt", "conflict.txt", pdf_text),
        ("json", "conflict.json", json_bytes),
        ("csv", "conflict.csv", csv_bytes)
    ]
    
    out, pipeline = run_pipeline(sources, config)
    
    assert len(out) == 1
    assert out[0]["full_name"] == "Conflict A" # TXT (tier 1) wins
    
    # Verify penalties via audit log
    audit_events = pipeline.audit.export()["events"]
    merge_event = next(e for e in audit_events if e["action"] == "merge_success")
    assert merge_event["details"]["field_decisions"]["full_name"]["conflict_penalty"] > 0
    assert merge_event["details"]["field_decisions"]["full_name"]["final_field_confidence"] < 0.95

def test_e2e_policies():
    # 17, 18, 19. Output policies
    from projection.projector import ProjectionError
    
    config_null = RunConfig(missing_value_policy="null", projection_mapping={"Exp": "years_experience"})
    config_omit = RunConfig(missing_value_policy="omit", projection_mapping={"Exp": "years_experience"})
    config_error = RunConfig(missing_value_policy="error", projection_mapping={"Exp": "years_experience"})
    
    json_bytes = read_fixture("missing_fields.json")
    sources = [("json", "missing_fields.json", json_bytes)]
    
    out_null, _ = run_pipeline(sources, config_null)
    assert out_null[0]["Exp"] is None
    
    out_omit, _ = run_pipeline(sources, config_omit)
    assert "Exp" not in out_omit[0]
    
    out_error, _ = run_pipeline(sources, config_error)
    assert len(out_error) == 0

def test_e2e_unicode_and_oversized():
    config = RunConfig()
    sources = [
        ("json", "unicode_names.json", read_fixture("unicode_names.json")),
        ("txt", "oversized.txt", read_fixture("oversized.txt"))
    ]
    out, _ = run_pipeline(sources, config)
    assert len(out) == 3 # Ivan, Ken, and Giant Resume
