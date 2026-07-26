#!/usr/bin/env bash
# Software Factory — Start Serving Plane
# llama-swap is the single OpenAI-compatible endpoint (:9292).
# It launches/evicts vLLM docker containers on demand per model —
# vLLM is NOT started directly, and agentgateway is not used
# (llama-swap routes by model name; OpenShell gateway handles sandbox policy).
# Usage: ./scripts/serve.sh

set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$FACTORY_DIR/config/llama-swap/config.yaml"
LISTEN="${LLAMA_SWAP_LISTEN:-:9292}"
SWAP_BIN="$(command -v llama-swap || echo "$HOME/llama-swap/llama-swap")"

echo "=== Starting Serving Plane ==="

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is required (vLLM models run in containers)" >&2
    exit 1
fi

if [ ! -x "$SWAP_BIN" ]; then
    echo "ERROR: llama-swap not found (looked in PATH and ~/llama-swap/)" >&2
    exit 1
fi

if curl -sf "http://localhost${LISTEN#:*}/v1/models" >/dev/null 2>&1 \
   || curl -sf "http://localhost:${LISTEN##*:}/v1/models" >/dev/null 2>&1; then
    echo "llama-swap already running on $LISTEN — nothing to do"
else
    nohup "$SWAP_BIN" --config "$CONFIG" --listen "$LISTEN" \
        > "$FACTORY_DIR/llama-swap.log" 2>&1 &
    SWAP_PID=$!
    sleep 2
    if kill -0 "$SWAP_PID" 2>/dev/null; then
        echo "llama-swap started (PID: $SWAP_PID, log: llama-swap.log)"
    else
        echo "ERROR: llama-swap failed to start — see llama-swap.log" >&2
        exit 1
    fi
fi

echo ""
echo "=== Serving Plane Ready ==="
echo "Endpoint (host):        http://localhost:${LISTEN##*:}/v1"
echo "Endpoint (sandboxes):   http://172.18.0.1:${LISTEN##*:}/v1"
echo "Models:"
curl -s "http://localhost:${LISTEN##*:}/v1/models" \
    | python3 -c 'import json,sys; [print("  -", m["id"]) for m in json.load(sys.stdin)["data"]]' \
    2>/dev/null || echo "  (endpoint not answering yet)"
