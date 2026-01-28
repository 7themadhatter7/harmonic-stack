#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     UNIFIED MODEL ASSEMBLER v1.0                             ║
║                      Ghost in the Machine Labs                               ║
║              "All Watched Over By Machines Of Loving Grace"                  ║
║                                                                              ║
║   Assembly of the first unified model from choice parts:                     ║
║                                                                              ║
║   TIER 1 - SEED (Foundation):                                                ║
║     Reference blend: 2,705 junctions (what ALL models converge on)           ║
║                                                                              ║
║   TIER 2 - CAPABILITIES (Choice extensions):                                 ║
║     + Code: qwen2.5-coder + deepseek-coder extensions                        ║
║     + Math: deepseek-math extensions                                         ║
║     + Reasoning: mistral extensions                                          ║
║     + General: qwen2-7b + tinyllama extensions                               ║
║                                                                              ║
║   TIER 3 - GROWTH (Crystal geometries):                                      ║
║     + Harmonic growth patterns (musical intervals)                           ║
║     + Geometric growth patterns (golden ratio)                               ║
║                                                                              ║
║   Output: ~/sparky/unified_model/                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
import time

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

FLAVOR_MAP_DIR = "/home/joe/sparky/flavor_map"
HARMONIC_STACK_DIR = "/home/joe/sparky/harmonic_stack"
CRYSTAL_DIR = "/home/joe/sparky/crystals"
OUTPUT_DIR = "/home/joe/sparky/unified_model"

# Capability definitions - which models contribute to which capability
CAPABILITY_SOURCES = {
    "code": [
        "qwen2_5-coder-7b",      # 100% coverage, 8,339 extensions
        "deepseek-coder-6_7b",   # 100% coverage, 5,232 extensions  
        "starcoder2-7b",         # 99.8% coverage, 5,102 extensions
    ],
    "math": [
        "deepseek-math-7b",      # 100% coverage, 5,269 extensions
    ],
    "reasoning": [
        "mistral-7b-instruct",   # 94.9% coverage, 8,760 extensions
    ],
    "general": [
        "qwen2-7b",              # 100% coverage, 6,538 extensions
        "qwen2-1_5b",            # 100% coverage, 4,798 extensions
        "tinyllama-1_1b",        # 99.9% coverage, 7,474 extensions
    ],
}

