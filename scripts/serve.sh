#!/usr/bin/env bash
# Software Factory — Start Serving Plane
# Usage: ./scripts/serve.sh

set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$FACTORY_DIR/config/llama-swap/config.yaml"

echo "=== Starting Serving Plane ==="

# 1. Start vLLM
echo "--- Starting vLLM ---"
if command -v vllm >/dev/null 2>&1; then
    vllm serve --config "$CONFIG" &
    VLLM_PID=$!
    echo "vLLM started (PID: $VLLM_PID)"
else
    echo "WARNING: vLLM not found — trying Ollama fallback"
    ollama serve &
    OLLAMA_PID=$!
    echo "Ollama started (PID: $OLLAMA_PID)"
fi

# 2. Start llama-swap
echo "--- Starting llama-swap ---"
if command -v llama-swap >/dev/null 2>&1; then
    llama-swap --config "$CONFIG" &
    SWAP_PID=$!
    echo "llama-swap started (PID: $SWAP_PID)"
else
    echo "WARNING: llama-swap not found — using direct vLLM endpoint"
fi

# 3. Start agentgateway (optional)
echo "--- Starting agentgateway ---"
if command -v agentgateway >/dev/null 2>&1; then
    agentgateway --config "$FACTORY_DIR/config/agentgateway.yaml" &
    GW_PID=$!
    echo "agentgateway started (PID: $GW_PID)"
else
    echo "WARNING: agentgateway not found — roles will call llama-swap directly"
fi

echo ""
echo "=== Serving Plane Ready ==="
echo "vLLM:    http://localhost:8000/v1"
echo "Ollama:  http://localhost:11434"
echo "Gateway: http://localhost:9000"
echo ""
echo "Press Ctrl+C to stop all services"

wait
