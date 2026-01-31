# Harmonic Stack Launcher

Auto-configure parallel inference based on hardware detection.

Ghost in the Machine Labs - All Watched Over By Machines Of Loving Grace

## Quick Start

```bash
# Detect hardware and show allocation plan
python harmonic_launcher.py

# Start Ollama with optimal settings
python harmonic_launcher.py --start

# Start and preload models
python harmonic_launcher.py --start --preload

# Save configuration
python harmonic_launcher.py --save
```

## Hardware Detection

The launcher auto-detects:
- **DGX Spark (GB10)** - 128GB unified memory, peaks at 16x parallel
- **AMD Ryzen AI MAX+ 395** - 64-92GB GPU allocation, peaks at 12x parallel
- **Generic NVIDIA GPUs** - Based on detected VRAM
- **Fallback** - Uses system RAM as proxy

### Force a Profile

```bash
python harmonic_launcher.py --profile dgx_spark
python harmonic_launcher.py --profile x2_92gb
python harmonic_launcher.py --profile generic_24gb
```

### Override GPU Memory

```bash
python harmonic_launcher.py --gpu-mem 64
```

## Model Allocation

Models are allocated by tier priority:

| Tier | Role | Parallel | Memory Strategy |
|------|------|----------|-----------------|
| 1 | Executive | 100% of peak | Always max slots |
| 2 | Directors | 75% of peak | High throughput |
| 3 | Specialists | 50% of peak | Balanced |
| 4 | Heavy | 33% of peak | Capability over speed |

### Custom Model Selection

```bash
# Minimal stack
python harmonic_launcher.py --models executive coder

# Full stack
python harmonic_launcher.py --models executive operator technical_director research_director creative_director coder analyst architect
```

## Example Output

```
============================================================
HARMONIC STACK ALLOCATION
Hardware: NVIDIA DGX Spark (GB10)
GPU Memory: 128GB
============================================================

[Tier 1: EXECUTIVE]
  executive                  16x  (7.3GB)
  operator                   16x  (7.3GB)

[Tier 2: DIRECTORS]
  technical_director         12x  (11.2GB)
  research_director          12x  (11.2GB)
  creative_director          12x  (11.2GB)

[Tier 3: SPECIALISTS]
  coder                       8x  (15.7GB)
  analyst                     8x  (9.2GB)

============================================================
Total Allocated: 73.1GB / 108.8GB available
Headroom: 35.7GB
============================================================
```

## Configuration Files

- `stack_config.yaml` - Model definitions, hardware profiles, stack presets
- `~/.harmonic_stack/config.yaml` - Saved runtime configuration

## Environment Variables

Set automatically based on hardware:

| Hardware | Variables |
|----------|-----------|
| All | `OLLAMA_NUM_PARALLEL=<max_allocated>` |
| AMD | `HSA_OVERRIDE_GFX_VERSION=11.0.0` |

## Benchmark Results

From January 31, 2026 testing:

| System | Peak Throughput | Sweet Spot |
|--------|-----------------|------------|
| DGX Spark | 334 tok/s | 16x parallel |
| X2 (92GB) | 223 tok/s | 12x parallel |

## Integration

### Python API

```python
from harmonic_launcher import detect_hardware, allocate_stack, start_ollama

hardware = detect_hardware()
allocation = allocate_stack(['executive', 'coder'], hardware)
start_ollama(hardware, max_parallel=16)
```

### Systemd Service (Linux)

```ini
[Unit]
Description=Harmonic Stack Ollama
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/harmonic/harmonic_launcher.py --start --preload
Restart=on-failure
Environment="OLLAMA_NUM_PARALLEL=16"

[Install]
WantedBy=multi-user.target
```

### Windows Task Scheduler

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\harmonic\harmonic_launcher.py --start"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "HarmonicStack" -Action $action -Trigger $trigger
```

## License

AGPL v3 for individuals, standard corporate licensing available.
