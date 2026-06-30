from typing import Any
from core.models import RawRecord
from adapters.base import BaseAdapter, ExtractionError, adapter_registry

class TxtAdapter(BaseAdapter):
    def extract(self, source_identifier: str, source_content: Any) -> list[RawRecord]:
        if isinstance(source_content, bytes):
            try:
                decoded = source_content.decode('utf-8-sig').strip()
            except UnicodeDecodeError as e:
                raise ExtractionError(source_identifier, "Encoding issue: must be UTF-8", {"error": str(e)})
        elif isinstance(source_content, str):
            decoded = source_content.strip()
        else:
            raise ExtractionError(source_identifier, "Invalid source_content type for TXT")
            
        if not decoded:
            raise ExtractionError(source_identifier, "TXT file is empty")

        text = decoded.strip()
        
        raw_data = {"extracted_text": text}
        for line in text.split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                raw_data[k.strip().lower()] = v.strip()
                
        return [RawRecord(
            source_type="txt",
            source_identifier=source_identifier,
            record_index=0,
            raw_data=raw_data
        )]

adapter_registry.register("txt", TxtAdapter())
