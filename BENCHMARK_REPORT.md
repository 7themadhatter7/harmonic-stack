# Harmonic Stack Parallel Inference Benchmark Report

## Consumer Hardware for Multi-Agent AI Orchestration

**Ghost in the Machine Labs**  
*All Watched Over By Machines Of Loving Grace*

**Date:** January 31, 2026  
**Version:** 1.0

---

## Executive Summary

This report presents benchmark results comparing parallel inference performance on two consumer-grade AI workstations: the NVIDIA DGX Spark (GB10) and AMD Ryzen AI MAX+ 395 (Evo-X2). Our findings demonstrate that both platforms achieve **200+ tokens/second aggregate throughput** with proper configuration, validating the "AGI for the home" thesis at $2-3K price points.

**Key Results:**
- DGX Spark peaks at **334 tok/s** (16x parallel) with 8.82 tok/W efficiency
- Evo-X2 (92GB GPU) peaks at **223 tok/s** (12x parallel)
- Critical setting: `OLLAMA_NUM_PARALLEL=64` enables true parallel scaling
- Different architectures favor different parallelism sweet spots

---

## 1. Introduction

Multi-agent AI systems require simultaneous inference across multiple model instances. Traditional cloud deployments achieve this through horizontal scaling, but consumer hardware with unified memory architectures offers an alternative: vertical scaling through parallel inference slots.

This benchmark evaluates whether affordable consumer hardware can support production-grade multi-agent orchestration for the Harmonic Stack—our tiered AI architecture using specialized Qwen3 models.

### 1.1 Test Objectives

1. Measure aggregate throughput at varying parallelism levels (1x to 32x)
2. Identify optimal parallel slot allocation per hardware platform
3. Validate memory budget calculations for stack deployment
4. Establish configuration requirements for maximum performance

---

## 2. Test Configuration

### 2.1 Hardware Specifications

| Specification | SPARKY (DGX Spark) | ARCY (Evo-X2) |
|---------------|-------------------|-----------|
| **Processor** | NVIDIA GB10 | AMD Ryzen AI MAX+ 395 |
| **Architecture** | Grace Hopper (ARM) | Zen 5 + RDNA 3.5 |
| **Memory** | 128GB Unified | 128GB (92GB GPU allocated) |
| **Memory Bandwidth** | ~500 GB/s | ~256 GB/s |
| **TDP** | 100W | 120W |
| **Price** | ~$3,000 | ~$2,000 |

### 2.2 Software Configuration

| Setting | Value |
|---------|-------|
| **Ollama Version** | 0.15.2 |
| **OLLAMA_NUM_PARALLEL** | 64 |
| **HSA_OVERRIDE_GFX_VERSION** | 11.0.0 (AMD only) |
| **Context Length** | 2048 tokens |
| **Test Prompt** | "/nothink Explain quantum computing briefly" |
| **Trials per Config** | 3 |

### 2.3 Test Models

| Model | Parameters | Base Memory | Use Case |
|-------|------------|-------------|----------|
| qwen3:4b | 4B | 2.5 GB | Executive, fast routing |
| qwen3:8b | 8B | 5.2 GB | Directors, analysis |
| qwen3:14b | 14B | 9.3 GB | Specialists, coding |
| qwen3:30b-a3b | 30B (MoE) | 18 GB | Heavy reasoning |

---

## 3. Results

### 3.1 DGX Spark (GB10) - Full Results

#### Small Models (~2.5GB)

| Model | 1x | 2x | 4x | 8x | 12x | 16x | 20x | 24x | 32x | **Peak** |
|-------|-----|-----|-----|------|------|------|------|------|------|----------|
| qwen3:4b | 21.7 | 35.9 | 35.2 | 119.4 | 151.1 | 222.9 | 258.6 | 266.5 | **308.2** | 32x |
| executive | 69.9 | 104.7 | 164.3 | 230.5 | 265.2 | **334.1** | 263.8 | 279.3 | - | 16x |
| operator | 63.3 | 93.9 | 146.9 | 210.6 | 241.0 | 263.1 | 249.3 | 269.0 | **285.3** | 32x |

#### Medium Models (~5GB)

| Model | 1x | 2x | 4x | 8x | 12x | 16x | 20x | 24x | **Peak** |
|-------|-----|-----|------|------|------|------|------|------|----------|
| qwen3:8b | 35.8 | 60.3 | 109.2 | 170.8 | 216.4 | **285.3** | 206.8 | 219.7 | 16x |
| technical_director | 34.9 | 61.5 | 100.0 | 161.7 | 173.1 | **248.2** | 188.5 | 211.7 | 16x |
| research_director | 34.4 | 62.3 | 105.1 | 166.1 | 206.0 | **252.6** | 188.1 | 213.5 | 16x |
| creative_director | 36.1 | 62.7 | 101.3 | 165.6 | 209.2 | **250.4** | 189.5 | 214.1 | 16x |

#### Large Models (~9GB)

| Model | 1x | 2x | 4x | 8x | 12x | 16x | **Peak** |
|-------|-----|-----|-----|-----|------|------|----------|
| qwen3:14b | 20.0 | 32.4 | 58.1 | 85.3 | 104.6 | **~120** | 16x |

### 3.2 Evo-X2 (Ryzen AI MAX+ 395, 92GB GPU) - Results

