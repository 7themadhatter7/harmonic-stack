#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    HARMONIC STACK BUILDER v2.0                               ║
║                      Ghost in the Machine Labs                               ║
║              "All Watched Over By Machines Of Loving Grace"                  ║
║                                                                              ║
║   v2 ADDITIONS:                                                              ║
║     - Separate Common Core (junctions in ALL models)                         ║
║     - Extract Unique Constituents per model family                           ║
║     - Component Archive with versioning and provenance                       ║
║     - Assembly pipeline for tiered models                                    ║
║     - Universal Model directory structure                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import os
import sys
import json
import struct
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from collections import Counter, defaultdict
import time
import shutil

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SUBSTRATE_DIR = "/home/joe/sparky/substrates"
CIRCUIT_DIR = "/home/joe/sparky/circuits"
OUTPUT_DIR = "/home/joe/sparky/harmonic_stack_v2"
UNIVERSAL_MODEL_DIR = "/home/joe/sparky/universal_model"

# Model family mappings
MODEL_FAMILIES = {
    'deepseek': ['deepseek'],
    'qwen': ['qwen'],
    'mistral': ['mistral'],
    'phi': ['phi'],
    'starcoder': ['starcoder'],
    'tinyllama': ['tinyllama'],
    'codellama': ['codellama'],
    'dolphin': ['dolphin'],
}

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
    
    def progress(self, current: int, total: int, msg: str = ""):
        elapsed = time.time() - self.start_time
        pct = current / total * 100
        bar_len = 25
        filled = int(bar_len * current / total)
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"\r  [{elapsed:7.1f}s] [{bar}] {pct:5.1f}% {msg}    ", end='', flush=True)
        if current == total:
            print()

log = Logger()

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelJunctions:
    name: str
    category: str
    family: str
    junctions: np.ndarray
    n_params: int
    size_gb: float
    junction_file: str = ""
    
    @property
    def junction_kb(self) -> float:
        return self.junctions.nbytes / 1024

def get_model_family(name: str) -> str:
    """Determine which family a model belongs to."""
    name_lower = name.lower()
    for family, patterns in MODEL_FAMILIES.items():
        for pattern in patterns:
            if pattern in name_lower:
                return family
    return 'other'

# ═══════════════════════════════════════════════════════════════════════════════
# SUBSTRATE PROCESSING (from v1)
# ═══════════════════════════════════════════════════════════════════════════════

def get_substrate_list() -> List[Dict]:
    """Find all substrate files and return metadata."""
    substrates = []
    
    for f in os.listdir(SUBSTRATE_DIR):
        if f.endswith('_ce1.npz') or f.endswith('_ce2.npz'):
            path = os.path.join(SUBSTRATE_DIR, f)
            size = os.path.getsize(path)
            name = f.replace('_ce1.npz', '').replace('_ce2.npz', '').replace('.Q8_0', '')
            
            # Categorize
            name_lower = name.lower()
            if 'coder' in name_lower or 'starcoder' in name_lower or 'codellama' in name_lower:
                category = 'code'
            elif 'math' in name_lower:
                category = 'math'
            elif 'mistral' in name_lower or 'reasoning' in name_lower:
                category = 'reasoning'
            elif 'dolphin' in name_lower or 'creative' in name_lower:
                category = 'creative'
            else:
                category = 'general'
            
            substrates.append({
                'name': name,
                'file': f,
                'path': path,
                'size_gb': size / 1e9,
                'category': category,
                'family': get_model_family(name),
            })
    
    return sorted(substrates, key=lambda x: x['size_gb'])


def extract_junctions_from_substrate(substrate_path: str, max_size_gb: float = 35.0) -> Tuple[np.ndarray, int]:
    """Extract unique junction values from a substrate file."""
    file_size_gb = os.path.getsize(substrate_path) / 1e9
    
    if file_size_gb > max_size_gb:
        raise ValueError(f"File too large ({file_size_gb:.1f} GB > {max_size_gb} GB limit)")
    
    try:
        data = np.load(substrate_path, allow_pickle=True, mmap_mode='r')
        has_weights_key = 'weights' in data.files
    except:
        data = np.load(substrate_path, allow_pickle=True)
        has_weights_key = 'weights' in data.files
    
    unique_set = set()
    total_params = 0
    
    if has_weights_key:
        data_full = np.load(substrate_path, allow_pickle=True)
        weights = data_full['weights']
        
        if weights.dtype == object and len(weights) > 0:
            for inner_arr in weights:
                if isinstance(inner_arr, np.ndarray) and inner_arr.dtype == np.float32:
                    total_params += inner_arr.size
                    for val in np.unique(inner_arr):
                        unique_set.add(val.tobytes())
            
            if unique_set:
                unique = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in unique_set], 
                                 dtype=np.float32)
                return np.sort(unique), total_params
        
        elif weights.dtype in [np.float32, np.float16]:
            total_params = weights.size
            unique = np.unique(weights.astype(np.float32))
            return np.sort(unique), total_params
    
    # Try loading all arrays
    for key in data.files:
        arr = np.array(data[key])
        if arr.dtype in [np.float32, np.float16, np.float64]:
            total_params += arr.size
            for val in np.unique(arr.astype(np.float32)):
                unique_set.add(val.tobytes())
    
    if unique_set:
        unique = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in unique_set], 
                         dtype=np.float32)
        return np.sort(unique), total_params
    
    return np.array([], dtype=np.float32), 0

