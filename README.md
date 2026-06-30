# Multi-Source Candidate Data Transformer

**Eightfold Engineering Intern Assignment (Jul-Dec 2026)**

## Overview
A deterministic ETL/MDM pipeline that ingests candidate data from multiple heterogeneous sources (structured: recruiter CSV, ATS JSON; unstructured: GitHub, LinkedIn, resume files, recruiter notes) and produces one clean canonical candidate profile per person.

## Key Features
- ✅ Deterministic processing (same inputs → same outputs)
- ✅ Robust error handling (bad sources don't crash pipeline)
- ✅ Explainable provenance and confidence scoring
- ✅ Runtime-configurable projection layer (reshapes output via JSON config)
- ✅ Strict separation: canonical record vs. projection layer
- ✅ Plugin/registry architecture (extensible without modifying core)

## Architecture Decisions (FIXED)
1. **12-stage linear pipeline**: Input validation → Source detection → Extraction → Schema mapping → Cleaning → Normalization → Internal validation → Entity resolution → Conflict resolution → Confidence scoring → Provenance finalization → Projection → Output validation → Audit logging
2. **Source priority order**: Resume > JSON/ATS > CSV > LinkedIn > GitHub (fixed business rule)
3. **Confidence scoring**: Tier-based additive model (see DECISIONS.md)
4. **Entity resolution**: Separate from conflict resolution (matcher.py vs merger.py)
5. **Projection**: Runtime JSON config reshapes canonical record without code changes

## Project Structure
```
candidate-transformer/
├── README.md
├── requirements.txt
├── main.py
├── pipeline.py
├── audit.py
├── config/
│   ├── default_config.json
│   └── examples/
│       └── custom_config.json
├── core/
│   ├── models.py
│   ├── registry.py
│   └── context.py
├── adapters/
│   ├── base.py
│   ├── csv_adapter.py
│   ├── json_adapter.py
│   ├── pdf_adapter.py
│   ├── txt_adapter.py
│   ├── github_adapter.py
│   └── linkedin_adapter.py
├── transform/
│   ├── mapper.py
│   ├── normalize.py
│   └── validator.py
├── resolve/
│   ├── matcher.py          # Entity resolution ONLY
│   └── merger.py           # Conflict resolution + confidence scoring
├── projection/
│   └── projector.py
├── samples/
│   ├── inputs/
│   └── outputs/
└── tests/
    └── test_core.py
```

## Implementation Status
**100% in design phase** - Zero implementation code written. Next concrete step is implementation starting with core/, adapters/base.py, and simplest adapters (CSV, JSON).

## Running the Project

### CLI Usage

The system exposes a Thin CLI (`main.py`) to run and manage the pipeline.

```bash
# Install dependencies
pip install -r requirements.txt

# 1. Run the complete pipeline

**Method A: Explicit Paths**
```bash
python main.py run \
    --csv samples/v1/inputs/recruiter_csv.csv \
    --json samples/v1/inputs/ATS_info.json \
    --pdf samples/v1/inputs/resume/pdf \
    --output outputs/result.json \
    --config config/default_config.json
```

**Method B: Input Configuration File**
```bash
# Pass all inputs via a single config file
python main.py run --input-config configs/input_config.json

# CLI arguments override config file values
python main.py run \
    --input-config configs/input_config.json \
    --output outputs/custom_result.json
```

# 2. Validate the generated dataset
python main.py validate --input samples/v1/inputs

# 3. Run benchmarks
python main.py benchmark

# 4. Generate datasets (with mutations)
python main.py generate-dataset --scale 100 --difficulty medium --seed 42
```

## Test Suite
Run the minimal 4-test suite:
```bash
pytest tests/test_core.py -v
```

## Design Constraints (From Assignment Brief)
- ~6-hour implementation budget
- Config loading must be architecturally separate from data pipeline
- Canonical record and projected output must remain strictly separated
- Deterministic and explainable over sophisticated
- Honest scoping over silent gaps
- CLI is sufficient (lower priority per brief)

## Known Limitations (Documented)
- No OCR for scanned/image-only PDF resumes
- No true multi-candidate splitting within single PDF/notes file
- LinkedIn adapter uses static/fixture-based payload (not live scraping)
- Entry-level (sub-record) merging for experience/education deferred to future work
- Stress-test scale validation not performed (conceptual only)

## DECISIONS.md
See DECISIONS.md for fully locked architectural decisions including:
- Exact confidence scoring formula and constants
- Source priority order
- Entity resolution matching policy
- All other FINALIZED architectural choices

---
*This document serves as the single source of truth for continuing implementation. Refer to the Project Knowledge Transfer Document for full design rationale and context.*