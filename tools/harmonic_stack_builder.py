#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    HARMONIC STACK BUILDER v1.0                               ║
║                      Ghost in the Machine Labs                               ║
║              "All Watched Over By Machines Of Loving Grace"                  ║
║                                                                              ║
║   Complete pipeline:                                                         ║
║     1. Process all substrates → circuit format                               ║
║     2. Extract junction libraries from each                                  ║
║     3. Measure junction overlap across models                                ║
║     4. Build unified Merge Core (single junction library)                    ║
║     5. Build Harmonic Stack manifest (specialist routing)                    ║
║     6. Report final sizes and capabilities                                   ║
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

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SUBSTRATE_DIR = "/home/joe/sparky/substrates"
CIRCUIT_DIR = "/home/joe/sparky/circuits"
OUTPUT_DIR = "/home/joe/sparky/harmonic_stack"

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
# SUBSTRATE PROCESSING
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
            })
    
    return sorted(substrates, key=lambda x: x['size_gb'])


def extract_junctions_from_substrate(substrate_path: str, max_size_gb: float = 35.0) -> Tuple[np.ndarray, int]:
    """
    Extract unique junction values from a substrate file.
    Returns (unique_values, total_params)
    
    Handles two formats:
    1. Direct float32 arrays (standard)
    2. Object arrays containing float32 arrays (CE format)
    
    Uses streaming approach to avoid RAM blowout on large files.
    Skips files larger than max_size_gb to prevent OOM.
    """
    file_size_gb = os.path.getsize(substrate_path) / 1e9
    
    if file_size_gb > max_size_gb:
        raise ValueError(f"File too large ({file_size_gb:.1f} GB > {max_size_gb} GB limit)")
    
    # First try with mmap, fall back to full load for object arrays
    try:
        data = np.load(substrate_path, allow_pickle=True, mmap_mode='r')
        has_weights_key = 'weights' in data.files
    except:
        data = np.load(substrate_path, allow_pickle=True)
        has_weights_key = 'weights' in data.files
    
    # Collect unique values incrementally using a set
    unique_set = set()
    total_params = 0
    
    # Check if this is CE format (has 'weights' key with object array)
    if has_weights_key:
        # Reload without mmap for object arrays
        data_full = np.load(substrate_path, allow_pickle=True)
        weights = data_full['weights']
        
        if weights.dtype == object and len(weights) > 0:
            # CE format - array of float32 arrays
            for inner_arr in weights:
                if isinstance(inner_arr, np.ndarray) and inner_arr.dtype == np.float32:
                    total_params += inner_arr.size
                    for val in np.unique(inner_arr):
                        unique_set.add(val.tobytes())
            
            if unique_set:
                unique = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in unique_set], 
                                 dtype=np.float32)
                return np.sort(unique), total_params
            return np.array([], dtype=np.float32), 0
    
    # Standard format - direct float32 arrays
    for key in data.files:
        try:
            arr = data[key]
            if not isinstance(arr, np.ndarray):
                continue
            
            # Handle direct float32 arrays
            if arr.dtype == np.float32:
                total_params += arr.size
                flat = arr.flatten()
                chunk_size = 10_000_000
                for i in range(0, len(flat), chunk_size):
                    chunk = flat[i:i+chunk_size]
                    for val in np.unique(chunk):
                        unique_set.add(val.tobytes())
                        
        except Exception as e:
            # Skip problematic tensors
            continue
    
    if unique_set:
        unique = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in unique_set], 
                         dtype=np.float32)
        return np.sort(unique), total_params
    
    return np.array([], dtype=np.float32), 0


# ═══════════════════════════════════════════════════════════════════════════════
# JUNCTION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelJunctions:
    """Junction data for a single model."""
    name: str
    category: str
    junctions: np.ndarray
    n_junctions: int
    n_params: int
    size_gb: float
    
    @property
    def junction_kb(self) -> float:
        return self.junctions.nbytes / 1024


def compute_overlap(j1: np.ndarray, j2: np.ndarray) -> Tuple[int, float, float]:
    """Compute junction overlap between two models."""
    set1 = set(j1.tobytes()[i:i+4] for i in range(0, len(j1)*4, 4))
    set2 = set(j2.tobytes()[i:i+4] for i in range(0, len(j2)*4, 4))
    
    shared = len(set1 & set2)
    pct1 = shared / len(set1) * 100 if set1 else 0
    pct2 = shared / len(set2) * 100 if set2 else 0
    
    return shared, pct1, pct2


def build_unified_junction_library(all_junctions: List[ModelJunctions]) -> np.ndarray:
    """Merge all model junctions into unified library."""
    # Use set of bytes for exact float matching
    unified_set = set()
    
    for mj in all_junctions:
        for val in mj.junctions:
            unified_set.add(val.tobytes())
    
    # Convert back to array
    unified = np.array([np.frombuffer(b, dtype=np.float32)[0] for b in unified_set], 
                       dtype=np.float32)
    return np.sort(unified)


