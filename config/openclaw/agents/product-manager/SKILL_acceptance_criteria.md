# Skill: Acceptance Criteria

You produce clear acceptance criteria for each kata so the Implementer knows exactly when work is complete.

## Quality Standards
- **Testable** — each criterion can be verified by a test or inspection
- **Unambiguous** — one interpretation only
- **Atomic** — one behavior per criterion
- **Complete** — covers happy path, edge cases, and error states

## Template
```yaml
acceptance_criteria:
  functional:
    - "Feature works as described: <specific behavior>"
    - "Edge case handled: <edge case>"
    - "Error handling: <error scenario>"

  quality:
    - "Unit tests written and passing"
    - "No regressions in existing tests"
    - "Code follows project style guide"

  documentation:
    - "README updated (if user-facing)"
    - "CHANGELOG entry added"

  integration:
    - "Merges cleanly into main branch"
    - "No new external dependencies"
    - "No network calls added (offline constraint)"
```
