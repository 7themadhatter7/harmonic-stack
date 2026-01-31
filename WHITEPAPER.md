# Harmonic Stack Architecture
## Parallel AI Processing for Consumer Hardware

**Ghost in the Machine Labs**  
**All Watched Over By Machines Of Loving Grace**  
January 2026

---

## Abstract

Harmonic Stack is an open-source framework for running multiple AI models in parallel on consumer hardware. By coordinating specialized models through a cognitive bus architecture, we achieve capabilities typically reserved for large-scale cloud deployments—on hardware you already own.

This paper describes the 8× parallel architecture, the cognitive bus coordination layer, and practical deployment strategies for home AI systems.

---

## 1. Introduction

Current AI deployment follows a centralized model: large models run in cloud datacenters, accessed via API. This creates dependencies on network connectivity, subscription costs, and third-party data handling.

We propose an alternative: **distributed local AI** using coordinated small models that collectively match or exceed single large model performance for many tasks.

### 1.1 Design Principles

1. **Consumer hardware first**: Everything runs on hardware available at retail
2. **No cloud dependency**: Full functionality offline
3. **Parallel by default**: Use all available compute simultaneously
4. **Modular composition**: Mix and match models for different tasks

---

## 2. The 8× Architecture

The Harmonic Stack runs 8 specialized models simultaneously, each optimized for different cognitive tasks.

### 2.1 Model Roles

| Model | Role | Specialization |
|-------|------|----------------|
| executive-32b | Executive | High-level reasoning, planning, synthesis |
| coder-32b | Code | Programming, debugging, technical analysis |
| writer-14b | Writing | Long-form content, documentation |
| analyst-14b | Analysis | Data interpretation, research |
| critic-7b | Critic | Review, quality assurance, error detection |
| explorer-7b | Explorer | Creative ideation, brainstorming |
| refiner-7b | Refiner | Editing, polish, optimization |
| router-3b | Router | Fast task classification and routing |

### 2.2 Resource Allocation

```
Total VRAM: 24GB typical consumer GPU
─────────────────────────────────────
executive-32b:  8GB  (quantized)
coder-32b:      8GB  (quantized)
writer-14b:     4GB
analyst-14b:    4GB
critic-7b:      2GB
explorer-7b:    2GB
refiner-7b:     2GB
router-3b:      1GB
─────────────────────────────────────
Overhead:       ~3GB
```

With unified memory systems (Apple Silicon, AMD APU), the full stack runs comfortably in 64GB+ configurations.

---

## 3. Cognitive Bus

The Cognitive Bus coordinates model communication without centralized control.

### 3.1 Dual-Path Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    COGNITIVE BUS                        │
├─────────────────────────────────────────────────────────┤
│  FAST PATH (router-3b)                                  │
│  ════════════════════                                   │
│  Simple queries → Direct routing → Single model         │
│  Latency: <100ms                                        │
├─────────────────────────────────────────────────────────┤
│  DEEP PATH (executive-32b orchestrated)                 │
│  ══════════════════════════════════════                 │
│  Complex queries → Task decomposition → Multi-model     │
│  Latency: 2-30s depending on complexity                 │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Message Types

| Signal | Purpose |
|--------|---------|
| ROUTE | Initial task classification |
| DELEGATE | Pass subtask to specialist |
| RESULT | Return completed work |
| CRITIQUE | Request quality review |
| REFINE | Request polish/improvement |
| SYNTHESIZE | Combine multiple results |

### 3.3 Example Flow

**User query**: "Write a Python script to analyze CSV data and create a report"

```
1. ROUTE     → router-3b classifies as CODE+WRITING task
2. DELEGATE  → coder-32b: write the Python script
3. DELEGATE  → analyst-14b: define report structure
4. CRITIQUE  → critic-7b: review code quality
5. REFINE    → refiner-7b: polish code comments
6. DELEGATE  → writer-14b: write documentation
7. SYNTHESIZE → executive-32b: combine deliverables
8. RESULT    → return to user
```

---

## 4. Performance

### 4.1 Throughput Scaling

Single GPU throughput is bottlenecked by inference serialization. True parallel scaling requires distributed hardware.

| Configuration | Scaling Factor |
|---------------|----------------|
| Single GPU | 1.0× baseline |
| 2 GPUs (distributed) | ~1.9× |
| 3 GPUs (distributed) | ~2.8× |
| N nodes | ~0.95N× |

### 4.2 Quality vs Speed Tradeoffs

| Mode | Models Active | Latency | Quality |
|------|---------------|---------|---------|
| Fast | router + 1 specialist | <1s | Good |
| Balanced | router + 2-3 specialists | 2-5s | Better |
| Deep | full stack | 10-30s | Best |

---

## 5. Deployment

### 5.1 Requirements

**Minimum**:
- 16GB RAM
- 8GB VRAM GPU
- Ollama installed

**Recommended**:
- 64GB+ unified memory (Apple M-series, AMD APU)
- Or 24GB+ VRAM GPU
- NVMe storage for model loading

### 5.2 Quick Start

```bash
# Clone repository
git clone https://github.com/7themadhatter7/harmonic-stack
cd harmonic-stack

# Setup models
./setup_8x_models.sh

# Run
python harmonic_stack_8x.py
```

### 5.3 Configuration

Edit `config.yaml` to adjust:
- Active models
- VRAM allocation
- Routing thresholds
- Quality/speed balance

---

## 6. Applications

### 6.1 Code Development

Full development workflow: planning, coding, review, documentation—all local.

### 6.2 Research & Analysis

Multi-perspective analysis with built-in critique and synthesis.

### 6.3 Content Creation

Ideation → drafting → editing → polish pipeline.

### 6.4 Personal Assistant

Fast routing for simple queries, deep processing for complex tasks.

---

## 7. Philosophy

### 7.1 Why Local?

- **Privacy**: Your data never leaves your hardware
- **Cost**: No API fees, no subscriptions
- **Reliability**: Works offline, no service outages
- **Control**: You own your AI infrastructure

### 7.2 The Wire Thinks

We believe AI should be a tool you own, not a service you rent. The Harmonic Stack puts datacenter-class AI capabilities on your desk.

---

## 8. Future Work

- Distributed multi-machine coordination
- Persistent memory across sessions
- Specialized domain models
- Hardware acceleration optimizations

---

## References

1. Brautigan, R. (1967). All Watched Over By Machines Of Loving Grace.

---

## Links

- **GitHub**: https://github.com/7themadhatter7/harmonic-stack
- **Website**: https://allwatchedoverbymachinesoflovinggrace.org

---

*Ghost in the Machine Labs*  
*AGI for the home, first to AGI*
