#!/usr/bin/env bash
# Evidence collection (plan #22) — real data from the kata board, artifact
# timelines, and the LLM usage log (evidence/usage.jsonl).
set -euo pipefail
FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export FACTORY_DIR
exec python3 "$FACTORY_DIR/scripts/factory/factory.py" evidence
