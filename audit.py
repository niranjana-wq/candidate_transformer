from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from core.models import RunConfig, AuditEntry

class AuditLogger:
    """
    Responsible ONLY for recording execution events and summarizing the run.
    Never makes business decisions.
    """
    def __init__(self, run_config: RunConfig):
        self.config = run_config
        self.entries: List[AuditEntry] = []
        # ISO format used strictly for logging/observability; does not impact business determinism
        self.start_time = datetime.now(timezone.utc).isoformat()
        
    def log(self, level: str, action: str, details: Dict[str, Any], candidate_id: Optional[str] = None, source: Optional[str] = None):
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            action=action,
            candidate_id=candidate_id,
            source=source,
            details=details
        )
        self.entries.append(entry)
        
    def log_info(self, action: str, details: Dict[str, Any], **kwargs):
        self.log("INFO", action, details, **kwargs)
        
    def log_warning(self, action: str, details: Dict[str, Any], **kwargs):
        self.log("WARNING", action, details, **kwargs)
        
    def log_error(self, action: str, details: Dict[str, Any], **kwargs):
        self.log("ERROR", action, details, **kwargs)
        
    def log_quarantine(self, source: str, reason: str, details: Optional[Dict[str, Any]] = None):
        d = details or {}
        d["reason"] = reason
        self.log_warning("quarantine", d, source=source)
        
    def export(self) -> Dict[str, Any]:
        end_time = datetime.now(timezone.utc).isoformat()
        
        # Calculate summary exactly as requested without mutating state
        total_processed = len(set(e.source for e in self.entries if e.action in ("extraction_success", "quarantine") and e.source))
        total_records = sum(e.details.get("count", 1) for e in self.entries if e.action == "extraction_success")
        total_merged = sum(1 for e in self.entries if e.action == "merge_success")
        total_quarantined = sum(1 for e in self.entries if e.action == "quarantine")
        total_warn = sum(1 for e in self.entries if e.level == "WARNING")
        total_err = sum(1 for e in self.entries if e.level == "ERROR")
        
        return {
            "run_info": {
                "timestamp": self.start_time,
                "end_time": end_time,
                "pipeline_version": "1.0.0",
                "configuration": self.config.model_dump()
            },
            "summary": {
                "total_sources_processed": total_processed,
                "total_records": total_records,
                "total_merged_candidates": total_merged,
                "total_quarantined_records": total_quarantined,
                "total_warnings": total_warn,
                "total_errors": total_err
            },
            "events": [e.model_dump() for e in self.entries]
        }
