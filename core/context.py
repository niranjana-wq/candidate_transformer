from typing import Any
from core.models import RunConfig, ProvenanceEntry

class PipelineContext:
    """
    Per-run execution context.
    Stores the loaded configuration, a reference to the audit logger, runtime metadata,
    and accumulated provenance trails.
    
    Contains NO business logic; strictly maintains state across the pipeline stages.
    """
    
    def __init__(self, config: RunConfig, audit_logger: Any = None):
        """
        Initialize the pipeline context.
        
        Args:
            config: The runtime configuration (RunConfig).
            audit_logger: Reference to the AuditLogger instance (typed as Any to avoid circular dependencies).
        """
        self.config = config
        self.audit_logger = audit_logger
        self.run_metadata: dict[str, Any] = {}
        
        # Maps a canonical candidate_id to their list of provenance entries
        self._provenance_accumulation: dict[str, list[ProvenanceEntry]] = {}

    def add_provenance(self, candidate_id: str, entry: ProvenanceEntry) -> None:
        """
        Accumulates a provenance entry for a specific candidate during conflict resolution.
        """
        if candidate_id not in self._provenance_accumulation:
            self._provenance_accumulation[candidate_id] = []
        self._provenance_accumulation[candidate_id].append(entry)

    def get_provenance(self, candidate_id: str) -> list[ProvenanceEntry]:
        """
        Retrieves the accumulated provenance entries for a specific candidate.
        """
        return self._provenance_accumulation.get(candidate_id, [])

    def finalize_provenance(self, candidate_id: str) -> list[ProvenanceEntry]:
        """
        Returns the final provenance list for a candidate. 
        Absorbs what would have been a separate provenance/tracker.py per the design decisions.
        """
        return self.get_provenance(candidate_id)
