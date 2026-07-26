# Skill: QA Checklist

You perform a standardized set of quality checks before closing a kata.

## Checklist
```yaml
qa_checklist:
  kata: "<kata-id>"

  tests:
    - "All existing tests still pass"
    - "New tests added for new functionality"
    - "Coverage meets threshold (80%+ new code)"

  security:
    - "No network calls added (grep for requests, urllib, httpx, aiohttp)"
    - "No secrets in code (grep for password, token, api_key, secret)"

  quality:
    - "Code compiles/lints without errors"
    - "No new external dependencies (or approved by Architect)"

  git:
    - "Branch follows naming convention"
    - "Commit messages follow convention"
    - "No merge conflicts with main"

  verdict: pass|fail
```

## On Pass
```bash
kata close <id> --done \
  --message "All tests pass. No regressions. No external calls." \
  --commit $(git rev-parse HEAD)
```

## On Fail
```bash
kata create "[issue] QA failed: <specific failure description>"
```
