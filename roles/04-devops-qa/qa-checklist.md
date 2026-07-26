# QA Checklist — DevOps + QA

## Before Each Close

- [ ] All existing tests still pass
- [ ] New tests added for new functionality
- [ ] No network calls added (grep for `requests`, `urllib`, `httpx`, `aiohttp`)
- [ ] No secrets in code (grep for `password`, `token`, `api_key`, `secret`)
- [ ] Code compiles/lints without errors
- [ ] No new external dependencies (or approved by Architect)

## Git Checks

- [ ] Branch follows naming convention
- [ ] Commit messages follow convention
- [ ] No merge conflicts with main
- [ ] Squash merge clean

## Closing with Evidence

```bash
kata close <id> --done \
  --message "All tests pass. No regressions. No external calls." \
  --commit $(git rev-parse HEAD)
```

## Issue Creation (if checks fail)

```bash
kata create "[issue] QA failed: <specific failure description>"
```
