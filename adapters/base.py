from abc import ABC, abstractmethod
from typing import Any
from core.models import RawRecord
from core.registry import Registry

class ExtractionError(Exception):
    """
    Raised when an entire source is unparseable or inaccessible.
    Provides structured data for the audit logger to quarantine the source.
    """
    def __init__(self, source_identifier: str, reason: str, details: dict | None = None):
        self.source_identifier = source_identifier
        self.reason = reason
        self.details = details or {}
        super().__init__(f"Extraction failed for {source_identifier}: {reason}")

class BaseAdapter(ABC):
    """
    The strict contract for all data extraction components.
    Adapters are purely extraction mechanisms. No mapping, normalizing, or business logic.
    """
    
    @abstractmethod
    def extract(self, source_identifier: str, source_content: Any) -> list[RawRecord]:
        """
        Extracts data from the raw source content.
        
        Args:
            source_identifier: Unique ID for the source (filename, URL, etc.)
            source_content: The raw bytes, string, or fixture data to parse.
            
        Returns:
            A list of RawRecord objects.
            
        Raises:
            ExtractionError: If the source cannot be processed.
        """
        pass

# Registry to hold all instantiated adapters
adapter_registry = Registry[BaseAdapter]("Adapters")
