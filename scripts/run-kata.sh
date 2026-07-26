#!/usr/bin/env bash
# Software Factory — Run a Single Kata End-to-End
# Usage: ./scripts/run-kata.sh "Description of the work"

set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DESCRIPTION="${1:?Usage: run-kata.sh \"Description of the work\"}"

cd "$FACTORY_DIR"

echo "=== Running Kata ==="
echo "Description: $DESCRIPTION"

# 1. Create the issue
echo ""
echo "--- Creating Issue ---"
kata create "$DESCRIPTION"
KATA_ID=$(kata list --agent | python3 -c "import sys,json; issues=json.load(sys.stdin); print(issues[-1]['id'])" 2>/dev/null || echo "check kata list")
echo "Created issue: $KATA_ID"

# 2. PM decomposes
echo ""
echo "--- PM Decomposition ---"
kata show "$KATA_ID"
# PM agent creates sub-issues if needed

# 3. Architect designs
echo ""
echo "--- Architect Design ---"
kata show "$KATA_ID"
# Architect agent produces design notes

# 4. Implementer codes
echo ""
echo "--- Implementer Codes ---"
kata claim "$KATA_ID"
# Implementer agent writes code + tests

# 5. DevOps+QA tests
echo ""
echo "--- DevOps+QA Tests ---"
sandbox exec --network-denied pytest -v
# If tests pass, close with evidence

# 6. Docs Engineer writes docs
echo ""
echo "--- Docs Engineer ---"
# Docs agent writes documentation

# 7. Close with evidence
echo ""
echo "--- Closing Issue ---"
COMMIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "no-git")
kata close "$KATA_ID" --done \
  --message "Completed: $DESCRIPTION" \
  --commit "$COMMIT_SHA"

echo ""
echo "=== Kata Complete ==="
kata show "$KATA_ID"
