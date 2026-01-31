#!/bin/bash
# Harmonic Stack Installer
# Ghost in the Machine Labs
#
# One-line install:
# curl -fsSL https://raw.githubusercontent.com/joeazadian/harmonic-stack/main/install.sh | bash

set -e

REPO_URL="https://github.com/joeazadian/harmonic-stack"
INSTALL_DIR="$HOME/harmonic-stack"

echo "============================================"
echo "  HARMONIC STACK INSTALLER"
echo "  Ghost in the Machine Labs"
echo "============================================"
echo
echo "This will install:"
echo "  - Harmonic Stack launcher and configuration"
echo "  - All required Ollama models"
echo "  - Auto-configured parallel inference"
echo
echo "Install location: $INSTALL_DIR"
echo

# Check for required tools
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: $1 is required but not installed."
        echo "Install it first, then re-run this script."
        exit 1
    fi
}

check_dependency git
check_dependency python3
check_dependency curl

# Check/install Ollama
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo
fi

# Clone or update repo
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning Harmonic Stack..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo

# Make scripts executable
chmod +x build_models.sh launch.sh

# Detect hardware and show plan
echo "Detecting hardware..."
python3 harmonic_launcher.py --detect
echo

# Ask to proceed
read -p "Proceed with installation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

# Build models
echo
echo "Building Ollama models (this may take a while)..."
./build_models.sh

# Save config
python3 harmonic_launcher.py --save

echo
echo "============================================"
echo "  INSTALLATION COMPLETE"
echo "============================================"
echo
echo "To start the Harmonic Stack:"
echo "  cd $INSTALL_DIR"
echo "  ./launch.sh --start --preload"
echo
echo "Or add to your shell profile:"
echo "  alias harmonic='$INSTALL_DIR/launch.sh'"
echo
echo "Documentation: $INSTALL_DIR/README.md"
echo "Benchmark Report: $INSTALL_DIR/BENCHMARK_REPORT.md"
echo
