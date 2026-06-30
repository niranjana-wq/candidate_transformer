from typing import List, Dict, Any, Tuple
from core.models import CanonicalRecord, ProvenanceEntry

from core.models import CanonicalRecord, ProvenanceEntry, RunConfig

LOGICAL_FIELDS = [
    ("full_name", 1),
    ("emails", 1),
    ("phones", 1),
    ("links.linkedin", 1),
    ("links.github", 1),
    ("location", 2),
    ("years_experience", 2),
    ("experience", 2),
    ("education", 2),
    ("headline", 3),
    ("skills", 3),
    ("links.portfolio", 3),
    ("links.other", 3)
]

def get_field(record: CanonicalRecord, path: str) -> Any:
    if path.startswith("links."):
        if not record.links: return None
        return getattr(record.links, path.split(".")[1], None)
    return getattr(record, path, None)

def set_field(record: CanonicalRecord, path: str, value: Any) -> None:
    if path.startswith("links."):
        if record.links is None:
            from core.models import Links
            record.links = Links()
        setattr(record.links, path.split(".")[1], value)
    else:
        setattr(record, path, value)

def is_empty(val: Any) -> bool:
    if val is None: return True
    if isinstance(val, (list, dict, str)) and len(val) == 0: return True
    if hasattr(val, 'model_dump'):
        return len(val.model_dump(exclude_none=True)) == 0
    return False

def is_corroborating(path: str, v1: Any, v2: Any) -> bool:
    if v1 == v2:
        return True
    
    if path in ["emails", "phones", "links.other"]:
        return bool(set(v1) & set(v2))
        
    if path == "skills":
        names1 = {s.name.lower() for s in v1 if s.name}
        names2 = {s.name.lower() for s in v2 if s.name}
        return bool(names1 & names2)
        
    if path == "experience":
        comps1 = {e.company.lower() for e in v1 if e.company}
        comps2 = {e.company.lower() for e in v2 if e.company}
        return bool(comps1 & comps2)
        
    if path == "education":
        inst1 = {e.institution.lower() for e in v1 if e.institution}
        inst2 = {e.institution.lower() for e in v2 if e.institution}
        return bool(inst1 & inst2)
        
    if path == "location":
        c1 = v1.country.lower() if v1.country else None
        c2 = v2.country.lower() if v2.country else None
        city1 = v1.city.lower() if v1.city else None
        city2 = v2.city.lower() if v2.city else None
        if c1 and c2 and c1 == c2: return True
        if city1 and city2 and city1 == city2: return True
        return False
        
    if isinstance(v1, str) and isinstance(v2, str):
        return v1.lower() == v2.lower()
        
    return False


