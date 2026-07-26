#!/usr/bin/env bash
# Software Factory — Teardown
# Usage: ./scripts/teardown.sh

set -euo pipefail

echo "=== Software Factory Teardown ==="

# 1. Tailscale logout
echo "--- Tailscale Logout ---"
if command -v tailscale >/dev/null 2>&1; then
    tailscale logout 2>/dev/null || echo "Already logged out"
else
    echo "Tailscale not found — skipping"
fi

# 2. Remove tokens/keys
echo "--- Removing Credentials ---"
rm -f ~/.config/nemoclaw/credentials.yaml 2>/dev/null || true
rm -f ~/.config/openshell/providers/*.yaml 2>/dev/null || true
rm -f ~/.ollama/auth.json 2>/dev/null || true

# 3. Stop running services
echo "--- Stopping Services ---"
pkill -f "vllm" 2>/dev/null || true
pkill -f "llama-swap" 2>/dev/null || true
pkill -f "agentgateway" 2>/dev/null || true
pkill -f "ollama" 2>/dev/null || true
pkill -f "openclaw" 2>/dev/null || true

echo ""
echo "=== Teardown Complete ==="
echo "Remember to:"
echo "  1. Remove this node from your Tailscale admin console"
echo "  2. Delete any API tokens created for this event"
echo "  3. Wipe the stage folder if on shared hardware"
