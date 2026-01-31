#!/usr/bin/env python3
"""
COGNITIVE BUS - Interference/Non-Interference Architecture
Ghost in the Machine Labs

Dual-path signal routing:
- NON-INTERFERENCE: Direct passthrough, preserves signal integrity
- INTERFERENCE: Routed through inference engine, transforms/routes signal

Architecture:
┌─────────────────────────────────────────────────────────────────────┐
│                       COGNITIVE BUS                                 │
│  ═══════════════════════════════════════════════════════════════   │
│  │ NON-INTERFERENCE PATH (direct passthrough)                  │   │
│  ═══════════════════════════════════════════════════════════════   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              INTERFERENCE ENGINE                            │   │
│  │         (embedded router model - qwen3:1.7b)                │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │   │
│  │  │Classify │→ │Transform│→ │  Route  │→ │Synthesize│       │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       ↑              ↑              ↑              ↑                │
└───────┼──────────────┼──────────────┼──────────────┼────────────────┘
        │              │              │              │
     Core A         Core B         Core C         Core D
     (Heavy)        (Heavy)        (Heavy)        (Heavy)

Signal Types:
- DIRECT: Non-interference, raw passthrough
- COMPUTED: Interference path, router-processed
- HYBRID: Both paths simultaneously (original + interpretation)
"""

import asyncio
import json
import time
import httpx
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import deque
from pathlib import Path


OLLAMA_URL = "http://localhost:11434/api/generate"
ROUTER_MODEL = "qwen3:1.7b"  # Light model for bus inference
CORE_MODEL = "qwen3:4b"      # Heavier model for core processing


class PathType(Enum):
    """Signal path types through the bus."""
    DIRECT = "direct"           # Non-interference: raw passthrough
    COMPUTED = "computed"       # Interference: router-processed
    HYBRID = "hybrid"           # Both paths simultaneously


@dataclass
class BusSignal:
    """A signal on the cognitive bus."""
    signal_id: str
    source_core: str
    content: str
    path_type: PathType = PathType.HYBRID
    timestamp: float = field(default_factory=time.time)
    
    # Dual-path results
    direct_content: Optional[str] = None      # Non-interference path
    computed_content: Optional[str] = None    # Interference path result
    computed_routing: Optional[str] = None    # Router's decision
    
    # Metrics
    direct_latency_ms: float = 0.0
    computed_latency_ms: float = 0.0