class EntityMerger:
    """
    Responsible ONLY for conflict resolution, confidence scoring, provenance, 
    and outputting the final CanonicalRecord for a given cluster.
    """
    
    @staticmethod
    def merge_cluster(candidate_id: str, cluster_records: List[Tuple[str, str, CanonicalRecord]], config: RunConfig) -> Tuple[CanonicalRecord, Dict[str, Any]]:
        """
        Merges a cluster of records into a single CanonicalRecord.
        Returns the finalized CanonicalRecord and a detailed audit summary dict.
        
        Args:
            candidate_id: The ID to assign to the final record.
            cluster_records: list of (source_type, source_identifier, record)
            config: RunConfig containing business rules (priorities, penalties, reliability)
        """
        # 1. Sort by Priority (lowest number = highest priority). 99 for unknown.
        # Stable sort with source_id tiebreaker ensures 100% deterministic behavior even with multiple identical source types.
        def get_priority(src_type):
            try:
                return config.priority_order.index(src_type.lower())
            except ValueError:
                return 99
                
        sorted_cluster = sorted(cluster_records, key=lambda x: (get_priority(x[0]), x[1]))
        
        final_record = CanonicalRecord(candidate_id=candidate_id)
        populated_confidences = []
        
        total_possible_weight = 0.0
        populated_weight_accum = 0.0
        weighted_field_conf_accum = 0.0
        
        audit_decisions = {}
        
        # Pre-calculate total possible weight
        for path, _ in LOGICAL_FIELDS:
            field_weight = config.confidence_field_weights.get(
                path, config.confidence_field_weights.get(path.split('.')[0], 0.0)
            )
            total_possible_weight += field_weight
        
        # 2. Process each logical field
        for path, tier in LOGICAL_FIELDS:
            sources_with_val = []
            for source_type, source_id, rec in sorted_cluster:
                val = get_field(rec, path)
                if not is_empty(val):
                    sources_with_val.append((source_type.lower(), source_id, val))
                    
            if not sources_with_val:
                continue
                
            # Winner is automatically the first item due to prior sorting
            winner_type, winner_id, winner_val = sources_with_val[0]
            
            base_conf = config.reliability.get(winner_type, 0.80)
            agreement_count = 0
            conflict_count = 0
            alt_values = []
            
            # Check remaining sources for corroboration / conflict
            for other_type, other_id, other_val in sources_with_val[1:]:
                if is_corroborating(path, winner_val, other_val):
                    agreement_count += 1
                else:
                    conflict_count += 1
                    # Safely serialize for audit log explainability
                    alt_repr = other_val.model_dump() if hasattr(other_val, 'model_dump') else (
                        [x.model_dump() for x in other_val] if isinstance(other_val, list) and len(other_val)>0 and hasattr(other_val[0], 'model_dump') else other_val
                    )
                    alt_values.append({"source": other_type, "value": alt_repr})
            
            # 3. Confidence Calculation
            field_weight = config.confidence_field_weights.get(
                path, config.confidence_field_weights.get(path.split('.')[0], 0.0)
            )

            # Tier-based penalty — locked values: Tier1=0.15, Tier2=0.08, Tier3=0.03
            TIER_PENALTIES = {1: 0.15, 2: 0.08, 3: 0.03}
            agreement_bonus = min(agreement_count * 0.02, 0.05)  # +0.02 per source, max +0.05
            penalty = TIER_PENALTIES.get(tier, 0.03) if conflict_count > 0 else 0.0
            
            field_conf = base_conf + agreement_bonus - penalty
            field_conf = round(max(0.10, min(1.00, field_conf)), 3)
            
            populated_confidences.append(field_conf)
            
            # Accumulate for overall confidence weighted average
            populated_weight_accum += field_weight
            weighted_field_conf_accum += field_weight * field_conf
            
            # 4. Set winner & Provenance
            
            if path == "skills":
                # Custom merge logic for skills: Union all unique skills across all sources
                skill_map = {}
                for s_type, s_id, s_val in sources_with_val:
                    src_base_conf = config.reliability.get(s_type, 0.80)
                    for skill in s_val:
                        s_name = skill.name.lower()
                        if s_name not in skill_map:
                            skill_map[s_name] = {"sources": set(), "max_base_conf": 0.0, "original_name": skill.name}
                        skill_map[s_name]["sources"].add(s_type)
                        skill_map[s_name]["max_base_conf"] = max(skill_map[s_name]["max_base_conf"], src_base_conf)
                
                merged_skills = []
                for s_name, data in skill_map.items():
                    s_count = len(data["sources"])
                    s_conf = data["max_base_conf"] + min((s_count - 1) * 0.05, 0.15)
                    s_conf = round(max(0.10, min(1.00, s_conf)), 3)
                    
                    from core.models import Skill
                    merged_skills.append(Skill(name=data["original_name"], confidence=s_conf, sources=list(data["sources"])))
                
                set_field(final_record, path, merged_skills)
                winner_val = merged_skills  # For audit log serialization
            else:
                set_field(final_record, path, winner_val)
                    
            method = "priority" if conflict_count > 0 else "agreement"
            if conflict_count == 0 and agreement_count == 0:
                method = "single_source"
                
            final_record.provenance.append(ProvenanceEntry(
                field=path,
                source="Multiple" if path == "skills" else winner_type,
                method="union" if path == "skills" else method,
                confidence=None if path == "skills" else field_conf,
                source_priority=get_priority(winner_type),
                agreement_count=agreement_count
            ))
            
            # 5. Audit Log Explainability
            win_repr = winner_val.model_dump() if hasattr(winner_val, 'model_dump') else (
                [x.model_dump() for x in winner_val] if isinstance(winner_val, list) and len(winner_val)>0 and hasattr(winner_val[0], 'model_dump') else winner_val
            )
            
            audit_decisions[path] = {
                "winning_source": winner_type,
                "winning_value": win_repr,
                "alternative_values_considered": alt_values,
                "reason_selected": f"Highest priority source ({winner_type}) won.",
                "source_reliability": base_conf,
                "agreement_count": agreement_count,
                "agreement_bonus": agreement_bonus,
                "conflict_count": conflict_count,
                "conflict_penalty": penalty,
                "final_field_confidence": field_conf
            }
            
        # Overall Confidence — simple unweighted average of populated fields only
        # Locked rule: clamp to [0.10, 1.00]
        if populated_confidences:
            overall_conf = sum(populated_confidences) / len(populated_confidences)
            final_record.overall_confidence = round(max(0.10, min(1.00, overall_conf)), 3)
        else:
            final_record.overall_confidence = 0.10
            
        audit_summary = {
            "overall_confidence": final_record.overall_confidence,
            "fields_populated": len(populated_confidences),
            "average_field_confidence": round(sum(populated_confidences) / len(populated_confidences), 3) if populated_confidences else 0.0,
            "field_decisions": audit_decisions
        }
        
        return final_record, audit_summary