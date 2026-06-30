import jellyfish
import re
from rapidfuzz import fuzz
from typing import List, Dict, Any, Tuple
from core.models import CanonicalRecord, RunConfig

class MatchDecision:
    def __init__(self, idx1: int, idx2: int):
        self.idx1 = idx1
        self.idx2 = idx2
        self.matched_fields = []
        self.field_scores = {}
        self.final_score = 0.0
        self.threshold = 0.0
        self.accepted = False
        self.reason = ""
        
    def to_dict(self):
        return {
            "idx1": self.idx1,
            "idx2": self.idx2,
            "matched_fields": self.matched_fields,
            "field_scores": self.field_scores,
            "final_score": self.final_score,
            "threshold": self.threshold,
            "accepted": self.accepted,
            "reason": self.reason
        }

class EntityMatcher:
    """
    Responsible ONLY for determining which records belong to the same candidate.
    Uses a multi-stage approach: Exact Matching -> Candidate Blocking -> RapidFuzz Scoring.
    """
    
    @staticmethod
    def _extract_blocks(record: CanonicalRecord) -> set[str]:
        blocks = set()
        
        # Name-based blocking
        if record.full_name:
            # Clean name of punctuation like commas
            clean_name = re.sub(r'[^\w\s]', ' ', record.full_name).strip()
            parts = clean_name.split()
            if len(parts) >= 2:
                # To be robust against "Doe Jon" vs "Jon Doe", we can block on both first and last
                p1 = parts[0]
                p2 = parts[-1]
                
                blocks.add(f"NAME:{jellyfish.soundex(p2)}")
                blocks.add(f"NAME:{jellyfish.soundex(p1)}")
                
                blocks.add(f"META:{jellyfish.metaphone(p2)}")
                blocks.add(f"META:{jellyfish.metaphone(p1)}")
                
                # First initial + last name
                blocks.add(f"INIT:{p1[0].upper()}{p2.lower()}")
                blocks.add(f"INIT:{p2[0].upper()}{p1.lower()}")
            elif len(parts) == 1:
                blocks.add(f"NAME:{jellyfish.soundex(parts[0])}")
                blocks.add(f"META:{jellyfish.metaphone(parts[0])}")
                
        # Company blocking
        for exp in record.experience:
            if exp.company:
                comp_norm = "".join(c for c in exp.company.lower() if c.isalnum())
                if comp_norm:
                    blocks.add(f"COMP:{comp_norm[:8]}")
                    
        # Education blocking
        for edu in record.education:
            if edu.institution:
                inst_norm = "".join(c for c in edu.institution.lower() if c.isalnum())
                if inst_norm:
                    blocks.add(f"EDU:{inst_norm[:8]}")
                    
        # Location blocking (City)
        if record.location and record.location.city:
            city_norm = "".join(c for c in record.location.city.lower() if c.isalpha())
            if city_norm:
                blocks.add(f"CITY:{city_norm}")
                
        # Email domain
        for email in record.emails:
            if "@" in email:
                domain = email.split("@")[-1].lower()
                blocks.add(f"DOMAIN:{domain}")
                
        return blocks
        
    def _calculate_similarity(r1: CanonicalRecord, r2: CanonicalRecord, weights: dict[str, float]) -> Tuple[float, dict[str, float], list[str]]:
        scores = {}
        matched = []
        
        # Calculate raw component scores
        comp_scores = {}
        comp_present = {}
        
        # Email
        has_e1 = bool(r1.emails)
        has_e2 = bool(r2.emails)
        comp_present["email"] = has_e1 or has_e2
        if has_e1 and has_e2:
            best = max((fuzz.ratio(e1.lower(), e2.lower()) / 100.0 for e1 in r1.emails for e2 in r2.emails), default=0.0)
            comp_scores["email"] = best
            if best > 0.8: matched.append("email")
        else:
            comp_scores["email"] = 0.0
            
        # Phone
        has_p1 = bool(r1.phones)
        has_p2 = bool(r2.phones)
        comp_present["phone"] = has_p1 or has_p2
        if has_p1 and has_p2:
            p1s = ["".join(c for c in p if c.isdigit()) for p in r1.phones]
            p2s = ["".join(c for c in p if c.isdigit()) for p in r2.phones]
            best = max((fuzz.ratio(p1, p2) / 100.0 for p1 in p1s for p2 in p2s), default=0.0)
            comp_scores["phone"] = best
            if best > 0.8: matched.append("phone")
        else:
            comp_scores["phone"] = 0.0
            
        # Name
        has_n1 = bool(r1.full_name)
        has_n2 = bool(r2.full_name)
        comp_present["name"] = has_n1 or has_n2
        if has_n1 and has_n2:
            best = fuzz.token_set_ratio(r1.full_name.lower(), r2.full_name.lower()) / 100.0
            comp_scores["name"] = best
            if best > 0.8: matched.append("name")
        else:
            comp_scores["name"] = 0.0
            
        # Company
        c1 = [e.company.lower() for e in r1.experience if e.company]
        c2 = [e.company.lower() for e in r2.experience if e.company]
        has_c1 = bool(c1)
        has_c2 = bool(c2)
        comp_present["company"] = has_c1 or has_c2
        if has_c1 and has_c2:
            best = max((fuzz.token_set_ratio(x, y) / 100.0 for x in c1 for y in c2), default=0.0)
            comp_scores["company"] = best
            if best > 0.8: matched.append("company")
        else:
            comp_scores["company"] = 0.0
            
        # Education
        ed1 = [e.institution.lower() for e in r1.education if e.institution]
        ed2 = [e.institution.lower() for e in r2.education if e.institution]
        has_ed1 = bool(ed1)
        has_ed2 = bool(ed2)
        comp_present["education"] = has_ed1 or has_ed2
        if has_ed1 and has_ed2:
            best = max((fuzz.token_set_ratio(x, y) / 100.0 for x in ed1 for y in ed2), default=0.0)
            comp_scores["education"] = best
            if best > 0.8: matched.append("education")
        else:
            comp_scores["education"] = 0.0
            
        # Location
        l1 = bool(r1.location and r1.location.city)
        l2 = bool(r2.location and r2.location.city)
        comp_present["location"] = l1 or l2
        if l1 and l2:
            best = fuzz.ratio(r1.location.city.lower(), r2.location.city.lower()) / 100.0
            comp_scores["location"] = best
            if best > 0.8: matched.append("location")
        else:
            comp_scores["location"] = 0.0
            
        final_score = 0.0
        
        for field, best in comp_scores.items():
            final_score += best * weights.get(field, 0.0)
            scores[field] = best
            
        # Issue 9: Require at least one strong identifier match (email, phone, or name)
        # to prevent spurious merges from weak fields like location/company.
        strong_match = False
        if comp_scores.get("email", 0) > 0.8: strong_match = True
        if comp_scores.get("phone", 0) > 0.8: strong_match = True
        if comp_scores.get("name", 0) > 0.8: strong_match = True
        
        if not strong_match:
            # If no strong match, penalize heavily to prevent merging based only on company/location
            final_score *= 0.5
                
        return final_score, scores, matched

    def match_records(records: List[CanonicalRecord], config: RunConfig = None) -> Tuple[List[List[int]], List[Dict[str, Any]]]:
        if config is None:
            config = RunConfig()
            
        n = len(records)
        parent = list(range(n))

        def find(i: int) -> int:
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]

        def union(i: int, j: int) -> None:
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j

        decisions = []

        # STAGE 1: Exact Matching
        email_map: Dict[str, int] = {}
        phone_map: Dict[str, int] = {}
        github_map: Dict[str, int] = {}
        linkedin_map: Dict[str, int] = {}

        for i, record in enumerate(records):
            for email in record.emails:
                email_lower = email.lower()
                if email_lower in email_map:
                    union(i, email_map[email_lower])
                else:
                    email_map[email_lower] = i
            
            for phone in record.phones:
                # Remove digits
                p_norm = "".join(c for c in phone if c.isdigit())
                if p_norm:
                    if p_norm in phone_map:
                        union(i, phone_map[p_norm])
                    else:
                        phone_map[p_norm] = i
                    
            github = record.links.github if record.links else None
            if github:
                github_lower = github.lower()
                if github_lower in github_map:
                    union(i, github_map[github_lower])
                else:
                    github_map[github_lower] = i
                    
            linkedin = record.links.linkedin if record.links else None
            if linkedin:
                linkedin_lower = linkedin.lower()
                if linkedin_lower in linkedin_map:
                    union(i, linkedin_map[linkedin_lower])
                else:
                    linkedin_map[linkedin_lower] = i

        # STAGE 2: Candidate Blocking
        cluster_blocks = {i: set() for i in range(n) if find(i) == i}
        for i, record in enumerate(records):
            root = find(i)
            cluster_blocks[root].update(EntityMatcher._extract_blocks(record))
            
        block_to_roots = {}
        for root, keys in cluster_blocks.items():
            for k in keys:
                if k not in block_to_roots:
                    block_to_roots[k] = []
                block_to_roots[k].append(root)

        # STAGE 3: Fuzzy Matching & Scoring
        threshold = config.match_threshold
        weights = config.match_weights
        
        compared = set()
        
        for k, roots in block_to_roots.items():
            if len(roots) < 2:
                continue
                
            for i in range(len(roots)):
                for j in range(i + 1, len(roots)):
                    r1 = find(roots[i])
                    r2 = find(roots[j])
                    if r1 == r2:
                        continue
                        
                    pair = tuple(sorted((r1, r2)))
                    if pair in compared:
                        continue
                    compared.add(pair)
                    
                    max_score = 0.0
                    best_scores = {}
                    best_matched = []
                    
                    members1 = [idx for idx in range(n) if find(idx) == r1]
                    members2 = [idx for idx in range(n) if find(idx) == r2]
                    
                    for m1 in members1:
                        for m2 in members2:
                            score, f_scores, matched = EntityMatcher._calculate_similarity(records[m1], records[m2], weights)
                            if score > max_score:
                                max_score = score
                                best_scores = f_scores
                                best_matched = matched
                                
                    decision = MatchDecision(r1, r2)
                    decision.matched_fields = best_matched
                    decision.field_scores = best_scores
                    decision.final_score = max_score
                    decision.threshold = threshold
                    
                    if max_score >= threshold:
                        decision.accepted = True
                        decision.reason = f"Score {max_score:.3f} >= {threshold:.3f}. Block: {k}"
                        union(r1, r2)
                    else:
                        decision.accepted = False
                        decision.reason = f"Score {max_score:.3f} < {threshold:.3f}. Block: {k}"
                        
                    decisions.append(decision.to_dict())

        # Form Final Clusters
        final_clusters_dict = {}
        for i in range(n):
            root = find(i)
            if root not in final_clusters_dict:
                final_clusters_dict[root] = []
            final_clusters_dict[root].append(i)

        final_clusters = list(final_clusters_dict.values())
        return final_clusters, decisions
