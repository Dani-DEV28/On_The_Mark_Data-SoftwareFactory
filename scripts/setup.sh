#!/usr/bin/env bash
# Software Factory — Full Stack Setup
# Usage: ./scripts/setup.sh

set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== Software Factory Setup ==="
echo "Factory dir: $FACTORY_DIR"

# 1. Check prerequisites
echo ""
echo "--- Checking Prerequisites ---"
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git not found"; exit 1; }

# 2. Try NemoClaw first (preferred)
echo ""
echo "--- Attempting NemoClaw Install ---"
if command -v nemoclaw >/dev/null 2>&1; then
    echo "NemoClaw already installed, running onboard..."
    nemoclaw onboard --non-interactive --provider ollama || true
elif curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash 2>/dev/null; then
    echo "NemoClaw installed successfully"
    nemoclaw onboard --non-interactive --provider ollama || true
else
    echo "NemoClaw install failed, falling back to OpenShell..."

    # 3. Try OpenShell direct (fallback)
    echo ""
    echo "--- Attempting OpenShell Install ---"
    if command -v openshell >/dev/null 2>&1; then
        echo "OpenShell already installed"
    elif curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh 2>/dev/null; then
        echo "OpenShell installed successfully"
    else
        echo "OpenShell install failed, falling back to OpenClaw only..."
    fi

    # 4. Install OpenClaw (always needed)
    echo ""
    echo "--- Installing OpenClaw ---"
    if command -v openclaw >/dev/null 2>&1; then
        echo "OpenClaw already installed"
    else
        npm install -g openclaw 2>/dev/null || pip install openclaw 2>/dev/null || {
            echo "WARNING: OpenClaw install failed — manual setup required"
        }
    fi
fi

# 5. Install kata CLI
echo ""
echo "--- Installing Kata ---"
if command -v kata >/dev/null 2>&1; then
    echo "Kata already installed"
else
    pip install kata 2>/dev/null || {
        echo "WARNING: Kata install failed — manual setup required"
    }
fi

# 6. Clone corpus repo
echo ""
echo "--- Cloning Corpus Repo ---"
if [ ! -d "$FACTORY_DIR/corpus/.git" ]; then
    git clone https://github.com/pallets/click.git "$FACTORY_DIR/corpus" 2>/dev/null || {
        echo "WARNING: Corpus clone failed — check network"
    }
else
    echo "Corpus already cloned"
fi

echo ""
echo "=== Setup Complete ==="
echo "Next: run ./scripts/serve.sh to start the serving plane"
