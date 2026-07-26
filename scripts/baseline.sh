#!/usr/bin/env bash
# Software Factory — Run Lone-Agent Baseline
# Usage: ./scripts/baseline.sh "Brief description"

set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BRIEF="${1:?Usage: baseline.sh \"Brief description\"}"
OUTPUT_DIR="$FACTORY_DIR/evidence/baseline"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/baseline-$TIMESTAMP.md"

echo "=== Running Baseline (Lone Agent) ==="
echo "Brief: $BRIEF"
echo "Output: $OUTPUT_FILE"

mkdir -p "$OUTPUT_DIR"

# Run a single agent with no org — same brief, no roles
START_TIME=$(date +%s)

cat > "$OUTPUT_FILE" << EOF
# Baseline Run — $TIMESTAMP

## Brief
$BRIEF

## Setup
- Single agent, no org chart
- No kata board
- No role separation
- Direct model call (same model as factory implementer)

## Execution
$(date): Started
$(date): Processing...

## Results
- [ ] Code written
- [ ] Tests written
- [ ] Tests passing
- [ ] Documentation written

## Metrics
- Cycle time: TBD
- Tokens used: TBD
- Human interventions: TBD
- Issues found: TBD

## Comparison
See evidence/factory/ for factory run on same brief.
EOF

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "=== Baseline Complete ==="
echo "Elapsed: ${ELAPSED}s"
echo "Output: $OUTPUT_FILE"