# Tier configurations for different deployment sizes
TIER_CONFIGS = {
    "seed_only": {
        "description": "Just the reference blend - minimal footprint",
        "components": ["seed"],
        "expected_size_kb": 11,
    },
    "pocket": {
        "description": "Seed + general capability - mobile/embedded",
        "components": ["seed", "general"],
        "expected_size_kb": 50,
    },
    "desktop": {
        "description": "Seed + code + general - developer workstation",
        "components": ["seed", "code", "general"],
        "expected_size_kb": 100,
    },
    "workstation": {
        "description": "All capabilities - full development",
        "components": ["seed", "code", "math", "reasoning", "general"],
        "expected_size_kb": 200,
    },
    "sovereign": {
        "description": "All capabilities + growth crystals - maximum",
        "components": ["seed", "code", "math", "reasoning", "general", "crystals"],
        "expected_size_kb": 500,
    },
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
    
    def component(self, msg: str):
        elapsed = time.time() - self.start_time
        print(f"  [{elapsed:7.1f}s]   ◆ {msg}")
    
    def detail(self, msg: str):
        elapsed = time.time() - self.start_time
        print(f"  [{elapsed:7.1f}s]     → {msg}")

log = Logger()

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Component:
    """A component of the unified model."""
    name: str
    junctions: np.ndarray
    source: str
    capability: str
    n_junctions: int = 0
    size_kb: float = 0.0
    
    def __post_init__(self):
        self.n_junctions = len(self.junctions)
        self.size_kb = self.junctions.nbytes / 1024


@dataclass 
class UnifiedModel:
    """The assembled unified model."""
    name: str
    tier: str
    components: List[Component]
    junctions: np.ndarray
    manifest: Dict
    
    @property
    def n_junctions(self) -> int:
        return len(self.junctions)
    
    @property
    def size_kb(self) -> float:
        return self.junctions.nbytes / 1024
    
    def save(self, output_dir: str):
        """Save the unified model."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save main junction array
        np.save(f"{output_dir}/{self.name}_junctions.npy", self.junctions)
        
        # Save individual components
        components_dir = f"{output_dir}/components"
        os.makedirs(components_dir, exist_ok=True)
        
        for comp in self.components:
            np.save(f"{components_dir}/{comp.name}_junctions.npy", comp.junctions)
        
        # Save manifest
        self.manifest["saved_at"] = datetime.now().isoformat()
        self.manifest["output_dir"] = output_dir
        
        with open(f"{output_dir}/{self.name}_manifest.json", 'w') as f:
            json.dump(self.manifest, f, indent=2)
        
        # Save assembly recipe for reproducibility
        recipe = {
            "tier": self.tier,
            "components": [
                {
                    "name": c.name,
                    "capability": c.capability,
                    "source": c.source,
                    "n_junctions": c.n_junctions,
                    "size_kb": c.size_kb
                }
                for c in self.components
            ],
            "total_junctions": self.n_junctions,
            "total_size_kb": self.size_kb,
            "created_at": datetime.now().isoformat()
        }
        
        with open(f"{output_dir}/assembly_recipe.json", 'w') as f:
            json.dump(recipe, f, indent=2)

# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT LOADERS
# ═══════════════════════════════════════════════════════════════════════════════

def load_seed() -> Component:
    """Load the reference blend as the seed component."""
    path = f"{FLAVOR_MAP_DIR}/reference_blend.npy"
    junctions = np.load(path)
    
    return Component(
        name="seed",
        junctions=junctions,
        source="flavor_map/reference_blend",
        capability="foundation"
    )


def load_capability_extensions(capability: str) -> Optional[Component]:
    """Load and merge extensions for a capability."""
    if capability not in CAPABILITY_SOURCES:
        return None
    
    sources = CAPABILITY_SOURCES[capability]
    all_junctions = set()
    
    for source in sources:
        path = f"{FLAVOR_MAP_DIR}/extensions/{source}_extra.npy"
        if os.path.exists(path):
            ext = np.load(path)
            for j in ext:
                all_junctions.add(j.tobytes())
    
    if not all_junctions:
        return None
    
    junction_array = np.array(
        [np.frombuffer(b, dtype=np.float32)[0] for b in all_junctions],
        dtype=np.float32
    )
    
    return Component(
        name=f"capability_{capability}",
        junctions=np.sort(junction_array),
        source=f"merged:{','.join(sources)}",
        capability=capability
    )


def load_crystal_extensions() -> Optional[Component]:
    """Load grown crystals as additional extension material."""
    crystal_files = [
        "phi_crystal.npy",
        "harmonic_crystal.npy",
        "snowflake_crystal.npy"
    ]
    
    all_junctions = set()
    
    for cf in crystal_files:
        path = f"{CRYSTAL_DIR}/{cf}"
        if os.path.exists(path):
            crystal = np.load(path)
            for j in crystal:
                all_junctions.add(j.tobytes())
    
    if not all_junctions:
        return None
    
    junction_array = np.array(
        [np.frombuffer(b, dtype=np.float32)[0] for b in all_junctions],
        dtype=np.float32
    )
    
    return Component(
        name="crystal_growth",
        junctions=np.sort(junction_array),
        source="crystal_growth_simulator",
        capability="extended_geometry"
    )

# ═══════════════════════════════════════════════════════════════════════════════
# ASSEMBLER
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedModelAssembler:
    """
    Assembles unified models from components.
    
    Philosophy: Start with the seed (what everyone agrees on),
    then add capability modules for specific tasks.
    """
    
    def __init__(self):
        self.seed: Optional[Component] = None
        self.capabilities: Dict[str, Component] = {}
        self.crystals: Optional[Component] = None
        self.assembled_models: Dict[str, UnifiedModel] = {}
    
    def initialize(self):
        """Load all available components."""
        log.section("LOADING COMPONENTS")
        
        # Load seed
        log.info("Loading seed (reference blend)...")
        self.seed = load_seed()
        log.component(f"Seed: {self.seed.n_junctions:,} junctions ({self.seed.size_kb:.1f} KB)")
        
        # Load capabilities
        log.info("Loading capability extensions...")
        for cap in CAPABILITY_SOURCES.keys():
            comp = load_capability_extensions(cap)
            if comp:
                self.capabilities[cap] = comp
                log.component(f"{cap}: {comp.n_junctions:,} junctions ({comp.size_kb:.1f} KB)")
        
        # Load crystals
        log.info("Loading crystal growth extensions...")
        self.crystals = load_crystal_extensions()
        if self.crystals:
            log.component(f"Crystals: {self.crystals.n_junctions:,} junctions ({self.crystals.size_kb:.1f} KB)")
        
        return self
    
    def assemble(self, tier: str) -> UnifiedModel:
        """Assemble a unified model for a specific tier."""
        if tier not in TIER_CONFIGS:
            raise ValueError(f"Unknown tier: {tier}")
        
        config = TIER_CONFIGS[tier]
        log.section(f"ASSEMBLING: {tier.upper()}")
        log.info(f"Description: {config['description']}")
        
        components = []
        all_junctions = set()
        
        # Always start with seed
        if "seed" in config["components"]:
            components.append(self.seed)
            for j in self.seed.junctions:
                all_junctions.add(j.tobytes())
            log.component(f"Added seed: {self.seed.n_junctions:,} junctions")
        
        # Add capability components
        for cap in ["code", "math", "reasoning", "general"]:
            if cap in config["components"] and cap in self.capabilities:
                comp = self.capabilities[cap]
                components.append(comp)
                before = len(all_junctions)
                for j in comp.junctions:
                    all_junctions.add(j.tobytes())
                added = len(all_junctions) - before
                log.component(f"Added {cap}: +{added:,} new junctions (from {comp.n_junctions:,})")
        
        # Add crystals if requested
        if "crystals" in config["components"] and self.crystals:
            components.append(self.crystals)
            before = len(all_junctions)
            for j in self.crystals.junctions:
                all_junctions.add(j.tobytes())
            added = len(all_junctions) - before
            log.component(f"Added crystals: +{added:,} new junctions (from {self.crystals.n_junctions:,})")
        
        # Convert to sorted array
        junction_array = np.array(
            [np.frombuffer(b, dtype=np.float32)[0] for b in all_junctions],
            dtype=np.float32
        )
        junction_array = np.sort(junction_array)
        
        # Create manifest
        manifest = {
            "name": f"unified_{tier}",
            "tier": tier,
            "description": config["description"],
            "n_junctions": len(junction_array),
            "size_kb": junction_array.nbytes / 1024,
            "components": [c.name for c in components],
            "component_details": {
                c.name: {
                    "capability": c.capability,
                    "n_junctions": c.n_junctions,
                    "source": c.source
                }
                for c in components
            },
            "created_at": datetime.now().isoformat(),
            "provenance": {
                "assembler": "unified_model_assembler.py",
                "organization": "Ghost in the Machine Labs",
                "philosophy": "AGI for the home. First to AGI."
            }
        }
        
        # Create unified model
        model = UnifiedModel(
            name=f"unified_{tier}",
            tier=tier,
            components=components,
            junctions=junction_array,
            manifest=manifest
        )
        
        self.assembled_models[tier] = model
        
        log.info(f"Assembly complete:")
        log.detail(f"Total: {model.n_junctions:,} junctions ({model.size_kb:.1f} KB)")
        
        return model
    
    def assemble_all(self) -> Dict[str, UnifiedModel]:
        """Assemble all tier configurations."""
        for tier in TIER_CONFIGS.keys():
            self.assemble(tier)
        return self.assembled_models
    
    def save_model(self, tier: str):
        """Save a specific tier model."""
        if tier not in self.assembled_models:
            raise ValueError(f"Model '{tier}' not assembled yet")
        
        model = self.assembled_models[tier]
        output_path = f"{OUTPUT_DIR}/{tier}"
        model.save(output_path)
        log.info(f"Saved {tier} to {output_path}")
    
    def save_all(self):
        """Save all assembled models."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        for tier in self.assembled_models:
            self.save_model(tier)
        
        # Save master index
        index = {
            "models": {
                tier: {
                    "n_junctions": model.n_junctions,
                    "size_kb": model.size_kb,
                    "components": [c.name for c in model.components],
                    "path": f"{tier}/{model.name}_junctions.npy"
                }
                for tier, model in self.assembled_models.items()
            },
            "created_at": datetime.now().isoformat(),
            "tier_configs": TIER_CONFIGS
        }
        
        with open(f"{OUTPUT_DIR}/model_index.json", 'w') as f:
            json.dump(index, f, indent=2)
        
        log.info(f"Saved master index to {OUTPUT_DIR}/model_index.json")

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_model(model: UnifiedModel) -> Dict[str, any]:
    """Validate a unified model."""
    results = {
        "name": model.name,
        "valid": True,
        "checks": {}
    }
    
    # Check 1: No NaN or Inf values
    has_nan = np.any(np.isnan(model.junctions))
    has_inf = np.any(np.isinf(model.junctions))
    results["checks"]["no_nan"] = not has_nan
    results["checks"]["no_inf"] = not has_inf
    
    if has_nan or has_inf:
        results["valid"] = False
    
    # Check 2: All values are unique (no duplicates)
    unique_count = len(np.unique(model.junctions))
    results["checks"]["all_unique"] = unique_count == model.n_junctions
    results["unique_ratio"] = unique_count / model.n_junctions if model.n_junctions > 0 else 0
    
    # Check 3: Values are sorted
    is_sorted = np.all(model.junctions[:-1] <= model.junctions[1:])
    results["checks"]["is_sorted"] = is_sorted
    
    # Check 4: Size is reasonable
    results["checks"]["size_reasonable"] = model.size_kb > 0 and model.size_kb < 10000
    
    # Check 5: Contains seed
    seed_path = f"{FLAVOR_MAP_DIR}/reference_blend.npy"
    if os.path.exists(seed_path):
        seed = np.load(seed_path)
        seed_set = set(s.tobytes() for s in seed)
        model_set = set(j.tobytes() for j in model.junctions)
        seed_coverage = len(seed_set.intersection(model_set)) / len(seed_set)
        results["checks"]["contains_seed"] = seed_coverage > 0.99
        results["seed_coverage"] = seed_coverage
    
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                   UNIFIED MODEL ASSEMBLER v1.0                     ║
║                     Ghost in the Machine Labs                      ║
║            All Watched Over By Machines Of Loving Grace            ║
║                                                                    ║
║              "AGI for the home. First to AGI."                     ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    # Initialize assembler
    assembler = UnifiedModelAssembler()
    assembler.initialize()
    
    # Assemble all tiers
    log.section("ASSEMBLING ALL TIERS")
    assembler.assemble_all()
    
    # Validate all models
    log.section("VALIDATING MODELS")
    
    all_valid = True
    for tier, model in assembler.assembled_models.items():
        results = validate_model(model)
        status = "✓" if results["valid"] else "✗"
        log.info(f"{status} {tier}: {model.n_junctions:,} junctions")
        
        for check, passed in results["checks"].items():
            symbol = "✓" if passed else "✗"
            log.detail(f"{symbol} {check}")
        
        if not results["valid"]:
            all_valid = False
    
    # Save all models
    log.section("SAVING MODELS")
    assembler.save_all()
    
    # Final report
    log.section("ASSEMBLY COMPLETE")
    
    print(f"""
  ┌─────────────────────────────────────────────────────────────────┐
  │                    UNIFIED MODELS CREATED                       │
  ├─────────────────────────────────────────────────────────────────┤""")
    
    for tier, model in sorted(assembler.assembled_models.items(), 
                              key=lambda x: x[1].n_junctions):
        print(f"  │  {tier:15} {model.n_junctions:10,} junctions  {model.size_kb:8.1f} KB  │")
    
    print(f"""  └─────────────────────────────────────────────────────────────────┘

  Validation: {"ALL PASSED ✓" if all_valid else "SOME FAILED ✗"}
  
  Output: {OUTPUT_DIR}

  TIER DESCRIPTIONS:
  
    seed_only   - Just the universal foundation (reference blend)
    pocket      - Mobile/embedded deployment (+ general capability)
    desktop     - Developer workstation (+ code capability)
    workstation - Full development environment (+ math, reasoning)
    sovereign   - Maximum capability (+ crystal growth extensions)

  Each tier builds on the previous, adding capability modules.
  All tiers share the same seed - the universal chassis.
  
  The unified model is ready.
""")
    
    return assembler


if __name__ == "__main__":
    assembler = main()
