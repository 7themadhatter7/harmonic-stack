#!/usr/bin/env python3
"""
OPERATOR OVERSIGHT - Dynamic Coordination for Multi-Model Systems
Ghost in the Machine Labs

Universal executive coordination layer for any multi-model workload.
The Operator monitors all model activity, generates intelligent briefings
using a lightweight model, and injects contextual suggestions before
major LLM calls. Suggestions, not commands — models retain autonomy.

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                     OPERATOR OVERSIGHT                          │
│                                                                 │
│  ┌─────────────────┐     ┌──────────────────────────────┐      │
│  │  Activity Log    │     │  Briefing Engine (8B model)  │      │
│  │  - observations  │────▶│  - reviews activity          │      │
│  │  - successes     │     │  - identifies patterns        │      │
│  │  - failures      │     │  - generates suggestions      │      │
│  └─────────────────┘     └──────────┬───────────────────┘      │
│                                      │                          │
│                                      ▼                          │
│                           [Operator notes]                      │
│                           Injected into worker prompts          │
│                           before each major task                │
└─────────────────────────────────────────────────────────────────┘

Coordination Flow:
1. Workers do work → Operator observes and logs (observe())
2. Before next worker call → Operator generates briefing (get_context())
3. Briefing injected as "[Operator notes]" in worker prompt
4. Worker decides what to do with suggestions — full autonomy preserved

This is substrate-agnostic: works for ARC puzzles, code generation,
document analysis, or any scenario where multiple models solve related
problems and shouldn't duplicate effort.

Usage:
    from operator_oversight import OperatorOversight

    operator = OperatorOversight(ollama_url="http://localhost:11434")
    await operator.initialize()

    # Worker starts task
    operator.observe("task_001", "starting", "analyst", detail="profiling input")

    # Worker completes
    operator.observe("task_001", "profiled", "analyst", detail="color remap pattern")
    operator.record_profile("task_001", "This is a color remap with flood fill")

    # Before next worker call, get Operator context
    ctx = await operator.get_context("task_002", category="color_remap",
                                      profile="Similar color pattern", group_size=5)
    # ctx contains both mechanical context and intelligent briefing
    # Inject into worker prompt: f"{worker_prompt}\n{ctx}"

    # Record outcomes
    operator.record_success(category="color_remap", approach="flood fill BFS", count=3)
    operator.record_failure(category="color_remap", approach="pixel-by-pixel comparison")

Notes on Thinking Mode (Qwen3 and similar):
    Qwen3 models have a "thinking mode" that dumps chain-of-thought into a
    separate field. For clean output, set "think": False in the Ollama API
    payload. The /no_think prompt prefix does NOT reliably work.

    WRONG: {"prompt": "/no_think " + prompt}
    RIGHT: {"prompt": prompt, "think": False}
"""

import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime

# Default: use lightweight model for briefings (low overhead)
DEFAULT_OPERATOR_MODEL = "analyst"  # 8B model, ~10s briefings
DEFAULT_OPERATOR_TIMEOUT = 30       # Fast briefings only
DEFAULT_OLLAMA_URL = "http://localhost:11434"


