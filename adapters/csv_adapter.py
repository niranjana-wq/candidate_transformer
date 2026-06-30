import csv
import io
from typing import Any
from core.models import RawRecord
from adapters.base import BaseAdapter, ExtractionError, adapter_registry

class CsvAdapter(BaseAdapter):
    def extract(self, source_identifier: str, source_content: Any) -> list[RawRecord]:
        if not isinstance(source_content, bytes):
            if isinstance(source_content, str):
                source_content = source_content.encode('utf-8')
            else:
                raise ExtractionError(source_identifier, "Invalid source_content type for CSV")

        try:
            # Handle BOM and encoding issues gracefully
            decoded = source_content.decode('utf-8-sig')
        except UnicodeDecodeError as e:
            raise ExtractionError(source_identifier, "Encoding issue: must be UTF-8", {"error": str(e)})

        if not decoded.strip():
            raise ExtractionError(source_identifier, "CSV file is empty")

        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(decoded[:1024])
        except csv.Error:
            dialect = csv.excel # Fallback to standard comma separated

        reader = csv.DictReader(io.StringIO(decoded), dialect=dialect)
        
        records = []
        for i, row in enumerate(reader):
            if not any(row.values()): # Skip entirely empty ragged rows
                continue
            
            # csv.DictReader maps ragged row extra values to a None key. Clean them out.
            clean_row = {k: v for k, v in row.items() if k is not None}
            
            records.append(RawRecord(
                source_type="csv",
                source_identifier=source_identifier,
                record_index=i,
                raw_data=clean_row
            ))
            
        return records

adapter_registry.register("csv", CsvAdapter())
