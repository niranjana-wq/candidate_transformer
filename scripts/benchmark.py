import os
import json
import time
import tracemalloc
import cProfile
import pstats
import io
from pathlib import Path
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(r"c:\Users\niran\OneDrive\Desktop\EightFold Transformer")))

from pipeline import Pipeline
from core.models import RunConfig

def load_sources(inputs_dir: Path):
    sources = []
    
    # 1. ATS JSON
    ats_path = inputs_dir / "ATS_info.json"
    if ats_path.exists():
        with open(ats_path, "rb") as f:
            sources.append(("json", "ATS_info.json", f.read()))
            
    # 2. CSV
    csv_path = inputs_dir / "recruiter_csv.csv"
    if csv_path.exists():
        with open(csv_path, "rb") as f:
            sources.append(("csv", "recruiter_csv.csv", f.read()))
            
    # 3. PDF
    pdf_dir = inputs_dir / "resume" / "pdf"
    if pdf_dir.exists():
        for p in pdf_dir.glob("*.pdf"):
            with open(p, "rb") as f:
                sources.append(("pdf", p.name, f.read()))
                
    return sources

def run_benchmark():
    workspace = Path(r"c:\Users\niran\OneDrive\Desktop\EightFold Transformer")
    v1_dir = workspace / "samples/v1"
    inputs_dir = v1_dir / "inputs"
    gt_dir = v1_dir / "ground_truth"
    
    print("Loading sources...")
    sources = load_sources(inputs_dir)
    total_input_records = 300 # 100 ATS, 100 CSV, 100 PDF
    
    config = RunConfig(include_provenance=True)
    pipeline = Pipeline(config)
    
    # --- PATCH TO CAPTURE CLUSTERS ---
    import resolve.merger
    original_merge = resolve.merger.EntityMerger.merge_cluster
    captured_clusters = []
    
    def patched_merge(candidate_id, cluster_records, config):
        # cluster_records: List[Tuple[str, str, CanonicalRecord]]
        cluster_ids = []
        for cr in cluster_records:
            cid = cr[2].candidate_id
            if cid:
                cluster_ids.append(cid)
            else:
                cluster_ids.append(cr[1])
        captured_clusters.append(cluster_ids)
        return original_merge(candidate_id, cluster_records, config)
        
    resolve.merger.EntityMerger.merge_cluster = staticmethod(patched_merge)
    # ---------------------------------
    
    print("Running pipeline with profiling...")
    tracemalloc.start()
    
    pr = cProfile.Profile()
    pr.enable()
    
    start_time = time.time()
    
    output = pipeline.run(sources)
    
    end_time = time.time()
    pr.disable()
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    exec_time = end_time - start_time
    records_per_sec = total_input_records / exec_time if exec_time > 0 else 0
    peak_mb = peak / (1024 * 1024)
    
    # Process profiler output
    s = io.StringIO()
    sortby = 'tottime'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(15)
    profiling_results = s.getvalue()
    
    # Load Evaluation Mapping
    with open(gt_dir / "evaluation_mapping.json", "r", encoding="utf-8") as f:
        eval_map = json.load(f)
        
    print("Analyzing clusters...")
    
    # Reverse map: from input ID to ground truth UUID
    input_to_uuid = {}
    for uid, data in eval_map.items():
        if data.get("ats_id"): input_to_uuid[data["ats_id"]] = uid
        if data.get("csv_id"): input_to_uuid[data["csv_id"]] = uid
        if data.get("pdf_filename"): input_to_uuid[data["pdf_filename"]] = uid
        
    clusters = captured_clusters
        
    num_singleton = sum(1 for c in clusters if len(c) == 1)
    num_merged = sum(1 for c in clusters if len(c) > 1)
    avg_size = sum(len(c) for c in clusters) / len(clusters) if clusters else 0
    
    # Calculate Precision, Recall, F1
    # Pairwise matching evaluation
    # True pairs: pairs of inputs that share the same UUID
    # Predicted pairs: pairs of inputs that are in the same cluster
    
    def get_pairs(clusters_list):
        pairs = set()
        for c in clusters_list:
            sorted_c = sorted(c)
            for i in range(len(sorted_c)):
                for j in range(i+1, len(sorted_c)):
                    pairs.add((sorted_c[i], sorted_c[j]))
        return pairs

    # Generate True Clusters
    true_clusters_dict = defaultdict(list)
    for in_id, uid in input_to_uuid.items():
        true_clusters_dict[uid].append(in_id)
        
    true_pairs = get_pairs(true_clusters_dict.values())
    pred_pairs = get_pairs(clusters)
    
    tp = len(true_pairs.intersection(pred_pairs))
    fp = len(pred_pairs - true_pairs)
    fn = len(true_pairs - pred_pairs)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    false_merge_rate = fp / len(pred_pairs) if len(pred_pairs) > 0 else 0
    false_split_rate = fn / len(true_pairs) if len(true_pairs) > 0 else 0
    
    # Cluster Accuracy (exact match of cluster)
    true_clusters_set = set(tuple(sorted(c)) for c in true_clusters_dict.values())
    pred_clusters_set = set(tuple(sorted(c)) for c in clusters)
    cluster_accuracy = len(true_clusters_set.intersection(pred_clusters_set)) / len(true_clusters_set) if true_clusters_set else 0

    # Confusion Analysis
    confusion = []
    
    # Find false merges (FP)
    false_merges = pred_pairs - true_pairs
    if false_merges:
        for p in list(false_merges)[:5]:
            uid1 = input_to_uuid.get(p[0])
            uid2 = input_to_uuid.get(p[1])
            confusion.append(f"- False Merge: {p[0]} (UUID: {uid1}) matched with {p[1]} (UUID: {uid2}).")
            confusion.append(f"  Reason: Algorithm likely matched on exactly identical name (ambiguous pair) despite differing contact info.")
            
    # Find false splits (FN)
    false_splits = true_pairs - pred_pairs
    if false_splits:
        for p in list(false_splits)[:5]:
            uid = input_to_uuid.get(p[0]) # Since it's a false split, they share the same UUID
            confusion.append(f"- False Split: {p[0]} and {p[1]} (UUID: {uid}).")
            # Lookup mutations
            muts = eval_map.get(uid, {}).get("mutations_applied", {})
            confusion.append(f"  Reason: Likely caused by mutations. Details: {muts}")

    report = [
        "# Benchmark Report",
        "\n## 1. Execution Performance",
        f"- **Total Execution Time**: {exec_time:.3f} seconds",
        f"- **Processing Speed**: {records_per_sec:.2f} records / second",
        f"- **Peak Memory Usage**: {peak_mb:.2f} MB",
        "\n## 2. Cluster Statistics",
        f"- **Total Output Clusters**: {len(clusters)} (Expected: 100)",
        f"- **Average Cluster Size**: {avg_size:.2f} (Expected: 3.00)",
        f"- **Singleton Clusters**: {num_singleton}",
        f"- **Merged Clusters**: {num_merged}",
        "\n## 3. Accuracy Metrics",
        f"- **Precision**: {precision:.4f} (True pairs found / All predicted pairs)",
        f"- **Recall**: {recall:.4f} (True pairs found / All actual true pairs)",
        f"- **F1 Score**: {f1:.4f}",
        f"- **False Merge Rate**: {false_merge_rate:.4f}",
        f"- **False Split Rate**: {false_split_rate:.4f}",
        f"- **Cluster Accuracy**: {cluster_accuracy:.4f} (Perfectly resolved clusters)",
        "\n## 4. Confusion Analysis"
    ] + confusion + [
        "\n## 5. Profiling & Bottlenecks",
        "```text",
        profiling_results,
        "```",
        "\n## 6. Identified Bottlenecks",
        "- `fuzzy_match` calls (like `SequenceMatcher`) and Cartesian product comparisons during the matching phase.",
        "- Extractor operations (e.g. `pypdf` parsing text from PDFs).",
        "\n## 7. Recommendations",
        "- Implement scalable blocking in the Matcher to avoid O(N^2) pairwise comparisons.",
        "- Optimize fuzzy matching using faster algorithms (e.g., rapidfuzz, phonetics).",
        "- Cache normalization outputs or implement memoization for standard fields."
    ]
    
    with open(workspace / "BENCHMARK_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))

if __name__ == "__main__":
    run_benchmark()
