#!/bin/bash
# Build Harmonic Stack Models
# Ghost in the Machine Labs
#
# This script creates all Ollama models for the Harmonic Stack
# from their Modelfiles.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODELS_DIR="$SCRIPT_DIR/models"

echo "============================================"
echo "  HARMONIC STACK MODEL BUILDER"
echo "  Ghost in the Machine Labs"
echo "============================================"
echo

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama is not running"
    echo "Start Ollama with: ollama serve"
    exit 1
fi

# Pull base models first
echo "Pulling base models..."
echo

BASE_MODELS=("qwen3:4b" "qwen3:8b" "qwen3:14b")

for model in "${BASE_MODELS[@]}"; do
    echo "Pulling $model..."
    ollama pull "$model"
    echo
done

# Build stack models
echo "Building Harmonic Stack models..."
echo

STACK_MODELS=(
    "executive"
    "operator"
    "technical_director"
    "research_director"
    "creative_director"
    "coder"
    "analyst"
)

for model in "${STACK_MODELS[@]}"; do
    modelfile="$MODELS_DIR/${model}.Modelfile"
    if [ -f "$modelfile" ]; then
        echo "Building $model..."
        ollama create "$model" -f "$modelfile"
        echo "  ✓ $model created"
    else
        echo "  ✗ $modelfile not found, skipping"
    fi
    echo
done

echo "============================================"
echo "  BUILD COMPLETE"
echo "============================================"
echo
echo "Available models:"
ollama list | grep -E "^(executive|operator|technical_director|research_director|creative_director|coder|analyst)"
echo
echo "Run 'python harmonic_launcher.py --start --preload' to deploy the stack."
