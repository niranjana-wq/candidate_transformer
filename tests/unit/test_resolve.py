import pytest
from resolve.matcher import EntityMatcher
from resolve.merger import EntityMerger
from core.models import CanonicalRecord, Links, Experience, RunConfig

# --- MATCHER TESTS ---

def test_matcher_same_email_diff_phone():
    r1 = CanonicalRecord(emails=["test@test.com"], phones=["111"])
    r2 = CanonicalRecord(emails=["test@test.com"], phones=["222"])
    clusters, _ = EntityMatcher.match_records([r1, r2])
    assert len(clusters) == 1
    assert set(clusters[0]) == {0, 1}

def test_matcher_same_phone_diff_email():
    r1 = CanonicalRecord(emails=["a@test.com"], phones=["111"])
    r2 = CanonicalRecord(emails=["b@test.com"], phones=["111"])
    clusters, _ = EntityMatcher.match_records([r1, r2])
    assert len(clusters) == 1
    assert set(clusters[0]) == {0, 1}

def test_matcher_same_github_diff_email():
    r1 = CanonicalRecord(emails=["a@test.com"], links=Links(github="git/j"))
    r2 = CanonicalRecord(emails=["b@test.com"], links=Links(github="git/j"))
    clusters, _ = EntityMatcher.match_records([r1, r2])
    assert len(clusters) == 1
    assert set(clusters[0]) == {0, 1}

def test_matcher_same_linkedin_diff_phone():
    r1 = CanonicalRecord(phones=["111"], links=Links(linkedin="li/j"))
    r2 = CanonicalRecord(phones=["222"], links=Links(linkedin="li/j"))
    clusters, _ = EntityMatcher.match_records([r1, r2])
    assert len(clusters) == 1
    assert set(clusters[0]) == {0, 1}

def test_matcher_transitive_clustering():
    # r1 and r2 share email. r2 and r3 share phone. All 3 should cluster.
    r1 = CanonicalRecord(emails=["test@test.com"], phones=["111"])
    r2 = CanonicalRecord(emails=["test@test.com"], phones=["222"])
    r3 = CanonicalRecord(emails=["other@test.com"], phones=["222"])
    clusters, _ = EntityMatcher.match_records([r1, r2, r3])
    assert len(clusters) == 1
    assert set(clusters[0]) == {0, 1, 2}

def test_matcher_fuzzy_multiple_above_threshold():
    # Floating record that fuzzy matches multiple anchors should remain singleton
    # Anchor 1: Johnathon Dae at Google
    a1 = CanonicalRecord(emails=["a@test.com"], full_name="Johnathon Dae", experience=[Experience(company="Google")])
    # Anchor 2: Johnathon Boe at Google
    a2 = CanonicalRecord(emails=["b@test.com"], full_name="Johnathon Boe", experience=[Experience(company="Google")])
    # Floating: Johnathon Doe at Google (fuzzy matches both > 85%)
    f = CanonicalRecord(full_name="Johnathon Doe", experience=[Experience(company="Google")])
    
    clusters, ambiguities = EntityMatcher.match_records([a1, a2, f])
    
    assert len(clusters) == 3 # Should not merge f into either because of ambiguity
    assert len(ambiguities) == 1

def test_matcher_false_split_preference():
    # Just basic test: if no deterministic anchor match and no fuzzy match, split is preferred
    r1 = CanonicalRecord(emails=["a@test.com"], full_name="John Doe")
    r2 = CanonicalRecord(emails=["b@test.com"], full_name="John Doe")
    clusters, _ = EntityMatcher.match_records([r1, r2])
    assert len(clusters) == 2


# --- MERGER TESTS ---

def test_merger_source_priority():
    # resume > json
    r1 = ("json", "1", CanonicalRecord(full_name="JSON Name"))
    r2 = ("resume", "2", CanonicalRecord(full_name="Resume Name"))
    
    merged, audit = EntityMerger.merge_cluster("cand1", [r1, r2], RunConfig())
    assert merged.full_name == "Resume Name"
    assert audit["field_decisions"]["full_name"]["winning_source"] == "resume"

