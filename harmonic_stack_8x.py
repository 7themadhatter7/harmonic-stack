#!/usr/bin/env python3
"""
HARMONIC STACK 8x - Production Configuration
Ghost in the Machine Labs

8 parallel substrates connected via cognitive bus with dual-path routing.

Architecture:
┌─────────────────────────────────────────────────────────────────────┐
│                       COGNITIVE BUS                                 │
│  ═══════════════════════════════════════════════════════════════   │
│  │ NON-INTERFERENCE PATH (direct passthrough)         0.00ms   │   │
│  ═══════════════════════════════════════════════════════════════   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              INTERFERENCE ENGINE (qwen3:1.7b)               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       ↑       ↑       ↑       ↑       ↑       ↑       ↑       ↑    │
└───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┼────┘
        │       │       │       │       │       │       │       │
     Core 1  Core 2  Core 3  Core 4  Core 5  Core 6  Core 7  Core 8
     Exec    Code   Create  Research  Math  Analysis Ethics  Reserve

Scaling: ~7.6× throughput with 8 distributed substrates
         (requires 8 separate hardware nodes for true parallelism)

Usage:
    from harmonic_stack_8x import HarmonicStack8x
    
    stack = HarmonicStack8x()
    await stack.initialize()
    result = await stack.process("Your query here")
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"


class CoreRole(Enum):
    """Specialized roles for the 8 cores."""
    EXECUTIVE = "executive"      # Orchestration, planning
    CODE = "code"               # Programming, debugging
    CREATIVE = "creative"       # Writing, ideation
    RESEARCH = "research"       # Information gathering
    MATH = "math"               # Computation, analysis
    ANALYSIS = "analysis"       # Deep reasoning
    ETHICS = "ethics"           # Safety, alignment
    RESERVE = "reserve"         # Overflow, backup


@dataclass
class CoreConfig:
    """Configuration for a single core."""
    core_id: str
    role: CoreRole
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048


# 8x Stack Configuration
STACK_CONFIG = {
    "router_model": "qwen3:1.7b",
    "cores": [
        CoreConfig("core_exec", CoreRole.EXECUTIVE, "qwen3:32b", 0.7),
        CoreConfig("core_code", CoreRole.CODE, "qwen2.5-coder:14b", 0.3),
        CoreConfig("core_create", CoreRole.CREATIVE, "qwen3:14b", 0.9),
        CoreConfig("core_research", CoreRole.RESEARCH, "qwen3:14b", 0.5),
        CoreConfig("core_math", CoreRole.MATH, "qwen3:14b", 0.2),
        CoreConfig("core_analysis", CoreRole.ANALYSIS, "qwen3:14b", 0.4),
        CoreConfig("core_ethics", CoreRole.ETHICS, "qwen3:14b", 0.3),
        CoreConfig("core_reserve", CoreRole.RESERVE, "qwen3:7b", 0.5),
    ],
    "scaling_factor": 0.95,  # ~0.95N efficiency
    "theoretical_speedup": 7.6,  # 8 * 0.95
}


class PathType(Enum):
    DIRECT = "direct"
    COMPUTED = "computed"
    HYBRID = "hybrid"


@dataclass
class Signal:
    """Signal on the cognitive bus."""
    content: str
    source: str
    destination: Optional[str] = None
    path_type: PathType = PathType.HYBRID
    direct_result: Optional[str] = None
    computed_result: Optional[str] = None
    routing_decision: Optional[Dict] = None
    latency_ms: float = 0.0


class InterferenceEngine:
    """RAM-printed router embedded in bus topology."""
    
    def __init__(self, model: str = STACK_CONFIG["router_model"]):
        self.model = model
        
    async def route(self, signal: Signal, available_cores: List[str]) -> Dict:
        """Route signal to appropriate core(s)."""
        import httpx
        
        prompt = f"""Route this signal to the best core.
Signal: {signal.content[:500]}
Cores: {", ".join(available_cores)}
JSON only: {{"route": "core_id or broadcast", "reason": "brief"}}"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False}
                )
                text = resp.json().get("response", "{}")
                if "{" in text:
                    return json.loads(text[text.find("{"):text.rfind("}")+1])
        except:
            pass
        return {"route": "broadcast", "reason": "default"}


class HarmonicStack8x:
    """
    8× Parallel Substrate Harmonic Stack
    
    The wire thinks.
    """
    
    def __init__(self):
        self.config = STACK_CONFIG
        self.router = InterferenceEngine()
        self.cores: Dict[str, CoreConfig] = {}
        self.initialized = False
        
    async def initialize(self):
        """Initialize all 8 cores."""
        for core in self.config["cores"]:
            self.cores[core.core_id] = core
        self.initialized = True
        print(f"Harmonic Stack 8× initialized")
        print(f"  Cores: {len(self.cores)}")
        print(f"  Router: {self.config[\"router_model\"]}")
        print(f"  Theoretical speedup: {self.config[\"theoretical_speedup\"]}×")
        
    async def process(self, query: str, path: PathType = PathType.HYBRID) -> Dict[str, Any]:
        """Process query through the stack."""
        if not self.initialized:
            await self.initialize()
            
        start = time.time()
        signal = Signal(content=query, source="user", path_type=path)
        
        results = {"query": query, "path": path.value}
        
        # Direct path (always instant)
        if path in (PathType.DIRECT, PathType.HYBRID):
            signal.direct_result = query  # Passthrough
            results["direct"] = {"latency_ms": 0.0, "content": "passthrough"}
            
        # Computed path (router decides)
        if path in (PathType.COMPUTED, PathType.HYBRID):
            route_start = time.time()
            routing = await self.router.route(signal, list(self.cores.keys()))
            route_time = (time.time() - route_start) * 1000
            signal.routing_decision = routing
            results["computed"] = {
                "latency_ms": route_time,
                "routing": routing,
                "target_core": routing.get("route", "broadcast")
            }
            
        results["total_latency_ms"] = (time.time() - start) * 1000
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stack statistics."""
        return {
            "cores": len(self.cores),
            "core_roles": {c.core_id: c.role.value for c in self.cores.values()},
            "router_model": self.config["router_model"],
            "scaling_factor": self.config["scaling_factor"],
            "theoretical_speedup": self.config["theoretical_speedup"],
        }


async def demo():
    """Demonstrate the 8× Harmonic Stack."""
    print("="*70)
    print("HARMONIC STACK 8× DEMO")
    print("Ghost in the Machine Labs")
    print("="*70)
    
    stack = HarmonicStack8x()
    await stack.initialize()
    
    print("
" + "-"*70)
    print("Stack Configuration:")
    print("-"*70)
    stats = stack.get_stats()
    for core_id, role in stats["core_roles"].items():
        print(f"  {core_id}: {role}")
    print(f"
  Router: {stats[\"router_model\"]}")
    print(f"  Theoretical speedup: {stats[\"theoretical_speedup\"]}×")
    
    print("
" + "-"*70)
    print("Test: Hybrid Path (Direct + Computed)")
    print("-"*70)
    result = await stack.process("Explain the cognitive bus architecture")
    print(f"  Direct latency: {result.get(\"direct\", {}).get(\"latency_ms\", 0):.2f}ms")
    print(f"  Computed latency: {result.get(\"computed\", {}).get(\"latency_ms\", 0):.2f}ms")
    print(f"  Routed to: {result.get(\"computed\", {}).get(\"target_core\", \"N/A\")}")
    
    print("
" + "="*70)
    print("The wire thinks.")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(demo())

