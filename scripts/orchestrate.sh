#!/usr/bin/env bash
# Software Factory — TPM-driven orchestration loop (plan #18).
# Workflow: Tech Lead -> PM -> Architect(optional) -> Implementer -> QA -> Docs
# QA failure -> Tech Lead review -> Implementer retry. TPM checks stop
# conditions every cycle and halts with a Factory Incident Report.
#
# Usage: ./scripts/orchestrate.sh [--limit N] [--katas a,b] [--once] [--cycles N]

set -uo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export FACTORY_DIR
PY="python3 $FACTORY_DIR/scripts/factory/factory.py"

LIMIT=2 KATAS="" ONCE=0 MAX_CYCLES=0
while [ $# -gt 0 ]; do
    case "$1" in
        --limit) LIMIT="$2"; shift 2 ;;
        --katas) KATAS="$2"; shift 2 ;;
        --once) ONCE=1; shift ;;
        --cycles) MAX_CYCLES="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

echo "=== Factory orchestrator (limit=$LIMIT katas=${KATAS:-auto}) ==="
$PY intake ${KATAS:+--katas "$KATAS"} --limit "$LIMIT"

cycle=0
stopcheck_errs=0
while true; do
    cycle=$((cycle + 1))
    echo "--- cycle $cycle ---"
    for gate in intake scoped designed implement qa tl-review docs; do
        $PY gate --gate "$gate" --limit "$LIMIT" ${KATAS:+--katas "$KATAS"}
        # Exit codes: 0=PASS, 2=per-kata HALT (quarantined at gate:halted,
        # incident report written — factory continues), 3=manual [stop] kata
        # (whole-factory stop), 1=stop-check itself failed.
        "$FACTORY_DIR/scripts/stop-gap.sh" check
        rc=$?
        if [ "$rc" -eq 3 ]; then
            echo "TPM FULL STOP — manual [stop] kata on board; stopping the factory"
            exit 2
        elif [ "$rc" -eq 2 ]; then
            echo "TPM: kata(s) quarantined at gate:halted (see evidence/incidents/); continuing"
            stopcheck_errs=0
        elif [ "$rc" -ne 0 ]; then
            stopcheck_errs=$((stopcheck_errs + 1))
            echo "WARN: stop-check error rc=$rc (${stopcheck_errs} consecutive) — continuing"
            if [ "$stopcheck_errs" -ge 3 ]; then
                echo "TPM HALT — stop-check itself is failing; halting as fail-safe"
                exit 3
            fi
        else
            stopcheck_errs=0
        fi
    done
    $PY heartbeat
    $PY status

    # Done when nothing is active in the working gates
    active=$($PY status | grep -cE "gate:(intaken|scoped|designed|implementing|qa|tl-review|documenting) " || true)
    if [ "$active" -eq 0 ]; then
        echo "=== All katas at gate:review, gate:halted, or done ==="
        break
    fi
    [ "$ONCE" -eq 1 ] && break
    [ "$MAX_CYCLES" -gt 0 ] && [ "$cycle" -ge "$MAX_CYCLES" ] && { echo "cycle limit reached"; break; }
    sleep 5
done
$PY evidence