def test_merger_null_never_overrides():
    # resume has priority but name is null
    r1 = ("json", "1", CanonicalRecord(full_name="JSON Name"))
    r2 = ("resume", "2", CanonicalRecord(full_name=None))
    
    merged, audit = EntityMerger.merge_cluster("cand1", [r1, r2], RunConfig())
    assert merged.full_name == "JSON Name"
    assert audit["field_decisions"]["full_name"]["winning_source"] == "json"

def test_merger_agreement_bonus_cap():
    # json base is 0.92, 4 agreements would be +0.08, capped at +0.05 => 0.97
    r_json = ("json", "1", CanonicalRecord(full_name="Same"))
    others = [("csv", str(i), CanonicalRecord(full_name="Same")) for i in range(2, 6)]
    
    merged, audit = EntityMerger.merge_cluster("cand1", [r_json] + others, RunConfig())
    dec = audit["field_decisions"]["full_name"]
    assert dec["agreement_bonus"] == 0.05
    assert dec["final_field_confidence"] == 0.97

def test_merger_tier_conflicts():
    # Tier 1: full_name (0.15)
    # Tier 2: years_experience (0.08)
    # Tier 3: headline (0.03)
    r1 = ("resume", "1", CanonicalRecord(full_name="A", years_experience=5.0, headline="Dev"))
    r2 = ("json", "2", CanonicalRecord(full_name="B", years_experience=6.0, headline="Engineer"))
    
    merged, audit = EntityMerger.merge_cluster("cand1", [r1, r2], RunConfig())
    dec_name = audit["field_decisions"]["full_name"]
    assert dec_name["conflict_penalty"] == 0.15
    
    dec_exp = audit["field_decisions"]["years_experience"]
    assert dec_exp["conflict_penalty"] == 0.08
    
    dec_head = audit["field_decisions"]["headline"]
    assert dec_head["conflict_penalty"] == 0.03

def test_merger_multiple_conflicts():
    r1 = ("resume", "1", CanonicalRecord(full_name="A"))
    r2 = ("json", "2", CanonicalRecord(full_name="B"))
    r3 = ("csv", "3", CanonicalRecord(full_name="C"))
    merged, audit = EntityMerger.merge_cluster("1", [r1, r2, r3], RunConfig())
    # Penalty doesn't compound per conflict item, just if conflict > 0
    assert audit["field_decisions"]["full_name"]["conflict_penalty"] == 0.15
    assert audit["field_decisions"]["full_name"]["conflict_count"] == 2

def test_merger_overall_confidence():
    r1 = ("resume", "1", CanonicalRecord(full_name="A", emails=["a@b.com"])) # resume base 0.95
    merged, audit = EntityMerger.merge_cluster("cand1", [r1], RunConfig())
    assert merged.overall_confidence == 0.95
    
    r2 = ("json", "2", CanonicalRecord(full_name="A", emails=["c@d.com"])) 
    # full_name: agreement +0.02 -> 0.97
    # emails: conflict -0.15 -> 0.80
    # overall: (0.97 + 0.80) / 2 = 0.885
    merged2, audit2 = EntityMerger.merge_cluster("cand2", [r1, r2], RunConfig())
    assert merged2.overall_confidence == 0.885

def test_merger_empty_excluded_from_confidence():
    # Only full_name is populated, should just be full_name score
    r1 = ("resume", "1", CanonicalRecord(full_name="A"))
    merged, audit = EntityMerger.merge_cluster("cand1", [r1], RunConfig())
    assert merged.overall_confidence == 0.95
    assert audit["fields_populated"] == 1

def test_merger_provenance():
    r1 = ("resume", "1", CanonicalRecord(full_name="A"))
    r2 = ("json", "2", CanonicalRecord(full_name="A")) # Agreement
    merged, audit = EntityMerger.merge_cluster("cand1", [r1, r2], RunConfig())
    
    prov = merged.provenance
    assert len(prov) == 1
    assert prov[0].field == "full_name"
    assert prov[0].source == "resume"
    assert prov[0].method == "agreement"