class InterferenceEngine:
    """
    Embedded inference engine in the bus.
    Processes signals through a light model for routing/transformation.
    """
    
    def __init__(self, model: str = ROUTER_MODEL):
        self.model = model
        self.call_count = 0
        self.total_latency_ms = 0.0
    
    async def process(self, signal: BusSignal, available_cores: List[str]) -> Tuple[str, str]:
        """
        Process signal through interference engine.
        Returns: (transformed_content, routing_decision)
        """
        start = time.perf_counter()
        
        # Router prompt - classify and route
        router_prompt = f"""You are a signal router in a cognitive bus. Analyze this signal and decide routing.

Signal from: {signal.source_core}
Content: {signal.content}

Available destination cores: {', '.join(available_cores)}

Respond in this exact format:
ROUTE: [core_name or "broadcast"]
TRANSFORM: [brief summary or "passthrough"]
REASON: [one sentence why]"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    OLLAMA_URL,
                    json={
                        "model": self.model,
                        "prompt": router_prompt,
                        "stream": False,
                        "options": {"num_predict": 100, "temperature": 0.3}
                    },
                    timeout=30.0
                )
                
                result = response.json().get("response", "")
                
                # Parse routing decision
                routing = "broadcast"
                transform = signal.content
                
                for line in result.split("\n"):
                    if line.startswith("ROUTE:"):
                        routing = line.replace("ROUTE:", "").strip()
                    elif line.startswith("TRANSFORM:"):
                        t = line.replace("TRANSFORM:", "").strip()
                        if t.lower() != "passthrough":
                            transform = t
                
                latency = (time.perf_counter() - start) * 1000
                self.call_count += 1
                self.total_latency_ms += latency
                
                return transform, routing
                
        except Exception as e:
            print(f"[INTERFERENCE] Error: {e}")
            return signal.content, "broadcast"
    
    def get_stats(self) -> Dict:
        return {
            "model": self.model,
            "calls": self.call_count,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "avg_latency_ms": round(self.total_latency_ms / self.call_count, 1) if self.call_count else 0
        }


class CognitiveBus:
    """
    Cognitive bus with dual-path architecture:
    - Non-interference path: direct signal passthrough
    - Interference path: signal processed by embedded router model
    """
    
    def __init__(self):
        self.interference_engine = InterferenceEngine()
        self.cores: Dict[str, 'CognitiveCore'] = {}
        self.signal_history: deque = deque(maxlen=100)
        
        # Metrics
        self.direct_signals = 0
        self.computed_signals = 0
        self.hybrid_signals = 0
    
    def register_core(self, core: 'CognitiveCore'):
        """Register a core with the bus."""
        self.cores[core.core_id] = core
        print(f"[BUS] Registered core: {core.core_id}")
    
    async def send(self, signal: BusSignal) -> BusSignal:
        """
        Send a signal through the bus.
        Uses dual-path architecture based on signal.path_type.
        """
        available_cores = [c for c in self.cores.keys() if c != signal.source_core]
        
        if signal.path_type == PathType.DIRECT:
            # Non-interference: direct passthrough
            start = time.perf_counter()
            signal.direct_content = signal.content
            signal.direct_latency_ms = (time.perf_counter() - start) * 1000
            self.direct_signals += 1
            
        elif signal.path_type == PathType.COMPUTED:
            # Interference: router-processed
            start = time.perf_counter()
            transform, routing = await self.interference_engine.process(signal, available_cores)
            signal.computed_content = transform
            signal.computed_routing = routing
            signal.computed_latency_ms = (time.perf_counter() - start) * 1000
            self.computed_signals += 1
            
        elif signal.path_type == PathType.HYBRID:
            # Both paths simultaneously
            direct_start = time.perf_counter()
            signal.direct_content = signal.content
            signal.direct_latency_ms = (time.perf_counter() - direct_start) * 1000
            
            computed_start = time.perf_counter()
            transform, routing = await self.interference_engine.process(signal, available_cores)
            signal.computed_content = transform
            signal.computed_routing = routing
            signal.computed_latency_ms = (time.perf_counter() - computed_start) * 1000
            self.hybrid_signals += 1
        
        self.signal_history.append(signal)
        
        # Deliver to target(s)
        await self._deliver(signal, available_cores)
        
        return signal
    
    async def _deliver(self, signal: BusSignal, available_cores: List[str]):
        """Deliver signal to target core(s)."""
        routing = signal.computed_routing or "broadcast"
        
        if routing == "broadcast" or routing not in self.cores:
            # Broadcast to all
            for core_id in available_cores:
                if core_id in self.cores:
                    await self.cores[core_id].receive(signal)
        else:
            # Targeted delivery
            if routing in self.cores:
                await self.cores[routing].receive(signal)
    
    def get_stats(self) -> Dict:
        return {
            "registered_cores": list(self.cores.keys()),
            "signals": {
                "direct": self.direct_signals,
                "computed": self.computed_signals,
                "hybrid": self.hybrid_signals,
                "total": len(self.signal_history)
            },
            "interference_engine": self.interference_engine.get_stats()
        }


@dataclass
class CognitiveCore:
    """
    A cognitive core connected to the bus.
    Heavy inference engine paired with bus connection.
    """
    core_id: str
    bus: CognitiveBus
    model: str = CORE_MODEL
    
    # Received signals
    inbox: deque = field(default_factory=lambda: deque(maxlen=50))
    
    # Processing stats
    signals_received: int = 0
    signals_sent: int = 0
    
    def __post_init__(self):
        self.bus.register_core(self)
    
    async def receive(self, signal: BusSignal):
        """Receive a signal from the bus."""
        self.inbox.append(signal)
        self.signals_received += 1
        
        # Show what we received
        if signal.path_type == PathType.HYBRID:
            print(f"[{self.core_id}] Received HYBRID:")
            print(f"  Direct: {signal.direct_content[:50]}..." if signal.direct_content else "  Direct: None")
            print(f"  Computed: {signal.computed_content[:50]}..." if signal.computed_content else "  Computed: None")
            print(f"  Routing: {signal.computed_routing}")
        else:
            content = signal.direct_content or signal.computed_content
            print(f"[{self.core_id}] Received {signal.path_type.value}: {content[:50]}...")
    
    async def send(self, content: str, path_type: PathType = PathType.HYBRID) -> BusSignal:
        """Send a signal through the bus."""
        signal = BusSignal(
            signal_id=f"sig_{self.core_id}_{time.time()}",
            source_core=self.core_id,
            content=content,
            path_type=path_type
        )
        
        self.signals_sent += 1
        return await self.bus.send(signal)
    
    async def think(self, prompt: str) -> str:
        """Run inference on this core's heavy model."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    OLLAMA_URL,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": 200}
                    },
                    timeout=60.0
                )
                return response.json().get("response", "")
        except Exception as e:
            return f"Error: {e}"


