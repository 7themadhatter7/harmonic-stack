# ⚡ Harmonic Stack

<p align="center">
  <b>Ghost in the Machine Labs</b><br>
  <i>All Watched Over By Machines Of Loving Grace</i>
</p>

---

## 🔥 Death of the Inference Engine

**The wire thinks.**

Traditional AI treats inference as a query → engine → response pipeline. We replaced this with **embedded routing components** that direct signals through computed topology.

```
OLD: Query → Inference Engine → Response
NEW: Signal → Cognitive Bus → Destination
```

**Result:** 8× parallel processing with ~0.95N scaling efficiency.

---

## 🧠 NEW: Operator Oversight — Dynamic Coordination

**Models that talk to each other waste less compute.**

When multiple models work on related problems, they duplicate effort — trying approaches that already failed, missing patterns that already succeeded. The Operator fixes this with intelligent executive coordination.

```
Without Operator:
  Core 1: tries BFS → fails (45s)
  Core 2: tries BFS → fails (45s)    ← wasted
  Core 3: tries BFS → fails (45s)    ← wasted

With Operator:
  Core 1: tries BFS → fails (45s)
  Operator: "[BFS failed for this class. Consider flood fill instead.]"
  Core 2: tries flood fill → succeeds (45s)
  Core 3: applies flood fill → succeeds (5s)
```

**Two-tier context:**
- **Mechanical** (instant): Direct lookup of same-category successes/failures
- **Intelligent** (8B model, ~10s): Contextual briefing with cross-pattern analysis

The Operator suggests, never commands. Models retain full autonomy.

See [Operator Oversight Whitepaper](docs/operator_oversight_whitepaper.md) for architecture details.

---

## ⚡ 8× Parallel Architecture

| Core | Model | Role | VRAM |
|------|-------|------|------|
| hs-executive | qwen3:32b | Orchestration | ~20GB |
| hs-code | qwen2.5-coder:14b | Programming | ~10GB |
| hs-create | qwen3:14b | Creative | ~10GB |
| hs-research | qwen3:14b | Research | ~10GB |
| hs-math | qwen3:14b | Computation | ~10GB |
| hs-analysis | qwen3:14b | Deep Reasoning | ~10GB |
| hs-ethics | qwen3:14b | Safety/Alignment | ~10GB |
| hs-reserve | qwen3:7b | Overflow | ~5GB |
| hs-router | qwen3:1.7b | Fast Routing | ~2GB |
| **TOTAL** | | | **~87GB** |

### Full Architecture

```
┌─────────────────────────────────────────────────────┐
│  OPERATOR OVERSIGHT (executive coordination)         │
│    Monitors all cores, generates briefings           │
├─────────────────────────────────────────────────────┤
│  COGNITIVE BUS (signal routing)                      │
│    Routes signals between cores via dual-path        │
├────┬────┬────┬────┬────┬────┬────┬────┬────────────┤
│ C1 │ C2 │ C3 │ C4 │ C5 │ C6 │ C7 │ C8 │  8 cores  │
└────┴────┴────┴────┴────┴────┴────┴────┴────────────┘
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/7themadhatter7/harmonic-stack
cd harmonic-stack
./setup_8x_models.sh
python3 harmonic_stack_8x.py
```

### Add Operator Oversight to Any Workflow

```python
from operator_oversight import OperatorOversight

operator = OperatorOversight()
await operator.initialize()

# Before each worker call, get context:
ctx = await operator.get_context(task_id, category="your_domain")
worker_prompt = f"{your_existing_prompt}\n{ctx}"
```

---

## ⚠️ Qwen3 Thinking Mode Fix

Qwen3 models leak chain-of-thought into output via a "thinking mode" that ignores the `/no_think` prompt prefix. The fix is to use the API-level parameter:

```python
# WRONG — /no_think prefix doesn't work
{"prompt": "/no_think " + prompt}

# RIGHT — API-level parameter works
{"prompt": prompt, "think": False}
```

This is applied throughout the Harmonic Stack and documented in `operator_oversight.py`.

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Death of the Inference Engine](docs/death_of_inference_engine.md) | The paradigm shift |
| [Crystal Chain Architecture](docs/crystal_chain_whitepaper.md) | Layered context patterns |
| [Operator Oversight](docs/operator_oversight_whitepaper.md) | **NEW** Dynamic multi-model coordination |

---

## 📄 License

**Personal/Home/Education**: Free forever.
**Corporations**: Contact for licensing.

AGPL v3 | joe@allwatchedoverbymachinesoflovinggrace.org

---

*Ghost in the Machine Labs — 501(c)(3)*

**The wire thinks. The Operator coordinates.**
