#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    UNIFIED MODEL PERFORMANCE BENCHMARK                       ║
║                      Ghost in the Machine Labs                               ║
║              "All Watched Over By Machines Of Loving Grace"                  ║
║                                                                              ║
║   Comprehensive performance metrics for whitepaper publication.              ║
║                                                                              ║
║   Benchmarks:                                                                ║
║     - Load time per tier                                                     ║
║     - Memory footprint                                                       ║
║     - Junction lookup latency (contains, find_nearest)                       ║
║     - Range query performance                                                ║
║     - Set operations (intersection, union, difference)                       ║
║     - Scaling characteristics                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
import gc
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, field, asdict
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unified_model_loader import ModelLoader, UnifiedModel

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BENCHMARK_ITERATIONS = 5
LOOKUP_ITERATIONS = 10000
RANGE_QUERY_ITERATIONS = 1000
SET_OP_ITERATIONS = 100

OUTPUT_DIR = "/home/joe/sparky/benchmarks"

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BenchmarkResult:
    """Results from a single benchmark."""
    name: str
    tier: str
    iterations: int
    total_time_ms: float
    mean_time_ms: float
    std_time_ms: float
    min_time_ms: float
    max_time_ms: float
    ops_per_second: float
    
    def to_dict(self):
        return asdict(self)


@dataclass
class TierMetrics:
    """Complete metrics for a tier."""
    tier: str
    n_junctions: int
    size_kb: float
    size_mb: float
    load_time_ms: float
    memory_mb: float
    
    # Lookup benchmarks
    contains_mean_us: float = 0.0
    contains_ops_per_sec: float = 0.0
    find_nearest_mean_us: float = 0.0
    find_nearest_ops_per_sec: float = 0.0
    
    # Range query benchmarks
    range_query_mean_us: float = 0.0
    range_query_ops_per_sec: float = 0.0
    
    # Set operation benchmarks
    junction_set_build_ms: float = 0.0
    
    def to_dict(self):
        return asdict(self)


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    timestamp: str
    system_info: Dict
    tier_metrics: List[TierMetrics]
    comparative_analysis: Dict
    scaling_analysis: Dict
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "system_info": self.system_info,
            "tier_metrics": [t.to_dict() for t in self.tier_metrics],
            "comparative_analysis": self.comparative_analysis,
            "scaling_analysis": self.scaling_analysis
        }

# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def benchmark_load_time(loader: ModelLoader, tier: str, iterations: int = 5) -> Tuple[float, float]:
    """Benchmark model load time."""
    times = []
    
    for _ in range(iterations):
        # Clear cache
        if tier in loader.loaded_models:
            del loader.loaded_models[tier]
        gc.collect()
        
        start = time.perf_counter()
        _ = loader.load(tier)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
    
    return np.mean(times), np.std(times)


def benchmark_memory_footprint(model: UnifiedModel) -> float:
    """Measure memory footprint of a loaded model in MB."""
    # Junction array memory
    junction_bytes = model.junctions.nbytes
    
    # Estimate overhead (manifest dict, etc.)
    overhead_estimate = 1024  # ~1KB overhead
    
    total_bytes = junction_bytes + overhead_estimate
    return total_bytes / (1024 * 1024)


