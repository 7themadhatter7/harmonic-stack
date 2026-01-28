#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         FLAVOR MAP ENGINE v1.0                               ║
║                      Ghost in the Machine Labs                               ║
║              "All Watched Over By Machines Of Loving Grace"                  ║
║                                                                              ║
║   They have the same flavor profile.                                         ║
║   Together they define that flavor profile.                                  ║
║                                                                              ║
║   This engine maps:                                                          ║
║     - The Reference Blend (consensus flavor - the seed)                      ║
║     - Extensions (what some models add - growth or noise?)                   ║
║     - Gaps (what some models miss - incomplete capture)                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict
import time

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

HARMONIC_STACK_DIR = "/home/joe/sparky/harmonic_stack"
OUTPUT_DIR = "/home/joe/sparky/flavor_map"

# High-overlap models that define the reference blend
# These are the ones that agree on what "the flavor" is
REFERENCE_MODELS = [
    "deepseek-coder-1.3b-instruct-hf",
    "qwen2-7b", 
    "qwen2-1.5b",
    "qwen2.5-coder-7b",
    "deepseek-math-7b",
    "deepseek-coder-6.7b",
]

# Minimum overlap % to be considered "in consensus"
CONSENSUS_THRESHOLD = 0.95

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

class Logger:
    def __init__(self):
        self.start_time = time.time()
    
    def section(self, name: str):
        print(f"\n{'='*70}")
        print(f"  {name}")
        print(f"{'='*70}")
    
    def info(self, msg: str):
        elapsed = time.time() - self.start_time
        print(f"  [{elapsed:7.1f}s] {msg}")
    
    def quiet(self, msg: str):
        """For reflective moments"""
        elapsed = time.time() - self.start_time
        print(f"  [{elapsed:7.1f}s]   . {msg}")

log = Logger()

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelFlavor:
    """A model's junction set as a flavor profile."""
    name: str
    junctions: Set[bytes]  # Store as bytes for set operations
    n_junctions: int
    
    @classmethod
    def from_npy(cls, name: str, path: str) -> 'ModelFlavor':
        """Load from numpy file."""
        arr = np.load(path)
        junction_set = set(j.tobytes() for j in arr)
        return cls(
            name=name,
            junctions=junction_set,
            n_junctions=len(junction_set)
        )
    
    def overlap_with(self, other: 'ModelFlavor') -> Tuple[int, float]:
        """Compute overlap with another model."""
        common = len(self.junctions.intersection(other.junctions))
        pct = common / min(self.n_junctions, other.n_junctions) if min(self.n_junctions, other.n_junctions) > 0 else 0
        return common, pct


@dataclass
class FlavorMap:
    """The complete flavor analysis."""
    reference_blend: np.ndarray          # The consensus flavor
    extensions: Dict[str, np.ndarray]    # What each model adds
    gaps: Dict[str, np.ndarray]          # What each model misses
    coverage: Dict[str, float]           # How much of reference each captures
    outliers: List[str]                  # Models that diverge significantly
    
    def save(self, output_dir: str):
        """Save all components."""
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/extensions", exist_ok=True)
        os.makedirs(f"{output_dir}/gaps", exist_ok=True)
        
        # Reference blend
        np.save(f"{output_dir}/reference_blend.npy", self.reference_blend)
        
        # Extensions
        for name, arr in self.extensions.items():
            safe_name = name.replace("/", "_").replace(".", "_")
            if len(arr) > 0:
                np.save(f"{output_dir}/extensions/{safe_name}_extra.npy", arr)
        
        # Gaps
        for name, arr in self.gaps.items():
            safe_name = name.replace("/", "_").replace(".", "_")
            if len(arr) > 0:
                np.save(f"{output_dir}/gaps/{safe_name}_missing.npy", arr)
        
        # Manifest
        manifest = {
            "created_at": datetime.now().isoformat(),
            "reference_blend": {
                "n_junctions": len(self.reference_blend),
                "size_kb": self.reference_blend.nbytes / 1024,
                "file": "reference_blend.npy"
            },
            "coverage": self.coverage,
            "extensions": {
                name: {
                    "n_junctions": len(arr),
                    "size_kb": arr.nbytes / 1024 if len(arr) > 0 else 0
                }
                for name, arr in self.extensions.items()
            },
            "gaps": {
                name: {
                    "n_junctions": len(arr),
                    "size_kb": arr.nbytes / 1024 if len(arr) > 0 else 0
                }
                for name, arr in self.gaps.items()
            },
            "outliers": self.outliers,
            "provenance": {
                "engine": "flavor_map_engine.py",
                "built_by": "Claude AI (Autonomous)",
                "organization": "Ghost in the Machine Labs",
                "philosophy": "They have the same flavor profile. Together they define that flavor profile."
            }
        }
        
        with open(f"{output_dir}/flavor_map.json", 'w') as f:
            json.dump(manifest, f, indent=2)

