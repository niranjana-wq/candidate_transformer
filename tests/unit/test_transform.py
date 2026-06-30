import pytest
from transform.mapper import SchemaMapper, mapping_registry
from transform.normalize import FieldNormalizer, NormalizationResult
from transform.validator import SchemaValidator
from core.models import CanonicalRecord

def test_mapper_path_translation():
    # Setup test mapping
    test_mapping = {
        "native_name": "full_name",
        "phone": "phones.0"
    }
    mapping_registry.register("test_src", test_mapping)
    
    raw = {
        "native_name": "Alice",
        "phone": "1234",
        "unknown_field": "ignore"
    }
    
    mapped = SchemaMapper.map_record("test_src", raw)
    
    assert mapped["full_name"] == "Alice"
    assert mapped["phones"]["0"] == "1234"
    assert "unknown_field" not in mapped

def test_mapper_unknown_source():
    # If source not registered, should return empty dict
    assert SchemaMapper.map_record("unknown_source", {"a": 1}) == {}

def test_normalizer_name():
    assert FieldNormalizer.normalize_field("name", " john DOE ").value == "John Doe"
    assert FieldNormalizer.normalize_field("name", 123).error is not None

def test_normalizer_email():
    assert FieldNormalizer.normalize_field("email", " TEST@Example.com ").value == "test@example.com"
    assert FieldNormalizer.normalize_field("email", "invalid-email").error is not None
    assert FieldNormalizer.normalize_field("email", "invalid-email").value is None

def test_normalizer_phone():
    # Standard format
    assert FieldNormalizer.normalize_field("phone", "+44 7911 123456").value == "+447911123456"
    
    # Missing country code without default region
    res = FieldNormalizer.normalize_field("phone", "7911 123456")
    assert res.value is None
    assert "Phone missing country code" in res.error
    
    # Missing country code WITH default region
    res_region = FieldNormalizer.normalize_field("phone", "7911 123456", default_region="GB")
    assert res_region.value == "+447911123456"

def test_normalizer_date():
    # Y2K deterministic fixed date
    res = FieldNormalizer.normalize_field("date", "Oct 12")
    assert res.value == "2000-10"

def test_normalizer_country():
    assert FieldNormalizer.normalize_field("country", " us ").value == "US"
    res = FieldNormalizer.normalize_field("country", "USA")
    assert res.value is None
    assert "ISO-3166 alpha-2" in res.error

def test_validator():
    # Valid dict
    valid_dict = {
        "full_name": "Alice",
        "emails": ["alice@test.com"]
    }
    res = SchemaValidator.validate(valid_dict, CanonicalRecord)
    assert res.is_valid
    assert res.validated_data.full_name == "Alice"
    
    # Invalid dict (emails must be list)
    invalid_dict = {
        "full_name": "Alice",
        "emails": "alice@test.com"
    }
    res2 = SchemaValidator.validate(invalid_dict, CanonicalRecord)
    assert not res2.is_valid
    assert len(res2.issues) > 0
    assert res2.validated_data is None
