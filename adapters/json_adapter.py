import json
from typing import Any
from core.models import RawRecord
from adapters.base import BaseAdapter, ExtractionError, adapter_registry

class JsonAdapter(BaseAdapter):
    def extract(self, source_identifier: str, source_content: Any) -> list[RawRecord]:
        if isinstance(source_content, bytes):
            try:
                source_content = source_content.decode('utf-8')
            except UnicodeDecodeError as e:
                raise ExtractionError(source_identifier, "Encoding issue: must be UTF-8", {"error": str(e)})

        if isinstance(source_content, str):
            try:
                data = json.loads(source_content)
            except json.JSONDecodeError as e:
                raise ExtractionError(source_identifier, "Malformed JSON", {"error": str(e)})
        else:
            data = source_content

        if not isinstance(data, (dict, list)):
            raise ExtractionError(source_identifier, "JSON must be an object or array of objects")

        records = []
        if isinstance(data, dict):
            # Single object
            records.append(RawRecord(
                source_type="json",
                source_identifier=source_identifier,
                record_index=0,
                raw_data=data
            ))
        else:
            # Array of objects
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    records.append(RawRecord(
                        source_type="json",
                        source_identifier=source_identifier,
                        record_index=i,
                        raw_data=item
                    ))
        
        return records

adapter_registry.register("json", JsonAdapter())
