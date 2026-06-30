import json
import argparse
import copy
from pathlib import Path
from scripts.dataset_generator.config import GeneratorConfig
from scripts.dataset_generator.master_generator import MasterGenerator
from scripts.dataset_generator.mutation_engine import MutationEngine
from scripts.dataset_generator.emitters.ats_emitter import AtsEmitter
from scripts.dataset_generator.emitters.csv_emitter import CsvEmitter
from scripts.dataset_generator.emitters.pdf_emitter import PdfEmitter
from scripts.dataset_generator.emitters.docx_emitter import DocxEmitter
from scripts.dataset_generator.validator import Validator

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1")
    parser.add_argument("--scale", type=int, default=100)
    parser.add_argument("--difficulty", default="medium")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    config = GeneratorConfig(args.version, args.scale, args.difficulty, args.seed)
    
    print(f"Generating Canonical Dataset (Version: {args.version}, Scale: {args.scale}, Difficulty: {args.difficulty})")
    
    master_gen = MasterGenerator(seed=args.seed)
    ambiguous_rate = config.profile.get("ambiguous_pairs", {}).get("rate", 0.0) if config.profile.get("ambiguous_pairs", {}).get("enabled") else 0.0
    master_records = master_gen.generate_dataset(scale=args.scale, ambiguous_rate=ambiguous_rate)
    
    # Save master ground truth
    with open(config.ground_truth_dir / "master_candidates.json", "w", encoding="utf-8") as f:
        json.dump(master_records, f, indent=2)
        
    engine = MutationEngine()
    evaluation_mapping = {}
    
    ats_records = []
    csv_records = []
    pdf_records = []
    docx_records = []
    
    for r in master_records:
        uid = r["uuid"]
        evaluation_mapping[uid] = {
            "mutations_applied": {}
        }
        
        # ATS
        ats_r = copy.deepcopy(r)
        ats_muts = engine.apply_mutations(ats_r, "ats", config.profile)
        evaluation_mapping[uid]["mutations_applied"]["ats"] = ats_muts
        evaluation_mapping[uid]["ats_id"] = f"MASTER-{uid[:8].upper()}"
        ats_records.append(ats_r)
        
        # CSV
        csv_r = copy.deepcopy(r)
        csv_muts = engine.apply_mutations(csv_r, "csv", config.profile)
        evaluation_mapping[uid]["mutations_applied"]["csv"] = csv_muts
        evaluation_mapping[uid]["csv_id"] = f"CAND-{uid[:8].upper()}"
        csv_records.append(csv_r)
        
        # PDF
        pdf_r = copy.deepcopy(r)
        pdf_muts = engine.apply_mutations(pdf_r, "pdf", config.profile)
        evaluation_mapping[uid]["mutations_applied"]["pdf"] = pdf_muts
        pdf_records.append(pdf_r) # filename generated during emit
        
        # DOCX
        docx_r = copy.deepcopy(r)
        docx_muts = engine.apply_mutations(docx_r, "docx", config.profile)
        evaluation_mapping[uid]["mutations_applied"]["docx"] = docx_muts
        docx_records.append(docx_r) # filename generated during emit

    print("Emitting artifacts...")
    AtsEmitter(config.inputs_dir).emit(ats_records)
    CsvEmitter(config.inputs_dir).emit(csv_records)
    PdfEmitter(config.inputs_dir).emit(pdf_records)
    DocxEmitter(config.inputs_dir).emit(docx_records)
    
    # Update mapping with filenames
    for i, r in enumerate(master_records):
        uid = r["uuid"]
        if "pdf_filename" in pdf_records[i]:
            evaluation_mapping[uid]["pdf_filename"] = pdf_records[i]["pdf_filename"]
        if "docx_filename" in docx_records[i]:
            evaluation_mapping[uid]["docx_filename"] = docx_records[i]["docx_filename"]

    with open(config.ground_truth_dir / "evaluation_mapping.json", "w", encoding="utf-8") as f:
        json.dump(evaluation_mapping, f, indent=2)
        
    print("Running Validator...")
    Validator(config).validate()
    print("Done!")

if __name__ == "__main__":
    main()
