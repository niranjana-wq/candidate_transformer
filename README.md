# Candidate Transformer

The Candidate Transformer is a data integration pipeline designed to extract, normalize, and merge candidate data from multiple heterogeneous sources. It performs robust entity resolution across structured systems (ATS JSON, Recruiter CSV) and unstructured documents (PDF and DOCX resumes) to generate a single canonical profile per candidate. The pipeline includes complete data provenance tracking and assigns deterministic confidence scores to every resolved field.

---

## Features

- Recruiter CSV support
- ATS JSON support
- Resume PDF support
- Resume DOCX support
- Canonical schema generation
- Entity matching
- Conflict resolution
- Provenance tracking
- Confidence calculation
- Runtime configurable output
- Validation
- Explain CLI
- Benchmark CLI
- Dataset Generation CLI

---

## Architecture

Structured Sources
    CSV
    ATS JSON

Unstructured Sources
    PDF
    DOCX

↓

Extraction

↓

Schema Mapping

↓

Normalization

↓

Entity Resolution

↓

Entity Merger

↓

Projection

↓

Canonical JSON

---

## Repository Structure

```
candidate-transformer/
├── adapters/         # Data extraction adapters for various source formats
├── config/           # Default pipeline runtime configurations
├── configs/          # Input/output path configurations
├── core/             # Canonical schema models and execution context
├── projection/       # JSON output projection formatting
├── resolve/          # Entity matching and merging logic
├── scripts/          # Synthetic dataset generation and benchmarking
├── tests/            # Unit, integration, and end-to-end tests
├── transform/        # Schema mapping and data normalization
├── README.md         # This documentation
├── main.py           # The thin CLI entry point
├── pipeline.py       # The core orchestrator
└── requirements.txt  # Python dependencies
```

---

## Requirements

- Python 3.10+
- pip
- Supported OS: Windows, macOS, Linux

---

## Installation

```bash
git clone https://github.com/niranjana-wq/candidate_transformer.git
cd candidate_transformer
pip install -r requirements.txt
```

---

## Configuration

The CLI supports dedicated configuration files to simplify execution without long command-line arguments.

`configs/input_config.json`
This file stores the file paths for your input sources (CSV, JSON, PDF, DOCX) and your desired output locations (`output` and `audit_output`). Using this file prevents you from needing to manually specify every path on the CLI.

`configs/output_config.json`
This is an isolated configuration file specifically containing only the `output` and `audit_output` paths, useful for strictly controlling where the generated datasets are saved when mixing explicit CLI inputs.

---

## Running the Pipeline

### Using configuration

```bash
python main.py run --input-config configs/input_config.json
```

### Using explicit CLI arguments

```bash
python main.py run \
    --csv samples/v1/inputs/recruiter_csv.csv \
    --json samples/v1/inputs/ATS_info.json \
    --pdf samples/v1/inputs/resumes/pdf \
    --docx samples/v1/inputs/resumes/docx \
    --output samples/outputs/result.json
```

CLI arguments always override configuration values. For example, to use an input config but write to a different output:
```bash
python main.py run \
    --input-config configs/input_config.json \
    --output outputs/custom_result.json
```

---

## Other CLI Commands

```bash
# Validate the synthetic dataset against the pipeline
python main.py validate

# Run the end-to-end precision and recall benchmark
python main.py benchmark

# Generate a new synthetic dataset
python main.py generate-dataset --scale 100 --difficulty medium

# Explain the conflict resolution and matching trace for a specific candidate
python main.py explain --candidate <candidate_id>

# Show help for the run command
python main.py run --help

# Show global CLI help
python main.py --help
```

---

## Canonical Output Schema

| Field | Type | Description |
|-------|------|-------------|
| `candidate_id` | String | Deterministic hash ID generated post-resolution. |
| `full_name` | String | Normalized full name of the candidate. |
| `emails` | List[String] | Deduplicated email addresses. |
| `phones` | List[String] | E.164 normalized phone numbers. |
| `location` | Object | Standardized location object (city, region, country). |
| `links` | Object | Categorized URLs (LinkedIn, GitHub, portfolio, other). |
| `headline` | String | Professional headline or summary. |
| `years_experience` | Float | Calculated total years of professional experience. |
| `skills` | List[Object] | Deduplicated array of extracted skills with confidences. |
| `experience` | List[Object] | Chronological array of professional roles (company, title, dates). |
| `education` | List[Object] | Array of educational degrees and institutions. |
| `provenance` | List[Object] | Traceability records indicating the winning source for each field. |
| `overall_confidence` | Float | Calculated profile quality score clamped between 0.10 and 1.00. |

---

## Sample Outputs

The pipeline generates two output files.

`samples/outputs/result.json`
Contains the final, resolved canonical profiles for all candidates.

`samples/outputs/result_audit.json`
Contains the structured audit logs, tracking extraction errors, pairwise match scores, and detailed merge/conflict resolution decisions.

---

## Entity Resolution Strategy

The pipeline employs a two-phase entity resolution strategy:

