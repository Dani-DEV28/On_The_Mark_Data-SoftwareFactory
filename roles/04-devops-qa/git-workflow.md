# Git Workflow — DevOps + QA

## Branch Strategy

```
main (protected)
├── feat/kata-001-timeout-flag
├── fix/kata-002-windows-env-var
└── docs/kata-003-readme-update
```

## Commit Convention

```
<type>(<scope>): <description>

Types: feat, fix, docs, test, refactor, chore
Scope: kata ID or module name
Description: imperative, lowercase, no period
```

## Rules

1. **Only DevOps+QA touches git** — no other role commits
2. Feature branches per kata — merge to main after QA passes
3. Squash commits on merge for clean history
4. Never force-push main
5. Never commit secrets, API keys, or tokens
