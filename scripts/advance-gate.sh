#!/usr/bin/env bash
# Advance katas through one gate (plan #18). Thin wrapper over the engine.
# Usage: ./scripts/advance-gate.sh --gate <intake|scoped|designed|implement|qa|tl-review|docs> [--limit N] [--katas a,b]
set -euo pipefail
FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export FACTORY_DIR
exec python3 -u "$FACTORY_DIR/scripts/factory/factory.py" gate "$@"