class OperatorOversight:
    """
    Executive coordination for multi-model cooperative systems.

    Monitors all model activity, generates intelligent briefings using
    a lightweight model, and injects contextual suggestions before
    major worker calls. Suggestions, not commands.

    Two-tier context:
        Tier 1 - Mechanical (instant, zero cost):
            Direct lookup of same-category successes/failures.
        Tier 2 - Intelligent Briefing (8B model call):
            Activates after 2+ approaches recorded. Operator reviews
            full activity, generates 2-3 sentence contextual suggestion.
    """

    def __init__(self, ollama_url: str = DEFAULT_OLLAMA_URL,
                 operator_model: str = DEFAULT_OPERATOR_MODEL,
                 operator_timeout: int = DEFAULT_OPERATOR_TIMEOUT):
        self.ollama_url = ollama_url
        self.operator_model = operator_model
        self.operator_timeout = operator_timeout

        # State
        self.activity_log: List[dict] = []
        self.successful_approaches: List[dict] = []
        self.failed_approaches: List[dict] = []
        self.active_profiles: Dict[str, str] = {}
        self.groups_processed = 0
        self.total_suggestions_made = 0

        # HTTP client
        self._client = None

    async def initialize(self):
        """Initialize async HTTP client."""
        try:
            import httpx
            self._client = httpx.AsyncClient(timeout=self.operator_timeout + 10)
        except ImportError:
            import aiohttp
            self._client = None  # Will use aiohttp in _generate()

    async def close(self):
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()

    # ── Observation Methods ────────────────────────────────────────

    def observe(self, task_id: str, stage: str, model: str,
                category: str = "", detail: str = ""):
        """
        Record model activity.

        Stages: "starting", "profiled", "solved", "failed", "generating"
        Category: any string grouping (e.g., "color_remap", "geometric", "code_gen")
        """
        self.activity_log.append({
            "task_id": task_id,
            "stage": stage,
            "model": model,
            "category": category,
            "detail": detail[:300],
            "time": datetime.now().isoformat(),
        })

    def record_profile(self, task_id: str, profile: str):
        """Store completed profile for cross-reference."""
        self.active_profiles[task_id] = profile[:500]

    def record_success(self, category: str, approach: str,
                       count: int = 1, profile: str = ""):
        """Record a successful approach for a category."""
        self.successful_approaches.append({
            "category": category,
            "approach": approach[:400],
            "profile": profile[:400],
            "count": count,
        })

    def record_failure(self, category: str, approach: str):
        """Record a failed approach for a category."""
        self.failed_approaches.append({
            "category": category,
            "approach": approach[:300],
        })

    # ── Briefing Generation ────────────────────────────────────────

    def _build_activity_summary(self, category: str) -> str:
        """Build compact summary of activity for the Operator to review."""
        lines = []

        if self.successful_approaches:
            lines.append(f"SOLVED ({len(self.successful_approaches)} groups so far):")
            for s in self.successful_approaches[-5:]:
                lines.append(f"  [{s['category']}] {s['approach'][:120]} -> solved {s['count']}")

        cat_fails = [f for f in self.failed_approaches if f["category"] == category]
        if cat_fails:
            lines.append(f"FAILED for {category} tasks:")
            for f in cat_fails[-3:]:
                lines.append(f"  {f['approach'][:120]}")

        other_fails = [f for f in self.failed_approaches if f["category"] != category][-2:]
        if other_fails:
            lines.append("Other failed approaches:")
            for f in other_fails:
                lines.append(f"  [{f['category']}] {f['approach'][:80]}")

        return "\n".join(lines)

    async def _generate(self, prompt: str, system: str = "") -> Optional[str]:
        """Call lightweight model for briefing generation."""
        payload = {
            "model": self.operator_model,
            "prompt": prompt,
            "stream": False,
            "think": False,  # CRITICAL: prevents thinking token leak
            "options": {"temperature": 0.3, "num_predict": 512}
        }
        if system:
            payload["system"] = system

        try:
            if self._client:
                # httpx path
                resp = await self._client.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=self.operator_timeout
                )
                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("response", "")
                    # Fallback: extract from thinking field if needed
                    if not result and data.get("thinking"):
                        result = data["thinking"]
                    return result
            else:
                # aiohttp fallback
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.ollama_url}/api/generate",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.operator_timeout)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data.get("response", "")
            return None
        except Exception:
            return None

    async def generate_briefing(self, task_id: str, category: str,
                                profile: str, group_size: int) -> str:
        """
        Generate contextual suggestions for the next worker.

        Uses lightweight model to produce intelligent briefing based on
        all observed activity. Returns empty string if no useful context.
        """
        if not self.successful_approaches and not self.failed_approaches:
            return ""

        activity = self._build_activity_summary(category)
        if not activity.strip():
            return ""

        prompt = f"""You are the Operator coordinating research across multiple task groups.

Current batch progress:
{activity}

A new group is about to be researched:
- Category: {category}
- Group size: {group_size} tasks
- Profile: {profile[:300]}

In 2-3 sentences, suggest what the worker should consider:
- What worked for similar tasks that might apply here?
- What failed that should be avoided?
- Any patterns you notice across groups?

Be specific and concise. These are suggestions, not orders."""

        system = ("You are the Operator - an executive coordinator for AI research. "
                  "Generate brief, specific suggestions to help workers "
                  "avoid duplicating effort. Be direct and actionable.")

        try:
            briefing = await self._generate(prompt, system)
            if briefing and len(briefing.strip()) > 20:
                self.total_suggestions_made += 1
                return f"\n[Operator notes] {briefing.strip()}"
            return ""
        except Exception:
            return ""

    # ── Main Entry Point ───────────────────────────────────────────

    async def get_context(self, task_id: str, category: str,
                          profile: str = "", group_size: int = 1) -> str:
        """
        Main entry point: generate Operator context for worker prompt injection.

        Combines:
            1. Mechanical context (instant, zero cost) - direct lookups
            2. Intelligent briefing (8B model call) - contextual suggestions

        Returns string to inject into worker prompt before generation.
        """
        self.groups_processed += 1

        # Tier 1: Fast mechanical context
        mechanical = []

        relevant_successes = [s for s in self.successful_approaches
                              if s["category"] == category]
        if relevant_successes:
            mechanical.append("Prior successes for similar tasks:")
            for s in relevant_successes[:3]:
                mechanical.append(f"  - {s['approach'][:150]} (solved {s['count']})")

        cat_failures = [f for f in self.failed_approaches
                        if f["category"] == category]
        if cat_failures:
            mechanical.append("Prior failures (avoid):")
            for f in cat_failures[:3]:
                mechanical.append(f"  - {f['approach'][:100]}")

        mech_text = "\n".join(mechanical)

        # Tier 2: Intelligent briefing (only after enough context)
        briefing = ""
        total_approaches = len(self.successful_approaches) + len(self.failed_approaches)
        if total_approaches >= 2:
            briefing = await self.generate_briefing(task_id, category, profile, group_size)

        parts = [p for p in [mech_text, briefing] if p.strip()]
        return "\n\n".join(parts)

    # ── Reporting ──────────────────────────────────────────────────

    def summary(self) -> dict:
        """Return summary statistics for logging/reporting."""
        return {
            "groups_processed": self.groups_processed,
            "successful_approaches": len(self.successful_approaches),
            "failed_approaches": len(self.failed_approaches),
            "suggestions_generated": self.total_suggestions_made,
            "profiles_cached": len(self.active_profiles),
            "total_observations": len(self.activity_log),
        }

    def __repr__(self):
        s = self.summary()
        return (f"OperatorOversight("
                f"groups={s['groups_processed']}, "
                f"successes={s['successful_approaches']}, "
                f"failures={s['failed_approaches']}, "
                f"briefings={s['suggestions_generated']})")


# ── Integration Example ────────────────────────────────────────────

async def example_integration():
    """
    Demonstrate Operator integration with a multi-model workflow.

    This shows the pattern — adapt for your specific workload.
    """
    operator = OperatorOversight()
    await operator.initialize()

    # Simulate group 1: analyst profiles, solver attempts, fails
    operator.observe("group_1", "starting", "analyst", category="spatial")
    operator.record_profile("group_1", "Grid rotation with color preservation")
    operator.observe("group_1", "profiled", "analyst", category="spatial",
                     detail="Grid rotation with color preservation")

    # Solver fails
    operator.record_failure(category="spatial", approach="BFS flood fill")
    operator.observe("group_1", "failed", "solver", category="spatial",
                     detail="BFS flood fill didn't match output")

    # Group 2 starts — Operator has context now
    operator.observe("group_2", "starting", "analyst", category="spatial")
    ctx = await operator.get_context("group_2", category="spatial",
                                      profile="Similar grid rotation", group_size=10)

    print(f"Operator context for group 2:\n{ctx}")
    print(f"\nOperator status: {operator}")

    await operator.close()


if __name__ == "__main__":
    asyncio.run(example_integration())
