import json
from typing import Any
from core.models import RawRecord
from adapters.base import BaseAdapter, ExtractionError, adapter_registry

class LinkedinAdapter(BaseAdapter):
    def extract(self, source_identifier: str, source_content: Any) -> list[RawRecord]:
        """
        Since live scraping is out of scope, source_content is expected to be a 
        JSON fixture mapping to the LinkedIn profile for this URL.
        """
        if "linkedin.com/in/" not in source_identifier:
            raise ExtractionError(source_identifier, "Invalid LinkedIn URL")

        data = None
        if isinstance(source_content, str):
            try:
                data = json.loads(source_content)
            except json.JSONDecodeError as e:
                raise ExtractionError(source_identifier, "Malformed LinkedIn fixture JSON", {"error": str(e)})
        elif isinstance(source_content, dict):
            data = source_content
        elif isinstance(source_content, bytes):
             try:
                 data = json.loads(source_content.decode('utf-8'))
             except Exception as e:
                 raise ExtractionError(source_identifier, "Malformed LinkedIn fixture bytes", {"error": str(e)})

        if not data:
            raise ExtractionError(source_identifier, "LinkedIn fixture data is missing or invalid")

        return [RawRecord(
            source_type="linkedin",
            source_identifier=source_identifier,
            record_index=0,
            raw_data=data
        )]

adapter_registry.register("linkedin", LinkedinAdapter())
