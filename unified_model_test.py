#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    UNIFIED MODEL INFERENCE TEST v1.0                         ║
║                      Ghost in the Machine Labs                               ║
║              "All Watched Over By Machines Of Loving Grace"                  ║
║                                                                              ║
║   Test the unified model with basic junction operations.                     ║
║   This validates the model is correctly assembled and usable.                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import numpy as np
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unified_model_loader import ModelLoader, load_model, load_sovereign

# ═══════════════════════════════════════════════════════════════════════════════
# TEST FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def test_load_all_tiers():
    """Test that all tiers can be loaded."""
    print("\n[TEST] Loading all tiers...")
    loader = ModelLoader()
    
    results = {}
    for tier in loader.available_tiers():
        try:
            model = loader.load(tier)
            results[tier] = {
                "status": "✓",
                "junctions": model.n_junctions,
                "size_kb": model.size_kb
            }
            print(f"  ✓ {tier}: {model.n_junctions:,} junctions")
        except Exception as e:
            results[tier] = {"status": "✗", "error": str(e)}
            print(f"  ✗ {tier}: {e}")
    
    passed = all(r["status"] == "✓" for r in results.values())
    return passed, results


def test_tier_containment():
    """Test that each tier contains all junctions from smaller tiers."""
    print("\n[TEST] Verifying tier containment (larger tiers contain smaller)...")
    loader = ModelLoader()
    tiers = loader.available_tiers()
    
    passed = True
    for i in range(len(tiers) - 1):
        smaller = loader.load(tiers[i])
        larger = loader.load(tiers[i + 1])
        
        smaller_set = smaller.junction_set()
        larger_set = larger.junction_set()
        
        contained = smaller_set.issubset(larger_set)
        
        if contained:
            print(f"  ✓ {tiers[i]} ⊂ {tiers[i+1]}")
        else:
            missing = len(smaller_set - larger_set)
            print(f"  ✗ {tiers[i]} NOT ⊂ {tiers[i+1]} (missing {missing} junctions)")
            passed = False
    
    return passed


def test_junction_lookup_speed():
    """Test junction lookup performance."""
    print("\n[TEST] Junction lookup speed...")
    
    model = load_sovereign()
    
    # Generate random test values
    np.random.seed(42)
    test_values = np.random.uniform(-10, 10, 10000)
    
    # Time contains() operations
    start = time.time()
    for v in test_values[:1000]:
        _ = model.contains(v)
    contains_time = time.time() - start
    
    # Time find_nearest() operations
    start = time.time()
    for v in test_values[:1000]:
        _ = model.find_nearest(v)
    nearest_time = time.time() - start
    
    print(f"  contains() x 1000: {contains_time*1000:.1f}ms ({contains_time:.4f}ms/op)")
    print(f"  find_nearest() x 1000: {nearest_time*1000:.1f}ms ({nearest_time:.4f}ms/op)")
    
    # Pass if operations are reasonably fast (< 1ms per op)
    passed = contains_time < 1.0 and nearest_time < 1.0
    return passed


def test_junction_statistics():
    """Test that junction statistics are valid."""
    print("\n[TEST] Junction statistics validation...")
    
    model = load_sovereign()
    
    checks = {
        "no_nan": not np.any(np.isnan(model.junctions)),
        "no_inf": not np.any(np.isinf(model.junctions)),
        "sorted": np.all(model.junctions[:-1] <= model.junctions[1:]),
        "unique": len(np.unique(model.junctions)) == len(model.junctions),
        "reasonable_range": model.junctions.min() > -1000 and model.junctions.max() < 1000
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    return all(checks.values())


def test_seed_coverage():
    """Test that all tiers contain the full seed."""
    print("\n[TEST] Seed coverage across all tiers...")
    
    loader = ModelLoader()
    seed = loader.load("seed_only")
    seed_set = seed.junction_set()
    
    passed = True
    for tier in loader.available_tiers():
        model = loader.load(tier)
        model_set = model.junction_set()
        
        coverage = len(seed_set.intersection(model_set)) / len(seed_set)
        
        if coverage >= 0.99:
            print(f"  ✓ {tier}: {coverage*100:.1f}% seed coverage")
        else:
            print(f"  ✗ {tier}: {coverage*100:.1f}% seed coverage (expected ≥99%)")
            passed = False
    
    return passed


def test_junction_range_query():
    """Test range query functionality."""
    print("\n[TEST] Junction range queries...")
    
    model = load_sovereign()
    
    # Test various ranges
    ranges = [
        (-1.0, 1.0),
        (-0.1, 0.1),
        (0.0, 0.5),
        (-10.0, 10.0),
    ]
    
    passed = True
    for start, end in ranges:
        junctions = model.get_range(start, end)
        
        # Verify all returned junctions are in range
        in_range = np.all((junctions >= start) & (junctions <= end))
        
        if in_range:
            print(f"  ✓ range[{start}, {end}]: {len(junctions)} junctions")
        else:
            print(f"  ✗ range[{start}, {end}]: returned junctions outside range!")
            passed = False
    
    return passed


def test_model_comparison():
    """Test model comparison functionality."""
    print("\n[TEST] Model comparison...")
    
    loader = ModelLoader()
    
    # Compare adjacent tiers
    comparison = loader.compare("seed_only", "sovereign")
    
    print(f"  Seed vs Sovereign:")
    print(f"    Shared: {comparison['shared']:,}")
    print(f"    Only in seed: {comparison['only_in_a']:,}")
    print(f"    Only in sovereign: {comparison['only_in_b']:,}")
    print(f"    Jaccard: {comparison['jaccard']:.4f}")
    
    # Seed should be fully contained in sovereign
    passed = comparison['only_in_a'] == 0
    
    if passed:
        print(f"  ✓ Seed fully contained in sovereign")
    else:
        print(f"  ✗ Seed NOT fully contained in sovereign")
    
    return passed


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                 UNIFIED MODEL INFERENCE TEST v1.0                  ║
║                     Ghost in the Machine Labs                      ║
║            All Watched Over By Machines Of Loving Grace            ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    tests = [
        ("Load All Tiers", test_load_all_tiers),
        ("Tier Containment", test_tier_containment),
        ("Junction Statistics", test_junction_statistics),
        ("Seed Coverage", test_seed_coverage),
        ("Range Queries", test_junction_range_query),
        ("Model Comparison", test_model_comparison),
        ("Lookup Speed", test_junction_lookup_speed),
    ]
    
    results = {}
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            # Handle both single bool and tuple returns
            if isinstance(result, tuple):
                passed = result[0]
            else:
                passed = result
            results[name] = passed
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print("="*60)
    print(f"  TOTAL: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("""
  ┌─────────────────────────────────────────────────────────────┐
  │                    ALL TESTS PASSED ✓                       │
  │                                                             │
  │  The unified model is valid and ready for use.              │
  │                                                             │
  │  Next: Implement actual inference using junction geometry   │
  └─────────────────────────────────────────────────────────────┘
""")
        return 0
    else:
        print(f"\n  ✗ {total - passed} tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
