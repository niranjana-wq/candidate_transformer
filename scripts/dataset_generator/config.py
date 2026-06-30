import os
import json
from pathlib import Path

# Paths
GENERATOR_DIR = Path(__file__).parent
PROFILES_DIR = GENERATOR_DIR / "profiles"
WORKSPACE_ROOT = GENERATOR_DIR.parent.parent
OUTPUT_DIR = WORKSPACE_ROOT / "samples"

class GeneratorConfig:
    def __init__(self, version="v1", scale=100, difficulty="medium", seed=42):
        self.version = version
        self.scale = scale
        self.difficulty = difficulty
        self.seed = seed
        self.profile = self._load_profile(difficulty)
        
        # Output paths
        self.base_out_dir = OUTPUT_DIR / self.version
        self.inputs_dir = self.base_out_dir / "inputs"
        self.ground_truth_dir = self.base_out_dir / "ground_truth"
        
        # Ensure directories exist
        self.inputs_dir.mkdir(parents=True, exist_ok=True)
        self.ground_truth_dir.mkdir(parents=True, exist_ok=True)
        (self.inputs_dir / "resume" / "pdf").mkdir(parents=True, exist_ok=True)
        (self.inputs_dir / "resume" / "docx").mkdir(parents=True, exist_ok=True)

    def _load_profile(self, difficulty: str) -> dict:
        profile_path = PROFILES_DIR / f"{difficulty}.json"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile {difficulty}.json not found in {PROFILES_DIR}")
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