1. **Blocking**: Candidates are grouped into blocks based on deterministic keys (e.g., exact email matches, normalized phone matches, or company + initial combinations) to dramatically reduce O(N^2) pairwise comparisons.
2. **Fuzzy Matching**: Records within the same block are compared pairwise using field-level string similarity algorithms (e.g., Jaro-Winkler for names) and structural comparisons. A dynamic weighted sum of field scores is calculated, and if the total score exceeds a configurable threshold (e.g., 0.65), the records are linked.
3. **Merge Strategy**: Connected components are grouped into clusters. 
4. **Conflict Resolution**: Within a cluster, conflicting fields are resolved based on a strict source-reliability priority (e.g., ATS JSON > Recruiter CSV > PDF Resumes).

---

## Confidence Model

The overall profile confidence is a continuous, deterministic score representing the quality and reliability of the merged canonical profile.

- **Source Reliability**: Each field begins with a baseline confidence derived from the reliability of the source that won the conflict resolution.
- **Corroboration**: Fields receive a positive modifier (up to 0.05) for every independent source that agrees with the winning value.
- **Conflict Penalties**: Fields receive a penalty based on their criticality tier (e.g., Tier 1 penalties for name mismatches) if multiple sources provide conflicting data.
- **Profile Completeness**: The final `overall_confidence` is calculated as an unweighted average of the populated field confidences, safely clamped between 0.10 and 1.00 to prevent edge-case distortions.

---

## Validation

The `validate` command tests the pipeline against the generated synthetic ground-truth datasets. 

It checks:
- Proper extraction of data from heterogeneous sources.
- Accurate entity linking across deliberately corrupted records (OCR simulation, missing data, typos).
- Graceful handling of missing files, malformed JSON/CSV inputs, and corrupted PDFs.

---

## Benchmark

The `benchmark` command runs the pipeline end-to-end against the ground-truth dataset and calculates performance metrics.

Outputs include:
- **Precision**: Accuracy of the entity matches.
- **Recall**: Completeness of finding all true matches.
- **F1 Score**: Harmonic mean of precision and recall.
- **Execution Time**: Pipeline processing speed.
- **Peak Memory Usage**: RAM footprint during execution.

---

## Testing

The repository relies on `pytest` for unit, integration, and end-to-end tests.

To run the suite:
```bash
pytest tests/
```

The tests cover:
- Adapter extraction logic (including malformed inputs).
- Normalization routines (dates, phones, emails).
- Matcher boundary conditions (exact, fuzzy, and non-matches).
- Projector schema compliance.

---

## Assumptions

- **UTF-8 inputs**: All structured files (CSV, JSON) are expected to be UTF-8 encoded.
- **Text-based PDFs**: PDFs must contain extractable text. Scanned PDFs are not supported natively without an OCR pre-processor.
- **Phone normalization**: Phone numbers can be successfully cast to the E.164 standard.
- **Missing values**: Fields that cannot be extracted or resolved are omitted or cast to `null`.
- **Supported date formats**: Experience dates follow YYYY-MM or standard month/year textual representations.

---

## Known Limitations

- **Scanned PDFs without OCR**: Image-only resumes will yield empty extraction results.
- **Heavy OCR corruption**: Severe typos (e.g., "l" instead of "1") in critical identifiers like emails may cause false splits in entity resolution.
- **Nickname resolution limitations**: Highly irregular nicknames without associated email matches may fail to link to legal names.
- **Limited semantic matching**: Job titles and skills are matched lexically; "Software Engineer" and "Backend Developer" are not currently understood as semantically identical.

---

## Future Improvements

- **Semantic entity resolution**: Integrating embeddings to match semantically similar skills and job titles.
- **Better OCR**: Adding an optical character recognition dependency (like Tesseract) for scanned documents.
- **Distributed processing**: Implementing PySpark or Ray for horizontal scaling across millions of candidates.
- **Additional adapters**: Building direct API integrations for Workday, Greenhouse, or Lever.

---

## Design Decisions

- **Why the canonical schema was chosen**: Pydantic was used to strictly enforce the output schema, forbidding extra fields and ensuring downstream consumers receive predictable data.
- **Why the pipeline is modular**: The pipeline is strictly segmented (Extract -> Map -> Normalize -> Resolve -> Merge -> Project) to ensure that logic does not bleed across boundaries, improving testability.
- **Why adapters are separated**: Each file format (CSV, JSON, PDF) has unique parsing logic. Adapters abstract this complexity away, emitting standard `RawRecord` objects to the core pipeline.
- **Why normalization is isolated**: Standardizing dates, strings, and phone numbers before matching significantly improves the accuracy of fuzzy string comparisons.
- **Why matching and merging are separate**: The Matcher determines *who* is the same person, while the Merger determines *what* information to keep. Separating them prevents the matcher from making data-retention decisions.
- **Why the CLI is intentionally thin**: The `main.py` entrypoint only handles arguments, file loading, and JSON serialization. All business logic resides in the testable `pipeline.py` and `core/` modules.

---

## Submission Deliverables

- [x] Source code
- [x] README
- [x] Configurable output
- [x] Validation
- [x] Benchmark
- [x] Explain CLI
- [x] Sample inputs
- [x] Tests