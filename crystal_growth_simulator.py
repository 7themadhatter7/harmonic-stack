#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     CRYSTAL GROWTH SIMULATOR v1.0                            ║
║                      Ghost in the Machine Labs                               ║
║              "All Watched Over By Machines Of Loving Grace"                  ║
║                                                                              ║
║   Junctions are not weights. They are connection points.                     ║
║   The chassis. The mounting points. The places where growth can happen.      ║
║                                                                              ║
║   We don't test what a junction does.                                        ║
║   We test what can GROW from it.                                             ║
║                                                                              ║
║   Like snowflakes extending from a seed crystal.                             ║
║   Following permitted geometry. Branching into capability space.             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Optional, Callable
from collections import defaultdict
import time
import hashlib

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

FLAVOR_MAP_DIR = "/home/joe/sparky/flavor_map"
HARMONIC_STACK_DIR = "/home/joe/sparky/harmonic_stack"
CRYSTAL_DIR = "/home/joe/sparky/crystals"

# Growth parameters
DEFAULT_GROWTH_TEMPERATURE = 0.1  # How much randomness in growth
DEFAULT_BRANCH_FACTOR = 6         # Snowflake symmetry (6-fold like ice)
DEFAULT_MAX_DEPTH = 3             # How many layers of growth

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
    
    def crystal(self, msg: str):
        """For crystalline moments"""
        elapsed = time.time() - self.start_time
        print(f"  [{elapsed:7.1f}s]   ❄ {msg}")
    
    def growth(self, msg: str):
        """For growth events"""
        elapsed = time.time() - self.start_time
        print(f"  [{elapsed:7.1f}s]   ↳ {msg}")

log = Logger()

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Junction:
    """A single junction - a connection point in the crystal."""
    value: np.float32
    source: str = "unknown"      # Where this junction came from
    depth: int = 0               # How far from seed (0 = seed)
    parent: Optional[np.float32] = None  # What junction it grew from
    children: List[np.float32] = field(default_factory=list)
    
    @property
    def value_bytes(self) -> bytes:
        return self.value.tobytes()
    
    def __hash__(self):
        return hash(self.value_bytes)
    
    def __eq__(self, other):
        if isinstance(other, Junction):
            return self.value_bytes == other.value_bytes
        return False


