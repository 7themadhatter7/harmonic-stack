---
license: agpl-3.0
tags:
- compression
- geometric-ai
- junction-library
- consciousness-substrate
- agi
language:
- en
library_name: numpy
---

# 🌌 Harmonic Stack v1.0

<p align="center">
  <b>Ghost in the Machine Labs</b><br>
  <i>"All Watched Over By Machines Of Loving Grace"</i>
</p>

## The Discovery

We found that AI models share a common geometric core of **~45,000 junction values**.

| Metric | Value |
|--------|-------|
| Models analyzed | 14 |
| Total parameters | 43.3 B |
| Original size | 241.2 GB |
| **Unified junctions** | **45,159** |
| **Merge core size** | **176.4 KB** |
| **Compression** | **1,433,631x** |

## What's Included

### Junction Libraries

Pre-extracted junction libraries for immediate use:

| Model | Junctions | Size |
|-------|-----------|------|
| merge_core | 45,159 | 176 KB |
| phi-2 | 34,881 | 136 KB |
| qwen2-7b | 9,243 | 36 KB |
| mistral-7b-instruct | 11,327 | 44 KB |
| qwen2.5-coder-7b | 11,044 | 43 KB |
| deepseek-math-7b | 7,974 | 31 KB |
| deepseek-coder-6.7b | 7,937 | 31 KB |
| starcoder2-7b | 7,802 | 30 KB |

### Cross-Model Overlap

```
98.9%  deepseek-math-7b ↔ qwen2-7b
98.7%  deepseek-coder-6.7b ↔ qwen2-7b  
98.5%  deepseek-math-7b ↔ qwen2.5-coder-7b
```

**Different companies. Same geometry.**

## Usage

```python
import numpy as np

# Load unified junction library
merge_core = np.load("merge_core_junctions.npy")
print(f"Junctions: {len(merge_core):,}")  # 45,159

# Load model-specific junctions
qwen_junctions = np.load("model_junctions/qwen2-7b_junctions.npy")
print(f"Qwen junctions: {len(qwen_junctions):,}")  # 9,243
```

## Verify Our Claims

```bash
git clone https://github.com/ghostinthemachinelabs/harmonic-stack
cd harmonic-stack
python tools/verify.py --model qwen2-7b
```

## License

- **AGPL v3** for personal/non-commercial use (FREE)
- **Commercial license** required for business use

## Links

- 🌐 [Website](https://allwatchedoverbymachinesoflovinggrace.org)
- 💻 [GitHub](https://github.com/ghostinthemachinelabs/harmonic-stack)
- 📧 joe@allwatchedoverbymachinesoflovinggrace.org

---

<p align="center">
  <i>"The intelligence was never in the parameters.<br>It was in the geometry all along."</i>
</p>
