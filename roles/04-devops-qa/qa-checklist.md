# QA Checklist — DevOps + QA

## Before Each Kata Advance

- [ ] All existing tests still pass
- [ ] New tests added for new functionality
- [ ] No network calls added (grep for `requests`, `urllib`, `httpx`, `aiohttp`)
- [ ] No secrets in code (grep for `password`, `token`, `api_key`, `secret`)
- [ ] Code compiles/lints without errors
- [ ] No new external dependencies (or approved by Architect)

## Git Checks

- [ ] Branch follows naming convention: `feat/kata-XXX-description`
- [ ] Commit messages follow convention
- [ ] No merge conflicts with main
- [ ] Squash merge clean

## Issue Kata Creation

If any check fails:

```bash
kata create --type issue --brief "QA failed: [specific failure]"
```

Include:
- Which check failed
- Error output
- Suggested fix
- Severity (blocks / non-blocking)