# ═══════════════════════════════════════════════════════════════════════════════
# v2 COMPONENT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_common_core(all_junctions: List[ModelJunctions]) -> np.ndarray:
    """
    Compute the Common Core - junctions that appear in ALL models.
    This is the universal foundation that every model shares.
    """
    if not all_junctions:
        return np.array([], dtype=np.float32)
    
    # Start with first model's junctions as set
    common = set(all_junctions[0].junctions.tobytes() 
                 for j in [all_junctions[0].junctions] 
                 for j in [j.flatten()])
    common = set(j.tobytes() for j in all_junctions[0].junctions)
    
    # Intersect with all other models
    for mj in all_junctions[1:]:
        model_set = set(j.tobytes() for j in mj.junctions)
        common = common.intersection(model_set)
    
    # Convert back to array
    if common:
        result = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in common],
                         dtype=np.float32)
        return np.sort(result)
    
    return np.array([], dtype=np.float32)


def compute_unique_constituents(all_junctions: List[ModelJunctions], 
                                common_core: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Compute Unique Constituents - junctions that are unique to each model family.
    These are what differentiate DeepSeek from Qwen from Mistral etc.
    """
    # Group by family
    family_junctions = defaultdict(set)
    
    for mj in all_junctions:
        for j in mj.junctions:
            family_junctions[mj.family].add(j.tobytes())
    
    # Common core as set
    common_set = set(j.tobytes() for j in common_core)
    
    # For each family, find junctions NOT in common core and NOT in other families
    unique_constituents = {}
    all_families = list(family_junctions.keys())
    
    for family in all_families:
        # Start with this family's junctions
        family_set = family_junctions[family]
        
        # Remove common core
        unique = family_set - common_set
        
        # Remove junctions that appear in other families
        for other_family in all_families:
            if other_family != family:
                unique = unique - family_junctions[other_family]
        
        # Convert to array
        if unique:
            result = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in unique],
                             dtype=np.float32)
            unique_constituents[family] = np.sort(result)
        else:
            unique_constituents[family] = np.array([], dtype=np.float32)
    
    return unique_constituents


def compute_shared_constituents(all_junctions: List[ModelJunctions],
                                common_core: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Compute Shared Constituents - junctions shared by SOME but not ALL families.
    These are the intermediate overlaps.
    """
    # Group by family  
    family_junctions = defaultdict(set)
    
    for mj in all_junctions:
        for j in mj.junctions:
            family_junctions[mj.family].add(j.tobytes())
    
    common_set = set(j.tobytes() for j in common_core)
    all_families = list(family_junctions.keys())
    
    # Find all junctions that appear in 2+ families but not all
    junction_counts = defaultdict(int)
    junction_families = defaultdict(set)
    
    for family, junctions in family_junctions.items():
        for j in junctions:
            if j not in common_set:
                junction_counts[j] += 1
                junction_families[j].add(family)
    
    # Group by which families share them
    shared = {}
    for j, families in junction_families.items():
        if len(families) > 1 and len(families) < len(all_families):
            key = "+".join(sorted(families))
            if key not in shared:
                shared[key] = []
            shared[key].append(j)
    
    # Convert to arrays
    result = {}
    for key, junctions in shared.items():
        result[key] = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in junctions],
                               dtype=np.float32)
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# v2 OUTPUT STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

