from typing import Any
from core.models import RawRecord
from adapters.base import BaseAdapter, ExtractionError, adapter_registry

try:
    import requests
except ImportError:
    requests = None

class GithubAdapter(BaseAdapter):
    def extract(self, source_identifier: str, source_content: Any) -> list[RawRecord]:
        if not requests:
            raise ExtractionError(source_identifier, "requests library not installed")

        url = str(source_identifier)
        if "github.com/" not in url:
            raise ExtractionError(source_identifier, "Invalid GitHub URL")

        parts = url.rstrip('/').split('/')
        username = parts[-1]
        
        api_url = f"https://api.github.com/users/{username}"
        
        try:
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 404:
                raise ExtractionError(source_identifier, "GitHub profile not found (404)")
            if response.status_code in (403, 429):
                raise ExtractionError(source_identifier, "GitHub API rate limit exceeded")
                
            response.raise_for_status()
            data = response.json()
            
            return [RawRecord(
                source_type="github",
                source_identifier=source_identifier,
                record_index=0,
                raw_data=data
            )]
            
        except requests.RequestException as e:
            raise ExtractionError(source_identifier, "Network error fetching GitHub profile", {"error": str(e)})

adapter_registry.register("github", GithubAdapter())
