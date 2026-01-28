#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        UNIFIED MODEL LOADER v1.0                             ║
║                      Ghost in the Machine Labs                               ║
║              "All Watched Over By Machines Of Loving Grace"                  ║
║                                                                              ║
║   Load and use the unified junction models.                                  ║
║                                                                              ║
║   Available tiers:                                                           ║
║     - seed_only:   2,705 junctions   ( 10.6 KB) - Foundation                 ║
║     - pocket:     12,281 junctions   ( 48.0 KB) - Mobile/Embedded            ║
║     - desktop:    14,678 junctions   ( 57.3 KB) - Developer                  ║
║     - workstation:17,688 junctions   ( 69.1 KB) - Full capabilities          ║
║     - sovereign: 140,539 junctions   (549.0 KB) - Maximum + crystals         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

UNIFIED_MODEL_DIR = "/home/joe/sparky/unified_model"

TIERS = ["seed_only", "pocket", "desktop", "workstation", "sovereign"]

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UnifiedModel:
    """A loaded unified model."""
    name: str
    tier: str
    junctions: np.ndarray
    manifest: Dict
    
    @property
    def n_junctions(self) -> int:
        return len(self.junctions)
    
    @property
    def size_kb(self) -> float:
        return self.junctions.nbytes / 1024
    
    def contains(self, value: float, tolerance: float = 1e-7) -> bool:
        """Check if model contains a specific junction value."""
        return np.any(np.isclose(self.junctions, value, rtol=tolerance))
    
    def find_nearest(self, value: float) -> Tuple[float, int]:
        """Find the nearest junction to a value. Returns (junction, index)."""
        distances = np.abs(self.junctions - value)
        idx = np.argmin(distances)
        return self.junctions[idx], idx
    
    def get_range(self, start: float, end: float) -> np.ndarray:
        """Get all junctions within a value range."""
        mask = (self.junctions >= start) & (self.junctions <= end)
        return self.junctions[mask]
    
    def junction_set(self) -> Set[bytes]:
        """Get junctions as a set for fast lookups."""
        return set(j.tobytes() for j in self.junctions)
    
    def __repr__(self):
        return f"UnifiedModel('{self.name}', {self.n_junctions:,} junctions, {self.size_kb:.1f} KB)"

# ═══════════════════════════════════════════════════════════════════════════════
# LOADER
# ═══════════════════════════════════════════════════════════════════════════════

class ModelLoader:
    """
    Load and manage unified models.
    
    Usage:
        loader = ModelLoader()
        model = loader.load("sovereign")
        
        # Check if model contains a junction
        if model.contains(0.5):
            print("Found!")
        
        # Find nearest junction
        nearest, idx = model.find_nearest(0.5)
    """
    
    def __init__(self, model_dir: str = None):
        self.model_dir = model_dir or UNIFIED_MODEL_DIR
        self.loaded_models: Dict[str, UnifiedModel] = {}
        self.index: Optional[Dict] = None
        
        # Load index
        self._load_index()
    
    def _load_index(self):
        """Load the master model index."""
        index_path = f"{self.model_dir}/model_index.json"
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                self.index = json.load(f)
    
    def available_tiers(self) -> List[str]:
        """Get list of available tiers."""
        if self.index:
            return list(self.index.get("models", {}).keys())
        return TIERS
    
    def tier_info(self, tier: str) -> Optional[Dict]:
        """Get info about a tier without loading it."""
        if self.index and tier in self.index.get("models", {}):
            return self.index["models"][tier]
        return None
    
    def load(self, tier: str) -> UnifiedModel:
        """Load a unified model by tier name."""
        # Check cache
        if tier in self.loaded_models:
            return self.loaded_models[tier]
        
        # Validate tier
        if tier not in self.available_tiers():
            raise ValueError(f"Unknown tier: {tier}. Available: {self.available_tiers()}")
        
        # Load junction array
        junction_path = f"{self.model_dir}/{tier}/unified_{tier}_junctions.npy"
        if not os.path.exists(junction_path):
            raise FileNotFoundError(f"Model file not found: {junction_path}")
        
        junctions = np.load(junction_path)
        
        # Load manifest
        manifest_path = f"{self.model_dir}/{tier}/unified_{tier}_manifest.json"
        manifest = {}
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        
        # Create model
        model = UnifiedModel(
            name=f"unified_{tier}",
            tier=tier,
            junctions=junctions,
            manifest=manifest
        )
        
        # Cache
        self.loaded_models[tier] = model
        
        return model
    
    def load_all(self) -> Dict[str, UnifiedModel]:
        """Load all available tiers."""
        for tier in self.available_tiers():
            self.load(tier)
        return self.loaded_models
    
    def compare(self, tier_a: str, tier_b: str) -> Dict:
        """Compare two tiers."""
        model_a = self.load(tier_a)
        model_b = self.load(tier_b)
        
        set_a = model_a.junction_set()
        set_b = model_b.junction_set()
        
        shared = set_a.intersection(set_b)
        only_a = set_a - set_b
        only_b = set_b - set_a
        
        return {
            "tier_a": tier_a,
            "tier_b": tier_b,
            "shared": len(shared),
            "only_in_a": len(only_a),
            "only_in_b": len(only_b),
            "a_size": len(set_a),
            "b_size": len(set_b),
            "jaccard": len(shared) / len(set_a.union(set_b)) if set_a or set_b else 0,
        }
    
    def status(self):
        """Print status of all tiers."""
        print("\n" + "="*60)
        print("  UNIFIED MODEL STATUS")
        print("="*60)
        
        for tier in self.available_tiers():
            info = self.tier_info(tier)
            if info:
                loaded = "✓" if tier in self.loaded_models else " "
                print(f"  [{loaded}] {tier:15} {info['n_junctions']:10,} junctions  {info['size_kb']:8.1f} KB")
        
        print("="*60 + "\n")

# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_default_loader = None

def get_loader() -> ModelLoader:
    """Get the default model loader (singleton)."""
    global _default_loader
    if _default_loader is None:
        _default_loader = ModelLoader()
    return _default_loader

def load_model(tier: str = "sovereign") -> UnifiedModel:
    """Convenience function to load a model."""
    return get_loader().load(tier)

def load_seed() -> UnifiedModel:
    """Load just the seed model."""
    return load_model("seed_only")

def load_sovereign() -> UnifiedModel:
    """Load the maximum capability model."""
    return load_model("sovereign")

# ═══════════════════════════════════════════════════════════════════════════════
# DEMO / MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def demo():
    """Demonstrate model loading."""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                    UNIFIED MODEL LOADER v1.0                       ║
║                     Ghost in the Machine Labs                      ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    # Create loader
    loader = ModelLoader()
    
    # Show status
    loader.status()
    
    # Load sovereign model
    print("Loading sovereign model...")
    sovereign = loader.load("sovereign")
    print(f"  Loaded: {sovereign}")
    
    # Basic stats
    print(f"\n  Statistics:")
    print(f"    Min junction:  {sovereign.junctions.min():.6f}")
    print(f"    Max junction:  {sovereign.junctions.max():.6f}")
    print(f"    Mean junction: {sovereign.junctions.mean():.6f}")
    print(f"    Std deviation: {sovereign.junctions.std():.6f}")
    
    # Find nearest to some values
    print(f"\n  Sample lookups:")
    for test_val in [0.0, 0.5, 1.0, -0.5, 0.12345]:
        nearest, idx = sovereign.find_nearest(test_val)
        contains = "✓" if sovereign.contains(test_val) else "✗"
        print(f"    {test_val:8.5f} → nearest: {nearest:10.6f} (idx {idx:6}) [{contains}]")
    
    # Compare tiers
    print(f"\n  Tier progression:")
    prev_tier = None
    for tier in loader.available_tiers():
        model = loader.load(tier)
        if prev_tier:
            comparison = loader.compare(prev_tier, tier)
            added = comparison["only_in_b"]
            print(f"    {prev_tier:12} → {tier:12}: +{added:,} junctions")
        prev_tier = tier
    
    print(f"""
  
  The unified model is loaded and ready.
  
  Usage:
    from unified_model_loader import load_model, load_sovereign
    
    model = load_sovereign()
    if model.contains(0.5):
        print("Junction found!")
    
    nearest, idx = model.find_nearest(0.5)
""")
    
    return loader


if __name__ == "__main__":
    loader = demo()