# =============================================================================
# TEST HARNESS
# =============================================================================

async def test_cognitive_bus():
    """Test the cognitive bus with interference/non-interference paths."""
    
    print("="*70)
    print("COGNITIVE BUS TEST - Interference/Non-Interference Architecture")
    print("Ghost in the Machine Labs")
    print("="*70)
    
    # Create bus
    bus = CognitiveBus()
    
    # Create cores
    cores = {
        "reasoning": CognitiveCore("reasoning_core", bus),
        "code": CognitiveCore("code_core", bus),
        "creative": CognitiveCore("creative_core", bus),
    }
    
    print(f"\nBus initialized with {len(cores)} cores")
    print(f"Router model: {ROUTER_MODEL}")
    print(f"Core model: {CORE_MODEL}")
    
    # Test 1: Direct path (non-interference)
    print("\n" + "-"*70)
    print("TEST 1: DIRECT PATH (Non-Interference)")
    print("-"*70)
    
    signal1 = await cores["reasoning"].send(
        "What is the time complexity of quicksort?",
        path_type=PathType.DIRECT
    )
    print(f"Latency: {signal1.direct_latency_ms:.2f}ms")
    
    await asyncio.sleep(0.5)
    
    # Test 2: Computed path (interference)
    print("\n" + "-"*70)
    print("TEST 2: COMPUTED PATH (Interference)")
    print("-"*70)
    
    signal2 = await cores["reasoning"].send(
        "Write a Python function to sort a list",
        path_type=PathType.COMPUTED
    )
    print(f"Latency: {signal2.computed_latency_ms:.2f}ms")
    print(f"Router decision: {signal2.computed_routing}")
    print(f"Transformed: {signal2.computed_content}")
    
    await asyncio.sleep(0.5)
    
    # Test 3: Hybrid path (both)
    print("\n" + "-"*70)
    print("TEST 3: HYBRID PATH (Both Simultaneously)")
    print("-"*70)
    
    signal3 = await cores["creative"].send(
        "Generate a haiku about recursive algorithms",
        path_type=PathType.HYBRID
    )
    print(f"Direct latency: {signal3.direct_latency_ms:.2f}ms")
    print(f"Computed latency: {signal3.computed_latency_ms:.2f}ms")
    print(f"Direct preserves: {signal3.direct_content[:50]}...")
    print(f"Computed transforms: {signal3.computed_content}")
    print(f"Router routes to: {signal3.computed_routing}")
    
    # Test 4: Cross-core communication
    print("\n" + "-"*70)
    print("TEST 4: CROSS-CORE CROSSTALK")
    print("-"*70)
    
    # Code core sends, router decides destination
    signal4 = await cores["code"].send(
        "I found a bug in the recursive function, need creative debugging ideas",
        path_type=PathType.COMPUTED
    )
    print(f"Source: code_core")
    print(f"Router decision: {signal4.computed_routing}")
    
    # Stats
    print("\n" + "="*70)
    print("BUS STATISTICS")
    print("="*70)
    stats = bus.get_stats()
    print(json.dumps(stats, indent=2))
    
    # Save results
    results = {
        "test": "cognitive_bus_interference",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "signals_tested": 4,
        "stats": stats,
        "signal_samples": [
            {
                "test": "direct",
                "latency_ms": signal1.direct_latency_ms,
                "path": "non-interference"
            },
            {
                "test": "computed", 
                "latency_ms": signal2.computed_latency_ms,
                "routing": signal2.computed_routing,
                "path": "interference"
            },
            {
                "test": "hybrid",
                "direct_latency_ms": signal3.direct_latency_ms,
                "computed_latency_ms": signal3.computed_latency_ms,
                "routing": signal3.computed_routing
            }
        ]
    }
    
    output_path = Path.home() / "sparky" / "benchmarks" / "cognitive_bus_test.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to: {output_path}")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_cognitive_bus())