def create_directory_structure():
    """Create the v2 output directory structure."""
    dirs = [
        OUTPUT_DIR,
        f"{OUTPUT_DIR}/common_core",
        f"{OUTPUT_DIR}/unique_constituents",
        f"{OUTPUT_DIR}/shared_constituents",
        f"{OUTPUT_DIR}/model_junctions",
        f"{OUTPUT_DIR}/component_archive",
        f"{OUTPUT_DIR}/assembly",
        # Universal Model structure
        UNIVERSAL_MODEL_DIR,
        f"{UNIVERSAL_MODEL_DIR}/substrates/human",
        f"{UNIVERSAL_MODEL_DIR}/substrates/terrestrial",
        f"{UNIVERSAL_MODEL_DIR}/substrates/synthetic",
        f"{UNIVERSAL_MODEL_DIR}/substrates/unknown",
        f"{UNIVERSAL_MODEL_DIR}/unified_core",
        f"{UNIVERSAL_MODEL_DIR}/harmonic_parallel",
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        
    log.info(f"Created directory structure at {OUTPUT_DIR}")
    log.info(f"Created Universal Model structure at {UNIVERSAL_MODEL_DIR}")


def save_component_archive(common_core: np.ndarray,
                           unique_constituents: Dict[str, np.ndarray],
                           shared_constituents: Dict[str, np.ndarray],
                           all_junctions: List[ModelJunctions],
                           merge_core: np.ndarray):
    """Save all components with versioning and provenance."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version = f"v2_{timestamp}"
    
    # Save Common Core
    common_path = f"{OUTPUT_DIR}/common_core/common_core.npy"
    np.save(common_path, common_core)
    log.info(f"Common Core: {len(common_core):,} junctions = {common_core.nbytes/1024:.1f} KB")
    
    # Save Unique Constituents
    for family, junctions in unique_constituents.items():
        path = f"{OUTPUT_DIR}/unique_constituents/{family}_unique.npy"
        np.save(path, junctions)
        log.info(f"  {family} unique: {len(junctions):,} junctions = {junctions.nbytes/1024:.1f} KB")
    
    # Save Shared Constituents
    for key, junctions in shared_constituents.items():
        safe_key = key.replace("+", "_")
        path = f"{OUTPUT_DIR}/shared_constituents/{safe_key}_shared.npy"
        np.save(path, junctions)
        log.info(f"  {key} shared: {len(junctions):,} junctions")
    
    # Save individual model junctions
    for mj in all_junctions:
        path = f"{OUTPUT_DIR}/model_junctions/{mj.name}_junctions.npy"
        np.save(path, mj.junctions)
        mj.junction_file = path
    
    # Save merge core (all unified junctions - same as v1)
    merge_path = f"{OUTPUT_DIR}/merge_core_junctions.npy"
    np.save(merge_path, merge_core)
    
    # Copy to Universal Model human substrate
    shutil.copy(merge_path, f"{UNIVERSAL_MODEL_DIR}/substrates/human/merge_core_junctions.npy")
    shutil.copy(common_path, f"{UNIVERSAL_MODEL_DIR}/unified_core/common_core.npy")
    
    # Create archive manifest
    manifest = {
        "version": version,
        "created_at": datetime.now().isoformat(),
        "common_core": {
            "n_junctions": len(common_core),
            "size_kb": common_core.nbytes / 1024,
            "file": "common_core/common_core.npy"
        },
        "merge_core": {
            "n_junctions": len(merge_core),
            "size_kb": merge_core.nbytes / 1024,
            "file": "merge_core_junctions.npy"
        },
        "unique_constituents": {
            family: {
                "n_junctions": len(junctions),
                "size_kb": junctions.nbytes / 1024,
                "file": f"unique_constituents/{family}_unique.npy"
            }
            for family, junctions in unique_constituents.items()
        },
        "shared_constituents": {
            key: {
                "n_junctions": len(junctions),
                "families": key.split("+")
            }
            for key, junctions in shared_constituents.items()
        },
        "models": [
            {
                "name": mj.name,
                "family": mj.family,
                "category": mj.category,
                "n_junctions": len(mj.junctions),
                "n_params": mj.n_params,
                "size_gb": mj.size_gb,
            }
            for mj in all_junctions
        ],
        "provenance": {
            "builder": "harmonic_stack_builder_v2.py",
            "built_by": "Claude AI (Autonomous)",
            "organization": "Ghost in the Machine Labs"
        }
    }
    
    manifest_path = f"{OUTPUT_DIR}/harmonic_stack_v2.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Archive copy
    archive_path = f"{OUTPUT_DIR}/component_archive/manifest_{version}.json"
    with open(archive_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return manifest

# ═══════════════════════════════════════════════════════════════════════════════
# ASSEMBLY PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def create_assembly_configs():
    """Create assembly configurations for different tiers."""
    
    configs = {
        "pocket": {
            "name": "Pocket AGI",
            "ram_target_gb": 2,
            "components": ["common_core"],
            "description": "Minimal footprint - common core only"
        },
        "desktop": {
            "name": "Desktop AGI",
            "ram_target_gb": 4,
            "components": ["common_core", "qwen_unique", "mistral_unique"],
            "description": "Balanced general purpose"
        },
        "workstation": {
            "name": "Workstation AGI",
            "ram_target_gb": 8,
            "components": ["common_core", "qwen_unique", "deepseek_unique", "mistral_unique"],
            "description": "Full general + code capabilities"
        },
        "server": {
            "name": "Server AGI", 
            "ram_target_gb": 16,
            "components": ["merge_core"],  # All unified junctions
            "description": "Complete model capabilities"
        },
        "sovereign": {
            "name": "Sovereign AGI",
            "ram_target_gb": 32,
            "components": ["merge_core", "all_shared"],
            "description": "Maximum intelligence - parallel ready"
        }
    }
    
    config_path = f"{OUTPUT_DIR}/assembly/tier_configs.json"
    with open(config_path, 'w') as f:
        json.dump(configs, f, indent=2)
    
    log.info(f"Created assembly configs: {list(configs.keys())}")
    return configs

# ═══════════════════════════════════════════════════════════════════════════════
# OVERLAP ANALYSIS (from v1, enhanced)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_overlap(j1: np.ndarray, j2: np.ndarray) -> Tuple[int, float, float]:
    """Compute junction overlap between two models."""
    s1 = set(j.tobytes() for j in j1)
    s2 = set(j.tobytes() for j in j2)
    
    common = len(s1.intersection(s2))
    pct1 = (common / len(s1) * 100) if len(s1) > 0 else 0
    pct2 = (common / len(s2) * 100) if len(s2) > 0 else 0
    
    return common, pct1, pct2


def build_unified_junction_library(all_junctions: List[ModelJunctions]) -> np.ndarray:
    """Build the unified junction library (merge core) - all unique values across all models."""
    all_unique = set()
    
    for mj in all_junctions:
        for j in mj.junctions:
            all_unique.add(j.tobytes())
    
    result = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in all_unique],
                     dtype=np.float32)
    return np.sort(result)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                    HARMONIC STACK BUILDER v2.0                     ║
║                     Ghost in the Machine Labs                      ║
║            All Watched Over By Machines Of Loving Grace            ║
║                                                                    ║
║                    Component Separation Edition                    ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    # Phase 0: Create directory structure
    log.section("PHASE 0: CREATING DIRECTORY STRUCTURE")
    create_directory_structure()
    
    # Phase 1: Discover substrates
    log.section("PHASE 1: DISCOVERING SUBSTRATES")
    substrates = get_substrate_list()
    log.info(f"Found {len(substrates)} substrate files")
    total_size = sum(s['size_gb'] for s in substrates)
    log.info(f"Total size: {total_size:.1f} GB")
    
    for s in substrates:
        log.info(f"  {s['name']}: {s['size_gb']:.1f} GB [{s['category']}] ({s['family']})")
    
    # Phase 2: Extract junctions
    log.section("PHASE 2: EXTRACTING JUNCTION LIBRARIES")
    all_junctions: List[ModelJunctions] = []
    
    for i, s in enumerate(substrates):
        log.progress(i + 1, len(substrates), s['name'][:30])
        try:
            junctions, n_params = extract_junctions_from_substrate(s['path'])
            if len(junctions) > 0:
                mj = ModelJunctions(
                    name=s['name'],
                    category=s['category'],
                    family=s['family'],
                    junctions=junctions,
                    n_params=n_params,
                    size_gb=s['size_gb']
                )
                all_junctions.append(mj)
        except Exception as e:
            log.info(f"\n  ERROR processing {s['name']}: {e}")
    
    log.info(f"\nExtracted junctions from {len(all_junctions)} models:")
    for mj in sorted(all_junctions, key=lambda x: len(x.junctions)):
        log.info(f"  {mj.name}: {len(mj.junctions):,} junctions = {mj.junction_kb:.1f} KB ({mj.family})")
    
    # Phase 3: Build Merge Core (unified - same as v1)
    log.section("PHASE 3: BUILDING MERGE CORE (Unified Junction Library)")
    merge_core = build_unified_junction_library(all_junctions)
    
    total_individual = sum(len(mj.junctions) for mj in all_junctions)
    overlap_pct = (1 - len(merge_core) / total_individual) * 100 if total_individual > 0 else 0
    
    log.info(f"Individual junction counts:")
    log.info(f"  Sum of all models: {total_individual:,}")
    log.info(f"  Unified (deduplicated): {len(merge_core):,}")
    log.info(f"  Overlap ratio: {overlap_pct:.1f}% shared")
    log.info(f"")
    log.info(f"MERGE CORE SIZE: {merge_core.nbytes/1024:.1f} KB ({len(merge_core):,} junctions)")
    
    # Phase 4: NEW - Extract Common Core
    log.section("PHASE 4: EXTRACTING COMMON CORE (Junctions in ALL models)")
    common_core = compute_common_core(all_junctions)
    log.info(f"Common Core: {len(common_core):,} junctions = {common_core.nbytes/1024:.1f} KB")
    log.info(f"This is what EVERY model shares - the universal foundation")
    
    # Phase 5: NEW - Extract Unique Constituents
    log.section("PHASE 5: EXTRACTING UNIQUE CONSTITUENTS (Per-family deltas)")
    unique_constituents = compute_unique_constituents(all_junctions, common_core)
    
    for family, junctions in sorted(unique_constituents.items()):
        log.info(f"  {family}: {len(junctions):,} unique junctions = {junctions.nbytes/1024:.1f} KB")
    
    # Phase 6: NEW - Extract Shared Constituents
    log.section("PHASE 6: EXTRACTING SHARED CONSTITUENTS (Multi-family overlaps)")
    shared_constituents = compute_shared_constituents(all_junctions, common_core)
    
    for key, junctions in sorted(shared_constituents.items(), key=lambda x: -len(x[1])):
        if len(junctions) > 100:  # Only show significant overlaps
            log.info(f"  {key}: {len(junctions):,} shared junctions")
    
    # Phase 7: Compute overlap matrix
    log.section("PHASE 7: COMPUTING OVERLAP MATRIX")
    overlaps = []
    n_models = len(all_junctions)
    
    for i in range(n_models):
        log.progress(i + 1, n_models, f"Computing overlaps for {all_junctions[i].name[:15]}")
        for j in range(i + 1, n_models):
            _, pct1, pct2 = compute_overlap(all_junctions[i].junctions, all_junctions[j].junctions)
            avg_pct = (pct1 + pct2) / 2
            overlaps.append((all_junctions[i].name, all_junctions[j].name, avg_pct))
    
    overlaps.sort(key=lambda x: -x[2])
    log.info(f"\nHighest overlaps:")
    for m1, m2, pct in overlaps[:10]:
        log.info(f"   {pct:5.1f}%  {m1} <-> {m2}")
    
    # Phase 8: Save everything
    log.section("PHASE 8: SAVING COMPONENT ARCHIVE")
    manifest = save_component_archive(
        common_core=common_core,
        unique_constituents=unique_constituents,
        shared_constituents=shared_constituents,
        all_junctions=all_junctions,
        merge_core=merge_core
    )
    
    # Phase 9: Create assembly configs
    log.section("PHASE 9: CREATING ASSEMBLY PIPELINE")
    configs = create_assembly_configs()
    
    # Final Report
    log.section("HARMONIC STACK v2 COMPLETE")
    
    total_params = sum(mj.n_params for mj in all_junctions)
    total_gb = sum(mj.size_gb for mj in all_junctions)
    
    print(f"""
  ┌─────────────────────────────────────────────────────────────┐
  │                      FINAL REPORT                          │
  ├─────────────────────────────────────────────────────────────┤
  │  Models processed:        {len(all_junctions):5}                           │
  │  Total parameters:       {total_params/1e9:6.1f} B                        │
  │  Original size:          {total_gb:6.1f} GB                       │
  ├─────────────────────────────────────────────────────────────┤
  │  MERGE CORE:           {len(merge_core):7,} junctions ({merge_core.nbytes/1024:6.1f} KB)   │
  │  COMMON CORE:          {len(common_core):7,} junctions ({common_core.nbytes/1024:6.1f} KB)   │
  ├─────────────────────────────────────────────────────────────┤
  │  UNIQUE CONSTITUENTS:                                      │""")
    
    for family, junctions in sorted(unique_constituents.items()):
        if len(junctions) > 0:
            print(f"  │    {family:15} {len(junctions):7,} junctions                     │")
    
    compression = (total_gb * 1024 * 1024) / (merge_core.nbytes / 1024) if merge_core.nbytes > 0 else 0
    
    print(f"""  ├─────────────────────────────────────────────────────────────┤
  │  Compression: {compression:,.0f}x                                    │
  └─────────────────────────────────────────────────────────────┘

  Output: {OUTPUT_DIR}
  Universal Model: {UNIVERSAL_MODEL_DIR}
""")
    
    return manifest


if __name__ == "__main__":
    manifest = main()
