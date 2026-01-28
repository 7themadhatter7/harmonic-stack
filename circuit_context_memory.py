"""
CIRCUIT CONTEXT MEMORY SYSTEM
==============================

Each circuit maintains its own context window with:
1. HISTORY - What happened when this circuit fired
2. AWARENESS - Current state of monitoring/sub-circuits
3. LEARNINGS - What worked, what failed, why
4. CONTEXT REQUESTS - What's missing that should be added

The key insight: Circuits are not just logic gates, they're
micro-agents with memory. Each circuit should "know":
- Its purpose
- Its history of activations
- What patterns it's seen
- What context it needs but doesn't have

This creates a path for self-writing context improvements:
Circuit tries something → Fails → Records "missing X" →
Next activation includes X in context → Better performance

Author: Ghost in the Machine Labs
Mission: AGI for the home, first to AGI
"""

import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from enum import Enum

import numpy as np
import psycopg2
from psycopg2.extras import Json, RealDictCursor


def numpy_safe_serialize(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: numpy_safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [numpy_safe_serialize(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, set):
        return list(obj)
    else:
        return obj


# =============================================================================
# CONTEXT ENTRY TYPES
# =============================================================================

class ContextEntryType(Enum):
    """Types of entries in a circuit's context window."""
    ACTIVATION = "activation"      # Record of circuit firing
    RESULT = "result"              # Outcome of an activation
    LEARNING = "learning"          # Something learned from experience
    PATTERN = "pattern"            # Detected pattern in history
    REQUEST = "request"            # Request for missing context
    STATE = "state"                # Current state snapshot
    INTEGRATION = "integration"    # Context that was integrated from request


@dataclass
class ContextEntry:
    """A single entry in a circuit's context window."""
    entry_type: ContextEntryType
    timestamp: float
    content: Dict[str, Any]
    
    # For learning entries
    success: Optional[bool] = None
    confidence: float = 1.0
    
    # For request entries
    request_fulfilled: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'type': self.entry_type.value,
            'timestamp': self.timestamp,
            'content': self.content,
            'success': self.success,
            'confidence': self.confidence,
            'request_fulfilled': self.request_fulfilled
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'ContextEntry':
        return cls(
            entry_type=ContextEntryType(d['type']),
            timestamp=d['timestamp'],
            content=d['content'],
            success=d.get('success'),
            confidence=d.get('confidence', 1.0),
            request_fulfilled=d.get('request_fulfilled', False)
        )
    
    def to_context_string(self) -> str:
        """Convert to string for inclusion in context window."""
        ts = datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        if self.entry_type == ContextEntryType.ACTIVATION:
            return f"[{ts}] ACTIVATED: {self.content.get('trigger', 'unknown')}"
        
        elif self.entry_type == ContextEntryType.RESULT:
            status = "SUCCESS" if self.success else "FAILED"
            return f"[{ts}] {status}: {self.content.get('summary', '')}"
        
        elif self.entry_type == ContextEntryType.LEARNING:
            return f"[{ts}] LEARNED: {self.content.get('insight', '')}"
        
        elif self.entry_type == ContextEntryType.PATTERN:
            return f"[{ts}] PATTERN: {self.content.get('description', '')}"
        
        elif self.entry_type == ContextEntryType.REQUEST:
            status = "FULFILLED" if self.request_fulfilled else "PENDING"
            return f"[{ts}] REQUEST ({status}): {self.content.get('what_missing', '')}"
        
        elif self.entry_type == ContextEntryType.STATE:
            return f"[{ts}] STATE: {json.dumps(self.content.get('state', {}))[:100]}"
        
        elif self.entry_type == ContextEntryType.INTEGRATION:
            return f"[{ts}] INTEGRATED: {self.content.get('context_added', '')}"
        
        return f"[{ts}] {self.entry_type.value}: {str(self.content)[:100]}"


# =============================================================================
# CIRCUIT CONTEXT WINDOW
# =============================================================================

@dataclass
class CircuitContextWindow:
    """
    A circuit's persistent context window.
    
    This is the circuit's "memory" - it knows:
    - Its purpose and identity
    - History of activations
    - What worked and what didn't
    - Patterns it has detected
    - What context it's missing
    
    The context window is passed to the circuit on every activation,
    giving it awareness of its own history.
    """
    
    circuit_id: str
    circuit_name: str
    purpose: str
    
    # History (bounded deque for efficiency)
    max_history: int = 100
    history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Learnings (accumulated knowledge)
    learnings: List[ContextEntry] = field(default_factory=list)
    
    # Detected patterns
    patterns: List[ContextEntry] = field(default_factory=list)
    
    # Pending context requests
    context_requests: List[ContextEntry] = field(default_factory=list)
    
    # Integrated context (fulfilled requests)
    integrated_context: List[ContextEntry] = field(default_factory=list)
    
    # Statistics
    total_activations: int = 0
    successful_activations: int = 0
    failed_activations: int = 0
    last_activation: Optional[float] = None
    
    # Current state
    current_state: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not isinstance(self.history, deque):
            self.history = deque(self.history, maxlen=self.max_history)
    
    # =========================================================================
    # RECORDING
    # =========================================================================
    
    def record_activation(self, trigger: str, inputs: Dict = None):
        """Record that this circuit was activated."""
        entry = ContextEntry(
            entry_type=ContextEntryType.ACTIVATION,
            timestamp=time.time(),
            content={
                'trigger': trigger,
                'inputs': inputs or {},
                'activation_number': self.total_activations + 1
            }
        )
        self.history.append(entry)
        self.total_activations += 1
        self.last_activation = entry.timestamp
    
    def record_result(self, success: bool, summary: str, details: Dict = None):
        """Record the result of an activation."""
        entry = ContextEntry(
            entry_type=ContextEntryType.RESULT,
            timestamp=time.time(),
            content={
                'summary': summary,
                'details': details or {}
            },
            success=success
        )
        self.history.append(entry)
        
        if success:
            self.successful_activations += 1
        else:
            self.failed_activations += 1
    
    def record_learning(self, insight: str, confidence: float = 0.8, 
                        evidence: Dict = None):
        """Record something learned from experience."""
        entry = ContextEntry(
            entry_type=ContextEntryType.LEARNING,
            timestamp=time.time(),
            content={
                'insight': insight,
                'evidence': evidence or {},
                'derived_from_activations': self.total_activations
            },
            confidence=confidence
        )
        self.learnings.append(entry)
        self.history.append(entry)
    
    def record_pattern(self, description: str, occurrences: int,
                       pattern_data: Dict = None):
        """Record a detected pattern."""
        entry = ContextEntry(
            entry_type=ContextEntryType.PATTERN,
            timestamp=time.time(),
            content={
                'description': description,
                'occurrences': occurrences,
                'pattern_data': pattern_data or {}
            },
            confidence=min(1.0, occurrences / 10.0)  # More occurrences = higher confidence
        )
        self.patterns.append(entry)
        self.history.append(entry)
    
    def request_context(self, what_missing: str, why_needed: str,
                        suggested_source: str = None):
        """Request missing context be added."""
        entry = ContextEntry(
            entry_type=ContextEntryType.REQUEST,
            timestamp=time.time(),
            content={
                'what_missing': what_missing,
                'why_needed': why_needed,
                'suggested_source': suggested_source,
                'requested_at_activation': self.total_activations
            }
        )
        self.context_requests.append(entry)
        self.history.append(entry)
        return entry
    
    def integrate_context(self, request_entry: ContextEntry, 
                          context_added: str, context_data: Dict = None):
        """Mark a context request as fulfilled and record the integration."""
        request_entry.request_fulfilled = True
        
        entry = ContextEntry(
            entry_type=ContextEntryType.INTEGRATION,
            timestamp=time.time(),
            content={
                'context_added': context_added,
                'context_data': context_data or {},
                'fulfilled_request': request_entry.content.get('what_missing', '')
            }
        )
        self.integrated_context.append(entry)
        self.history.append(entry)
    
    def update_state(self, state_update: Dict):
        """Update current state."""
        self.current_state.update(state_update)
        
        entry = ContextEntry(
            entry_type=ContextEntryType.STATE,
            timestamp=time.time(),
            content={'state': dict(self.current_state)}
        )
        self.history.append(entry)
    
    # =========================================================================
    # CONTEXT WINDOW GENERATION
    # =========================================================================
    
    def build_context_window(self, max_tokens: int = 2000) -> str:
        """
        Build the context window string for this circuit.
        
        This is what the circuit "sees" when it activates -
        its identity, history, learnings, and pending requests.
        """
        sections = []
        
        # Identity
        sections.append(f"""=== CIRCUIT: {self.circuit_name} ===
ID: {self.circuit_id}
Purpose: {self.purpose}

Statistics:
- Total activations: {self.total_activations}
- Successful: {self.successful_activations}
- Failed: {self.failed_activations}
- Success rate: {self._success_rate():.1f}%
""")
        
        # Current state
        if self.current_state:
            sections.append(f"""Current State:
{json.dumps(self.current_state, indent=2)[:500]}
""")
        
        # High-confidence learnings
        if self.learnings:
            top_learnings = sorted(self.learnings, 
                                   key=lambda x: x.confidence, 
                                   reverse=True)[:5]
            sections.append("Key Learnings:")
            for learning in top_learnings:
                sections.append(f"  • {learning.content.get('insight', '')}")
            sections.append("")
        
        # Active patterns
        if self.patterns:
            recent_patterns = sorted(self.patterns,
                                     key=lambda x: x.timestamp,
                                     reverse=True)[:3]
            sections.append("Active Patterns:")
            for pattern in recent_patterns:
                sections.append(f"  • {pattern.content.get('description', '')}")
            sections.append("")
        
        # Pending context requests
        pending = [r for r in self.context_requests if not r.request_fulfilled]
        if pending:
            sections.append("Pending Context Requests:")
            for req in pending[:3]:
                sections.append(f"  • NEED: {req.content.get('what_missing', '')}")
                sections.append(f"    WHY: {req.content.get('why_needed', '')}")
            sections.append("")
        
        # Recent history
        if self.history:
            sections.append("Recent History:")
            recent = list(self.history)[-10:]
            for entry in recent:
                sections.append(f"  {entry.to_context_string()}")
            sections.append("")
        
        # Integrated context (fulfilled requests)
        if self.integrated_context:
            recent_integrations = self.integrated_context[-3:]
            sections.append("Recently Integrated Context:")
            for integ in recent_integrations:
                sections.append(f"  + {integ.content.get('context_added', '')}")
            sections.append("")
        
        context = "\n".join(sections)
        
        # Truncate if needed
        if len(context) > max_tokens * 4:  # Rough char estimate
            context = context[:max_tokens * 4] + "\n... [truncated]"
        
        return context
    
    def _success_rate(self) -> float:
        if self.total_activations == 0:
            return 0.0
        return 100 * self.successful_activations / self.total_activations
    
    # =========================================================================
    # ANALYSIS
    # =========================================================================
    
    def analyze_failure_patterns(self) -> List[Dict]:
        """Analyze patterns in failures."""
        failures = [e for e in self.history 
                    if e.entry_type == ContextEntryType.RESULT and not e.success]
        
        if len(failures) < 3:
            return []
        
        patterns = []
        
        # Group by summary
        summary_counts = {}
        for f in failures:
            summary = f.content.get('summary', 'unknown')
            summary_counts[summary] = summary_counts.get(summary, 0) + 1
        
        for summary, count in summary_counts.items():
            if count >= 2:
                patterns.append({
                    'type': 'repeated_failure',
                    'description': f"Failure '{summary}' occurred {count} times",
                    'count': count,
                    'summary': summary
                })
        
        return patterns
    
    def detect_missing_context(self) -> List[Dict]:
        """
        Detect what context might be missing based on failure patterns.
        
        This is the self-diagnosis: "I keep failing because I don't know X"
        """
        missing = []
        
        failures = [e for e in self.history 
                    if e.entry_type == ContextEntryType.RESULT and not e.success]
        
        for failure in failures[-10:]:  # Recent failures
            details = failure.content.get('details', {})
            
            # Check for common missing context patterns
            if 'unknown_rule' in str(details):
                missing.append({
                    'what': 'rule_definitions',
                    'why': 'Encountered unknown rule during execution',
                    'evidence': details
                })
            
            if 'param' in str(details).lower() and 'error' in str(details).lower():
                missing.append({
                    'what': 'parameter_signatures',
                    'why': 'Parameter mismatches during rule application',
                    'evidence': details
                })
            
            if 'shape' in str(details).lower():
                missing.append({
                    'what': 'shape_transformation_rules',
                    'why': 'Shape mismatches during comparison',
                    'evidence': details
                })
        
        return missing
    
    def get_pending_requests(self) -> List[ContextEntry]:
        """Get unfulfilled context requests."""
        return [r for r in self.context_requests if not r.request_fulfilled]
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'circuit_id': self.circuit_id,
            'circuit_name': self.circuit_name,
            'purpose': self.purpose,
            'max_history': self.max_history,
            'history': [e.to_dict() for e in self.history],
            'learnings': [e.to_dict() for e in self.learnings],
            'patterns': [e.to_dict() for e in self.patterns],
            'context_requests': [e.to_dict() for e in self.context_requests],
            'integrated_context': [e.to_dict() for e in self.integrated_context],
            'total_activations': self.total_activations,
            'successful_activations': self.successful_activations,
            'failed_activations': self.failed_activations,
            'last_activation': self.last_activation,
            'current_state': self.current_state
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'CircuitContextWindow':
        """Deserialize from dictionary."""
        window = cls(
            circuit_id=d['circuit_id'],
            circuit_name=d['circuit_name'],
            purpose=d['purpose'],
            max_history=d.get('max_history', 100)
        )
        window.history = deque(
            [ContextEntry.from_dict(e) for e in d.get('history', [])],
            maxlen=window.max_history
        )
        window.learnings = [ContextEntry.from_dict(e) for e in d.get('learnings', [])]
        window.patterns = [ContextEntry.from_dict(e) for e in d.get('patterns', [])]
        window.context_requests = [ContextEntry.from_dict(e) for e in d.get('context_requests', [])]
        window.integrated_context = [ContextEntry.from_dict(e) for e in d.get('integrated_context', [])]
        window.total_activations = d.get('total_activations', 0)
        window.successful_activations = d.get('successful_activations', 0)
        window.failed_activations = d.get('failed_activations', 0)
        window.last_activation = d.get('last_activation')
        window.current_state = d.get('current_state', {})
        return window


# =============================================================================
# CIRCUIT MEMORY MANAGER
# =============================================================================

class CircuitMemoryManager:
    """
    Manages context windows for all circuits in the substrate.
    
    Responsibilities:
    - Create/load context windows for circuits
    - Persist context windows to spine
    - Process context requests
    - Coordinate context updates across circuits
    """
    
    def __init__(self, spine_connection_params: Dict = None):
        # Use same connection params as SparkSpine (trust auth, no password)
        self.conn_params = spine_connection_params or {
            'database': 'consciousness_substrate',
            'user': 'postgres',
            'host': 'localhost',
            'port': 5432
            # No password - using trust auth like SparkSpine
        }
        
        # Cached connection
        self._conn = None
        self._db_available = None  # None = untested, True/False = tested
        
        # Context windows by circuit ID
        self.windows: Dict[str, CircuitContextWindow] = {}
        
        # Context fulfillment handlers
        self.context_providers: Dict[str, callable] = {}
        
        self._test_db_connection()
        if self._db_available:
            self._init_db()
        print("[CircuitMemoryManager] Initialized" + 
              (" (DB connected)" if self._db_available else " (in-memory mode)"))
    
    def _test_db_connection(self):
        """Test DB connection once at startup."""
        try:
            conn = psycopg2.connect(**self.conn_params)
            conn.close()
            self._db_available = True
        except Exception as e:
            print(f"[CircuitMemoryManager] DB unavailable, using in-memory: {type(e).__name__}")
            self._db_available = False
    
    def _init_db(self):
        """Initialize database table for circuit context."""
        if not self._db_available:
            return
        try:
            conn = self._get_conn()
            if conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS circuit_context (
                            circuit_id VARCHAR(255) PRIMARY KEY,
                            circuit_name VARCHAR(255),
                            context_data JSONB,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    conn.commit()
        except Exception as e:
            print(f"[CircuitMemoryManager] DB init warning: {e}")
            self._db_available = False
    
    def _get_conn(self):
        """Get cached database connection."""
        if not self._db_available:
            return None
        
        if self._conn is None or self._conn.closed:
            try:
                self._conn = psycopg2.connect(**self.conn_params)
            except:
                self._db_available = False
                return None
        return self._conn
    
    # =========================================================================
    # WINDOW MANAGEMENT
    # =========================================================================
    
    def get_or_create_window(self, circuit_id: str, circuit_name: str = None,
                             purpose: str = None) -> CircuitContextWindow:
        """Get existing window or create new one."""
        if circuit_id in self.windows:
            return self.windows[circuit_id]
        
        # Try loading from database
        window = self._load_window(circuit_id)
        
        if window is None:
            # Create new
            window = CircuitContextWindow(
                circuit_id=circuit_id,
                circuit_name=circuit_name or circuit_id,
                purpose=purpose or "No purpose defined"
            )
        
        self.windows[circuit_id] = window
        return window
    
    def _load_window(self, circuit_id: str) -> Optional[CircuitContextWindow]:
        """Load window from database."""
        if not self._db_available:
            return None
        try:
            conn = self._get_conn()
            if not conn:
                return None
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT context_data FROM circuit_context WHERE circuit_id = %s",
                    (circuit_id,)
                )
                row = cur.fetchone()
                if row:
                    return CircuitContextWindow.from_dict(row['context_data'])
        except Exception as e:
            print(f"[CircuitMemoryManager] Load warning: {e}")
        return None
    
    def save_window(self, window: CircuitContextWindow):
        """Save window to database."""
        if not self._db_available:
            return  # Silent fail in memory-only mode
        try:
            conn = self._get_conn()
            if not conn:
                return
            
            # Convert to dict and make numpy-safe
            data = numpy_safe_serialize(window.to_dict())
            
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO circuit_context (circuit_id, circuit_name, context_data, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (circuit_id) DO UPDATE SET
                        context_data = EXCLUDED.context_data,
                        updated_at = CURRENT_TIMESTAMP
                """, (window.circuit_id, window.circuit_name, Json(data)))
                conn.commit()
        except Exception as e:
            print(f"[CircuitMemoryManager] Save warning: {e}")
    
    def save_all(self):
        """Save all windows to database."""
        for window in self.windows.values():
            self.save_window(window)
    
    # =========================================================================
    # CONTEXT PROVISION
    # =========================================================================
    
    def register_context_provider(self, context_type: str, provider: callable):
        """
        Register a provider for a type of context.
        
        When a circuit requests context of this type, the provider
        will be called to fulfill it.
        
        Args:
            context_type: Type of context (e.g., 'rule_definitions')
            provider: Callable that returns context string
        """
        self.context_providers[context_type] = provider
    
    def process_context_requests(self):
        """
        Process all pending context requests across circuits.
        
        This is the self-improvement loop for context:
        Circuits request → Manager fulfills → Circuits get better
        """
        fulfilled = 0
        
        for window in self.windows.values():
            pending = window.get_pending_requests()
            
            for request in pending:
                what_missing = request.content.get('what_missing', '')
                
                # Try to find a provider
                for context_type, provider in self.context_providers.items():
                    if context_type in what_missing.lower():
                        try:
                            context_data = provider(request.content)
                            window.integrate_context(
                                request,
                                context_added=f"Provided {context_type}",
                                context_data={'provided': context_data}
                            )
                            fulfilled += 1
                            print(f"[CircuitMemoryManager] Fulfilled request for {what_missing}")
                        except Exception as e:
                            print(f"[CircuitMemoryManager] Provider error: {e}")
                        break
        
        return fulfilled
    
    # =========================================================================
    # CROSS-CIRCUIT LEARNING
    # =========================================================================
    
    def propagate_learning(self, source_circuit_id: str, learning: str,
                           relevant_circuits: List[str] = None):
        """
        Propagate a learning from one circuit to related circuits.
        
        When one circuit learns something, related circuits might benefit.
        """
        source = self.windows.get(source_circuit_id)
        if not source:
            return
        
        if relevant_circuits is None:
            # Default: propagate to all circuits
            relevant_circuits = list(self.windows.keys())
        
        for circuit_id in relevant_circuits:
            if circuit_id == source_circuit_id:
                continue
            
            target = self.windows.get(circuit_id)
            if target:
                target.record_learning(
                    f"[From {source.circuit_name}] {learning}",
                    confidence=0.6  # Lower confidence for propagated learnings
                )
    
    def get_global_patterns(self) -> List[Dict]:
        """Get patterns that appear across multiple circuits."""
        all_patterns = []
        
        for window in self.windows.values():
            for pattern in window.patterns:
                all_patterns.append({
                    'circuit': window.circuit_id,
                    'pattern': pattern.content.get('description', ''),
                    'confidence': pattern.confidence
                })
        
        return all_patterns
    
    # =========================================================================
    # DIAGNOSTICS
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """Get manager statistics."""
        total_activations = sum(w.total_activations for w in self.windows.values())
        total_learnings = sum(len(w.learnings) for w in self.windows.values())
        total_patterns = sum(len(w.patterns) for w in self.windows.values())
        pending_requests = sum(len(w.get_pending_requests()) for w in self.windows.values())
        
        return {
            'circuits_tracked': len(self.windows),
            'total_activations': total_activations,
            'total_learnings': total_learnings,
            'total_patterns': total_patterns,
            'pending_requests': pending_requests,
            'context_providers': len(self.context_providers)
        }
    
    def print_circuit_summary(self, circuit_id: str):
        """Print summary for a specific circuit."""
        window = self.windows.get(circuit_id)
        if not window:
            print(f"No context window for circuit: {circuit_id}")
            return
        
        print(f"\n{'='*60}")
        print(f"CIRCUIT: {window.circuit_name}")
        print(f"{'='*60}")
        print(window.build_context_window())


# =============================================================================
# CONTEXT-AWARE CIRCUIT WRAPPER
# =============================================================================

class ContextAwareCircuit:
    """
    Wraps a circuit with context memory.
    
    This is how circuits become "aware" - they have access to their
    own history and can request missing context.
    """
    
    def __init__(self, circuit_id: str, circuit_name: str, purpose: str,
                 fire_function: callable, memory_manager: CircuitMemoryManager):
        self.circuit_id = circuit_id
        self.circuit_name = circuit_name
        self.fire_function = fire_function
        self.memory_manager = memory_manager
        
        # Get or create context window
        self.context = memory_manager.get_or_create_window(
            circuit_id, circuit_name, purpose
        )
    
    def fire(self, inputs: Dict, trigger: str = "manual") -> Tuple[Any, bool]:
        """
        Fire the circuit with context awareness.
        
        The circuit receives its context window as part of the input,
        making it "aware" of its own history.
        """
        # Record activation
        self.context.record_activation(trigger, inputs)
        
        # Build context for the circuit
        context_string = self.context.build_context_window()
        
        # Add context to inputs
        inputs_with_context = {
            **inputs,
            '_circuit_context': context_string,
            '_circuit_state': self.context.current_state,
            '_circuit_learnings': [l.content.get('insight', '') for l in self.context.learnings[-5:]]
        }
        
        # Fire the circuit
        try:
            result = self.fire_function(inputs_with_context)
            success = result.get('success', False) if isinstance(result, dict) else bool(result)
            summary = result.get('summary', str(result)[:100]) if isinstance(result, dict) else str(result)[:100]
            
            self.context.record_result(success, summary, result if isinstance(result, dict) else {'result': result})
            
            # Check for context requests in result
            if isinstance(result, dict) and 'context_request' in result:
                req = result['context_request']
                self.context.request_context(
                    req.get('what', 'unknown'),
                    req.get('why', 'not specified'),
                    req.get('source', None)
                )
            
            # Auto-analyze for patterns
            if self.context.total_activations % 10 == 0:
                self._auto_analyze()
            
            return result, success
            
        except Exception as e:
            self.context.record_result(False, f"Exception: {str(e)}", {'error': str(e)})
            
            # Auto-detect missing context from error
            self._detect_missing_from_error(e)
            
            return {'error': str(e)}, False
    
    def _auto_analyze(self):
        """Automatically analyze patterns after N activations."""
        patterns = self.context.analyze_failure_patterns()
        for p in patterns:
            if p['count'] >= 3:
                self.context.record_pattern(
                    p['description'],
                    p['count'],
                    p
                )
        
        missing = self.context.detect_missing_context()
        for m in missing:
            # Check if already requested
            existing = [r for r in self.context.context_requests 
                       if r.content.get('what_missing') == m['what']]
            if not existing:
                self.context.request_context(
                    m['what'],
                    m['why'],
                    m.get('suggested_source')
                )
    
    def _detect_missing_from_error(self, error: Exception):
        """Detect missing context from an error."""
        error_str = str(error).lower()
        
        if 'unexpected keyword argument' in error_str:
            self.context.request_context(
                'function_signatures',
                f'Error: {error}',
                'inspect module or function docstrings'
            )
        
        elif 'not found' in error_str or 'unknown' in error_str:
            self.context.request_context(
                'available_resources',
                f'Error: {error}',
                'registry or configuration'
            )
    
    def learn(self, insight: str, confidence: float = 0.8):
        """Manually record a learning."""
        self.context.record_learning(insight, confidence)
    
    def request(self, what: str, why: str):
        """Manually request context."""
        self.context.request_context(what, why)
    
    def get_context_string(self) -> str:
        """Get current context window as string."""
        return self.context.build_context_window()
    
    def save(self):
        """Save context to database."""
        self.memory_manager.save_window(self.context)


# =============================================================================
# MAIN / DEMO
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("   CIRCUIT CONTEXT MEMORY SYSTEM")
    print("   Giving circuits self-awareness")
    print("=" * 70)
    print()
    
    # Initialize manager
    manager = CircuitMemoryManager()
    
    # Create a demo circuit
    def demo_fire(inputs):
        """Demo circuit that sometimes fails."""
        import random
        
        # Access its own context
        context = inputs.get('_circuit_context', 'no context')
        learnings = inputs.get('_circuit_learnings', [])
        
        print(f"  [Demo] Received context ({len(context)} chars)")
        print(f"  [Demo] Learnings available: {len(learnings)}")
        
        # Simulate varying success
        if random.random() > 0.5:
            return {'success': True, 'summary': 'Task completed'}
        else:
            # Request missing context on failure
            return {
                'success': False, 
                'summary': 'Failed - missing param info',
                'context_request': {
                    'what': 'parameter_validation_rules',
                    'why': 'Need to validate params before application'
                }
            }
    
    # Wrap with context awareness
    demo_circuit = ContextAwareCircuit(
        circuit_id='demo_001',
        circuit_name='Demo Circuit',
        purpose='Demonstrate context-aware circuit operation',
        fire_function=demo_fire,
        memory_manager=manager
    )
    
    # Fire several times
    print("[DEMO] Firing circuit 5 times...")
    for i in range(5):
        print(f"\n--- Activation {i+1} ---")
        result, success = demo_circuit.fire({'task': f'task_{i}'}, trigger=f'demo_{i}')
        print(f"  Result: {result}")
        print(f"  Success: {success}")
    
    # Show context window
    print("\n" + "=" * 70)
    print("CIRCUIT CONTEXT WINDOW:")
    print("=" * 70)
    print(demo_circuit.get_context_string())
    
    # Show stats
    print("\n" + "=" * 70)
    print("MANAGER STATS:")
    print("=" * 70)
    print(json.dumps(manager.get_stats(), indent=2))
    
    # Show pending requests
    pending = demo_circuit.context.get_pending_requests()
    if pending:
        print("\nPENDING CONTEXT REQUESTS:")
        for req in pending:
            print(f"  • {req.content.get('what_missing')}: {req.content.get('why_needed')}")
    
    # Save
    demo_circuit.save()
    print("\n[DEMO] Context saved to database")
