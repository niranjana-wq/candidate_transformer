import argparse
import json
import sys
import io
import time
from pathlib import Path

# Force UTF-8 stdout for Windows
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from core.models import RunConfig
from pipeline import Pipeline

def cmd_run(args):
    print("====================================")
    print("EightFold Transformer")
    print("====================================")
    
    # Input Configuration Loading
    input_config = {}
    if getattr(args, "input_config", None):
        input_config_path = Path(args.input_config)
        if not input_config_path.exists():
            print(f"FATAL: Missing input configuration file at {args.input_config}", file=sys.stderr)
            sys.exit(1)
        try:
            with open(input_config_path, 'r', encoding='utf-8') as f:
                input_config = json.load(f)
        except Exception as e:
            print(f"FATAL: Invalid input configuration - {str(e)}", file=sys.stderr)
            sys.exit(1)

    # Configuration Verification
    config_path = Path(args.config)
    
    if not config_path.exists():
        if args.config == "config/default_config.json":
            print("Using built-in default configuration.")
            config = RunConfig()
        else:
            print(f"FATAL: Missing configuration file at {args.config}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            config = RunConfig(**config_data)
        except Exception as e:
            print(f"FATAL: Invalid configuration - {str(e)}", file=sys.stderr)
            sys.exit(1)
            
    # Precedence: CLI overrides config file
    csv_arg = args.csv or input_config.get("csv")
    json_arg = args.json or input_config.get("json")
    pdf_arg = args.pdf or input_config.get("pdf")
    docx_arg = args.docx or input_config.get("docx")
    output_arg = args.output or input_config.get("output")
    audit_arg = input_config.get("audit_output")
    
    if not output_arg:
        print("FATAL: Output path is required (via CLI --output or in config file).", file=sys.stderr)
        sys.exit(1)
        
    print("\nLoading inputs...")
    sources = []
    
    # ATS JSON
    if json_arg:
        p = Path(json_arg)
        if p.exists():
            with open(p, 'rb') as f:
                sources.append(("json", p.name, f.read()))
            print("✓ ATS JSON")
        else:
            print(f"ERROR: Invalid ATS JSON path {json_arg}", file=sys.stderr)
            
    # CSV
    if csv_arg:
        p = Path(csv_arg)
        if p.exists():
            with open(p, 'rb') as f:
                sources.append(("csv", p.name, f.read()))
            print("✓ Recruiter CSV")
        else:
            print(f"ERROR: Invalid CSV path {csv_arg}", file=sys.stderr)
            
    # PDFs
    if pdf_arg:
        p_dir = Path(pdf_arg)
        if p_dir.exists() and p_dir.is_dir():
            count = 0
            for p in p_dir.glob("*.pdf"):
                with open(p, 'rb') as f:
                    sources.append(("pdf", p.name, f.read()))
                count += 1
            if count > 0:
                print(f"✓ PDF Resumes ({count})")
        else:
            print(f"ERROR: Invalid PDF folder {pdf_arg}", file=sys.stderr)
            
    # DOCXs
    if docx_arg:
        p_dir = Path(docx_arg)
        if p_dir.exists() and p_dir.is_dir():
            count = 0
            for p in p_dir.glob("*.docx"):
                with open(p, 'rb') as f:
                    sources.append(("docx", p.name, f.read()))
                count += 1
            if count > 0:
                print(f"✓ DOCX Resumes ({count})")
        else:
            print(f"ERROR: Invalid DOCX folder {docx_arg}", file=sys.stderr)
            
    if not sources:
        print("FATAL: No valid sources loaded", file=sys.stderr)
        sys.exit(1)
        
    print("\nRunning pipeline...")
    print("✓ Extraction\n✓ Mapping\n✓ Normalization\n✓ Entity Resolution\n✓ Projection")
    
    start_time = time.time()
    try:
        pipeline = Pipeline(config)
        results = pipeline.run(sources)
    except Exception as e:
        print(f"FATAL: Pipeline execution failed - {str(e)}", file=sys.stderr)
        sys.exit(1)
        
    exec_time = time.time() - start_time
    
    print("\nWriting output...")
    try:
        output_path = Path(output_arg)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
        if audit_arg:
            audit_path = Path(audit_arg)
        else:
            audit_path = output_path.with_name(output_path.stem + "_audit.json")
            
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump(pipeline.audit.export(), f, indent=2)
            
        print(f"✓ {output_arg}")
        print(f"✓ {audit_path}")
    except Exception as e:
        print(f"FATAL: Could not write output to {output_arg} - {str(e)}", file=sys.stderr)
        sys.exit(1)
        
    print("\nSummary")
    print(f"Candidates Processed : {len(sources)}")
    print(f"Canonical Profiles   : {len(results)}")
    print(f"Execution Time       : {exec_time:.2f} s")
    print("\nDone.")

def cmd_validate(args):
    print("Running validation...")
    try:
        from scripts.dataset_generator.config import GeneratorConfig
        from scripts.dataset_generator.validator import Validator
        
        # We dummy-instantiate config to point to input dir
        # The existing validator mostly just needs ground_truth_dir and inputs_dir
        config = GeneratorConfig()
        
        input_dir = Path(args.input)
        if not input_dir.exists():
            print("✗ Validation failed: Input directory does not exist.")
            sys.exit(1)
            
        config.inputs_dir = input_dir
        config.ground_truth_dir = input_dir.parent / "ground_truth"
        config.base_out_dir = input_dir.parent
        
        validator = Validator(config)
        validator.validate()
        print("✓ Passed. See DATASET_GENERATION_REPORT.md for details.")
    except Exception as e:
        print(f"✗ Validation failed: {str(e)}", file=sys.stderr)
        sys.exit(1)

def cmd_benchmark(args):
    print("Running benchmark...")
    try:
        from scripts.benchmark import run_benchmark
        run_benchmark()
        
        # Read the generated report to print the summary metrics to console
        with open("BENCHMARK_REPORT.md", "r") as f:
            content = f.read()
            
        import re
        f1 = re.search(r'- \*\*F1 Score\*\*: (\d+\.\d+)', content)
        p = re.search(r'- \*\*Precision\*\*: (\d+\.\d+)', content)
        r = re.search(r'- \*\*Recall\*\*: (\d+\.\d+)', content)
        t = re.search(r'- \*\*Total Execution Time\*\*: (\d+\.\d+)', content)
        m = re.search(r'- \*\*Peak Memory Usage\*\*: (\d+\.\d+)', content)
        
        print(f"Precision      : {p.group(1) if p else 'N/A'}")
        print(f"Recall         : {r.group(1) if r else 'N/A'}")
        print(f"F1             : {f1.group(1) if f1 else 'N/A'}")
        print(f"Execution Time : {t.group(1) if t else 'N/A'} s")
        print(f"Memory         : {m.group(1) if m else 'N/A'} MB")
        
    except Exception as e:
        print(f"FATAL: Benchmark failed - {str(e)}", file=sys.stderr)
        sys.exit(1)

def cmd_generate(args):
    print(f"Running dataset generator (scale={args.scale}, difficulty={args.difficulty})...")
    try:
        from scripts.dataset_generator.config import GeneratorConfig
        from scripts.dataset_generator.master_generator import MasterGenerator
        from scripts.dataset_generator.mutation_engine import MutationEngine
        from scripts.dataset_generator.emitters.ats_emitter import AtsEmitter
        from scripts.dataset_generator.emitters.csv_emitter import CsvEmitter
        from scripts.dataset_generator.emitters.pdf_emitter import PdfEmitter
        from scripts.dataset_generator.emitters.docx_emitter import DocxEmitter
        import copy
        
        config = GeneratorConfig("v1", args.scale, args.difficulty, args.seed)
        
        master_gen = MasterGenerator(seed=args.seed)
        ambiguous_rate = config.profile.get("ambiguous_pairs", {}).get("rate", 0.0) if config.profile.get("ambiguous_pairs", {}).get("enabled") else 0.0
        master_records = master_gen.generate_dataset(scale=args.scale, ambiguous_rate=ambiguous_rate)
        
        with open(config.ground_truth_dir / "master_candidates.json", "w", encoding="utf-8") as f:
            json.dump(master_records, f, indent=2)
            
        engine = MutationEngine()
        evaluation_mapping = {}
        ats_records, csv_records, pdf_records, docx_records = [], [], [], []
        
        for r in master_records:
            uid = r["uuid"]
            evaluation_mapping[uid] = {"mutations_applied": {}}
            
            ats_r = copy.deepcopy(r)
            evaluation_mapping[uid]["mutations_applied"]["ats"] = engine.apply_mutations(ats_r, "ats", config.profile)
            evaluation_mapping[uid]["ats_id"] = f"MASTER-{uid[:8].upper()}"
            ats_records.append(ats_r)
            
            csv_r = copy.deepcopy(r)
            evaluation_mapping[uid]["mutations_applied"]["csv"] = engine.apply_mutations(csv_r, "csv", config.profile)
            evaluation_mapping[uid]["csv_id"] = f"CAND-{uid[:8].upper()}"
            csv_records.append(csv_r)
            
            pdf_r = copy.deepcopy(r)
            evaluation_mapping[uid]["mutations_applied"]["pdf"] = engine.apply_mutations(pdf_r, "pdf", config.profile)
            pdf_records.append(pdf_r)
            
            docx_r = copy.deepcopy(r)
            evaluation_mapping[uid]["mutations_applied"]["docx"] = engine.apply_mutations(docx_r, "docx", config.profile)
            docx_records.append(docx_r)
            
        AtsEmitter(config.inputs_dir).emit(ats_records)
        CsvEmitter(config.inputs_dir).emit(csv_records)
        PdfEmitter(config.inputs_dir).emit(pdf_records)
        DocxEmitter(config.inputs_dir).emit(docx_records)
        
        for i, r in enumerate(master_records):
            uid = r["uuid"]
            if "pdf_filename" in pdf_records[i]:
                evaluation_mapping[uid]["pdf_filename"] = pdf_records[i]["pdf_filename"]
            if "docx_filename" in docx_records[i]:
                evaluation_mapping[uid]["docx_filename"] = docx_records[i]["docx_filename"]

        with open(config.ground_truth_dir / "evaluation_mapping.json", "w", encoding="utf-8") as f:
            json.dump(evaluation_mapping, f, indent=2)
            
        print("Dataset generated successfully.")
    except Exception as e:
        print(f"FATAL: Generation failed - {str(e)}", file=sys.stderr)
        sys.exit(1)

def cmd_explain(args):
    print(f"Explaining candidate: {args.candidate}")
    
    audit_path = Path(args.audit)
    if not audit_path.exists():
        print(f"FATAL: Could not find audit log at {args.audit}.", file=sys.stderr)
        print("Please run the pipeline first, or specify --audit <path_to_audit_json>", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(audit_path, 'r', encoding='utf-8') as f:
            audit_log = json.load(f)
    except Exception as e:
        print(f"FATAL: Failed to read audit log: {str(e)}", file=sys.stderr)
        sys.exit(1)
        
    events = audit_log.get("events", [])
    merge_events = [e for e in events if e.get("action") == "merge_success" and e.get("candidate_id") == args.candidate]
    
    if not merge_events:
        print(f"\nCandidate {args.candidate} not found in the audit log.")
        sys.exit(1)
        
    event = merge_events[0]
    details = event.get("details", {})
    
    print("\n====================================")
    print(f"Explainability Trace: {args.candidate}")
    print("====================================")
    
    print("\n--- Merger Summary ---")
    print(f"Overall Confidence   : {details.get('overall_confidence', 'N/A')}")
    print(f"Fields Populated     : {details.get('fields_populated', 0)}")
    print(f"Completeness Factor  : {details.get('completeness_multiplier', 0.0)}")
    
    print("\n--- Field Level Conflict Resolution ---")
    field_decisions = details.get("field_decisions", {})
    for field, decision in field_decisions.items():
        print(f"\n[ {field} ]")
        print(f"  Winning Source   : {decision.get('winning_source')}")
        val_repr = str(decision.get('winning_value'))[:80]
        if len(str(decision.get('winning_value'))) > 80: val_repr += "..."
        print(f"  Winning Value    : {val_repr}")
        print(f"  Field Confidence : {decision.get('final_field_confidence')}")
        print(f"  Agreements       : {decision.get('agreement_count', 0)}")
        print(f"  Conflicts        : {decision.get('conflict_count', 0)}")
        print(f"  Reason Selected  : {decision.get('reason_selected')}")
        
    print("\n--- Matching Ambiguities / Matcher Trace ---")
    ambiguities = [e for e in events if e.get("action") == "ambiguous_match"]
    found_ambiguity = False
    for a in ambiguities:
        d = a.get("details", {})
        # Note: In a real distributed system we might log idx to candidate mappings, 
        # but the merge log tells us the final outcome. The ambiguous match log is just 
        # pairwise traces.
        if d.get("accepted"):
            found_ambiguity = True
            print(f"\nPairwise Match Score: {d.get('final_score')} >= {d.get('threshold')}")
            print(f"Reason: {d.get('reason')}")
            print(f"Matched Fields: {d.get('matched_fields')}")
            print(f"Detailed Scores: {d.get('field_scores')}")
            
    if not found_ambiguity:
        print("\nNo fuzzy/ambiguous pairwise match traces led to this candidate (likely exact match or single source).")
        
    print("\n====================================")

def main():
    parser = argparse.ArgumentParser(description="EightFold Transformer CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    run_parser = subparsers.add_parser("run", help="Run the complete pipeline")
    run_parser.add_argument("--csv", help="Recruiter CSV")
    run_parser.add_argument("--json", help="ATS JSON")
    run_parser.add_argument("--pdf", help="Folder containing PDFs")
    run_parser.add_argument("--docx", help="Folder containing DOCX files")
    run_parser.add_argument("--input-config", help="Input configuration JSON file")
    run_parser.add_argument("--config", default="config/default_config.json", help="Optional runtime config")
    run_parser.add_argument("--output", help="Output JSON location")
    
    # validate command
    validate_parser = subparsers.add_parser("validate", help="Run dataset validation")
    validate_parser.add_argument("--input", default="samples/v1/inputs", help="Input dataset directory")
    
    # benchmark command
    subparsers.add_parser("benchmark", help="Run the existing benchmark")
    
    # generate-dataset command
    gen_parser = subparsers.add_parser("generate-dataset", help="Generate canonical dataset")
    gen_parser.add_argument("--scale", type=int, default=100)
    gen_parser.add_argument("--difficulty", default="medium")
    gen_parser.add_argument("--seed", type=int, default=42)
    
    # explain command
    explain_parser = subparsers.add_parser("explain", help="Explain candidate matching")
    explain_parser.add_argument("--candidate", required=True, help="Candidate ID")
    explain_parser.add_argument("--audit", default="samples/outputs/result_audit.json", help="Path to audit JSON")

    try:
        args = parser.parse_args()
        
        if args.command == "run":
            cmd_run(args)
        elif args.command == "validate":
            cmd_validate(args)
        elif args.command == "benchmark":
            cmd_benchmark(args)
        elif args.command == "generate-dataset":
            cmd_generate(args)
        elif args.command == "explain":
            cmd_explain(args)
            
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.", file=sys.stderr)
        sys.exit(130)

if __name__ == "__main__":
    main()
