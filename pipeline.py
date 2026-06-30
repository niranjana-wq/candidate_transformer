import hashlib
from typing import List, Dict, Any, Tuple
from core.models import RunConfig, CanonicalRecord, RawRecord
from core.context import PipelineContext
from adapters.base import adapter_registry, ExtractionError
import adapters.csv_adapter
import adapters.json_adapter
import adapters.pdf_adapter
import adapters.txt_adapter
import adapters.github_adapter
import adapters.linkedin_adapter
from transform.mapper import SchemaMapper
import transform.default_mappings  # Register mappings before pipeline starts
from transform.normalize import FieldNormalizer
from transform.validator import SchemaValidator
from resolve.matcher import EntityMatcher
from resolve.merger import EntityMerger
from projection.projector import Projector, ProjectionError
from audit import AuditLogger

class Pipeline:
    """
    Single orchestrator of the application. 
    Coordinates execution strictly in the finalized order. Contains ZERO business logic.
    """
    def __init__(self, config: RunConfig):
        self.config = config
        self.audit = AuditLogger(config)
        self.context = PipelineContext(config, self.audit)
        
        # Fail fast on projection config validation
        try:
            Projector.validate_config(config)
        except ProjectionError as e:
            raise ValueError(f"Projection configuration invalid: {str(e)}")

    def run(self, sources: List[Tuple[str, str, Any]]) -> List[Dict[str, Any]]:
        # 1. Extraction Layer
        all_raw_records: List[RawRecord] = []
        for src_type, src_id, content in sources:
            try:
                adapter = adapter_registry.get(src_type)
                if not adapter:
                    self.audit.log_error("adapter_missing", {"source_type": src_type}, source=src_id)
                    continue
                records = adapter.extract(src_id, content)
                all_raw_records.extend(records)
                self.audit.log_info("extraction_success", {"count": len(records)}, source=src_id)
                
            except ExtractionError as e:
                self.audit.log_quarantine(src_id, e.reason, e.details)
            except Exception as e:
                self.audit.log_quarantine(src_id, f"Unexpected extraction failure: {str(e)}")

        valid_canonical_records: List[Tuple[str, str, CanonicalRecord, int]] = []
        
        for raw in all_raw_records:
            # 2. Schema Mapping
            mapped = SchemaMapper.map_record(raw.source_type, raw.raw_data)
            
            # 3. Normalization Orchestration
            normalized = self._normalize(mapped)
            
            # 4. Validation
            val_result = SchemaValidator.validate(normalized, CanonicalRecord)
            if val_result.is_valid:
                valid_canonical_records.append((raw.source_type, raw.source_identifier, val_result.validated_data, raw.record_index or 0))
                self.audit.log_info("validation_success", {}, source=raw.source_identifier)
            else:
                issues = [{"field": i.field, "error": i.error} for i in val_result.issues]
                self.audit.log_warning("validation_failure", {"issues": issues}, source=raw.source_identifier)

        if not valid_canonical_records:
            return []

        # 5. Entity Resolution (Matching)
        records_only = [r[2] for r in valid_canonical_records]
        clusters, ambiguities = EntityMatcher.match_records(records_only, self.config)
        
        for amb in ambiguities:
            self.audit.log_warning("ambiguous_match", amb)

        final_outputs = []
        
        # 6. Conflict Resolution (Merging) & Projection
        for cluster_indices in clusters:
            # Strip record_index when passing to Merger to respect its signature
            cluster_records = [(valid_canonical_records[i][0], valid_canonical_records[i][1], valid_canonical_records[i][2]) for i in cluster_indices]
            
            # Deterministic Candidate ID generation based on sorted source identifiers and record indices
            source_fingerprint = ",".join(sorted(f"{valid_canonical_records[i][0]}:{valid_canonical_records[i][1]}:{valid_canonical_records[i][3]}" for i in cluster_indices))
            candidate_id = hashlib.sha256(source_fingerprint.encode()).hexdigest()[:12]
            
            # Conflict Resolution
            final_record, audit_summary = EntityMerger.merge_cluster(candidate_id, cluster_records, self.config)
            self.audit.log_info("merge_success", audit_summary, candidate_id=candidate_id)
            
            # Projection
            try:
                projected = Projector.project(final_record, self.config)
                final_outputs.append(projected)
            except ProjectionError as e:
                self.audit.log_error("projection_failure", {"error": str(e)}, candidate_id=candidate_id)
                
        return final_outputs

    def _normalize(self, mapped: Dict[str, Any]) -> Dict[str, Any]:
        """Iteratively applies the structural normalizer layer. Never defines the business rules."""
        norm = {}
        for k, v in mapped.items():
            if k == "full_name":
                norm[k] = FieldNormalizer.normalize_field("name", v).value
            elif k in ("emails", "phones", "skills"):
                # Structurally coerce flat adapter strings into canonical arrays
                items = v if isinstance(v, list) else ([v] if v else [])
                processed_items = []
                for item in items:
                    if isinstance(item, str) and ',' in item:
                        processed_items.extend([x.strip() for x in item.split(',')])
                    else:
                        processed_items.append(item)
                        
                norm_type = {"emails": "email", "phones": "phone", "skills": "skill"}[k]
                normalized_items = [FieldNormalizer.normalize_field(norm_type, i).value for i in processed_items]
                norm[k] = [x for x in normalized_items if x]
            elif k == "location" and isinstance(v, dict):
                loc = v.copy()
                if "country" in loc:
                    loc["country"] = FieldNormalizer.normalize_field("country", loc["country"]).value
                norm[k] = loc
            elif k == "experience":
                norm[k] = FieldNormalizer.normalize_field("experience", v).value
                if norm[k]:
                    from transform.normalize import enrich_years_experience
                    yoe = enrich_years_experience(norm[k])
                    if yoe is not None and "years_experience" not in norm:
                        norm["years_experience"] = yoe
            elif k == "education":
                norm[k] = FieldNormalizer.normalize_field("education", v).value
            else:
                norm[k] = v
        return norm
