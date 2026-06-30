import pytest
from unittest.mock import patch, MagicMock
from adapters.csv_adapter import CsvAdapter
from adapters.json_adapter import JsonAdapter
from adapters.pdf_adapter import PdfAdapter
from adapters.txt_adapter import TxtAdapter
from adapters.github_adapter import GithubAdapter
from adapters.linkedin_adapter import LinkedinAdapter
from adapters.base import ExtractionError

def test_csv_adapter_extract():
    adapter = CsvAdapter()
    bytes_data = b"candidate_name,email\nAlice,alice@test.com\nBob,bob@test.com"
    records = adapter.extract("test.csv", bytes_data)
    
    assert len(records) == 2
    assert records[0].source_type == "csv"
    assert records[0].raw_data["candidate_name"] == "Alice"
    assert records[1].raw_data["candidate_name"] == "Bob"
    assert records[0].record_index == 0
    assert records[1].record_index == 1

def test_csv_adapter_invalid():
    adapter = CsvAdapter()
    with pytest.raises(ExtractionError):
        # Malformed CSV parsing shouldn't fail the program, but raise ExtractionError
        # Actually standard python csv handles almost anything, but let's test a DecodeError
        adapter.extract("test.csv", b"\xff\xfe")

def test_json_adapter_extract():
    adapter = JsonAdapter()
    # Test array of objects
    bytes_data = b'[{"name":"Alice"},{"name":"Bob"}]'
    records = adapter.extract("test.json", bytes_data)
    
    assert len(records) == 2
    assert records[0].raw_data["name"] == "Alice"
    assert records[1].record_index == 1 # 0-indexed or 1-indexed based on implementation
    
    # Test single object
    bytes_data_single = b'{"name":"Charlie"}'
    records_single = adapter.extract("test2.json", bytes_data_single)
    assert len(records_single) == 1
    assert records_single[0].raw_data["name"] == "Charlie"

def test_json_adapter_invalid():
    adapter = JsonAdapter()
    with pytest.raises(ExtractionError):
        adapter.extract("test.json", b"not-json")

def test_txt_adapter_extract():
    adapter = TxtAdapter()
    bytes_data = b"Name: Alice\nEmail: alice@test.com"
    records = adapter.extract("test.txt", bytes_data)
    assert len(records) == 1
    assert "Name: Alice" in records[0].raw_data["extracted_text"]

@patch('adapters.github_adapter.requests')
def test_github_adapter_extract(mock_requests):
    import requests
    adapter = GithubAdapter()
    
    # Mock successful response
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"name": "Alice", "bio": "Dev"}
    mock_requests.get.return_value = mock_resp
    
    records = adapter.extract("https://github.com/alice", None)
    assert len(records) == 1
    assert records[0].source_type == "github"
    assert records[0].raw_data["name"] == "Alice"
    
    # Mock timeout/failure
    mock_requests.get.side_effect = requests.RequestException("Timeout")
    mock_requests.RequestException = requests.RequestException
    with pytest.raises(ExtractionError):
        adapter.extract("https://github.com/alice", None)

def test_linkedin_adapter_extract():
    adapter = LinkedinAdapter()
    bytes_data = b'{"full_name":"Alice"}'
    records = adapter.extract("https://linkedin.com/in/alice", bytes_data)
    assert len(records) == 1
    assert records[0].source_type == "linkedin"
    assert records[0].raw_data["full_name"] == "Alice"

def test_pdf_adapter_extract():
    # We won't test PyPDF2 byte parsing deeply here, but we can test bad bytes
    adapter = PdfAdapter()
    with pytest.raises(ExtractionError):
        adapter.extract("test.pdf", b"not-a-pdf")
