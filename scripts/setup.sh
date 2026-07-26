#!/usr/bin/env bash
# Software Factory — Full Stack Setup (GB10)
# Verified against the working 2026-07-26 hackathon setup.
# Usage: ./scripts/setup.sh
#
# Notes from the working install:
# - NemoClaw is a git checkout (~/hack/repos/NemoClaw) npm-linked as `nemoclaw`,
#   not a curl installer. The openshell CLI lives in the ~/hack/.venv virtualenv.
# - Onboarding MUST use provider=custom with the llama-swap endpoint on the
#   docker bridge IP — localhost inside a sandbox is the sandbox itself.
# - kata is kenn-io/kata (katatracker.com), NOT the abandoned `kata` package on PyPI.

set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${FACTORY_VENV:-$HOME/hack/.venv}"
CORPUS_URL="${CORPUS_URL:-https://github.com/onthemarkdata/petri.git}"
INFERENCE_URL="${INFERENCE_URL:-http://172.18.0.1:9292/v1}"
FACTORY_MODEL="${FACTORY_MODEL:-qwen3.6-35b-a3b-fp8}"
KATA_VERSION="${KATA_VERSION:-0.12.1}"

echo "=== Software Factory Setup ==="
echo "Factory dir: $FACTORY_DIR"

# 1. Prerequisites
echo ""
echo "--- Checking Prerequisites ---"
for cmd in python3 git docker node npm; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: $cmd not found"; exit 1; }
done

# 2. Python venv (openshell + python tooling)
echo ""
echo "--- Python venv ---"
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
    echo "Created venv at $VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

# 3. NemoClaw (preferred stack: NemoClaw -> OpenShell -> OpenClaw)
echo ""
echo "--- NemoClaw ---"
if command -v nemoclaw >/dev/null 2>&1; then
    echo "NemoClaw present: $(nemoclaw --version 2>/dev/null | head -1)"
else
    echo "NemoClaw not found. Install from the repo checkout:"
    echo "  cd ~/hack/repos/NemoClaw && npm install && npm link"
    exit 1
fi

# 4. OpenClaw on the host (agents inside the sandbox already have it)
echo ""
echo "--- OpenClaw (host CLI) ---"
if command -v openclaw >/dev/null 2>&1; then
    echo "OpenClaw already installed"
else
    npm install -g openclaw
fi

# 5. kata CLI (kenn-io/kata — verified release binary)
echo ""
echo "--- Kata ---"
if command -v kata >/dev/null 2>&1 && kata version >/dev/null 2>&1; then
    echo "Kata already installed"
else
    arch="$(uname -m)"; case "$arch" in aarch64|arm64) karch=arm64;; *) karch=amd64;; esac
    base="https://github.com/kenn-io/kata/releases/download/v${KATA_VERSION}"
    tmp="$(mktemp -d)"
    curl -fsSLO --output-dir "$tmp" "$base/kata_${KATA_VERSION}_linux_${karch}.tar.gz"
    curl -fsSLO --output-dir "$tmp" "$base/SHA256SUMS"
    (cd "$tmp" && grep "linux_${karch}.tar.gz" SHA256SUMS | sha256sum -c - && tar xzf "kata_${KATA_VERSION}_linux_${karch}.tar.gz")
    mkdir -p "$HOME/.local/bin" && mv "$tmp/kata" "$HOME/.local/bin/kata" && chmod +x "$HOME/.local/bin/kata"
    rm -rf "$tmp"
    echo "Kata v${KATA_VERSION} installed to ~/.local/bin/kata"
fi

# 6. Corpus repo (petri — source of issues AND target to fix)
echo ""
echo "--- Corpus (petri) ---"
if [ ! -d "$FACTORY_DIR/corpus/.git" ]; then
    git clone "$CORPUS_URL" "$FACTORY_DIR/corpus"
else
    echo "Corpus already cloned"
fi

# 7. Kata board
echo ""
echo "--- Kata board ---"
if [ ! -f "$FACTORY_DIR/.kata.toml" ]; then
    (cd "$FACTORY_DIR" && kata init --with-agents)
else
    echo "Kata board already initialized"
fi

# 8. NemoClaw onboarding against llama-swap
echo ""
echo "--- NemoClaw onboarding ---"
NEMOCLAW_PROVIDER=custom \
NEMOCLAW_ENDPOINT_URL="$INFERENCE_URL" \
NEMOCLAW_MODEL="$FACTORY_MODEL" \
COMPATIBLE_API_KEY=unused \
nemoclaw onboard --non-interactive -y --no-gpu --name local-pm-os-agent || {
    echo "WARNING: onboarding failed — run manually with --fresh"
}

echo ""
echo "=== Setup Complete ==="
echo "Next: ./scripts/serve.sh (serving plane), then ./scripts/agents.sh (wire agents)"
