#!/usr/bin/env python3
"""
Harmonic Stack Launcher - Auto-configure parallel inference based on hardware
Ghost in the Machine Labs

Detects hardware, allocates memory budget, launches Ollama with optimal settings.
"""

import subprocess
import platform
import os
import sys
import json
import yaml
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

# ============================================================================
# MODEL SPECIFICATIONS
# ============================================================================

MODELS = {
    # Tier 1: Executive (max parallel)
    'executive': {'base_gb': 2.5, 'kv_gb': 0.3, 'tier': 1, 'source': 'qwen3:4b'},
    'operator': {'base_gb': 2.5, 'kv_gb': 0.3, 'tier': 1, 'source': 'qwen3:4b'},
    
    # Tier 2: Directors (high parallel)
    'technical_director': {'base_gb': 5.2, 'kv_gb': 0.5, 'tier': 2, 'source': 'qwen3:8b'},
    'research_director': {'base_gb': 5.2, 'kv_gb': 0.5, 'tier': 2, 'source': 'qwen3:8b'},
    'creative_director': {'base_gb': 5.2, 'kv_gb': 0.5, 'tier': 2, 'source': 'qwen3:8b'},
    
    # Tier 3: Specialists (medium parallel)
    'analyst': {'base_gb': 5.2, 'kv_gb': 0.5, 'tier': 3, 'source': 'qwen3:8b'},
    'coder': {'base_gb': 9.3, 'kv_gb': 0.8, 'tier': 3, 'source': 'qwen3:14b'},
    
    # Tier 4: Heavy (lower parallel, high capability)
    'architect': {'base_gb': 18.0, 'kv_gb': 1.2, 'tier': 4, 'source': 'qwen3:30b-a3b'},
    
    # Base models (for direct use)
    'qwen3:4b': {'base_gb': 2.5, 'kv_gb': 0.3, 'tier': 1, 'source': 'qwen3:4b'},
    'qwen3:8b': {'base_gb': 5.2, 'kv_gb': 0.5, 'tier': 2, 'source': 'qwen3:8b'},
    'qwen3:14b': {'base_gb': 9.3, 'kv_gb': 0.8, 'tier': 3, 'source': 'qwen3:14b'},
    'qwen3:30b-a3b': {'base_gb': 18.0, 'kv_gb': 1.2, 'tier': 4, 'source': 'qwen3:30b-a3b'},
}

# Parallel steps to try (descending)
PARALLEL_STEPS = [24, 20, 16, 12, 8, 6, 4, 2, 1]

# ============================================================================
# HARDWARE PROFILES
# ============================================================================

HARDWARE_PROFILES = {
    'dgx_spark': {
        'name': 'NVIDIA DGX Spark (GB10)',
        'gpu_mem_gb': 128,
        'peak_parallel': 16,  # Sweet spot from benchmarks
        'max_parallel': 32,
        'reserve_pct': 0.15,
        'env': {},
    },
    'evo_x2_92gb': {
        'name': 'AMD Ryzen AI MAX+ 395 (92GB GPU)',
        'gpu_mem_gb': 92,
        'peak_parallel': 12,  # Sweet spot from benchmarks
        'max_parallel': 16,
        'reserve_pct': 0.15,
        'env': {'HSA_OVERRIDE_GFX_VERSION': '11.0.0'},
    },
    'evo_x2_64gb': {
        'name': 'AMD Ryzen AI MAX+ 395 (64GB GPU)',
        'gpu_mem_gb': 64,
        'peak_parallel': 8,
        'max_parallel': 12,
        'reserve_pct': 0.15,
        'env': {'HSA_OVERRIDE_GFX_VERSION': '11.0.0'},
    },
    'generic_48gb': {
        'name': 'Generic 48GB GPU',
        'gpu_mem_gb': 48,
        'peak_parallel': 8,
        'max_parallel': 12,
        'reserve_pct': 0.20,
        'env': {},
    },
    'generic_24gb': {
        'name': 'Generic 24GB GPU',
        'gpu_mem_gb': 24,
        'peak_parallel': 4,
        'max_parallel': 8,
        'reserve_pct': 0.20,
        'env': {},
    },
    'generic_16gb': {
        'name': 'Generic 16GB GPU',
        'gpu_mem_gb': 16,
        'peak_parallel': 4,
        'max_parallel': 6,
        'reserve_pct': 0.20,
        'env': {},
    },
}

# ============================================================================
# HARDWARE DETECTION
# ============================================================================

