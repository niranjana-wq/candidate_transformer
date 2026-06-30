import json
from pathlib import Path
from scripts.dataset_generator.config import GeneratorConfig

class Validator:
    def __init__(self, config: GeneratorConfig):
        self.config = config
        
    def validate(self):
        eval_map_path = self.config.ground_truth_dir / "evaluation_mapping.json"
        with open(eval_map_path, "r", encoding="utf-8") as f:
            eval_map = json.load(f)
            
        stats = {
            "ats": {"generated": 0, "mutations": {}},
            "csv": {"generated": 0, "mutations": {}},
            "pdf": {"generated": 0, "mutations": {}},
            "docx": {"generated": 0, "mutations": {}}
        }
        
        missing_files = []
        
        # We know ATS and CSV are single files.
        ats_file = self.config.inputs_dir / "ATS_info.json"
        csv_file = self.config.inputs_dir / "recruiter_csv.csv"
        
        if not ats_file.exists(): missing_files.append("ATS_info.json")
        if not csv_file.exists(): missing_files.append("recruiter_csv.csv")
        
        for uid, data in eval_map.items():
            if ats_file.exists(): stats["ats"]["generated"] += 1
            if csv_file.exists(): stats["csv"]["generated"] += 1
            
            pdf_path = self.config.inputs_dir / "resume" / "pdf" / data.get("pdf_filename", "MISSING.pdf")
            if pdf_path.exists():
                stats["pdf"]["generated"] += 1
            else:
                missing_files.append(data.get("pdf_filename"))
                
            docx_path = self.config.inputs_dir / "resume" / "docx" / data.get("docx_filename", "MISSING.docx")
            if docx_path.exists():
                stats["docx"]["generated"] += 1
            else:
                missing_files.append(data.get("docx_filename"))
                
            # Aggregate mutation stats
            for source, muts in data.get("mutations_applied", {}).items():
                for mut in muts:
                    mtype = mut["type"]
                    if mtype not in stats[source]["mutations"]:
                        stats[source]["mutations"][mtype] = 0
                    stats[source]["mutations"][mtype] += 1
                    
        report = [
            f"# Dataset Generation Report (Version {self.config.version})",
            f"\n## Configuration",
            f"- Scale: {self.config.scale}",
            f"- Difficulty: {self.config.difficulty}",
            f"- Seed: {self.config.seed}",
            f"\n## Files Generated",
            f"- ATS Records: {stats['ats']['generated']}",
            f"- CSV Records: {stats['csv']['generated']}",
            f"- PDF Resumes: {stats['pdf']['generated']}",
            f"- DOCX Resumes: {stats['docx']['generated']}",
            f"\n## Mutation Statistics"
        ]
        
        for source in ["ats", "csv", "pdf", "docx"]:
            report.append(f"\n### {source.upper()}")
            for mtype, count in stats[source]["mutations"].items():
                report.append(f"- {mtype}: {count} occurrences")
                
        report.append("\n## Missing Files")
        if missing_files:
            for f in missing_files:
                report.append(f"- {f}")
        else:
            report.append("- None")
            
        report.append("\n## Readiness Assessment")
        if not missing_files:
            report.append("**Verdict: READY**")
            report.append("The dataset was successfully generated with controlled mutations. It is ready for Entity Resolution benchmarking.")
        else:
            report.append("**Verdict: FAILED**")
            report.append("Some files failed to generate. Check logs.")
            
        report_path = self.config.base_out_dir / "DATASET_GENERATION_REPORT.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
