#!/bin/bash
# Harmonic Stack Launcher - Linux
# Ghost in the Machine Labs

set -e

cd "$(dirname "$0")"

echo "============================================"
echo "  HARMONIC STACK LAUNCHER"
echo "  Ghost in the Machine Labs"
echo "============================================"
echo

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

if ! command -v ollama &> /dev/null; then
    echo "ERROR: ollama not found"
    exit 1
fi

# Parse arguments
START_FLAG=""
PRELOAD_FLAG=""

for arg in "$@"; do
    case $arg in
        --start|-s)
            START_FLAG="--start"
            ;;
        --preload|-p)
            PRELOAD_FLAG="--preload"
            ;;
    esac
done

# Run launcher
python3 harmonic_launcher.py $START_FLAG $PRELOAD_FLAG --save

echo
echo "Done."