def detect_nvidia_gpu() -> Optional[Dict]:
    """Detect NVIDIA GPU and memory"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            line = result.stdout.strip().split('\n')[0]
            name, mem_mb = line.rsplit(',', 1)
            return {
                'vendor': 'nvidia',
                'name': name.strip(),
                'memory_gb': int(mem_mb.strip()) / 1024
            }
    except Exception:
        pass
    return None

def detect_amd_gpu() -> Optional[Dict]:
    """Detect AMD GPU - check Windows first, then ROCm"""
    system = platform.system()
    
    if system == 'Windows':
        # Check for Radeon via PowerShell
        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-WmiObject Win32_VideoController | Where-Object {$_.Name -like "*Radeon*"} | Select-Object Name,AdapterRAM'],
                capture_output=True, text=True, timeout=10
            )
            if 'Radeon' in result.stdout:
                # AdapterRAM is unreliable for unified memory, use profile detection
                if '8060S' in result.stdout or 'MAX+' in result.stdout.upper():
                    return {
                        'vendor': 'amd',
                        'name': 'AMD Radeon 8060S (Ryzen AI MAX+)',
                        'memory_gb': None  # Will be set by profile
                    }
        except Exception:
            pass
    else:
        # Try ROCm
        try:
            result = subprocess.run(
                ['rocm-smi', '--showmeminfo', 'vram'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                # Parse ROCm output
                for line in result.stdout.split('\n'):
                    if 'Total' in line:
                        # Extract memory value
                        pass
        except Exception:
            pass
    return None

def detect_system_memory() -> float:
    """Detect total system memory in GB"""
    system = platform.system()
    
    if system == 'Windows':
        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 '(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB'],
                capture_output=True, text=True, timeout=10
            )
            return float(result.stdout.strip())
        except Exception:
            pass
    else:
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        kb = int(line.split()[1])
                        return kb / 1024 / 1024
        except Exception:
            pass
    return 64.0  # Default fallback

def detect_hardware() -> Dict:
    """Auto-detect hardware and select best profile"""
    
    # Check for DGX Spark specifically
    system = platform.system()
    if system == 'Linux':
        try:
            with open('/etc/hostname', 'r') as f:
                hostname = f.read().strip().lower()
                if 'dgx' in hostname or 'spark' in hostname:
                    return {
                        'profile': 'dgx_spark',
                        'detected': 'DGX Spark (hostname)',
                        **HARDWARE_PROFILES['dgx_spark']
                    }
        except Exception:
            pass
        
        # Check for GB10 chip
        nvidia = detect_nvidia_gpu()
        if nvidia and 'GB10' in nvidia.get('name', ''):
            return {
                'profile': 'dgx_spark',
                'detected': nvidia['name'],
                **HARDWARE_PROFILES['dgx_spark']
            }
    
    # Check for AMD (X2)
    amd = detect_amd_gpu()
    if amd:
        sys_mem = detect_system_memory()
        # Estimate GPU allocation based on system memory
        # X2 typically has 64GB or 92GB GPU from 128GB total
        if sys_mem >= 120:
            profile = 'evo_x2_92gb'  # Assume 92GB GPU config
        else:
            profile = 'evo_x2_64gb'
        return {
            'profile': profile,
            'detected': amd['name'],
            **HARDWARE_PROFILES[profile]
        }
    
    # Check NVIDIA generic
    nvidia = detect_nvidia_gpu()
    if nvidia:
        mem = nvidia['memory_gb']
        if mem >= 100:
            profile = 'dgx_spark'
        elif mem >= 40:
            profile = 'generic_48gb'
        elif mem >= 20:
            profile = 'generic_24gb'
        else:
            profile = 'generic_16gb'
        
        hw = HARDWARE_PROFILES[profile].copy()
        hw['gpu_mem_gb'] = mem  # Use actual detected memory
        return {
            'profile': profile,
            'detected': nvidia['name'],
            **hw
        }
    
    # Fallback: use system memory as proxy
    sys_mem = detect_system_memory()
    if sys_mem >= 120:
        return {'profile': 'evo_x2_92gb', 'detected': 'Unknown (128GB RAM)', **HARDWARE_PROFILES['evo_x2_92gb']}
    elif sys_mem >= 60:
        return {'profile': 'evo_x2_64gb', 'detected': 'Unknown (64GB RAM)', **HARDWARE_PROFILES['evo_x2_64gb']}
    else:
        return {'profile': 'generic_24gb', 'detected': 'Unknown', **HARDWARE_PROFILES['generic_24gb']}

# ============================================================================
# MEMORY ALLOCATION
# ============================================================================

def model_memory(model_name: str, parallel: int) -> float:
    """Calculate memory for model at given parallelism"""
    spec = MODELS.get(model_name, MODELS.get('qwen3:4b'))
    return spec['base_gb'] + (parallel * spec['kv_gb'])

def allocate_stack(
    models: List[str],
    hardware: Dict,
    min_parallel: int = 1
) -> Dict[str, Dict]:
    """
    Allocate parallel slots to models based on tier priority.
    Higher tier models get slots first, then lower tiers fill remaining.
    """
    gpu_mem = hardware['gpu_mem_gb']
    reserve = hardware.get('reserve_pct', 0.15)
    peak_parallel = hardware.get('peak_parallel', 16)
    max_parallel = hardware.get('max_parallel', 24)
    
    available = gpu_mem * (1 - reserve)
    allocation = {}
    
    # Sort models by tier (lower tier = higher priority)
    model_specs = [(m, MODELS.get(m, MODELS['qwen3:4b'])) for m in models]
    model_specs.sort(key=lambda x: x[1]['tier'])
    
    # First pass: allocate at peak parallel for tier 1, scale down for others
    for model_name, spec in model_specs:
        tier = spec['tier']
        
        # Tier-based parallel target
        if tier == 1:
            target_parallel = peak_parallel
        elif tier == 2:
            target_parallel = int(peak_parallel * 0.75)
        elif tier == 3:
            target_parallel = int(peak_parallel * 0.5)
        else:
            target_parallel = int(peak_parallel * 0.33)
        
        target_parallel = max(min_parallel, min(target_parallel, max_parallel))
        
        # Find highest parallel that fits
        allocated = False
        for p in PARALLEL_STEPS:
            if p > target_parallel:
                continue
            if p < min_parallel:
                break
                
            mem_needed = model_memory(model_name, p)
            if mem_needed <= available:
                allocation[model_name] = {
                    'parallel': p,
                    'memory_gb': round(mem_needed, 1),
                    'tier': tier,
                    'source': spec.get('source', model_name)
                }
                available -= mem_needed
                allocated = True
                break
        
        if not allocated:
            allocation[model_name] = {
                'parallel': 0,
                'memory_gb': 0,
                'tier': tier,
                'source': spec.get('source', model_name),
                'status': 'skipped'
            }
    
    return allocation

# ============================================================================
# OLLAMA INTEGRATION
# ============================================================================

def check_ollama_running() -> bool:
    """Check if Ollama is already running"""
    try:
        import urllib.request
        req = urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2)
        return req.status == 200
    except Exception:
        return False

def stop_ollama():
    """Stop running Ollama instances"""
    system = platform.system()
    
    if system == 'Windows':
        subprocess.run(['taskkill', '/IM', 'ollama.exe', '/F'], 
                       capture_output=True, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(['pkill', '-f', 'ollama serve'], 
                       capture_output=True, stderr=subprocess.DEVNULL)
    time.sleep(2)

def start_ollama(hardware: Dict, max_parallel: int):
    """Start Ollama with optimal configuration"""
    env = os.environ.copy()
    
    # Set parallel slots
    env['OLLAMA_NUM_PARALLEL'] = str(max_parallel)
    
    # Add hardware-specific env vars
    for key, val in hardware.get('env', {}).items():
        env[key] = val
    
    system = platform.system()
    
    print(f"Starting Ollama with NUM_PARALLEL={max_parallel}")
    
    if system == 'Windows':
        # Windows: use start /b for background
        subprocess.Popen(
            ['ollama', 'serve'],
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        # Linux: use nohup
        subprocess.Popen(
            ['nohup', 'ollama', 'serve'],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    
    # Wait for startup
    for _ in range(30):
        time.sleep(1)
        if check_ollama_running():
            print("Ollama started successfully")
            return True
    
    print("WARNING: Ollama may not have started correctly")
    return False

def preload_models(allocation: Dict):
    """Preload allocated models into Ollama"""
    for model_name, cfg in allocation.items():
        if cfg.get('parallel', 0) > 0:
            source = cfg.get('source', model_name)
            print(f"Preloading {model_name} ({source})...")
            try:
                # Quick inference to load model
                subprocess.run(
                    ['ollama', 'run', source, '/nothink hi'],
                    capture_output=True, timeout=60
                )
            except Exception as e:
                print(f"  Warning: {e}")

# ============================================================================
# OUTPUT / REPORTING
# ============================================================================

def print_allocation(hardware: Dict, allocation: Dict):
    """Print allocation summary"""
    total_mem = sum(cfg.get('memory_gb', 0) for cfg in allocation.values())
    available = hardware['gpu_mem_gb'] * (1 - hardware.get('reserve_pct', 0.15))
    
    print()
    print("=" * 60)
    print(f"HARMONIC STACK ALLOCATION")
    print(f"Hardware: {hardware.get('name', hardware.get('detected', 'Unknown'))}")
    print(f"GPU Memory: {hardware['gpu_mem_gb']}GB")
    print("=" * 60)
    
    # Group by tier
    tiers = {}
    for model, cfg in allocation.items():
        tier = cfg.get('tier', 9)
        if tier not in tiers:
            tiers[tier] = []
        tiers[tier].append((model, cfg))
    
    tier_names = {1: 'EXECUTIVE', 2: 'DIRECTORS', 3: 'SPECIALISTS', 4: 'HEAVY'}
    
    for tier_num in sorted(tiers.keys()):
        print(f"\n[Tier {tier_num}: {tier_names.get(tier_num, 'OTHER')}]")
        for model, cfg in tiers[tier_num]:
            if cfg.get('parallel', 0) > 0:
                print(f"  {model:25} {cfg['parallel']:3}x  ({cfg['memory_gb']:.1f}GB)")
            else:
                print(f"  {model:25}  SKIPPED (insufficient memory)")
    
    print()
    print("=" * 60)
    print(f"Total Allocated: {total_mem:.1f}GB / {available:.1f}GB available")
    print(f"Headroom: {available - total_mem:.1f}GB")
    print("=" * 60)

def save_config(hardware: Dict, allocation: Dict, path: str = None):
    """Save configuration to file"""
    if path is None:
        path = Path.home() / '.harmonic_stack' / 'config.yaml'
    
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    config = {
        'hardware': {
            'profile': hardware.get('profile'),
            'detected': hardware.get('detected'),
            'gpu_mem_gb': hardware['gpu_mem_gb'],
            'peak_parallel': hardware.get('peak_parallel'),
            'max_parallel': hardware.get('max_parallel'),
        },
        'allocation': allocation,
        'env': hardware.get('env', {}),
    }
    
    with open(path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"\nConfiguration saved to: {path}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Harmonic Stack Launcher - Auto-configure parallel inference'
    )
    parser.add_argument('--detect', action='store_true', 
                        help='Detect hardware and exit')
    parser.add_argument('--profile', choices=list(HARDWARE_PROFILES.keys()),
                        help='Force specific hardware profile')
    parser.add_argument('--models', nargs='+', 
                        help='Models to allocate (default: standard stack)')
    parser.add_argument('--start', action='store_true',
                        help='Start Ollama with optimal config')
    parser.add_argument('--preload', action='store_true',
                        help='Preload models after starting')
    parser.add_argument('--save', type=str, nargs='?', const='default',
                        help='Save configuration to file')
    parser.add_argument('--gpu-mem', type=int,
                        help='Override GPU memory (GB)')
    
    args = parser.parse_args()
    
    # Detect or use forced profile
    if args.profile:
        hardware = {'profile': args.profile, **HARDWARE_PROFILES[args.profile]}
        hardware['detected'] = f'Forced: {args.profile}'
    else:
        hardware = detect_hardware()
    
    if args.gpu_mem:
        hardware['gpu_mem_gb'] = args.gpu_mem
    
    if args.detect:
        print(f"Detected: {hardware.get('detected', 'Unknown')}")
        print(f"Profile: {hardware.get('profile')}")
        print(f"GPU Memory: {hardware['gpu_mem_gb']}GB")
        print(f"Peak Parallel: {hardware.get('peak_parallel')}")
        print(f"Environment: {hardware.get('env', {})}")
        return
    
    # Default model stack
    if args.models:
        models = args.models
    else:
        models = [
            'executive', 'operator',
            'technical_director', 'research_director', 'creative_director',
            'coder', 'analyst',
        ]
    
    # Allocate
    allocation = allocate_stack(models, hardware)
    
    # Find max parallel across allocation for Ollama setting
    max_parallel = max(cfg.get('parallel', 1) for cfg in allocation.values())
    
    # Print summary
    print_allocation(hardware, allocation)
    
    # Save config
    if args.save:
        save_path = None if args.save == 'default' else args.save
        save_config(hardware, allocation, save_path)
    
    # Start Ollama
    if args.start:
        if check_ollama_running():
            print("\nOllama already running, stopping...")
            stop_ollama()
        
        start_ollama(hardware, max_parallel)
        
        if args.preload:
            preload_models(allocation)

if __name__ == '__main__':
    main()