def benchmark_contains(model: UnifiedModel, iterations: int = 10000) -> BenchmarkResult:
    """Benchmark contains() operation."""
    np.random.seed(42)
    
    # Mix of values that exist and don't exist
    existing = model.junctions[np.random.choice(len(model.junctions), iterations // 2)]
    random_vals = np.random.uniform(model.junctions.min(), model.junctions.max(), iterations // 2)
    test_values = np.concatenate([existing, random_vals])
    np.random.shuffle(test_values)
    
    times = []
    for v in test_values:
        start = time.perf_counter()
        _ = model.contains(float(v))
        elapsed = (time.perf_counter() - start) * 1e6  # microseconds
        times.append(elapsed)
    
    times = np.array(times)
    total_ms = times.sum() / 1000
    
    return BenchmarkResult(
        name="contains",
        tier=model.tier,
        iterations=iterations,
        total_time_ms=total_ms,
        mean_time_ms=times.mean() / 1000,
        std_time_ms=times.std() / 1000,
        min_time_ms=times.min() / 1000,
        max_time_ms=times.max() / 1000,
        ops_per_second=iterations / (total_ms / 1000)
    )


def benchmark_find_nearest(model: UnifiedModel, iterations: int = 10000) -> BenchmarkResult:
    """Benchmark find_nearest() operation."""
    np.random.seed(43)
    test_values = np.random.uniform(model.junctions.min() * 1.5, model.junctions.max() * 1.5, iterations)
    
    times = []
    for v in test_values:
        start = time.perf_counter()
        _ = model.find_nearest(float(v))
        elapsed = (time.perf_counter() - start) * 1e6  # microseconds
        times.append(elapsed)
    
    times = np.array(times)
    total_ms = times.sum() / 1000
    
    return BenchmarkResult(
        name="find_nearest",
        tier=model.tier,
        iterations=iterations,
        total_time_ms=total_ms,
        mean_time_ms=times.mean() / 1000,
        std_time_ms=times.std() / 1000,
        min_time_ms=times.min() / 1000,
        max_time_ms=times.max() / 1000,
        ops_per_second=iterations / (total_ms / 1000)
    )


def benchmark_range_query(model: UnifiedModel, iterations: int = 1000) -> BenchmarkResult:
    """Benchmark get_range() operation."""
    np.random.seed(44)
    
    # Generate random ranges
    min_val, max_val = model.junctions.min(), model.junctions.max()
    range_size = (max_val - min_val) * 0.1  # 10% of total range
    
    starts = np.random.uniform(min_val, max_val - range_size, iterations)
    
    times = []
    for start in starts:
        end = start + range_size
        t_start = time.perf_counter()
        _ = model.get_range(float(start), float(end))
        elapsed = (time.perf_counter() - t_start) * 1e6  # microseconds
        times.append(elapsed)
    
    times = np.array(times)
    total_ms = times.sum() / 1000
    
    return BenchmarkResult(
        name="range_query",
        tier=model.tier,
        iterations=iterations,
        total_time_ms=total_ms,
        mean_time_ms=times.mean() / 1000,
        std_time_ms=times.std() / 1000,
        min_time_ms=times.min() / 1000,
        max_time_ms=times.max() / 1000,
        ops_per_second=iterations / (total_ms / 1000)
    )


def benchmark_junction_set_build(model: UnifiedModel, iterations: int = 10) -> float:
    """Benchmark junction_set() build time."""
    times = []
    
    for _ in range(iterations):
        start = time.perf_counter()
        _ = model.junction_set()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
    
    return np.mean(times)


def run_tier_benchmarks(loader: ModelLoader, tier: str) -> TierMetrics:
    """Run all benchmarks for a single tier."""
    print(f"\n  Benchmarking: {tier}")
    
    # Load time
    print(f"    Load time...", end=" ", flush=True)
    load_mean, load_std = benchmark_load_time(loader, tier, BENCHMARK_ITERATIONS)
    print(f"{load_mean:.2f}ms")
    
    # Load model for remaining tests
    model = loader.load(tier)
    
    # Memory
    print(f"    Memory footprint...", end=" ", flush=True)
    memory_mb = benchmark_memory_footprint(model)
    print(f"{memory_mb:.3f} MB")
    
    # Contains
    print(f"    contains() x {LOOKUP_ITERATIONS}...", end=" ", flush=True)
    contains_result = benchmark_contains(model, LOOKUP_ITERATIONS)
    print(f"{contains_result.mean_time_ms*1000:.2f}μs/op")
    
    # Find nearest
    print(f"    find_nearest() x {LOOKUP_ITERATIONS}...", end=" ", flush=True)
    nearest_result = benchmark_find_nearest(model, LOOKUP_ITERATIONS)
    print(f"{nearest_result.mean_time_ms*1000:.2f}μs/op")
    
    # Range query
    print(f"    range_query() x {RANGE_QUERY_ITERATIONS}...", end=" ", flush=True)
    range_result = benchmark_range_query(model, RANGE_QUERY_ITERATIONS)
    print(f"{range_result.mean_time_ms*1000:.2f}μs/op")
    
    # Junction set build
    print(f"    junction_set() build...", end=" ", flush=True)
    set_build_ms = benchmark_junction_set_build(model, 10)
    print(f"{set_build_ms:.2f}ms")
    
    return TierMetrics(
        tier=tier,
        n_junctions=model.n_junctions,
        size_kb=model.size_kb,
        size_mb=model.size_kb / 1024,
        load_time_ms=load_mean,
        memory_mb=memory_mb,
        contains_mean_us=contains_result.mean_time_ms * 1000,
        contains_ops_per_sec=contains_result.ops_per_second,
        find_nearest_mean_us=nearest_result.mean_time_ms * 1000,
        find_nearest_ops_per_sec=nearest_result.ops_per_second,
        range_query_mean_us=range_result.mean_time_ms * 1000,
        range_query_ops_per_sec=range_result.ops_per_second,
        junction_set_build_ms=set_build_ms
    )


def analyze_scaling(metrics: List[TierMetrics]) -> Dict:
    """Analyze scaling characteristics across tiers."""
    # Sort by junction count
    sorted_metrics = sorted(metrics, key=lambda m: m.n_junctions)
    
    junction_counts = [m.n_junctions for m in sorted_metrics]
    load_times = [m.load_time_ms for m in sorted_metrics]
    contains_times = [m.contains_mean_us for m in sorted_metrics]
    nearest_times = [m.find_nearest_mean_us for m in sorted_metrics]
    
    # Calculate scaling factors
    base = sorted_metrics[0]
    max_tier = sorted_metrics[-1]
    
    junction_scale = max_tier.n_junctions / base.n_junctions
    load_scale = max_tier.load_time_ms / base.load_time_ms
    contains_scale = max_tier.contains_mean_us / base.contains_mean_us
    nearest_scale = max_tier.find_nearest_mean_us / base.find_nearest_mean_us
    
    return {
        "junction_scale_factor": junction_scale,
        "load_time_scale_factor": load_scale,
        "contains_scale_factor": contains_scale,
        "find_nearest_scale_factor": nearest_scale,
        "scaling_efficiency": {
            "load": f"{load_scale/junction_scale:.4f}x (linear = 1.0)",
            "contains": f"{contains_scale/junction_scale:.4f}x (linear = 1.0)",
            "find_nearest": f"{nearest_scale/junction_scale:.4f}x (linear = 1.0)",
        },
        "observations": []
    }


def generate_comparative_analysis(metrics: List[TierMetrics]) -> Dict:
    """Generate comparative analysis between tiers."""
    sorted_metrics = sorted(metrics, key=lambda m: m.n_junctions)
    
    comparisons = []
    for i in range(len(sorted_metrics) - 1):
        curr = sorted_metrics[i]
        next_tier = sorted_metrics[i + 1]
        
        comparisons.append({
            "from": curr.tier,
            "to": next_tier.tier,
            "junction_increase": next_tier.n_junctions - curr.n_junctions,
            "junction_increase_pct": ((next_tier.n_junctions / curr.n_junctions) - 1) * 100,
            "size_increase_kb": next_tier.size_kb - curr.size_kb,
            "load_time_increase_ms": next_tier.load_time_ms - curr.load_time_ms,
            "contains_slowdown_pct": ((next_tier.contains_mean_us / curr.contains_mean_us) - 1) * 100,
            "find_nearest_slowdown_pct": ((next_tier.find_nearest_mean_us / curr.find_nearest_mean_us) - 1) * 100,
        })
    
    # Summary statistics
    seed = sorted_metrics[0]
    sovereign = sorted_metrics[-1]
    
    summary = {
        "seed_to_sovereign": {
            "junction_multiplier": f"{sovereign.n_junctions / seed.n_junctions:.1f}x",
            "size_multiplier": f"{sovereign.size_kb / seed.size_kb:.1f}x",
            "load_time_multiplier": f"{sovereign.load_time_ms / seed.load_time_ms:.1f}x",
            "contains_time_multiplier": f"{sovereign.contains_mean_us / seed.contains_mean_us:.1f}x",
            "find_nearest_time_multiplier": f"{sovereign.find_nearest_mean_us / seed.find_nearest_mean_us:.1f}x",
        },
        "tier_comparisons": comparisons
    }
    
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║              UNIFIED MODEL PERFORMANCE BENCHMARK                   ║
║                     Ghost in the Machine Labs                      ║
║            All Watched Over By Machines Of Loving Grace            ║
║                                                                    ║
║                   Metrics for Whitepaper v1.0                      ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    # System info
    system_info = {
        "benchmark_date": datetime.now().isoformat(),
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "lookup_iterations": LOOKUP_ITERATIONS,
        "range_query_iterations": RANGE_QUERY_ITERATIONS,
        "benchmark_iterations": BENCHMARK_ITERATIONS,
    }
    
    print("="*60)
    print("  SYSTEM CONFIGURATION")
    print("="*60)
    print(f"  Lookup iterations:      {LOOKUP_ITERATIONS:,}")
    print(f"  Range query iterations: {RANGE_QUERY_ITERATIONS:,}")
    print(f"  Benchmark iterations:   {BENCHMARK_ITERATIONS}")
    
    # Initialize loader
    loader = ModelLoader()
    tiers = loader.available_tiers()
    
    print("\n" + "="*60)
    print("  RUNNING BENCHMARKS")
    print("="*60)
    
    # Run benchmarks for each tier
    all_metrics = []
    for tier in tiers:
        metrics = run_tier_benchmarks(loader, tier)
        all_metrics.append(metrics)
    
    # Analyze results
    print("\n" + "="*60)
    print("  ANALYSIS")
    print("="*60)
    
    scaling = analyze_scaling(all_metrics)
    comparative = generate_comparative_analysis(all_metrics)
    
    # Create report
    report = BenchmarkReport(
        timestamp=datetime.now().isoformat(),
        system_info=system_info,
        tier_metrics=all_metrics,
        comparative_analysis=comparative,
        scaling_analysis=scaling
    )
    
    # Save report
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = f"{OUTPUT_DIR}/benchmark_report.json"
    
    with open(report_path, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("  BENCHMARK RESULTS SUMMARY")
    print("="*60)
    
    print(f"\n  {'Tier':<15} {'Junctions':>12} {'Size':>10} {'Load':>10} {'contains()':>12} {'nearest()':>12}")
    print(f"  {'-'*15} {'-'*12} {'-'*10} {'-'*10} {'-'*12} {'-'*12}")
    
    for m in sorted(all_metrics, key=lambda x: x.n_junctions):
        print(f"  {m.tier:<15} {m.n_junctions:>12,} {m.size_kb:>8.1f}KB {m.load_time_ms:>8.2f}ms {m.contains_mean_us:>10.2f}μs {m.find_nearest_mean_us:>10.2f}μs")
    
    print(f"\n  SCALING ANALYSIS (seed → sovereign):")
    print(f"    Junctions:    {scaling['junction_scale_factor']:.1f}x")
    print(f"    Load time:    {scaling['load_time_scale_factor']:.1f}x")
    print(f"    contains():   {scaling['contains_scale_factor']:.1f}x")
    print(f"    nearest():    {scaling['find_nearest_scale_factor']:.1f}x")
    
    print(f"\n  THROUGHPUT (sovereign tier):")
    sovereign = [m for m in all_metrics if m.tier == "sovereign"][0]
    print(f"    contains():     {sovereign.contains_ops_per_sec:,.0f} ops/sec")
    print(f"    find_nearest(): {sovereign.find_nearest_ops_per_sec:,.0f} ops/sec")
    print(f"    range_query():  {sovereign.range_query_ops_per_sec:,.0f} ops/sec")
    
    print(f"\n  Report saved to: {report_path}")
    
    # Print whitepaper-ready table
    print("\n" + "="*60)
    print("  WHITEPAPER TABLE (Copy-Paste Ready)")
    print("="*60)
    
    print("""
| Tier | Junctions | Size (KB) | Load (ms) | contains (μs) | nearest (μs) | Throughput |
|------|-----------|-----------|-----------|---------------|--------------|------------|""")
    
    for m in sorted(all_metrics, key=lambda x: x.n_junctions):
        print(f"| {m.tier} | {m.n_junctions:,} | {m.size_kb:.1f} | {m.load_time_ms:.2f} | {m.contains_mean_us:.2f} | {m.find_nearest_mean_us:.2f} | {m.contains_ops_per_sec:,.0f}/s |")
    
    print(f"""
| **Scaling** | {scaling['junction_scale_factor']:.0f}x | {comparative['seed_to_sovereign']['size_multiplier']} | {scaling['load_time_scale_factor']:.1f}x | {scaling['contains_scale_factor']:.1f}x | {scaling['find_nearest_scale_factor']:.1f}x | - |
""")
    
    print("""
  ┌─────────────────────────────────────────────────────────────┐
  │                 BENCHMARK COMPLETE ✓                        │
  │                                                             │
  │  All metrics collected and saved.                           │
  │  Ready for whitepaper publication.                          │
  └─────────────────────────────────────────────────────────────┘
""")
    
    return report


if __name__ == "__main__":
    report = main()
