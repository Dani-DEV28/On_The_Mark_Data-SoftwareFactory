#!/usr/bin/env bash
# Baseline comparison (plan #23): one generalist agent, no org, no gates —
# same kata, so cycle time / quality / tokens compare against the factory.
# Usage: ./scripts/baseline.sh --kata <id>   (or -repo <url> --kata <id>)
set -euo pipefail
FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export FACTORY_DIR
KATA=""
while [ $# -gt 0 ]; do
    case "$1" in
        --kata) KATA="$2"; shift 2 ;;
        -repo|--repo) shift 2 ;;   # accepted for plan-compat; corpus already cloned
        *) shift ;;
    esac
done
[ -n "$KATA" ] || { echo "Usage: $0 --kata <id>"; exit 1; }
exec python3 "$FACTORY_DIR/scripts/factory/factory.py" baseline --kata "$KATA"