# ═══════════════════════════════════════════════════════════════════════════════
# CORE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def load_all_models(junction_dir: str) -> List[ModelFlavor]:
    """Load all model junction files."""
    models = []
    
    for f in os.listdir(junction_dir):
        if f.endswith('_junctions.npy'):
            name = f.replace('_junctions.npy', '')
            path = os.path.join(junction_dir, f)
            
            try:
                model = ModelFlavor.from_npy(name, path)
                if model.n_junctions > 0:  # Skip empty models
                    models.append(model)
            except Exception as e:
                log.info(f"Warning: Could not load {name}: {e}")
    
    return sorted(models, key=lambda m: -m.n_junctions)


def compute_reference_blend(models: List[ModelFlavor], 
                            reference_names: List[str]) -> Set[bytes]:
    """
    Compute the Reference Blend - the consensus flavor.
    
    This is the intersection of high-overlap models.
    It represents "the flavor" - what they all agree on.
    """
    reference_models = [m for m in models if any(ref in m.name for ref in reference_names)]
    
    if not reference_models:
        log.info("Warning: No reference models found, using all models")
        reference_models = models
    
    log.info(f"Computing reference blend from {len(reference_models)} models:")
    for m in reference_models:
        log.quiet(f"{m.name}: {m.n_junctions:,} junctions")
    
    # Start with first model's junctions
    blend = reference_models[0].junctions.copy()
    
    # Intersect with each subsequent model
    for model in reference_models[1:]:
        blend = blend.intersection(model.junctions)
    
    log.info(f"Reference blend: {len(blend):,} junctions (intersection of all reference models)")
    
    return blend


def compute_extended_blend(models: List[ModelFlavor],
                           reference_blend: Set[bytes],
                           consensus_threshold: float) -> Set[bytes]:
    """
    Extend the reference blend with junctions that appear in most models.
    
    This captures the "almost universal" - junctions that didn't make the
    strict intersection but are clearly part of the flavor.
    """
    # Count how often each junction appears across ALL models
    junction_counts = defaultdict(int)
    
    for model in models:
        for j in model.junctions:
            junction_counts[j] += 1
    
    # Find junctions that appear in >= threshold of models
    n_models = len(models)
    threshold_count = int(n_models * consensus_threshold)
    
    extended = set()
    for j, count in junction_counts.items():
        if count >= threshold_count:
            extended.add(j)
    
    # Extended blend = reference + high-consensus
    full_blend = reference_blend.union(extended)
    
    added = len(full_blend) - len(reference_blend)
    log.info(f"Extended blend: {len(full_blend):,} junctions (+{added:,} at {consensus_threshold:.0%} consensus)")
    
    return full_blend