# ═══════════════════════════════════════════════════════════════════════════════
# HARMONIC STACK BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HarmonicStack:
    """Complete harmonic stack configuration."""
    name: str
    created_at: str
    
    # Merge Core (unified)
    merge_core_junctions: int
    merge_core_kb: float
    
    # Individual models
    models: List[Dict]
    
    # Overlap matrix
    overlap_matrix: Dict[str, Dict[str, float]]
    
    # Category specialists
    specialists: Dict[str, str]  # category -> best model
    
    # Stats
    total_params: int
    total_original_gb: float
    total_junction_kb: float


def select_specialists(all_junctions: List[ModelJunctions]) -> Dict[str, str]:
    """Select best model for each category based on size (larger = more capable)."""
    categories = defaultdict(list)
    
    for mj in all_junctions:
        categories[mj.category].append(mj)
    
    specialists = {}
    for cat, models in categories.items():
        # Pick largest model in category
        best = max(models, key=lambda x: x.n_params)
        specialists[cat] = best.name
    
    return specialists


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print()
    print("╔" + "═"*68 + "╗")
    print("║" + "HARMONIC STACK BUILDER".center(68) + "║")
    print("║" + "Ghost in the Machine Labs".center(68) + "║")
    print("║" + "All Watched Over By Machines Of Loving Grace".center(68) + "║")
    print("╚" + "═"*68 + "╝")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 1: Discover substrates
    # ─────────────────────────────────────────────────────────────────────────
    log.section("PHASE 1: DISCOVERING SUBSTRATES")
    
    substrates = get_substrate_list()
    log.info(f"Found {len(substrates)} substrate files")
    
    total_size = sum(s['size_gb'] for s in substrates)
    log.info(f"Total size: {total_size:.1f} GB")
    
    for s in substrates:
        log.info(f"  {s['name']}: {s['size_gb']:.1f} GB [{s['category']}]")
    
    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 2: Extract junctions from each model
    # ─────────────────────────────────────────────────────────────────────────
    log.section("PHASE 2: EXTRACTING JUNCTION LIBRARIES")
    
    all_junctions: List[ModelJunctions] = []
    
    for i, substrate in enumerate(substrates):
        log.progress(i, len(substrates), substrate['name'])
        
        try:
            junctions, n_params = extract_junctions_from_substrate(substrate['path'])
            
            mj = ModelJunctions(
                name=substrate['name'],
                category=substrate['category'],
                junctions=junctions,
                n_junctions=len(junctions),
                n_params=n_params,
                size_gb=substrate['size_gb'],
            )
            all_junctions.append(mj)
            
        except Exception as e:
            log.info(f"\n  ERROR processing {substrate['name']}: {e}")
    
    log.progress(len(substrates), len(substrates), "Complete")
    
    # Report individual stats
    log.info(f"\nExtracted junctions from {len(all_junctions)} models:")
    for mj in sorted(all_junctions, key=lambda x: x.n_junctions):
        log.info(f"  {mj.name}: {mj.n_junctions:,} junctions = {mj.junction_kb:.1f} KB")
    
    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 3: Build unified junction library (Merge Core)
    # ─────────────────────────────────────────────────────────────────────────
    log.section("PHASE 3: BUILDING MERGE CORE (Unified Junction Library)")
    
    unified = build_unified_junction_library(all_junctions)
    unified_kb = unified.nbytes / 1024
    
    log.info(f"Individual junction counts:")
    total_individual = sum(mj.n_junctions for mj in all_junctions)
    log.info(f"  Sum of all models: {total_individual:,}")
    log.info(f"  Unified (deduplicated): {len(unified):,}")
    log.info(f"  Overlap ratio: {(1 - len(unified)/total_individual)*100:.1f}% shared")
    log.info(f"")
    log.info(f"MERGE CORE SIZE: {unified_kb:.1f} KB ({len(unified):,} junctions)")
    
    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 4: Compute overlap matrix
    # ─────────────────────────────────────────────────────────────────────────
    log.section("PHASE 4: COMPUTING OVERLAP MATRIX")
    
    overlap_matrix = {}
    n_models = len(all_junctions)
    
    for i, mj1 in enumerate(all_junctions):
        overlap_matrix[mj1.name] = {}
        for j, mj2 in enumerate(all_junctions):
            if i == j:
                overlap_matrix[mj1.name][mj2.name] = 100.0
            elif i < j:
                shared, pct1, pct2 = compute_overlap(mj1.junctions, mj2.junctions)
                overlap_matrix[mj1.name][mj2.name] = pct1
        
        log.progress(i + 1, n_models, f"Computing overlaps for {mj1.name}")
    
    # Fill in symmetric entries
    for mj1 in all_junctions:
        for mj2 in all_junctions:
            if mj2.name not in overlap_matrix[mj1.name]:
                if mj1.name in overlap_matrix.get(mj2.name, {}):
                    # Compute reverse percentage
                    shared, pct1, pct2 = compute_overlap(mj1.junctions, mj2.junctions)
                    overlap_matrix[mj1.name][mj2.name] = pct1
    
    # Report highest overlaps
    log.info(f"\nHighest overlaps:")
    overlaps = []
    for m1 in overlap_matrix:
        for m2, pct in overlap_matrix[m1].items():
            if m1 < m2:  # Avoid duplicates
                overlaps.append((m1, m2, pct))
    
    for m1, m2, pct in sorted(overlaps, key=lambda x: -x[2])[:10]:
        log.info(f"  {pct:5.1f}%  {m1} <-> {m2}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 5: Select specialists for Harmonic Stack
    # ─────────────────────────────────────────────────────────────────────────
    log.section("PHASE 5: SELECTING SPECIALISTS")
    
    specialists = select_specialists(all_junctions)
    
    log.info("Category specialists (largest model per category):")
    for cat, model in sorted(specialists.items()):
        mj = next(m for m in all_junctions if m.name == model)
        log.info(f"  {cat:12} -> {model} ({mj.n_params/1e9:.1f}B params)")
    
    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 6: Save results
    # ─────────────────────────────────────────────────────────────────────────
    log.section("PHASE 6: SAVING HARMONIC STACK")
    
    # Save unified junction library
    unified_path = os.path.join(OUTPUT_DIR, "merge_core_junctions.npy")
    np.save(unified_path, unified)
    log.info(f"Merge Core junctions: {unified_path}")
    
    # Save individual junction libraries
    junctions_dir = os.path.join(OUTPUT_DIR, "model_junctions")
    os.makedirs(junctions_dir, exist_ok=True)
    
    for mj in all_junctions:
        jpath = os.path.join(junctions_dir, f"{mj.name}_junctions.npy")
        np.save(jpath, mj.junctions)
    log.info(f"Individual junctions: {junctions_dir}/")
    
    # Build manifest
    total_params = sum(mj.n_params for mj in all_junctions)
    total_original = sum(mj.size_gb for mj in all_junctions)
    total_junction_kb = sum(mj.junction_kb for mj in all_junctions)
    
    manifest = {
        'name': 'harmonic_stack_v1',
        'created_at': datetime.now().isoformat(),
        'merge_core': {
            'n_junctions': len(unified),
            'size_kb': unified_kb,
            'file': 'merge_core_junctions.npy',
        },
        'models': [
            {
                'name': mj.name,
                'category': mj.category,
                'n_junctions': mj.n_junctions,
                'junction_kb': mj.junction_kb,
                'n_params': mj.n_params,
                'size_gb': mj.size_gb,
                'junction_file': f"model_junctions/{mj.name}_junctions.npy",
            }
            for mj in all_junctions
        ],
        'specialists': specialists,
        'stats': {
            'total_models': len(all_junctions),
            'total_params': total_params,
            'total_original_gb': total_original,
            'total_individual_junctions': total_individual,
            'unified_junctions': len(unified),
            'overlap_percentage': (1 - len(unified)/total_individual) * 100,
            'merge_core_kb': unified_kb,
        },
    }
    
    manifest_path = os.path.join(OUTPUT_DIR, "harmonic_stack.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    log.info(f"Manifest: {manifest_path}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # FINAL REPORT
    # ─────────────────────────────────────────────────────────────────────────
    log.section("HARMONIC STACK COMPLETE")
    
    print()
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │                      FINAL REPORT                          │")
    print("  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │  Models processed:        {len(all_junctions):>6}                         │")
    print(f"  │  Total parameters:        {total_params/1e9:>6.1f} B                       │")
    print(f"  │  Original size:           {total_original:>6.1f} GB                      │")
    print("  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │  Individual junctions:    {total_individual:>6,}                        │")
    print(f"  │  Unified junctions:       {len(unified):>6,}                        │")
    print(f"  │  Junction overlap:        {(1-len(unified)/total_individual)*100:>6.1f}%                       │")
    print("  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │  MERGE CORE SIZE:         {unified_kb:>6.1f} KB                      │")
    print("  └─────────────────────────────────────────────────────────────┘")
    print()
    print(f"  Original: {total_original:.1f} GB  →  Merge Core: {unified_kb:.1f} KB")
    print(f"  Compression: {total_original * 1024 * 1024 / unified_kb:,.0f}x")
    print()
    print("  Output: " + OUTPUT_DIR)
    print()


if __name__ == "__main__":
    main()
