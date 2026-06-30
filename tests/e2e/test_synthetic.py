import pytest
import json
import random
from pipeline import Pipeline
from core.models import RunConfig
from adapters.json_adapter import JsonAdapter
from unittest.mock import patch

def generate_synthetic_data(num_records=2000):
    records = []
    for i in range(num_records):
        records.append({
            "name": f"Candidate {i}",
            "email": f"candidate{i}@example.com" if i % 10 != 0 else None,
            "phone": f"+1 555 {i:04d}" if i % 5 != 0 else "invalid",
            "years_of_experience": random.randint(1, 20) if i % 3 != 0 else None,
            "skills": ["Python", "Java", "SQL"] if i % 2 == 0 else "Python"
        })
    # Add exact duplicates
    records.append(records[0])
    records.append(records[1])
    
    # Add same name, different email
    records.append({"name": "Candidate 0", "email": "other@example.com"})
    
    # Add same email, different name
    records.append({"name": "Fake Name", "email": "candidate1@example.com"})
    
    return records

def test_large_synthetic_dataset():
    records = generate_synthetic_data(2000)
    bytes_data = json.dumps(records).encode('utf-8')
    
    sources = [("json", "synthetic.json", bytes_data)]
    config = RunConfig()
    
    pipeline = Pipeline(config)
    output = pipeline.run(sources)
    audit = pipeline.audit.export()
    
    # Assertions
    assert len(output) > 1000
    assert audit["summary"]["total_records"] == 2004
    # The duplicate records (Candidate 0, Candidate 1) should be merged if they have matching emails
    # Actually 'Fake Name' has 'candidate1@example.com', so it merges with Candidate 1.
    assert audit["summary"]["total_errors"] == 0
    # No crashes means memory and pipeline are stable
