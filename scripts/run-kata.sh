#!/usr/bin/env bash
# Software Factory — Run a Single Kata
# Usage: ./scripts/run-kata.sh "Brief description"

set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BRIEF="${1:?Usage: run-kata.sh \"Brief description\"}"

echo "=== Running Kata ==="
echo "Brief: $BRIEF"

# 1. Tech Lead creates the kata
echo ""
echo "--- [Gate 0] Briefed ---"
kata create --type feature --brief "$BRIEF"
KATA_ID=$(kata list --status briefed --tail 1 --id)
echo "Created kata: $KATA_ID"

# 2. PM decomposes
echo ""
echo "--- [Gate 1] Scoped ---"
kata claim "$KATA_ID" --agent product-manager
# PM agent processes the brief...
kata advance "$KATA_ID" --to scoped

# 3. Architect designs
echo ""
echo "--- [Gate 2] Designed ---"
kata claim "$KATA_ID" --agent architect
# Architect agent produces design notes...
kata advance "$KATA_ID" --to designed

# 4. Implementer codes
echo ""
echo "--- [Gate 3] In Progress ---"
kata claim "$KATA_ID" --agent implementer
# Implementer agent writes code...
kata advance "$KATA_ID" --to in-progress

# 5. DevOps+QA tests
echo ""
echo "--- [Gate 4] In Review ---"
kata claim "$KATA_ID" --agent devops-qa
# DevOps+QA agent runs tests in sandbox...
kata advance "$KATA_ID" --to in-review

# 6. Docs Engineer writes docs
echo ""
echo "--- [Gate 5] Documented ---"
kata claim "$KATA_ID" --agent docs-engineer
# Docs Engineer agent writes documentation...
kata advance "$KATA_ID" --to documented

# 7. Tech Lead reviews and closes
echo ""
echo "--- [Gate 6] Done ---"
kata claim "$KATA_ID" --agent tech-lead
# Tech Lead reviews final output...
kata advance "$KATA_ID" --to done

echo ""
echo "=== Kata Complete ==="
kata status "$KATA_ID"
