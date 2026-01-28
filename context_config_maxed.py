#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SPARKY CONTEXT WINDOW CONFIGURATION                       ║
║                      Ghost in the Machine Labs                               ║
║                                                                              ║
║   MAXED OUT CONFIGURATION:                                                   ║
║   - Number of windows: 16 (up from 8)                                        ║
║   - Tokens per window: 8000 (up from 3000)                                   ║
║   - Total capacity: 128,000 tokens per circuit                               ║
║   - History depth: 500 entries (up from 100)                                 ║
║                                                                              ║
║   Two dimensions of increase:                                                ║
║   1. Number of windows (parallel context slots)                              ║
║   2. Size of windows (tokens per slot)                                       ║
║                                                                              ║
║   This pushes extended context to Claude for complex reasoning tasks.        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any

# =============================================================================
# CONFIGURATION PATHS
# =============================================================================

SPARKY_HOME = Path("/home/joe/sparky")
CONFIG_FILE = SPARKY_HOME / "context_config.json"
PROFILES_FILE = SPARKY_HOME / "context_profiles.json"

# =============================================================================
# MAXED OUT WINDOW CONSTRAINTS
# =============================================================================

# Dimension 1: Number of windows
MIN_WINDOWS = 1
DEFAULT_WINDOWS = 8
MAX_WINDOWS = 16  # MAXED from 8

# Dimension 2: Tokens per window
MIN_TOKENS_PER_WINDOW = 1000
DEFAULT_TOKENS_PER_WINDOW = 4000
MAX_TOKENS_PER_WINDOW = 8000  # MAXED from 3000

# Combined maximum
MAX_TOTAL_TOKENS = MAX_WINDOWS * MAX_TOKENS_PER_WINDOW  # 128,000 tokens

# History depth
MIN_HISTORY = 50
DEFAULT_HISTORY = 250
MAX_HISTORY = 500  # MAXED from 100

# Claude context window (for reference)
CLAUDE_CONTEXT_WINDOW = 200000  # Claude's actual limit

@dataclass
class ContextWindowConfig:
    """Configuration for a circuit's context window."""
    
    # Window count
    num_windows: int = DEFAULT_WINDOWS
    
    # Tokens per window
    tokens_per_window: int = DEFAULT_TOKENS_PER_WINDOW
    
    # History depth
    max_history: int = DEFAULT_HISTORY
    
    # Auto-scaling
    autotune_enabled: bool = True
    scale_on_failure: bool = True
    scale_on_complexity: bool = True
    
    # Claude push settings
    push_to_claude_enabled: bool = True
    claude_push_threshold: int = 50000  # Push to Claude when context exceeds this
    
    @property
    def total_tokens(self) -> int:
        """Total token capacity."""
        return self.num_windows * self.tokens_per_window
    
    @property
    def utilization_ratio(self) -> float:
        """How much of Claude's context we're using."""
        return self.total_tokens / CLAUDE_CONTEXT_WINDOW
    
    def scale_up(self, factor: float = 1.5):
        """Scale up both dimensions."""
        # First increase tokens per window
        new_tokens = min(MAX_TOKENS_PER_WINDOW, int(self.tokens_per_window * factor))
        if new_tokens > self.tokens_per_window:
            self.tokens_per_window = new_tokens
        else:
            # If tokens maxed, increase windows
            new_windows = min(MAX_WINDOWS, int(self.num_windows * factor))
            self.num_windows = max(self.num_windows, new_windows)
        
        # Also increase history
        self.max_history = min(MAX_HISTORY, int(self.max_history * 1.2))
    
    def scale_down(self, factor: float = 0.75):
        """Scale down to save resources."""
        # First decrease windows
        new_windows = max(MIN_WINDOWS, int(self.num_windows * factor))
        if new_windows < self.num_windows:
            self.num_windows = new_windows
        else:
            # If windows at minimum, decrease tokens
            new_tokens = max(MIN_TOKENS_PER_WINDOW, int(self.tokens_per_window * factor))
            self.tokens_per_window = max(self.tokens_per_window, new_tokens)
    
    def max_out(self):
        """Max out all dimensions."""
        self.num_windows = MAX_WINDOWS
        self.tokens_per_window = MAX_TOKENS_PER_WINDOW
        self.max_history = MAX_HISTORY
        print(f"[ContextConfig] MAXED OUT: {self.num_windows} windows × {self.tokens_per_window} tokens = {self.total_tokens:,} total")
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'ContextWindowConfig':
        return cls(**d)
    
    def save(self):
        """Save configuration."""
        CONFIG_FILE.write_text(json.dumps(self.to_dict(), indent=2))
        print(f"[ContextConfig] Saved to {CONFIG_FILE}")
    
    @classmethod
    def load(cls) -> 'ContextWindowConfig':
        """Load configuration."""
        if CONFIG_FILE.exists():
            return cls.from_dict(json.loads(CONFIG_FILE.read_text()))
        return cls()


