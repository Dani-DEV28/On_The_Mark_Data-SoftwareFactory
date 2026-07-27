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
PY="python3 -u $FACTORY_DIR/scripts/factory/factory.py"

# Single-instance guard: two orchestrators would race on katas and the corpus.
exec 200>"$FACTORY_DIR/.orchestrate.lock"
if ! flock -n 200; then
    echo "ERROR: another orchestrator is already running (lock: .orchestrate.lock)"
    echo "       watch it with: tail -f evidence/factory.log — or kill it first."
    exit 1
fi

LIMIT=1 KATAS="" ONCE=0 MAX_CYCLES=0   # focus mode: whole team on ONE kata at a time
while [ $# -gt 0 ]; do
    case "$1" in
        --limit) LIMIT="$2"; shift 2 ;;
        --katas) KATAS="$2"; shift 2 ;;
        --once) ONCE=1; shift ;;
        --cycles) MAX_CYCLES="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

RUN_START=$(date +%s)
echo "╔══════════════════════════════════════════════════════════════"
echo "║ SOFTWARE FACTORY — orchestrator starting $(date '+%Y-%m-%d %H:%M:%S')"
echo "║ mode: FOCUS (all agents on one kata) — katas: ${KATAS:-auto from backlog}"
echo "║ model: ${SFAI_MODEL:-qwen3.6-35b-a3b-fp8}"
echo "║ gates: intake→scoped→designed→implement→qa→(tl-review)→docs→ci→review"
echo "║ persistent log: evidence/factory.log   TPM config: config/stop-gap.yaml"
echo "╚══════════════════════════════════════════════════════════════"
[ -n "$KATAS" ] && $PY intake --katas "$KATAS" --limit "$LIMIT"

# First kata currently sitting in a working gate (in-flight work resumes first)
pick_focus() {
    $PY status 2>/dev/null \
        | grep -E "gate:(intaken|scoped|designed|implementing|qa|tl-review|documenting|ci) " \
        | head -1 | awk "{print \$3}" | tr -d ","
}

cycle=0
stopcheck_errs=0
while true; do
    cycle=$((cycle + 1))
    CYCLE_START=$(date +%s)

    # FOCUS: exactly one kata gets the whole team. Explicit --katas wins;
    # otherwise resume in-flight work; otherwise intake the next from backlog.
    FOCUS="$KATAS"
    if [ -z "$FOCUS" ]; then
        FOCUS=$(pick_focus)
        if [ -z "$FOCUS" ]; then
            intake_out=$($PY intake --limit 1)
            echo "$intake_out"
            newly=$(echo "$intake_out" | grep -oE "intaken: [0-9]+" | grep -oE "[0-9]+" || echo 0)
            if [ "${newly:-0}" -eq 0 ]; then
                echo ""
                echo "╔══════════════════════════════════════════════════════════════"
                echo "║ BACKLOG DRAINED — nothing left to intake — $(( $(date +%s) - RUN_START ))s total"
                echo "║ review the work:   kata list --label gate:review"
                echo "╚══════════════════════════════════════════════════════════════"
                break
            fi
            FOCUS=$(pick_focus)
        fi
    fi
    echo ""
    echo "━━━ cycle $cycle — $(date '+%H:%M:%S') — FOCUS: $FOCUS ━━━"
    # Two concurrent lanes still run (planning + heavy), but both serve the
    # focus kata only; vLLM batches whatever overlaps.
    $PY cycle --limit "$LIMIT" --katas "$FOCUS"
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
    $PY heartbeat
    $PY status
    echo "━━━ cycle $cycle done in $(( $(date +%s) - CYCLE_START ))s (run total $(( $(date +%s) - RUN_START ))s) ━━━"

    # Explicit --katas mode: done when the requested katas leave the pipeline.
    # (Auto mode terminates via BACKLOG DRAINED at the top of the loop.)
    if [ -n "$KATAS" ]; then
        active=$($PY status | grep -cE "gate:(intaken|scoped|designed|implementing|qa|tl-review|documenting|ci) " || true)
        if [ "$active" -eq 0 ]; then
            echo ""
            echo "╔══════════════════════════════════════════════════════════════"
            echo "║ REQUESTED KATAS at gate:review, gate:halted, or done — $(( $(date +%s) - RUN_START ))s total"
            echo "║ review the work:   kata list --label gate:review"
            echo "║ inspect a fix:     cd corpus && git diff main...factory/<kata>"
            echo "║ incidents (if any): ls evidence/incidents/"
            echo "╚══════════════════════════════════════════════════════════════"
            break
        fi
    fi
    [ "$ONCE" -eq 1 ] && break
    [ "$MAX_CYCLES" -gt 0 ] && [ "$cycle" -ge "$MAX_CYCLES" ] && { echo "cycle limit reached"; break; }
    sleep 5
done
$PY evidence
