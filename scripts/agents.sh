#!/usr/bin/env bash
# Software Factory — Launch All Agents
# Usage: ./scripts/agents.sh

set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS_DIR="$FACTORY_DIR/config/openclaw/agents"

echo "=== Launching Factory Agents ==="

roles=(
    "tech-lead"
    "product-manager"
    "architect"
    "devops-qa"
    "tpm"
    "implementer"
    "docs-engineer"
)

for role in "${roles[@]}"; do
    echo "--- Starting $role ---"
    if [ -f "$AGENTS_DIR/$role/SOUL.md" ]; then
        # OpenClaw agent launch (syntax depends on version)
        openclaw agent start \
            --name "$role" \
            --soul "$AGENTS_DIR/$role/SOUL.md" \
            --model auto \
            2>/dev/null &
        echo "$role started"
    else
        echo "WARNING: $AGENTS_DIR/$role/SOUL.md not found — skipping"
    fi
done

echo ""
echo "=== All Agents Launched ==="
echo "Roles: ${roles[*]}"
echo ""
echo "Kata board: $FACTORY_DIR/kata-board/"
echo "Corpus:     $FACTORY_DIR/corpus/"

wait
