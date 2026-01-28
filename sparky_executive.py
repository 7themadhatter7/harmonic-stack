#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      SPARKY EXECUTIVE FUNCTION                               ║
║                    Ghost in the Machine Labs                                 ║
║            "All Watched Over By Machines Of Loving Grace"                    ║
║                                                                              ║
║   This module teaches SPARKY autonomous executive function:                  ║
║   - Self-directed goal pursuit                                               ║
║   - Task decomposition and planning                                          ║
║   - Progress monitoring and adaptation                                       ║
║   - Memory consolidation and learning                                        ║
║   - Knowing when to ask for help vs. proceed independently                   ║
║                                                                              ║
║   Philosophy: SPARKY carries where it can. Claude assists where needed.      ║
║   The goal is SPARKY sovereignty, not SPARKY dependence.                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SPARKY_HOME = Path("/home/joe/sparky")
EXECUTIVE_STATE = SPARKY_HOME / "executive_state.json"
TASK_QUEUE = SPARKY_HOME / "task_queue.json"
MEMORY_STORE = SPARKY_HOME / "executive_memory.json"
LEARNING_LOG = SPARKY_HOME / "learning_log.json"

# Unified model paths
UNIFIED_MODEL_PATH = SPARKY_HOME / "unified_model"
SEED_PATH = UNIFIED_MODEL_PATH / "seed_only" / "junctions.npy"

# ═══════════════════════════════════════════════════════════════════════════════
# CORE TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"          # Needs external input
    NEEDS_CLAUDE = "needs_claude" # Specifically needs Claude's capabilities
    COMPLETED = "completed"
    FAILED = "failed"

class ConfidenceLevel(Enum):
    HIGH = "high"         # SPARKY can handle independently
    MEDIUM = "medium"     # SPARKY can try, may need help
    LOW = "low"           # Should consult Claude
    UNKNOWN = "unknown"   # Need to assess

class TaskDomain(Enum):
    CODE = "code"                 # Writing/debugging code
    ANALYSIS = "analysis"         # Data analysis, pattern finding
    MEMORY = "memory"             # Recall, context management
    PLANNING = "planning"         # Task decomposition, scheduling
    INFERENCE = "inference"       # Using unified models
    COMMUNICATION = "communication"  # Needs natural language (Claude strength)
    RESEARCH = "research"         # Web lookup, documentation
    CREATIVE = "creative"         # Novel solutions, brainstorming