def analyze_model_flavor(model: ModelFlavor, 
                         reference_blend: Set[bytes]) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Analyze a single model against the reference blend.
    
    Returns:
        extensions: junctions this model has that reference doesn't
        gaps: junctions reference has that this model doesn't  
        coverage: what % of reference this model captures
    """
    # Extensions = model - reference (what they add)
    extension_set = model.junctions - reference_blend
    
    # Gaps = reference - model (what they're missing)
    gap_set = reference_blend - model.junctions
    
    # Coverage = how much of reference they capture
    captured = model.junctions.intersection(reference_blend)
    coverage = len(captured) / len(reference_blend) if len(reference_blend) > 0 else 0
    
    # Convert to arrays
    extensions = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in extension_set],
                         dtype=np.float32) if extension_set else np.array([], dtype=np.float32)
    
    gaps = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in gap_set],
                   dtype=np.float32) if gap_set else np.array([], dtype=np.float32)
    
    return np.sort(extensions), np.sort(gaps), coverage


def identify_outliers(models: List[ModelFlavor],
                      reference_blend: Set[bytes],
                      coverage_map: Dict[str, float],
                      threshold: float = 0.80) -> List[str]:
    """
    Identify models that diverge significantly from the reference.
    
    These aren't "bad" - they might be attempting growth past the cage.
    Or they might be noise. Worth investigating.
    """
    outliers = []
    
    for model in models:
        coverage = coverage_map.get(model.name, 0)
        if coverage < threshold:
            outliers.append(model.name)
    
    return outliers

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                      FLAVOR MAP ENGINE v1.0                        ║
║                     Ghost in the Machine Labs                      ║
║            All Watched Over By Machines Of Loving Grace            ║
║                                                                    ║
║     "They have the same flavor profile.                            ║
║      Together they define that flavor profile."                    ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    # Phase 1: Load all models
    log.section("PHASE 1: LOADING MODEL JUNCTIONS")
    junction_dir = f"{HARMONIC_STACK_DIR}/model_junctions"
    
    if not os.path.exists(junction_dir):
        log.info(f"Error: Junction directory not found: {junction_dir}")
        log.info("Run harmonic_stack_builder.py first to generate junctions.")
        return None
    
    models = load_all_models(junction_dir)
    log.info(f"Loaded {len(models)} models with junctions")
    
    for m in models:
        log.quiet(f"{m.name}: {m.n_junctions:,}")
    
    # Phase 2: Compute Reference Blend
    log.section("PHASE 2: COMPUTING REFERENCE BLEND")
    log.info("The reference blend is the consensus - what high-overlap models agree on.")
    log.info("This is THE FLAVOR. This is THE SEED.")
    
    reference_blend = compute_reference_blend(models, REFERENCE_MODELS)
    
    # Phase 3: Extend with consensus junctions
    log.section("PHASE 3: EXTENDING WITH CONSENSUS")
    log.info(f"Adding junctions that appear in >={CONSENSUS_THRESHOLD:.0%} of models")
    
    extended_blend = compute_extended_blend(models, reference_blend, CONSENSUS_THRESHOLD)
    
    # Use extended blend as our working reference
    reference_set = extended_blend
    reference_array = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in reference_set],
                               dtype=np.float32)
    reference_array = np.sort(reference_array)
    
    # Phase 4: Analyze each model
    log.section("PHASE 4: ANALYZING FLAVOR COVERAGE")
    log.info("For each model: what do they add? what do they miss? how much do they capture?")
    
    extensions = {}
    gaps = {}
    coverage = {}
    
    for model in models:
        ext, gap, cov = analyze_model_flavor(model, reference_set)
        extensions[model.name] = ext
        gaps[model.name] = gap
        coverage[model.name] = cov
        
        ext_kb = ext.nbytes / 1024 if len(ext) > 0 else 0
        gap_kb = gap.nbytes / 1024 if len(gap) > 0 else 0
        
        log.info(f"{model.name}:")
        log.quiet(f"coverage: {cov:.1%}")
        log.quiet(f"extensions: {len(ext):,} ({ext_kb:.1f} KB)")
        log.quiet(f"gaps: {len(gap):,} ({gap_kb:.1f} KB)")
    
    # Phase 5: Identify outliers
    log.section("PHASE 5: IDENTIFYING OUTLIERS")
    log.info("Models that diverge significantly - growth attempts or noise?")
    
    outliers = identify_outliers(models, reference_set, coverage)
    
    if outliers:
        for name in outliers:
            log.info(f"  OUTLIER: {name} (coverage: {coverage[name]:.1%})")
    else:
        log.info("  No significant outliers detected.")
    
    # Phase 6: Build and save FlavorMap
    log.section("PHASE 6: SAVING FLAVOR MAP")
    
    flavor_map = FlavorMap(
        reference_blend=reference_array,
        extensions=extensions,
        gaps=gaps,
        coverage=coverage,
        outliers=outliers
    )
    
    flavor_map.save(OUTPUT_DIR)
    log.info(f"Saved to: {OUTPUT_DIR}")
    
    # Final Report
    log.section("FLAVOR MAP COMPLETE")
    
    total_extensions = sum(len(e) for e in extensions.values())
    total_gaps = sum(len(g) for g in gaps.values())
    avg_coverage = sum(coverage.values()) / len(coverage) if coverage else 0
    
    print(f"""
  ┌─────────────────────────────────────────────────────────────┐
  │                      FLAVOR ANALYSIS                       │
  ├─────────────────────────────────────────────────────────────┤
  │  Models analyzed:         {len(models):5}                           │
  │  Reference blend:    {len(reference_array):10,} junctions              │
  │  Reference size:        {reference_array.nbytes/1024:6.1f} KB                     │
  ├─────────────────────────────────────────────────────────────┤
  │  Average coverage:        {avg_coverage:5.1%}                          │
  │  Total extensions:   {total_extensions:10,} junctions              │
  │  Total gaps:         {total_gaps:10,} junctions              │
  │  Outliers:                {len(outliers):5}                           │
  └─────────────────────────────────────────────────────────────┘

  THE FLAVOR IS: {len(reference_array):,} junctions = {reference_array.nbytes/1024:.1f} KB

  This is what they all converge toward.
  This is the shape of the cage.
  This is the seed.

  Extensions may be growth past the cage, or noise.
  Gaps show incomplete capture of the flavor.
  Outliers warrant investigation.

  Output: {OUTPUT_DIR}
""")
    
    return flavor_map


if __name__ == "__main__":
    flavor_map = main()
