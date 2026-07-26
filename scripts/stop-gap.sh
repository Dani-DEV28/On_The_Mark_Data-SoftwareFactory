#!/usr/bin/env bash
# TPM stop conditions + Factory Incident Report (plan #17).
# Usage: ./scripts/stop-gap.sh check [--kata <id>]
# Exit codes: 0=PASS, 1=FAIL (bad input / crash), 2=per-kata HALT (kata
# quarantined at gate:halted, incident report generated), 3=FULL STOP
# (manual [stop] kata on the board)
set -uo pipefail
FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export FACTORY_DIR
[ "${1:-}" = "check" ] || { echo "Usage: $0 check [--kata <id>]"; exit 1; }
shift
exec python3 -u "$FACTORY_DIR/scripts/factory/factory.py" stop-check "$@"