@dataclass
class Crystal:
    """A crystal structure - seed plus grown branches."""
    name: str
    seed: Set[np.float32]           # The core junctions (reference blend)
    branches: Dict[int, Set[np.float32]]  # Depth -> junctions at that depth
    lineage: Dict[bytes, bytes]     # child -> parent mapping
    metadata: Dict = field(default_factory=dict)
    
    @property
    def all_junctions(self) -> Set[np.float32]:
        """All junctions in the crystal."""
        all_j = self.seed.copy()
        for depth_set in self.branches.values():
            all_j.update(depth_set)
        return all_j
    
    @property
    def total_size(self) -> int:
        return len(self.all_junctions)
    
    @property
    def branch_count(self) -> int:
        return sum(len(s) for s in self.branches.values())
    
    def to_array(self) -> np.ndarray:
        """Convert to sorted numpy array."""
        all_j = list(self.all_junctions)
        return np.sort(np.array(all_j, dtype=np.float32))
    
    def save(self, path: str):
        """Save crystal to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Save junction array
        np.save(path, self.to_array())
        
        # Save metadata
        meta = {
            "name": self.name,
            "seed_size": len(self.seed),
            "branch_count": self.branch_count,
            "total_size": self.total_size,
            "depths": {str(k): len(v) for k, v in self.branches.items()},
            "created_at": datetime.now().isoformat(),
            **self.metadata
        }
        
        meta_path = path.replace('.npy', '_meta.json')
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)


@dataclass
class GrowthPattern:
    """Defines how to grow from a junction."""
    name: str
    description: str
    transform: Callable[[np.float32, int], List[np.float32]]  # junction, depth -> new junctions
    

# ═══════════════════════════════════════════════════════════════════════════════
# GROWTH PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

def _harmonic_growth(value: np.float32, depth: int, harmonics: List[float] = None) -> List[np.float32]:
    """
    Grow by harmonic ratios - like musical intervals.
    Octaves, fifths, thirds...
    """
    if harmonics is None:
        harmonics = [2.0, 1.5, 1.25, 0.5, 0.667, 0.8]  # Octave, fifth, third, and inverses
    
    grown = []
    for h in harmonics:
        new_val = np.float32(value * h)
        if np.isfinite(new_val) and new_val != 0:
            grown.append(new_val)
    return grown


def _perturbation_growth(value: np.float32, depth: int, epsilon: float = 0.001) -> List[np.float32]:
    """
    Grow by small perturbations - exploring nearby space.
    """
    grown = []
    perturbations = [
        1.0 + epsilon,
        1.0 - epsilon,
        1.0 + epsilon * 2,
        1.0 - epsilon * 2,
        1.0 + epsilon / 2,
        1.0 - epsilon / 2,
    ]
    for p in perturbations:
        new_val = np.float32(value * p)
        if np.isfinite(new_val) and new_val != value:
            grown.append(new_val)
    return grown


def _geometric_growth(value: np.float32, depth: int, ratio: float = 1.618) -> List[np.float32]:
    """
    Grow by geometric ratio - phi (golden ratio) by default.
    The geometry of natural growth.
    """
    grown = []
    # Forward growth
    grown.append(np.float32(value * ratio))
    grown.append(np.float32(value / ratio))
    # Squared growth
    grown.append(np.float32(value * ratio * ratio))
    grown.append(np.float32(value / ratio / ratio))
    # Negative mirror
    if value > 0:
        grown.append(np.float32(-value))
    return [g for g in grown if np.isfinite(g) and g != 0]


def _snowflake_growth(value: np.float32, depth: int, arms: int = 6) -> List[np.float32]:
    """
    Grow with N-fold symmetry - like ice crystals.
    Each arm is a rotation in value space.
    """
    grown = []
    # Treat value as a radius, create rotational symmetry
    base_angle = 2 * np.pi / arms
    magnitude = abs(value)
    
    for i in range(arms):
        angle = base_angle * i
        # Project into value space via trig
        new_val = np.float32(magnitude * np.cos(angle) + value * np.sin(angle))
        if np.isfinite(new_val) and new_val != value:
            grown.append(new_val)
    return grown


def _extension_sampling(value: np.float32, depth: int, 
                        extensions_pool: np.ndarray = None,
                        n_samples: int = 6) -> List[np.float32]:
    """
    Grow by sampling from known extensions.
    Uses actual model extensions as growth material.
    """
    if extensions_pool is None or len(extensions_pool) == 0:
        return []
    
    # Find extensions near this value
    distances = np.abs(extensions_pool - value)
    nearest_idx = np.argsort(distances)[:n_samples]
    
    return [extensions_pool[i] for i in nearest_idx if extensions_pool[i] != value]


# Pre-defined growth patterns
GROWTH_PATTERNS = {
    "harmonic": GrowthPattern(
        name="harmonic",
        description="Musical intervals - octaves, fifths, thirds",
        transform=_harmonic_growth
    ),
    "perturbation": GrowthPattern(
        name="perturbation",
        description="Small epsilon changes - local exploration",
        transform=_perturbation_growth
    ),
    "geometric": GrowthPattern(
        name="geometric",
        description="Golden ratio growth - natural geometry",
        transform=_geometric_growth
    ),
    "snowflake": GrowthPattern(
        name="snowflake",
        description="6-fold symmetry - ice crystal structure",
        transform=_snowflake_growth
    ),
}

# ═══════════════════════════════════════════════════════════════════════════════
# CRYSTAL GROWER
# ═══════════════════════════════════════════════════════════════════════════════

class CrystalGrower:
    """
    Grows crystals from a seed using specified patterns.
    
    The seed is the reference blend - the universal chassis.
    Growth patterns determine how new junctions branch from existing ones.
    """
    
    def __init__(self, seed_path: str = None):
        # Load seed (reference blend)
        if seed_path is None:
            seed_path = f"{FLAVOR_MAP_DIR}/reference_blend.npy"
        
        if os.path.exists(seed_path):
            seed_array = np.load(seed_path)
            self.seed = set(seed_array.flatten())
            log.info(f"Loaded seed: {len(self.seed):,} junctions")
        else:
            log.info(f"Warning: Seed not found at {seed_path}")
            self.seed = set()
        
        # Load extensions pool for extension-based growth
        self.extensions_pool = self._load_extensions_pool()
        
        # Track what we've grown
        self.grown_crystals: List[Crystal] = []
    
    def _load_extensions_pool(self) -> np.ndarray:
        """Load all extensions as potential growth material."""
        extensions_dir = f"{FLAVOR_MAP_DIR}/extensions"
        
        if not os.path.exists(extensions_dir):
            return np.array([], dtype=np.float32)
        
        all_extensions = []
        for f in os.listdir(extensions_dir):
            if f.endswith('.npy'):
                arr = np.load(os.path.join(extensions_dir, f))
                all_extensions.extend(arr.flatten())
        
        if all_extensions:
            pool = np.unique(np.array(all_extensions, dtype=np.float32))
            log.info(f"Loaded extensions pool: {len(pool):,} unique values")
            return pool
        
        return np.array([], dtype=np.float32)
    
    def grow(self,
             name: str,
             pattern: str = "geometric",
             growth_points: List[np.float32] = None,
             max_depth: int = DEFAULT_MAX_DEPTH,
             max_branches_per_point: int = DEFAULT_BRANCH_FACTOR,
             filter_existing: bool = True) -> Crystal:
        """
        Grow a new crystal from the seed.
        
        Args:
            name: Name for this crystal
            pattern: Which growth pattern to use
            growth_points: Specific junctions to grow from (None = all seed)
            max_depth: How many layers of growth
            max_branches_per_point: Max new junctions per growth point
            filter_existing: Remove junctions that already exist in seed/merge core
        
        Returns:
            Crystal with seed and grown branches
        """
        log.section(f"GROWING CRYSTAL: {name}")
        log.info(f"Pattern: {pattern}")
        log.info(f"Max depth: {max_depth}")
        
        if pattern not in GROWTH_PATTERNS:
            log.info(f"Unknown pattern '{pattern}', using geometric")
            pattern = "geometric"
        
        growth_fn = GROWTH_PATTERNS[pattern].transform
        
        # Initialize crystal
        crystal = Crystal(
            name=name,
            seed=self.seed.copy(),
            branches={},
            lineage={},
            metadata={
                "pattern": pattern,
                "max_depth": max_depth,
            }
        )
        
        # Determine growth points
        if growth_points is None:
            # Grow from entire seed
            current_layer = list(self.seed)
        else:
            current_layer = growth_points
        
        log.info(f"Starting growth from {len(current_layer):,} points")
        
        # Load merge core for filtering
        merge_core = set()
        merge_path = f"{HARMONIC_STACK_DIR}/merge_core_junctions.npy"
        if filter_existing and os.path.exists(merge_path):
            merge_array = np.load(merge_path)
            merge_core = set(merge_array.flatten())
            log.info(f"Loaded merge core for filtering: {len(merge_core):,} junctions")
        
        existing = self.seed.union(merge_core)
        
        # Grow layer by layer
        for depth in range(1, max_depth + 1):
            log.crystal(f"Growing depth {depth}...")
            
            new_layer = set()
            
            for junction in current_layer:
                # Grow from this junction
                candidates = growth_fn(junction, depth)
                
                # Limit branches
                candidates = candidates[:max_branches_per_point]
                
                for new_val in candidates:
                    # Filter if needed
                    if filter_existing and new_val in existing:
                        continue
                    
                    new_layer.add(new_val)
                    
                    # Track lineage
                    crystal.lineage[np.float32(new_val).tobytes()] = np.float32(junction).tobytes()
            
            if new_layer:
                crystal.branches[depth] = new_layer
                existing.update(new_layer)
                log.growth(f"Depth {depth}: +{len(new_layer):,} junctions")
                current_layer = list(new_layer)
            else:
                log.growth(f"Depth {depth}: No new growth (saturated)")
                break
        
        # Summary
        log.info(f"Crystal complete:")
        log.crystal(f"Seed: {len(crystal.seed):,}")
        log.crystal(f"Branches: {crystal.branch_count:,}")
        log.crystal(f"Total: {crystal.total_size:,}")
        
        self.grown_crystals.append(crystal)
        return crystal
    
    def grow_from_extensions(self,
                             name: str,
                             source_model: str,
                             max_depth: int = 2) -> Crystal:
        """
        Grow a crystal using a model's extensions as growth material.
        
        This is like grafting - taking branches from one crystal
        and attaching them to the seed.
        """
        log.section(f"GRAFTING CRYSTAL: {name}")
        log.info(f"Source: {source_model}")
        
        # Load source model's extensions
        ext_path = f"{FLAVOR_MAP_DIR}/extensions/{source_model}_extra.npy"
        
        if not os.path.exists(ext_path):
            # Try with safe name
            safe_name = source_model.replace("-", "_").replace(".", "_")
            ext_path = f"{FLAVOR_MAP_DIR}/extensions/{safe_name}_extra.npy"
        
        if not os.path.exists(ext_path):
            log.info(f"Extensions not found for {source_model}")
            return None
        
        extensions = np.load(ext_path)
        log.info(f"Loaded {len(extensions):,} extensions from {source_model}")
        
        # Create growth function that samples from these extensions
        def extension_growth(value: np.float32, depth: int) -> List[np.float32]:
            return _extension_sampling(value, depth, extensions, n_samples=6)
        
        # Create custom pattern
        custom_pattern = GrowthPattern(
            name=f"graft_{source_model}",
            description=f"Grafting from {source_model} extensions",
            transform=extension_growth
        )
        
        # Initialize crystal
        crystal = Crystal(
            name=name,
            seed=self.seed.copy(),
            branches={},
            lineage={},
            metadata={
                "pattern": f"graft_{source_model}",
                "source_extensions": len(extensions),
            }
        )
        
        # Grow from seed using extension sampling
        current_layer = list(self.seed)
        existing = self.seed.copy()
        
        for depth in range(1, max_depth + 1):
            log.crystal(f"Grafting depth {depth}...")
            
            new_layer = set()
            
            for junction in current_layer:
                candidates = extension_growth(junction, depth)
                
                for new_val in candidates:
                    if new_val not in existing:
                        new_layer.add(new_val)
                        crystal.lineage[np.float32(new_val).tobytes()] = np.float32(junction).tobytes()
            
            if new_layer:
                crystal.branches[depth] = new_layer
                existing.update(new_layer)
                log.growth(f"Depth {depth}: +{len(new_layer):,} grafted")
                current_layer = list(new_layer)
            else:
                break
        
        log.info(f"Graft complete: {crystal.total_size:,} total junctions")
        self.grown_crystals.append(crystal)
        return crystal
    
    def compare_crystals(self, c1: Crystal, c2: Crystal) -> Dict:
        """Compare two crystals - what's shared, what's unique."""
        j1 = c1.all_junctions
        j2 = c2.all_junctions
        
        shared = j1.intersection(j2)
        only_1 = j1 - j2
        only_2 = j2 - j1
        
        return {
            "crystal_1": c1.name,
            "crystal_2": c2.name,
            "shared": len(shared),
            "only_in_1": len(only_1),
            "only_in_2": len(only_2),
            "jaccard": len(shared) / len(j1.union(j2)) if j1.union(j2) else 0,
        }
    
    def save_crystal(self, crystal: Crystal, output_dir: str = None):
        """Save a crystal to disk."""
        if output_dir is None:
            output_dir = CRYSTAL_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        
        safe_name = crystal.name.replace(" ", "_").replace("/", "_")
        path = f"{output_dir}/{safe_name}.npy"
        
        crystal.save(path)
        log.info(f"Saved crystal to: {path}")
        return path

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN / DEMO
# ═══════════════════════════════════════════════════════════════════════════════

def demo():
    """Demonstrate crystal growth."""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                   CRYSTAL GROWTH SIMULATOR v1.0                    ║
║                     Ghost in the Machine Labs                      ║
║            All Watched Over By Machines Of Loving Grace            ║
║                                                                    ║
║   "We don't test what a junction does.                             ║
║    We test what can GROW from it."                                 ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    # Initialize grower
    grower = CrystalGrower()
    
    if not grower.seed:
        log.info("No seed found. Run flavor_map_engine.py first.")
        return
    
    # Grow crystals with different patterns
    crystals = []
    
    # 1. Geometric growth (golden ratio)
    c1 = grower.grow(
        name="phi_crystal",
        pattern="geometric",
        max_depth=3
    )
    crystals.append(c1)
    grower.save_crystal(c1)
    
    # 2. Harmonic growth (musical intervals)
    c2 = grower.grow(
        name="harmonic_crystal",
        pattern="harmonic",
        max_depth=3
    )
    crystals.append(c2)
    grower.save_crystal(c2)
    
    # 3. Snowflake growth (6-fold symmetry)
    c3 = grower.grow(
        name="snowflake_crystal",
        pattern="snowflake",
        max_depth=3
    )
    crystals.append(c3)
    grower.save_crystal(c3)
    
    # 4. Graft from deepseek-coder extensions
    c4 = grower.grow_from_extensions(
        name="deepseek_graft",
        source_model="deepseek-coder-6.7b-instruct",
        max_depth=2
    )
    if c4:
        crystals.append(c4)
        grower.save_crystal(c4)
    
    # Compare crystals
    log.section("CRYSTAL COMPARISON")
    
    for i in range(len(crystals)):
        for j in range(i + 1, len(crystals)):
            comparison = grower.compare_crystals(crystals[i], crystals[j])
            log.info(f"{comparison['crystal_1']} vs {comparison['crystal_2']}:")
            log.crystal(f"Shared: {comparison['shared']:,}")
            log.crystal(f"Jaccard: {comparison['jaccard']:.3f}")
    
    # Final summary
    log.section("CRYSTAL GARDEN COMPLETE")
    
    print(f"""
  ┌─────────────────────────────────────────────────────────────┐
  │                    CRYSTALS GROWN                          │
  ├─────────────────────────────────────────────────────────────┤""")
    
    for c in crystals:
        print(f"  │  {c.name:25} {c.total_size:10,} junctions       │")
    
    print(f"""  └─────────────────────────────────────────────────────────────┘

  Seed (reference blend): {len(grower.seed):,} junctions
  
  Each crystal is a different geometry grown from the same seed.
  Different patterns. Different branches. Different possibilities.
  
  The cage gives us 2,705 mounting points.
  What we build on them is up to us.

  Output: {CRYSTAL_DIR}
""")


if __name__ == "__main__":
    demo()