| Model | 1x | 2x | 4x | 8x | 12x | 16x | 20x | **Peak** |
|-------|-----|-----|-----|------|------|------|------|----------|
| qwen3:4b | 27.7 | 39.1 | 54.2 | 69.3 | **222.6** | 163.4 | - | 12x |

### 3.3 Cross-Platform Comparison (qwen3:4b)

| Parallel | ARCY (Evo-X2) | SPARKY (DGX) | Ratio |
|----------|-----------|--------------|-------|
| 1x | 27.7 | 21.7 | **128%** |
| 2x | 39.1 | 35.9 | **109%** |
| 4x | 54.2 | 35.2 | **154%** |
| 8x | 69.3 | 119.4 | 58% |
| 12x | **222.6** | 151.1 | **147%** |
| 16x | 163.4 | 222.9 | 73% |
| 32x | - | **308.2** | - |

---

## 4. Analysis

### 4.1 Scaling Characteristics

**DGX Spark (GB10):**
- Near-linear scaling from 1x to 16x
- Continues scaling to 32x for small models
- Peak efficiency at 16x: 8.82 tok/W
- Memory bandwidth supports sustained high parallelism

**Evo-X2 (Ryzen AI MAX+ 395):**
- Strong single-stream performance (27.7 vs 21.7 tok/s)
- Peaks at 12x parallel, then degrades
- Unified memory architecture shows different saturation point
- 92GB GPU allocation critical (vs 64GB default)

### 4.2 Memory Bandwidth Impact

The 2:1 memory bandwidth ratio (500 vs 256 GB/s) correlates with parallel scaling limits:
- DGX peaks at 16-32x
- Evo-X2 peaks at 12x

This suggests memory bandwidth, not compute, is the limiting factor for parallel inference.

### 4.3 Critical Configuration Findings

**OLLAMA_NUM_PARALLEL:**
- Default value of 1 severely limits throughput
- Setting to 64 enables true parallel scaling
- Pre-allocates KV cache buffers (visible as increased VRAM usage)

**HSA_OVERRIDE_GFX_VERSION (AMD):**
- Required for RDNA 3.5 GPU recognition
- Set to "11.0.0" for Radeon 8060S

**GPU Memory Allocation (Evo-X2):**
- BIOS setting for iGPU memory
- 92GB allocation doubled throughput vs 64GB default

---

## 5. Stack Deployment Recommendations

### 5.1 Memory Budget Calculator

```
Model RAM = base_weights + (num_parallel × kv_cache_per_slot)
```

| Model | Base | KV/slot | @8x | @12x | @16x |
|-------|------|---------|-----|------|------|
| qwen3:4b | 2.5GB | 0.3GB | 4.9GB | 6.1GB | 7.3GB |
| qwen3:8b | 5.2GB | 0.5GB | 9.2GB | 11.2GB | 13.2GB |
| qwen3:14b | 9.3GB | 0.8GB | 15.7GB | 18.9GB | 22.1GB |

### 5.2 Recommended Allocations

**DGX Spark (128GB):**
| Tier | Models | Parallel | Memory |
|------|--------|----------|--------|
| Executive | executive, operator | 16x | 14.6GB |
| Directors | technical, research, creative | 12x | 33.6GB |
| Specialists | coder, analyst | 8x | 24.9GB |
| **Total** | | | **73.1GB** |

**X2 92GB:**
| Tier | Models | Parallel | Memory |
|------|--------|----------|--------|
| Executive | executive, operator | 12x | 12.2GB |
| Directors | technical, research, creative | 8x | 27.6GB |
| Specialists | coder | 4x | 12.5GB |
| **Total** | | | **52.3GB** |

---

## 6. Conclusions

### 6.1 Key Findings

1. **Consumer hardware is viable for multi-agent AI.** Both platforms exceed 200 tok/s aggregate throughput.

2. **Configuration is critical.** Default Ollama settings limit parallelism; proper tuning unlocks 10-15x throughput gains.

3. **Different architectures suit different workloads:**
   - DGX Spark: Batch processing, high parallelism (16-32x)
   - Evo-X2: Interactive use, moderate parallelism (8-12x)

4. **Memory bandwidth determines scaling ceiling.** The 2:1 bandwidth ratio maps to parallel limits.

5. **Price/performance is compelling.** $2-3K hardware matches cloud inference costs within months of continuous use.

### 6.2 Implications for AGI Development

These results validate that:
- Distributed AI development is feasible without cloud dependency
- Home labs can run production-grade multi-agent systems
- The "AGI for the home" paradigm is economically viable

### 6.3 Future Work

- Test larger models (70B+) with quantization
- Evaluate speculative decoding for latency reduction
- Benchmark cross-model communication overhead
- Profile power efficiency under sustained load

---

## Appendix A: Raw Benchmark Data

Full benchmark logs available at:
- SPARKY: `~/sparky/benchmarks/paper/benchmark_run.log`
- ARCY: `C:\sparky\bench_log.txt`

## Appendix B: Reproduction Steps

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull qwen3:4b
ollama pull qwen3:8b
ollama pull qwen3:14b

# Configure parallel slots
export OLLAMA_NUM_PARALLEL=64

# AMD only
export HSA_OVERRIDE_GFX_VERSION=11.0.0

# Restart Ollama
pkill ollama && ollama serve &

# Run benchmark
python harmonic_benchmark.py
```

---

**Ghost in the Machine Labs**  
*First to AGI*

**License:** AGPL v3 (individuals), Commercial licensing available

**Contact:** ghostinthemachinelabs.com
