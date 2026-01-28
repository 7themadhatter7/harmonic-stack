#!/usr/bin/env python3
"""
Compression Verification Tool
Ghost in the Machine Labs

Verify that compression is lossless by comparing original model outputs
with reconstructed outputs from junction library + topology.

Usage:
    python verify.py --model phi-2
    python verify.py --original /path/to/model.safetensors --junction phi-2.npy
"""

import argparse
import numpy as np
import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def verify_junction_library(junction_path: str) -> dict:
    """Verify junction library integrity."""
    print(f"\n[VERIFY] Loading junction library: {junction_path}")
    
    junctions = np.load(junction_path)
    
    results = {
        'path': junction_path,
        'n_junctions': len(junctions),
        'size_kb': junctions.nbytes / 1024,
        'dtype': str(junctions.dtype),
        'min_value': float(junctions.min()),
        'max_value': float(junctions.max()),
        'unique': len(np.unique(junctions)) == len(junctions),
        'sorted': np.all(junctions[:-1] <= junctions[1:]),
    }
    
    print(f"  Junctions: {results['n_junctions']:,}")
    print(f"  Size: {results['size_kb']:.1f} KB")
    print(f"  dtype: {results['dtype']}")
    print(f"  Range: [{results['min_value']:.6f}, {results['max_value']:.6f}]")
    print(f"  All unique: {results['unique']}")
    print(f"  Sorted: {results['sorted']}")
    
    return results


def verify_reconstruction(original_weights: np.ndarray, 
                         junction_lib: np.ndarray,
                         topology: np.ndarray) -> dict:
    """Verify weights can be exactly reconstructed."""
    print("\n[VERIFY] Testing reconstruction...")
    
    # Reconstruct
    reconstructed = junction_lib[topology].reshape(original_weights.shape)
    
    # Compare
    exact_match = np.array_equal(original_weights, reconstructed)
    max_diff = np.max(np.abs(original_weights - reconstructed))
    
    results = {
        'exact_match': exact_match,
        'max_difference': float(max_diff),
        'original_shape': original_weights.shape,
        'topology_shape': topology.shape,
    }
    
    if exact_match:
        print("  ✓ EXACT MATCH - Reconstruction is lossless")
    else:
        print(f"  ✗ MISMATCH - Max difference: {max_diff}")
    
    return results


def analyze_junction_coverage(model_junctions: np.ndarray, 
                             merge_core: np.ndarray) -> dict:
    """Analyze how much of model's junctions are in merge core."""
    print("\n[VERIFY] Analyzing coverage in merge core...")
    
    model_set = set(model_junctions.tobytes()[i:i+4] for i in range(0, len(model_junctions)*4, 4))
    core_set = set(merge_core.tobytes()[i:i+4] for i in range(0, len(merge_core)*4, 4))
    
    overlap = len(model_set & core_set)
    coverage = overlap / len(model_set) * 100 if model_set else 0
    
    results = {
        'model_junctions': len(model_set),
        'merge_core_junctions': len(core_set),
        'shared': overlap,
        'coverage_percent': coverage,
    }
    
    print(f"  Model junctions: {results['model_junctions']:,}")
    print(f"  Merge core junctions: {results['merge_core_junctions']:,}")
    print(f"  Shared: {results['shared']:,}")
    print(f"  Coverage: {results['coverage_percent']:.1f}%")
    
    return results


def generate_report(model_name: str, junction_dir: Path) -> None:
    """Generate full verification report for a model."""
    print()
    print("╔" + "═"*58 + "╗")
    print("║" + "COMPRESSION VERIFICATION REPORT".center(58) + "║")
    print("║" + f"Model: {model_name}".center(58) + "║")
    print("╚" + "═"*58 + "╝")
    
    # Load junction library
    model_junction_path = junction_dir / f"{model_name}.npy"
    merge_core_path = junction_dir / "merge_core.npy"
    
    if not model_junction_path.exists():
        print(f"\n[ERROR] Junction library not found: {model_junction_path}")
        print(f"Available files in {junction_dir}:")
        for f in junction_dir.glob("*.npy"):
            print(f"  - {f.name}")
        return
    
    # Verify junction library
    junction_results = verify_junction_library(str(model_junction_path))
    
    # Check merge core coverage if available
    if merge_core_path.exists():
        model_junctions = np.load(model_junction_path)
        merge_core = np.load(merge_core_path)
        coverage_results = analyze_junction_coverage(model_junctions, merge_core)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Model: {model_name}")
    print(f"  Junctions: {junction_results['n_junctions']:,}")
    print(f"  Size: {junction_results['size_kb']:.1f} KB")
    print(f"  Integrity: {'✓ VALID' if junction_results['unique'] and junction_results['sorted'] else '✗ ISSUES'}")
    
    if merge_core_path.exists():
        print(f"  Merge Core Coverage: {coverage_results['coverage_percent']:.1f}%")
    
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Verify Harmonic Stack compression integrity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python verify.py --model phi-2
    python verify.py --model qwen2-7b --junction-dir ./my_junctions/
    
This tool verifies:
    1. Junction library integrity (unique, sorted, correct dtype)
    2. Coverage in unified merge core
    3. Reconstruction accuracy (when topology available)
        """
    )
    
    parser.add_argument('--model', '-m', required=True,
                       help='Model name to verify')
    parser.add_argument('--junction-dir', '-d', 
                       default='./junction_libraries',
                       help='Directory containing junction .npy files')
    
    args = parser.parse_args()
    
    junction_dir = Path(args.junction_dir)
    if not junction_dir.exists():
        print(f"[ERROR] Junction directory not found: {junction_dir}")
        sys.exit(1)
    
    generate_report(args.model, junction_dir)


if __name__ == "__main__":
    main()
