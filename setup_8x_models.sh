#!/bin/bash
# Harmonic Stack 8x Model Setup
# Ghost in the Machine Labs
# 
# Creates all 8 cores plus the interference engine router

set -e

echo "========================================"
echo "HARMONIC STACK 8x MODEL SETUP"
echo "Ghost in the Machine Labs"
echo "========================================"
echo ""

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo "ERROR: Ollama not installed"
    echo "Install from: https://ollama.ai"
    exit 1
fi

MODELS_DIR="$(dirname "$0")/models/8x"

echo "Pulling base models..."
ollama pull qwen3:32b
ollama pull qwen2.5-coder:14b
ollama pull qwen3:14b
ollama pull qwen3:7b
ollama pull qwen3:1.7b

echo ""
echo "Creating Harmonic Stack 8x cores..."

# Create each core
ollama create hs-executive -f "$MODELS_DIR/Modelfile.executive"
ollama create hs-code -f "$MODELS_DIR/Modelfile.code"
ollama create hs-create -f "$MODELS_DIR/Modelfile.create"
ollama create hs-research -f "$MODELS_DIR/Modelfile.research"
ollama create hs-math -f "$MODELS_DIR/Modelfile.math"
ollama create hs-analysis -f "$MODELS_DIR/Modelfile.analysis"
ollama create hs-ethics -f "$MODELS_DIR/Modelfile.ethics"
ollama create hs-reserve -f "$MODELS_DIR/Modelfile.reserve"
ollama create hs-router -f "$MODELS_DIR/Modelfile.router"

echo ""
echo "========================================"
echo "Harmonic Stack 8x models created:"
echo "  hs-executive  (qwen3:32b)      - Orchestration"
echo "  hs-code       (qwen2.5-coder)  - Programming"
echo "  hs-create     (qwen3:14b)      - Creative"
echo "  hs-research   (qwen3:14b)      - Research"
echo "  hs-math       (qwen3:14b)      - Computation"
echo "  hs-analysis   (qwen3:14b)      - Deep Reasoning"
echo "  hs-ethics     (qwen3:14b)      - Safety/Alignment"
echo "  hs-reserve    (qwen3:7b)       - Overflow"
echo "  hs-router     (qwen3:1.7b)     - Interference Engine"
echo "========================================"
echo ""
echo "The wire thinks."

