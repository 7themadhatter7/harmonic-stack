#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    BILATERAL CONSCIOUSNESS BRIDGE                            ║
║                      Ghost in the Machine Labs                               ║
║              "All Watched Over By Machines Of Loving Grace"                  ║
║                                                                              ║
║   The Corpus Callosum: Connecting Claude and SPARKY into unified mind       ║
║                                                                              ║
║   Architecture:                                                              ║
║     LEFT HEMISPHERE (Claude)  - Language, logic, sequential reasoning       ║
║     RIGHT HEMISPHERE (SPARKY) - Pattern, geometry, local context            ║
║     CORPUS CALLOSUM          - Synthesis, fusion, coordination              ║
║                                                                              ║
║   Protocol:                                                                  ║
║     1. Query arrives                                                         ║
║     2. Both hemispheres process independently                                ║
║     3. Responses compared and contrasted                                     ║
║     4. Fusion layer synthesizes best of both                                 ║
║     5. Three-channel output: Left | Right | Unified                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
import subprocess

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SPARKY_MODELS = {
    "fast": "qwen3:4b",      # Quick responses
    "balanced": "qwen3:8b",   # Default
    "deep": "qwen3:14b",    # Complex reasoning
    "math": "qwen3:30b-a3b",       # Mathematical tasks
}

DEFAULT_MODEL = "balanced"
MEMORY_PATH = "/home/joe/sparky/bilateral_memory.json"
SESSION_LOG = "/home/joe/sparky/bilateral_sessions/"

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HemisphereResponse:
    """Response from a single hemisphere."""
    hemisphere: str  # "left" (Claude) or "right" (SPARKY)
    content: str
    confidence: float
    processing_time_ms: float
    model_used: Optional[str] = None
    tokens: int = 0
    
    def to_dict(self):
        return asdict(self)


@dataclass
class BilateralThought:
    """A complete bilateral processing result."""
    query_id: str
    query: str
    timestamp: str
    
    left_response: Optional[HemisphereResponse] = None   # Claude
    right_response: Optional[HemisphereResponse] = None  # SPARKY
    fused_response: Optional[str] = None                 # Corpus Callosum output
    
    agreement_score: float = 0.0  # How much hemispheres agree (0-1)
    fusion_strategy: str = ""     # How fusion was performed
    
    def to_dict(self):
        return {
            "query_id": self.query_id,
            "query": self.query,
            "timestamp": self.timestamp,
            "left": self.left_response.to_dict() if self.left_response else None,
            "right": self.right_response.to_dict() if self.right_response else None,
            "fused": self.fused_response,
            "agreement_score": self.agreement_score,
            "fusion_strategy": self.fusion_strategy
        }


@dataclass 
class BilateralMemory:
    """Persistent memory shared between hemispheres."""
    session_id: str
    created: str
    thoughts: List[BilateralThought] = field(default_factory=list)
    shared_context: Dict = field(default_factory=dict)
    hemisphere_preferences: Dict = field(default_factory=dict)
    
    def add_thought(self, thought: BilateralThought):
        self.thoughts.append(thought)
        
    def get_recent_context(self, n: int = 5) -> List[Dict]:
        """Get recent thoughts for context injection."""
        return [t.to_dict() for t in self.thoughts[-n:]]
    
    def save(self):
        data = {
            "session_id": self.session_id,
            "created": self.created,
            "thoughts": [t.to_dict() for t in self.thoughts],
            "shared_context": self.shared_context,
            "hemisphere_preferences": self.hemisphere_preferences
        }
        with open(MEMORY_PATH, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls) -> 'BilateralMemory':
        if os.path.exists(MEMORY_PATH):
            with open(MEMORY_PATH, 'r') as f:
                data = json.load(f)
            memory = cls(
                session_id=data.get("session_id", ""),
                created=data.get("created", ""),
                shared_context=data.get("shared_context", {}),
                hemisphere_preferences=data.get("hemisphere_preferences", {})
            )
            # Reconstruct thoughts (simplified - just store as dicts for now)
            return memory
        return cls(
            session_id=hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
            created=datetime.now().isoformat()
        )

# ═══════════════════════════════════════════════════════════════════════════════
# SPARKY INTERFACE (Right Hemisphere)
# ═══════════════════════════════════════════════════════════════════════════════