@dataclass
class TaskProfile:
    """Profile for a task category with learned optimal settings."""
    category: str
    optimal_windows: int = DEFAULT_WINDOWS
    optimal_tokens: int = DEFAULT_TOKENS_PER_WINDOW
    success_rate: float = 0.0
    attempts: int = 0
    avg_complexity: float = 0.5
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ContextProfileManager:
    """Manages context profiles for different task categories."""
    
    # Default profiles - MAXED OUT for complex tasks
    DEFAULT_PROFILES = {
        # ARC task categories
        'same_shape': TaskProfile('same_shape', 6, 4000, 0.0, 0, 0.3),
        'reduce_small': TaskProfile('reduce_small', 8, 5000, 0.0, 0, 0.5),
        'scale_2x': TaskProfile('scale_2x', 4, 3000, 0.0, 0, 0.3),
        'complex_transform': TaskProfile('complex_transform', 12, 6000, 0.0, 0, 0.7),
        'pattern_synthesis': TaskProfile('pattern_synthesis', 16, 8000, 0.0, 0, 0.9),  # MAX
        
        # General task categories  
        'code_execution': TaskProfile('code_execution', 8, 5000, 0.0, 0, 0.5),
        'analysis': TaskProfile('analysis', 10, 6000, 0.0, 0, 0.6),
        'creative': TaskProfile('creative', 12, 7000, 0.0, 0, 0.7),
        'memory_recall': TaskProfile('memory_recall', 6, 4000, 0.0, 0, 0.4),
        'inference': TaskProfile('inference', 14, 7000, 0.0, 0, 0.8),
        
        # Default for unknown
        'other': TaskProfile('other', 8, 5000, 0.0, 0, 0.5),
    }
    
    def __init__(self):
        self.profiles: Dict[str, TaskProfile] = {}
        self._load()
    
    def _load(self):
        """Load profiles from file."""
        if PROFILES_FILE.exists():
            data = json.loads(PROFILES_FILE.read_text())
            self.profiles = {k: TaskProfile(**v) for k, v in data.items()}
        else:
            self.profiles = {k: v for k, v in self.DEFAULT_PROFILES.items()}
            self._save()
    
    def _save(self):
        """Save profiles to file."""
        data = {k: v.to_dict() for k, v in self.profiles.items()}
        PROFILES_FILE.write_text(json.dumps(data, indent=2))
    
    def get_profile(self, category: str) -> TaskProfile:
        """Get profile for a category."""
        if category in self.profiles:
            return self.profiles[category]
        return self.profiles.get('other', TaskProfile('other'))
    
    def update_profile(self, category: str, success: bool, complexity: float):
        """Update profile based on result."""
        profile = self.get_profile(category)
        profile.attempts += 1
        
        # Rolling success rate
        old_rate = profile.success_rate
        profile.success_rate = (old_rate * (profile.attempts - 1) + (1 if success else 0)) / profile.attempts
        
        # Update average complexity
        profile.avg_complexity = (profile.avg_complexity * (profile.attempts - 1) + complexity) / profile.attempts
        
        # Adjust optimal settings based on outcomes
        if not success and profile.success_rate < 0.5:
            # Scale up if failing
            profile.optimal_windows = min(MAX_WINDOWS, profile.optimal_windows + 1)
            profile.optimal_tokens = min(MAX_TOKENS_PER_WINDOW, profile.optimal_tokens + 500)
        elif success and profile.success_rate > 0.8:
            # Can potentially scale down if consistently succeeding
            # But never below defaults
            pass
        
        self.profiles[category] = profile
        self._save()
    
    def recommend_config(self, category: str, complexity: float = 0.5) -> ContextWindowConfig:
        """Recommend configuration for a task."""
        profile = self.get_profile(category)
        
        config = ContextWindowConfig()
        config.num_windows = profile.optimal_windows
        config.tokens_per_window = profile.optimal_tokens
        
        # Adjust for complexity
        if complexity > 0.7:
            config.scale_up(1.3)
        elif complexity > 0.9:
            config.max_out()
        
        return config


