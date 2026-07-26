#!/usr/bin/env bash
# Software Factory — Wire All 7 Agents (verified against OpenClaw 2026.5.27)
# Creates one isolated OpenClaw agent per role inside the NemoClaw sandbox,
# each with its SOUL.md persona as the agent workspace.
# Usage: ./scripts/agents.sh
#
# Real CLI (the old `openclaw agent start --soul` syntax does not exist):
#   openclaw agents add <name> --model <id> --workspace <dir> --non-interactive

set -uo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS_DIR="$FACTORY_DIR/config/openclaw/agents"
SANDBOX="${SFAI_SANDBOX:-local-pm-os-agent}"
MODEL="${SFAI_AGENT_MODEL:-inference/qwen3.6-35b-a3b-fp8}"

command -v nemoclaw >/dev/null 2>&1 || { echo "ERROR: nemoclaw not in PATH"; exit 1; }

roles=(tech-lead product-manager architect devops-qa tpm implementer docs-engineer)

echo "=== Wiring Factory Agents (sandbox: $SANDBOX, model: $MODEL) ==="

existing="$(nemoclaw "$SANDBOX" exec --timeout 60 -- openclaw agents list --json 2>/dev/null || echo '[]')"

ok=0; failed=0
for role in "${roles[@]}"; do
    if [ ! -f "$AGENTS_DIR/$role/SOUL.md" ]; then
        echo "WARNING: $AGENTS_DIR/$role/SOUL.md not found — skipping"
        failed=$((failed+1)); continue
    fi
    if echo "$existing" | grep -q "\"id\": \"$role\""; then
        echo "--- $role already wired ---"
        ok=$((ok+1)); continue
    fi
    echo "--- Wiring $role ---"
    nemoclaw "$SANDBOX" exec --timeout 60 -- mkdir -p "/sandbox/factory/agents/$role" \
        && nemoclaw "$SANDBOX" upload "$AGENTS_DIR/$role/SOUL.md" "/sandbox/factory/agents/$role/SOUL.md" >/dev/null \
        && nemoclaw "$SANDBOX" exec --timeout 120 -- openclaw agents add "$role" \
            --model "$MODEL" \
            --workspace "/sandbox/factory/agents/$role" \
            --non-interactive --json >/dev/null
    if [ $? -eq 0 ]; then
        echo "$role wired"
        ok=$((ok+1))
    else
        echo "ERROR: failed to wire $role"
        failed=$((failed+1))
    fi
done

echo ""
echo "=== Agent roster ==="
nemoclaw "$SANDBOX" exec --timeout 60 -- openclaw agents list 2>/dev/null | grep -vE "UNDICI|trace-warnings" || true
echo ""
echo "Wired: $ok  Failed: $failed  (roles: ${roles[*]})"
[ "$failed" -eq 0 ]