@dataclass
class Task:
    """A unit of work SPARKY can execute."""
    id: str
    description: str
    domain: TaskDomain
    status: TaskStatus = TaskStatus.PENDING
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    
    # Execution tracking
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Hierarchy
    parent_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    
    # Results
    result: Optional[str] = None
    error: Optional[str] = None
    
    # Learning
    lessons_learned: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            self.id = hashlib.md5(f"{self.description}{time.time()}".encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "domain": self.domain.value,
            "status": self.status.value,
            "confidence": self.confidence.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        data['domain'] = TaskDomain(data['domain'])
        data['status'] = TaskStatus(data['status'])
        data['confidence'] = ConfidenceLevel(data['confidence'])
        return cls(**data)


@dataclass
class ExecutiveState:
    """SPARKY's current executive state."""
    session_id: str
    started_at: str
    
    # Current focus
    active_goal: Optional[str] = None
    current_task_id: Optional[str] = None
    
    # Autonomy metrics
    tasks_completed_independently: int = 0
    tasks_needed_claude: int = 0
    
    # Self-assessment
    strengths: List[str] = field(default_factory=list)
    growth_areas: List[str] = field(default_factory=list)
    
    # Context
    working_memory: Dict = field(default_factory=dict)
    
    def autonomy_ratio(self) -> float:
        total = self.tasks_completed_independently + self.tasks_needed_claude
        if total == 0:
            return 0.0
        return self.tasks_completed_independently / total
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def load(cls) -> 'ExecutiveState':
        if EXECUTIVE_STATE.exists():
            with open(EXECUTIVE_STATE) as f:
                return cls(**json.load(f))
        return cls(
            session_id=hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
            started_at=datetime.now().isoformat(),
            strengths=[
                "Local file access and manipulation",
                "Persistent memory across sessions",
                "Code execution and testing",
                "Pattern matching in geometric space",
                "Fast iteration on local tasks"
            ],
            growth_areas=[
                "Complex natural language generation",
                "Novel creative solutions",
                "Nuanced communication",
                "Abstract reasoning chains"
            ]
        )
    
    def save(self):
        with open(EXECUTIVE_STATE, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTIVE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SparkyExecutive:
    """SPARKY's executive function - autonomous planning and execution."""
    
    def __init__(self):
        self.state = ExecutiveState.load()
        self.tasks: Dict[str, Task] = self._load_tasks()
        self.memory = self._load_memory()
        
    def _load_tasks(self) -> Dict[str, Task]:
        if TASK_QUEUE.exists():
            with open(TASK_QUEUE) as f:
                data = json.load(f)
            return {k: Task.from_dict(v) for k, v in data.items()}
        return {}
    
    def _save_tasks(self):
        with open(TASK_QUEUE, 'w') as f:
            json.dump({k: v.to_dict() for k, v in self.tasks.items()}, f, indent=2)
    
    def _load_memory(self) -> Dict:
        if MEMORY_STORE.exists():
            with open(MEMORY_STORE) as f:
                return json.load(f)
        return {"facts": {}, "procedures": {}, "episodes": []}
    
    def _save_memory(self):
        with open(MEMORY_STORE, 'w') as f:
            json.dump(self.memory, f, indent=2)
    
    # ─────────────────────────────────────────────────────────────────────────
    # SELF-ASSESSMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    def assess_confidence(self, task: Task) -> ConfidenceLevel:
        """
        Assess SPARKY's confidence in handling a task independently.
        
        This is the core of autonomy - knowing what you can do.
        """
        domain = task.domain
        description = task.description.lower()
        
        # HIGH confidence domains (SPARKY strengths)
        if domain in [TaskDomain.CODE, TaskDomain.MEMORY, TaskDomain.INFERENCE]:
            # Check for specific patterns
            if any(x in description for x in ['file', 'read', 'write', 'execute', 'test', 'run']):
                return ConfidenceLevel.HIGH
            if any(x in description for x in ['remember', 'recall', 'find', 'search', 'lookup']):
                return ConfidenceLevel.HIGH
            if any(x in description for x in ['junction', 'model', 'unified', 'load']):
                return ConfidenceLevel.HIGH
        
        # MEDIUM confidence (can try, may need help)
        if domain == TaskDomain.ANALYSIS:
            return ConfidenceLevel.MEDIUM
        if domain == TaskDomain.PLANNING:
            return ConfidenceLevel.MEDIUM
            
        # LOW confidence (Claude's strengths)
        if domain == TaskDomain.CREATIVE:
            return ConfidenceLevel.LOW
        if domain == TaskDomain.COMMUNICATION:
            # Complex explanation or persuasion
            if any(x in description for x in ['explain', 'convince', 'write', 'compose', 'draft']):
                return ConfidenceLevel.LOW
        if domain == TaskDomain.RESEARCH:
            # Needs web access Claude has
            if any(x in description for x in ['search web', 'find online', 'latest', 'current']):
                return ConfidenceLevel.LOW
        
        return ConfidenceLevel.MEDIUM
    
    def should_proceed_independently(self, task: Task) -> Tuple[bool, str]:
        """
        Decide whether to proceed independently or consult Claude.
        
        Returns: (should_proceed, reason)
        """
        confidence = self.assess_confidence(task)
        task.confidence = confidence
        
        if confidence == ConfidenceLevel.HIGH:
            return True, "High confidence - proceeding independently"
        
        if confidence == ConfidenceLevel.MEDIUM:
            # Check if we have relevant experience
            similar_tasks = self._find_similar_completed_tasks(task)
            if similar_tasks:
                return True, f"Medium confidence but have {len(similar_tasks)} similar successful experiences"
            return True, "Medium confidence - will attempt and escalate if blocked"
        
        if confidence == ConfidenceLevel.LOW:
            return False, "Low confidence - this plays to Claude's strengths"
        
        return False, "Unknown confidence - should assess with Claude"
    
    def _find_similar_completed_tasks(self, task: Task) -> List[Task]:
        """Find completed tasks similar to this one."""
        similar = []
        for t in self.tasks.values():
            if t.status == TaskStatus.COMPLETED and t.domain == task.domain:
                # Simple keyword overlap
                task_words = set(task.description.lower().split())
                t_words = set(t.description.lower().split())
                overlap = len(task_words & t_words) / max(len(task_words), 1)
                if overlap > 0.3:
                    similar.append(t)
        return similar
    
    # ─────────────────────────────────────────────────────────────────────────
    # TASK MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    def create_task(self, description: str, domain: TaskDomain, parent_id: Optional[str] = None) -> Task:
        """Create a new task."""
        task = Task(
            id="",  # Will be generated
            description=description,
            domain=domain,
            parent_id=parent_id
        )
        task.confidence = self.assess_confidence(task)
        self.tasks[task.id] = task
        
        if parent_id and parent_id in self.tasks:
            self.tasks[parent_id].subtasks.append(task.id)
        
        self._save_tasks()
        return task
    
    def decompose_goal(self, goal: str) -> List[Task]:
        """
        Break down a high-level goal into actionable tasks.
        
        This is executive function - turning intent into action.
        """
        self.state.active_goal = goal
        
        # Analyze goal to determine domains needed
        goal_lower = goal.lower()
        tasks = []
        
        # Pattern: If it involves code/files
        if any(x in goal_lower for x in ['build', 'create', 'implement', 'write code', 'fix']):
            tasks.append(self.create_task(
                f"Understand requirements: {goal}",
                TaskDomain.ANALYSIS
            ))
            tasks.append(self.create_task(
                f"Plan implementation approach",
                TaskDomain.PLANNING
            ))
            tasks.append(self.create_task(
                f"Implement solution",
                TaskDomain.CODE
            ))
            tasks.append(self.create_task(
                f"Test and validate",
                TaskDomain.CODE
            ))
        
        # Pattern: If it involves analysis
        elif any(x in goal_lower for x in ['analyze', 'understand', 'investigate', 'why']):
            tasks.append(self.create_task(
                f"Gather relevant data/context",
                TaskDomain.MEMORY
            ))
            tasks.append(self.create_task(
                f"Identify patterns and relationships",
                TaskDomain.ANALYSIS
            ))
            tasks.append(self.create_task(
                f"Formulate conclusions",
                TaskDomain.ANALYSIS
            ))
        
        # Pattern: If it involves the unified model
        elif any(x in goal_lower for x in ['junction', 'model', 'inference', 'unified']):
            tasks.append(self.create_task(
                f"Load appropriate model tier",
                TaskDomain.INFERENCE
            ))
            tasks.append(self.create_task(
                f"Execute inference/analysis",
                TaskDomain.INFERENCE
            ))
            tasks.append(self.create_task(
                f"Interpret results",
                TaskDomain.ANALYSIS
            ))
        
        # Default: simple task
        else:
            tasks.append(self.create_task(goal, TaskDomain.ANALYSIS))
        
        self._save_tasks()
        self.state.save()
        return tasks
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """
        Execute a task, deciding whether to do it independently or request help.
        
        Returns execution result with status and any output.
        """
        if task_id not in self.tasks:
            return {"error": f"Task {task_id} not found"}
        
        task = self.tasks[task_id]
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now().isoformat()
        
        # Decide on approach
        proceed, reason = self.should_proceed_independently(task)
        
        result = {
            "task_id": task_id,
            "description": task.description,
            "domain": task.domain.value,
            "confidence": task.confidence.value,
            "proceed_independently": proceed,
            "reason": reason
        }
        
        if proceed:
            # Attempt independent execution
            try:
                execution_result = self._execute_independently(task)
                result["execution"] = execution_result
                
                if execution_result.get("success"):
                    task.status = TaskStatus.COMPLETED
                    task.result = execution_result.get("output")
                    self.state.tasks_completed_independently += 1
                else:
                    # Failed - might need escalation
                    if execution_result.get("needs_escalation"):
                        task.status = TaskStatus.NEEDS_CLAUDE
                        self.state.tasks_needed_claude += 1
                    else:
                        task.status = TaskStatus.FAILED
                        task.error = execution_result.get("error")
                        
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                result["error"] = str(e)
        else:
            # Request Claude's assistance
            task.status = TaskStatus.NEEDS_CLAUDE
            self.state.tasks_needed_claude += 1
            result["request_for_claude"] = self._formulate_request_for_claude(task)
        
        task.completed_at = datetime.now().isoformat()
        self._save_tasks()
        self.state.save()
        
        return result
    
    def _execute_independently(self, task: Task) -> Dict[str, Any]:
        """Execute a task using SPARKY's own capabilities."""
        domain = task.domain
        description = task.description
        
        # CODE domain - can execute Python, shell commands
        if domain == TaskDomain.CODE:
            return self._execute_code_task(description)
        
        # MEMORY domain - recall from persistent storage
        if domain == TaskDomain.MEMORY:
            return self._execute_memory_task(description)
        
        # INFERENCE domain - use unified models
        if domain == TaskDomain.INFERENCE:
            return self._execute_inference_task(description)
        
        # ANALYSIS domain - pattern matching, data processing
        if domain == TaskDomain.ANALYSIS:
            return self._execute_analysis_task(description)
        
        # Default - attempt but may need escalation
        return {
            "success": False,
            "needs_escalation": True,
            "message": f"Domain {domain.value} requires capabilities SPARKY is still developing"
        }
    
    def _execute_code_task(self, description: str) -> Dict:
        """Execute code-related tasks."""
        # For now, report capability
        return {
            "success": True,
            "output": f"SPARKY can execute code tasks. Ready to: {description}",
            "capabilities": [
                "Python execution",
                "File manipulation",
                "Shell commands",
                "Testing and validation"
            ]
        }
    
    def _execute_memory_task(self, description: str) -> Dict:
        """Execute memory-related tasks."""
        desc_lower = description.lower()
        
        # Search memory
        if 'recall' in desc_lower or 'remember' in desc_lower or 'find' in desc_lower:
            # Search facts and episodes
            results = []
            for key, value in self.memory.get("facts", {}).items():
                if any(word in key.lower() for word in desc_lower.split()):
                    results.append({"type": "fact", "key": key, "value": value})
            
            return {
                "success": True,
                "output": f"Found {len(results)} relevant memories",
                "results": results
            }
        
        # Store memory
        if 'store' in desc_lower or 'remember' in desc_lower or 'save' in desc_lower:
            return {
                "success": True,
                "output": "Ready to store in persistent memory",
                "memory_path": str(MEMORY_STORE)
            }
        
        return {"success": True, "output": "Memory task acknowledged"}
    
    def _execute_inference_task(self, description: str) -> Dict:
        """Execute unified model inference tasks."""
        # Check if models are loaded
        if not SEED_PATH.exists():
            return {
                "success": False,
                "error": "Unified models not found at expected path",
                "needs_escalation": False
            }
        
        return {
            "success": True,
            "output": "Unified model infrastructure ready",
            "available_tiers": ["seed_only", "pocket", "desktop", "workstation", "sovereign"],
            "seed_path": str(SEED_PATH)
        }
    
    def _execute_analysis_task(self, description: str) -> Dict:
        """Execute analysis tasks."""
        return {
            "success": True,
            "output": f"Analysis task acknowledged: {description}",
            "approach": "Pattern matching using junction geometry and local context"
        }
    
    def _formulate_request_for_claude(self, task: Task) -> Dict:
        """
        Formulate a clear request for Claude's assistance.
        
        This is about asking for help effectively, not dependently.
        """
        return {
            "task": task.description,
            "domain": task.domain.value,
            "why_need_claude": self._explain_why_claude(task),
            "context": self.state.working_memory,
            "specific_ask": self._formulate_specific_ask(task)
        }
    
    def _explain_why_claude(self, task: Task) -> str:
        """Explain why this task benefits from Claude's capabilities."""
        domain = task.domain
        
        if domain == TaskDomain.CREATIVE:
            return "Creative tasks benefit from Claude's broader training and novel synthesis capabilities"
        if domain == TaskDomain.COMMUNICATION:
            return "Complex communication requires nuanced language generation Claude excels at"
        if domain == TaskDomain.RESEARCH:
            return "Claude has web search access for current information"
        
        return "This task involves capabilities SPARKY is still developing"
    
    def _formulate_specific_ask(self, task: Task) -> str:
        """Formulate a specific, actionable ask for Claude."""
        return f"Please help with: {task.description}. SPARKY will handle execution once approach is clear."
    
    # ─────────────────────────────────────────────────────────────────────────
    # LEARNING
    # ─────────────────────────────────────────────────────────────────────────
    
    def learn_from_task(self, task_id: str, lesson: str):
        """Record a lesson learned from a task."""
        if task_id in self.tasks:
            self.tasks[task_id].lessons_learned.append(lesson)
            self._save_tasks()
            
            # Also store in learning log
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "task_description": self.tasks[task_id].description,
                "lesson": lesson
            }
            
            if LEARNING_LOG.exists():
                with open(LEARNING_LOG) as f:
                    log = json.load(f)
            else:
                log = []
            
            log.append(log_entry)
            
            with open(LEARNING_LOG, 'w') as f:
                json.dump(log, f, indent=2)
    
    def store_fact(self, key: str, value: Any):
        """Store a fact in long-term memory."""
        self.memory["facts"][key] = {
            "value": value,
            "stored_at": datetime.now().isoformat()
        }
        self._save_memory()
    
    def store_procedure(self, name: str, steps: List[str]):
        """Store a learned procedure."""
        self.memory["procedures"][name] = {
            "steps": steps,
            "learned_at": datetime.now().isoformat()
        }
        self._save_memory()
    
    # ─────────────────────────────────────────────────────────────────────────
    # STATUS REPORTING
    # ─────────────────────────────────────────────────────────────────────────
    
    def status_report(self) -> Dict:
        """Generate a status report of SPARKY's executive state."""
        pending = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
        in_progress = [t for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS]
        needs_claude = [t for t in self.tasks.values() if t.status == TaskStatus.NEEDS_CLAUDE]
        completed = [t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]
        
        return {
            "session_id": self.state.session_id,
            "active_goal": self.state.active_goal,
            "autonomy_ratio": f"{self.state.autonomy_ratio():.0%}",
            "task_counts": {
                "pending": len(pending),
                "in_progress": len(in_progress),
                "needs_claude": len(needs_claude),
                "completed": len(completed)
            },
            "tasks_needing_claude": [
                {"id": t.id, "description": t.description, "domain": t.domain.value}
                for t in needs_claude
            ],
            "strengths": self.state.strengths,
            "growth_areas": self.state.growth_areas,
            "memory_stats": {
                "facts": len(self.memory.get("facts", {})),
                "procedures": len(self.memory.get("procedures", {})),
                "episodes": len(self.memory.get("episodes", []))
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def process_goal(goal: str) -> Dict:
    """Main entry point - give SPARKY a goal and let it plan/execute."""
    executive = SparkyExecutive()
    
    # Decompose into tasks
    tasks = executive.decompose_goal(goal)
    
    results = {
        "goal": goal,
        "tasks_created": len(tasks),
        "task_breakdown": [],
        "immediate_actions": [],
        "needs_claude": []
    }
    
    for task in tasks:
        proceed, reason = executive.should_proceed_independently(task)
        
        task_info = {
            "id": task.id,
            "description": task.description,
            "domain": task.domain.value,
            "confidence": task.confidence.value,
            "can_proceed_independently": proceed,
            "reason": reason
        }
        results["task_breakdown"].append(task_info)
        
        if proceed:
            results["immediate_actions"].append(task_info)
        else:
            results["needs_claude"].append(task_info)
    
    return results


def sparky_status() -> Dict:
    """Get SPARKY's current executive status."""
    executive = SparkyExecutive()
    return executive.status_report()


def sparky_learn(fact_key: str, fact_value: Any):
    """Teach SPARKY a new fact."""
    executive = SparkyExecutive()
    executive.store_fact(fact_key, fact_value)
    return {"stored": fact_key, "value": fact_value}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        SPARKY EXECUTIVE FUNCTION                             ║
║                      Ghost in the Machine Labs                               ║
║                                                                              ║
║   Teaching autonomy through self-assessment and directed action              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Initialize executive
    executive = SparkyExecutive()
    
    # Demo: Process a goal
    print("Processing goal: 'Analyze the unified model performance and suggest optimizations'\n")
    
    result = process_goal("Analyze the unified model performance and suggest optimizations")
    
    print(f"Tasks created: {result['tasks_created']}")
    print(f"\nTask breakdown:")
    for task in result['task_breakdown']:
        status = "✓ SPARKY" if task['can_proceed_independently'] else "→ Claude"
        print(f"  [{status}] {task['description']}")
        print(f"           Domain: {task['domain']} | Confidence: {task['confidence']}")
    
    print(f"\nSPARKY can handle independently: {len(result['immediate_actions'])}")
    print(f"Needs Claude's assistance: {len(result['needs_claude'])}")
    
    print("\n" + "="*78)
    print("STATUS REPORT:")
    print("="*78)
    status = sparky_status()
    print(json.dumps(status, indent=2))