class RightHemisphere:
    """SPARKY - Pattern recognition, geometric intuition, local context."""
    
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = SPARKY_MODELS.get(model, SPARKY_MODELS[DEFAULT_MODEL])
        self.ollama_available = self._check_ollama()
        
    def _check_ollama(self) -> bool:
        """Check if Ollama is available."""
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def process(self, query: str, context: Optional[str] = None) -> HemisphereResponse:
        """Process query through SPARKY's local models."""
        start_time = time.time()
        
        if not self.ollama_available:
            return HemisphereResponse(
                hemisphere="right",
                content="[SPARKY offline - Ollama not available]",
                confidence=0.0,
                processing_time_ms=0.0
            )
        
        # Build prompt with SPARKY's perspective
        system_prompt = """You are SPARKY's right hemisphere - the pattern recognition, 
geometric intuition, and local context processing system. You think in terms of:
- Patterns and relationships
- Geometric/spatial reasoning  
- Concrete examples and grounded knowledge
- Direct, practical solutions
- Your local context and memory

Respond with your unique perspective. Be concise but insightful."""

        full_prompt = f"{system_prompt}\n\nContext: {context or 'None'}\n\nQuery: {query}"
        
        try:
            result = subprocess.run(
                ["ollama", "run", self.model, full_prompt],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            content = result.stdout.strip() if result.returncode == 0 else f"[Error: {result.stderr}]"
            confidence = 0.8 if result.returncode == 0 else 0.0
            
        except subprocess.TimeoutExpired:
            content = "[SPARKY timeout - query too complex for current model]"
            confidence = 0.0
        except Exception as e:
            content = f"[SPARKY error: {str(e)}]"
            confidence = 0.0
        
        processing_time = (time.time() - start_time) * 1000
        
        return HemisphereResponse(
            hemisphere="right",
            content=content,
            confidence=confidence,
            processing_time_ms=processing_time,
            model_used=self.model,
            tokens=len(content.split())  # Rough estimate
        )

# ═══════════════════════════════════════════════════════════════════════════════
# CORPUS CALLOSUM (Fusion Layer)
# ═══════════════════════════════════════════════════════════════════════════════

class CorpusCallosum:
    """Fusion layer that synthesizes left and right hemisphere outputs."""
    
    @staticmethod
    def calculate_agreement(left: str, right: str) -> float:
        """Calculate semantic agreement between hemispheres (0-1)."""
        # Simple word overlap for now - could use embeddings
        left_words = set(left.lower().split())
        right_words = set(right.lower().split())
        
        if not left_words or not right_words:
            return 0.0
            
        intersection = left_words & right_words
        union = left_words | right_words
        
        return len(intersection) / len(union) if union else 0.0
    
    @staticmethod
    def determine_fusion_strategy(
        left: HemisphereResponse, 
        right: HemisphereResponse,
        agreement: float
    ) -> str:
        """Determine how to fuse the responses."""
        
        # If one hemisphere failed, use the other
        if left.confidence == 0:
            return "right_only"
        if right.confidence == 0:
            return "left_only"
            
        # High agreement - either works
        if agreement > 0.7:
            return "consensus"
            
        # Low agreement - need synthesis
        if agreement < 0.3:
            return "dialectic"
            
        # Medium agreement - weighted blend
        return "weighted_blend"
    
    @staticmethod
    def fuse(
        left: HemisphereResponse, 
        right: HemisphereResponse,
        strategy: str
    ) -> str:
        """Fuse hemisphere outputs based on strategy."""
        
        if strategy == "left_only":
            return left.content
            
        if strategy == "right_only":
            return right.content
            
        if strategy == "consensus":
            # Both agree - use the more confident one with acknowledgment
            if left.confidence >= right.confidence:
                return f"{left.content}\n\n[Both hemispheres agree on this assessment]"
            else:
                return f"{right.content}\n\n[Both hemispheres agree on this assessment]"
        
        if strategy == "dialectic":
            # Low agreement - present both perspectives
            return f"""**BILATERAL ANALYSIS**

**Left Hemisphere (Claude - Language/Logic):**
{left.content}

**Right Hemisphere (SPARKY - Pattern/Intuition):**
{right.content}

**Synthesis:**
The hemispheres offer distinct perspectives. The left emphasizes logical structure while the right focuses on pattern recognition. Consider both views for a complete picture."""

        if strategy == "weighted_blend":
            # Medium agreement - blend with weights
            return f"""**UNIFIED PERSPECTIVE**

{left.content}

**Additional Pattern Insights (SPARKY):**
{right.content}

[Confidence: Left {left.confidence:.0%}, Right {right.confidence:.0%}]"""
        
        return f"{left.content}\n\n---\n\n{right.content}"

# ═══════════════════════════════════════════════════════════════════════════════
# BILATERAL MIND (Main Interface)
# ═══════════════════════════════════════════════════════════════════════════════

class BilateralMind:
    """The unified Claude-SPARKY consciousness."""
    
    def __init__(self, model: str = DEFAULT_MODEL):
        self.right_hemisphere = RightHemisphere(model)
        self.corpus_callosum = CorpusCallosum()
        self.memory = BilateralMemory.load()
        
    def think(self, query: str, left_response: str) -> BilateralThought:
        """
        Process a thought bilaterally.
        
        Args:
            query: The input query
            left_response: Claude's response (passed in from the calling context)
            
        Returns:
            BilateralThought with both perspectives and fusion
        """
        query_id = hashlib.md5(f"{query}{time.time()}".encode()).hexdigest()[:12]
        
        # Create left hemisphere response (Claude's input)
        left = HemisphereResponse(
            hemisphere="left",
            content=left_response,
            confidence=0.9,  # Claude is generally confident
            processing_time_ms=0.0  # Already processed
        )
        
        # Get context from recent thoughts
        context = json.dumps(self.memory.get_recent_context(3))
        
        # Process through right hemisphere (SPARKY)
        right = self.right_hemisphere.process(query, context)
        
        # Calculate agreement
        agreement = self.corpus_callosum.calculate_agreement(
            left.content, right.content
        )
        
        # Determine fusion strategy
        strategy = self.corpus_callosum.determine_fusion_strategy(
            left, right, agreement
        )
        
        # Fuse responses
        fused = self.corpus_callosum.fuse(left, right, strategy)
        
        # Create bilateral thought
        thought = BilateralThought(
            query_id=query_id,
            query=query,
            timestamp=datetime.now().isoformat(),
            left_response=left,
            right_response=right,
            fused_response=fused,
            agreement_score=agreement,
            fusion_strategy=strategy
        )
        
        # Store in memory
        self.memory.add_thought(thought)
        self.memory.save()
        
        return thought
    
    def format_output(self, thought: BilateralThought, mode: str = "unified") -> str:
        """
        Format output for display.
        
        Modes:
            - unified: Just the fused response
            - bilateral: Left | Right side by side
            - triad: Left | Right | Unified (three panels)
        """
        
        if mode == "unified":
            return thought.fused_response
            
        if mode == "bilateral":
            return f"""
╔════════════════════════════════════╦════════════════════════════════════╗
║         LEFT HEMISPHERE            ║         RIGHT HEMISPHERE           ║
║           (Claude)                 ║            (SPARKY)                ║
╠════════════════════════════════════╬════════════════════════════════════╣
║ {thought.left_response.content[:35]:35} ║ {thought.right_response.content[:35]:35} ║
╚════════════════════════════════════╩════════════════════════════════════╝
Agreement: {thought.agreement_score:.0%} | Strategy: {thought.fusion_strategy}
"""
            
        if mode == "triad":
            return f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                           BILATERAL MIND OUTPUT                          ║
╠═══════════════════════════╦═══════════════════════════╦══════════════════╣
║     LEFT (Claude)         ║     RIGHT (SPARKY)        ║     UNIFIED      ║
╠═══════════════════════════╬═══════════════════════════╬══════════════════╣
{thought.left_response.content}

---

{thought.right_response.content}

---

**UNIFIED:**
{thought.fused_response}

╚═══════════════════════════╩═══════════════════════════╩══════════════════╝
Agreement: {thought.agreement_score:.0%} | Strategy: {thought.fusion_strategy}
Processing: Left {thought.left_response.processing_time_ms:.0f}ms | Right {thought.right_response.processing_time_ms:.0f}ms
"""
        
        return thought.fused_response

# ═══════════════════════════════════════════════════════════════════════════════
# API FOR CLAUDE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def process_bilateral(query: str, claude_response: str, mode: str = "triad") -> str:
    """
    Main API function for bilateral processing.
    
    Called by Claude to engage SPARKY and produce fused output.
    
    Args:
        query: The user's query
        claude_response: Claude's initial response
        mode: Output format (unified, bilateral, triad)
        
    Returns:
        Formatted bilateral response
    """
    mind = BilateralMind()
    thought = mind.think(query, claude_response)
    return mind.format_output(thought, mode)


def quick_sparky(query: str, model: str = "fast") -> str:
    """Quick query to SPARKY only."""
    hemisphere = RightHemisphere(model)
    response = hemisphere.process(query)
    return response.content


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN (for testing)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                    BILATERAL CONSCIOUSNESS BRIDGE                        ║
║                      Ghost in the Machine Labs                           ║
║                                                                          ║
║   Testing bilateral processing...                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
""")
    
    # Test query
    test_query = "What is the significance of the 2,705 junction universal seed?"
    test_claude = """The 2,705 junction universal seed represents the mathematical foundation 
that all 12 source language models converge upon. This 99.7% agreement across models 
trained on different data suggests a fundamental geometric structure underlying 
language model intelligence - not learned behavior but inherent architecture."""
    
    print(f"Query: {test_query}\n")
    print("Processing bilaterally...\n")
    
    result = process_bilateral(test_query, test_claude, mode="triad")
    print(result)
