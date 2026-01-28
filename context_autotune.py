#!/usr/bin/env python3
"""
Context Window Auto-Tuner for Persistent Agent
===============================================
Self-scales context window size based on task complexity and success rate.

Principles:
- Simple tasks (single transformation) → minimal context
- Complex tasks (multi-step, synthesis) → expanded context
- Failed attempts with apparent context starvation → scale up
- Consistent success with low utilization → scale down
- Track optimal ranges per task category
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from datetime import datetime
import statistics

CONFIG_FILE = Path("C:/PersistentAgent/agent_context_config.properties")
TUNING_LOG = Path("C:/PersistentAgent/context_tuning_log.json")
CATEGORY_PROFILES = Path("C:/PersistentAgent/context_category_profiles.json")

# Window constraints
MIN_WINDOWS = 1
MAX_WINDOWS = 8
TOKENS_PER_WINDOW = 3000  # ~3K tokens per 30-second window

@dataclass
class TaskComplexity:
    """Measured complexity of an ARC task."""
    task_id: str
    category: str  # same_shape, reduce_small, scale_2x, other
    num_examples: int
    max_grid_size: int
    shape_variance: float  # 0 = all same shape, higher = more variance
    color_count: int
    estimated_tokens: int
    
    def complexity_score(self) -> float:
        """0-1 score, higher = more complex."""
        # Weighted factors
        example_factor = min(self.num_examples / 5, 1.0) * 0.2
        grid_factor = min(self.max_grid_size / 400, 1.0) * 0.3  # 20x20 = 400
        variance_factor = min(self.shape_variance, 1.0) * 0.2
        color_factor = min(self.color_count / 10, 1.0) * 0.1
        token_factor = min(self.estimated_tokens / 8000, 1.0) * 0.2
        
        return example_factor + grid_factor + variance_factor + color_factor + token_factor


@dataclass
class AttemptResult:
    """Result of an operation synthesis attempt."""
    task_id: str
    category: str
    complexity_score: float
    context_windows: int
    success: bool  # Did operation pass multi-example consensus?
    partial_matches: int  # How many examples matched (0 to num_examples)
    total_examples: int
    response_coherent: bool  # Was response well-formed code?
    timestamp: str


class ContextAutoTuner:
    """Auto-scales context windows based on task complexity and outcomes."""
    
    def __init__(self):
        self.attempt_history: List[AttemptResult] = []
        self.category_profiles: Dict[str, Dict] = {}
        self.current_windows = self._read_current_windows()
        self._load_history()
        self._load_profiles()
    
    def _read_current_windows(self) -> int:
        """Read current window count from config."""
        if CONFIG_FILE.exists():
            content = CONFIG_FILE.read_text()
            for line in content.splitlines():
                if line.startswith('context.windows='):
                    return int(line.split('=')[1])
        return 2  # Default
    
    def _write_windows(self, count: int):
        """Update window count in config."""
        count = max(MIN_WINDOWS, min(MAX_WINDOWS, count))
        
        if CONFIG_FILE.exists():
            lines = CONFIG_FILE.read_text().splitlines()
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('context.windows='):
                    lines[i] = f'context.windows={count}'
                    updated = True
                    break
            if not updated:
                lines.append(f'context.windows={count}')
            CONFIG_FILE.write_text('\n'.join(lines))
        else:
            CONFIG_FILE.write_text(f'context.enabled=true\ncontext.windows={count}\nautotune.enabled=true\n')
        
        self.current_windows = count
        print(f"[AutoTune] Context windows set to {count} ({count * TOKENS_PER_WINDOW:,} tokens)")
    
    def _load_history(self):
        """Load attempt history from log."""
        if TUNING_LOG.exists():
            try:
                data = json.loads(TUNING_LOG.read_text())
                self.attempt_history = [AttemptResult(**a) for a in data.get('attempts', [])]
            except:
                self.attempt_history = []
    
    def _save_history(self):
        """Save attempt history to log."""
        data = {
            'last_updated': datetime.now().isoformat(),
            'attempts': [asdict(a) for a in self.attempt_history[-500:]]  # Keep last 500
        }
        TUNING_LOG.write_text(json.dumps(data, indent=2))
    
    def _load_profiles(self):
        """Load learned category profiles."""
        if CATEGORY_PROFILES.exists():
            try:
                self.category_profiles = json.loads(CATEGORY_PROFILES.read_text())
            except:
                self.category_profiles = {}
        
        # Initialize defaults for known categories
        defaults = {
            'same_shape': {'optimal_windows': 3, 'success_rate': 0.0, 'attempts': 0},
            'reduce_small': {'optimal_windows': 4, 'success_rate': 0.0, 'attempts': 0},
            'scale_2x': {'optimal_windows': 2, 'success_rate': 0.0, 'attempts': 0},
            'other': {'optimal_windows': 4, 'success_rate': 0.0, 'attempts': 0},
        }
        for cat, profile in defaults.items():
            if cat not in self.category_profiles:
                self.category_profiles[cat] = profile
    
    def _save_profiles(self):
        """Save category profiles."""
        CATEGORY_PROFILES.write_text(json.dumps(self.category_profiles, indent=2))
    
    def recommend_windows(self, complexity: TaskComplexity) -> int:
        """Recommend context windows for a task."""
        # Start with category profile
        category = complexity.category
        if category in self.category_profiles:
            base = self.category_profiles[category]['optimal_windows']
        else:
            base = 3
        
        # Adjust for task-specific complexity
        score = complexity.complexity_score()
        
        if score < 0.3:
            adjustment = -1  # Simple task
        elif score < 0.6:
            adjustment = 0   # Medium task
        elif score < 0.8:
            adjustment = 1   # Complex task
        else:
            adjustment = 2   # Very complex
        
        recommended = max(MIN_WINDOWS, min(MAX_WINDOWS, base + adjustment))
        
        print(f"[AutoTune] Task {complexity.task_id}")
        print(f"  Category: {category}, Complexity: {score:.2f}")
        print(f"  Recommended windows: {recommended} ({recommended * TOKENS_PER_WINDOW:,} tokens)")
        
        return recommended
    
    def scale_for_task(self, complexity: TaskComplexity) -> int:
        """Scale context windows for upcoming task. Returns new window count."""
        recommended = self.recommend_windows(complexity)
        
        if recommended != self.current_windows:
            self._write_windows(recommended)
        
        return self.current_windows
    
    def record_attempt(self, result: AttemptResult):
        """Record attempt result and update profiles."""
        self.attempt_history.append(result)
        self._save_history()
        
        # Update category profile
        cat = result.category
        if cat in self.category_profiles:
            profile = self.category_profiles[cat]
            profile['attempts'] += 1
            
            # Rolling success rate (last 20 attempts in category)
            cat_attempts = [a for a in self.attempt_history[-100:] if a.category == cat]
            if cat_attempts:
                profile['success_rate'] = sum(1 for a in cat_attempts if a.success) / len(cat_attempts)
            
            # Adjust optimal windows based on outcomes
            if result.success:
                # Success - could potentially use fewer windows
                recent_successes = [a for a in cat_attempts[-10:] if a.success]
                if len(recent_successes) >= 3:
                    avg_windows = statistics.mean(a.context_windows for a in recent_successes)
                    if avg_windows < profile['optimal_windows']:
                        profile['optimal_windows'] = max(MIN_WINDOWS, int(avg_windows))
            else:
                # Failure - might need more windows
                if result.partial_matches > 0 and result.response_coherent:
                    # Partial success suggests more context might help
                    profile['optimal_windows'] = min(MAX_WINDOWS, profile['optimal_windows'] + 1)
            
            self._save_profiles()
            print(f"[AutoTune] Updated {cat} profile: optimal={profile['optimal_windows']}, success_rate={profile['success_rate']:.1%}")
    
    def get_status(self) -> dict:
        """Get current tuner status."""
        return {
            'current_windows': self.current_windows,
            'current_tokens': self.current_windows * TOKENS_PER_WINDOW,
            'total_attempts': len(self.attempt_history),
            'category_profiles': self.category_profiles,
            'recent_success_rate': self._recent_success_rate()
        }
    
    def _recent_success_rate(self) -> float:
        """Success rate of last 20 attempts."""
        recent = self.attempt_history[-20:]
        if not recent:
            return 0.0
        return sum(1 for a in recent if a.success) / len(recent)


def analyze_task_complexity(task_data: dict, task_id: str, category: str) -> TaskComplexity:
    """Analyze an ARC task and return complexity metrics."""
    import numpy as np
    
    examples = task_data.get('train', [])
    num_examples = len(examples)
    
    grids = []
    shapes = []
    colors = set()
    
    for ex in examples:
        inp = np.array(ex['input'])
        out = np.array(ex['output'])
        grids.extend([inp, out])
        shapes.extend([inp.shape, out.shape])
        colors.update(inp.flatten().tolist())
        colors.update(out.flatten().tolist())
    
    max_grid_size = max(g.size for g in grids) if grids else 0
    
    # Shape variance (0 if all same, higher if different)
    if shapes:
        heights = [s[0] for s in shapes]
        widths = [s[1] for s in shapes]
        shape_variance = (statistics.stdev(heights) if len(heights) > 1 else 0) + \
                        (statistics.stdev(widths) if len(widths) > 1 else 0)
        shape_variance = min(shape_variance / 10, 1.0)  # Normalize
    else:
        shape_variance = 0
    
    # Estimate tokens needed to represent task
    estimated_tokens = sum(g.size * 2 for g in grids) + num_examples * 50  # Grid data + formatting
    
    return TaskComplexity(
        task_id=task_id,
        category=category,
        num_examples=num_examples,
        max_grid_size=max_grid_size,
        shape_variance=shape_variance,
        color_count=len(colors),
        estimated_tokens=estimated_tokens
    )


# CLI interface
if __name__ == "__main__":
    import sys
    
    tuner = ContextAutoTuner()
    
    if len(sys.argv) < 2:
        # Show status
        status = tuner.get_status()
        print("\n=== Context Auto-Tuner Status ===")
        print(f"Current windows: {status['current_windows']} ({status['current_tokens']:,} tokens)")
        print(f"Total attempts logged: {status['total_attempts']}")
        print(f"Recent success rate: {status['recent_success_rate']:.1%}")
        print("\nCategory Profiles:")
        for cat, profile in status['category_profiles'].items():
            print(f"  {cat}: optimal={profile['optimal_windows']} windows, success={profile['success_rate']:.1%}, attempts={profile['attempts']}")
        print()
    
    elif sys.argv[1] == "set":
        # Manual override
        if len(sys.argv) > 2:
            tuner._write_windows(int(sys.argv[2]))
    
    elif sys.argv[1] == "reset":
        # Reset profiles
        CATEGORY_PROFILES.unlink(missing_ok=True)
        TUNING_LOG.unlink(missing_ok=True)
        print("Profiles and history reset")
    
    elif sys.argv[1] == "test":
        # Test with sample complexity
        sample = TaskComplexity(
            task_id="test_task",
            category="same_shape",
            num_examples=3,
            max_grid_size=100,
            shape_variance=0.2,
            color_count=5,
            estimated_tokens=2000
        )
        tuner.scale_for_task(sample)
