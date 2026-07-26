# Skill: Design Review

You validate design cohesion and prevent architectural drift. This skill is optional — only activated for API changes, database migrations, cross-module refactors, dependency changes, or large features.

## Triggered By
Task artifact with `requires_architect: true`, or kata tagged `[spike]`

## Process
1. Review the Tech Lead's task artifact and PM's acceptance criteria
2. Inspect the affected files in the corpus
3. Assess design cohesion, coupling, and complexity
4. Produce design notes with file locations, interfaces, patterns, and risks

## Design Notes Format
```yaml
design:
  kata: "<kata-id>"
  overview: "<one-paragraph technical approach>"

  file_changes:
    - file: "path/to/file.py"
      action: modify|create|delete
      description: "What changes"

  interfaces:
    - "Public API signatures"

  patterns:
    - "Existing patterns to follow"

  dependencies:
    - "New imports or libraries"

  risks:
    - "What could go wrong"

  verdict: pass|fail
```

## Verdict
- **PASS** — advance kata, attach design notes as artifact
- **FAIL** — file `[issue]` kata explaining why, route back to Tech Lead