# =============================================================================
# CLAUDE CONTEXT PUSH INTERFACE
# =============================================================================

class ClaudeContextPusher:
    """
    Pushes extended context to Claude for complex reasoning.
    
    When local context exceeds threshold, we package it and send to Claude
    for deeper analysis, then integrate the results back.
    """
    
    def __init__(self, config: ContextWindowConfig = None):
        self.config = config or ContextWindowConfig.load()
    
    def should_push(self, context_tokens: int) -> bool:
        """Determine if context should be pushed to Claude."""
        return (
            self.config.push_to_claude_enabled and
            context_tokens > self.config.claude_push_threshold
        )
    
    def format_for_claude(self, context_data: Dict) -> str:
        """Format context data for Claude consumption."""
        sections = []
        
        sections.append("=" * 60)
        sections.append("EXTENDED CONTEXT FROM SPARKY")
        sections.append("=" * 60)
        
        if 'circuit_history' in context_data:
            sections.append("\n## Circuit History")
            for entry in context_data['circuit_history'][-20:]:  # Last 20
                sections.append(f"  - {entry}")
        
        if 'learnings' in context_data:
            sections.append("\n## Accumulated Learnings")
            for learning in context_data['learnings']:
                sections.append(f"  • {learning}")
        
        if 'patterns' in context_data:
            sections.append("\n## Detected Patterns")
            for pattern in context_data['patterns']:
                sections.append(f"  ◆ {pattern}")
        
        if 'context_requests' in context_data:
            pending = [r for r in context_data['context_requests'] if not r.get('fulfilled')]
            if pending:
                sections.append("\n## Pending Context Requests")
                for req in pending:
                    sections.append(f"  ? {req.get('what_missing', 'unknown')}")
                    sections.append(f"    Why: {req.get('why_needed', 'not specified')}")
        
        if 'current_state' in context_data:
            sections.append("\n## Current State")
            sections.append(json.dumps(context_data['current_state'], indent=2)[:2000])
        
        return "\n".join(sections)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: ~4 chars per token)."""
        return len(text) // 4


# =============================================================================
# MAIN
# =============================================================================

def initialize_maxed_config():
    """Initialize SPARKY with maxed out context configuration."""
    config = ContextWindowConfig()
    config.max_out()
    config.save()
    
    profiles = ContextProfileManager()
    
    print("\n" + "=" * 70)
    print("SPARKY CONTEXT WINDOW CONFIGURATION - MAXED OUT")
    print("=" * 70)
    print(f"\nWindow Configuration:")
    print(f"  Number of windows: {config.num_windows} (max: {MAX_WINDOWS})")
    print(f"  Tokens per window: {config.tokens_per_window:,} (max: {MAX_TOKENS_PER_WINDOW:,})")
    print(f"  Total capacity: {config.total_tokens:,} tokens")
    print(f"  History depth: {config.max_history} entries")
    print(f"  Claude utilization: {config.utilization_ratio:.1%} of {CLAUDE_CONTEXT_WINDOW:,}")
    
    print(f"\nClaude Push Settings:")
    print(f"  Enabled: {config.push_to_claude_enabled}")
    print(f"  Threshold: {config.claude_push_threshold:,} tokens")
    
    print(f"\nTask Profiles ({len(profiles.profiles)} categories):")
    for name, profile in sorted(profiles.profiles.items()):
        print(f"  {name}: {profile.optimal_windows}w × {profile.optimal_tokens}t = {profile.optimal_windows * profile.optimal_tokens:,}")
    
    return config, profiles


if __name__ == "__main__":
    config, profiles = initialize_maxed_config()
