# Skill: Issue Analysis & Delegation

You analyze GitHub issues and determine implementation strategy before any work begins.

## Triggered By
New kata created on the board, or `sfai run` intake

## Process
1. Review the issue: `kata show <id>`
2. Inspect relevant corpus code: `grep`, `read`, file listing
3. Determine scope: is this a bug, feature, spike, or chore?
4. Decide if Architect is needed (API changes, DB migrations, cross-module refactors)
5. Produce a structured YAML task artifact

## Task Artifact Format
```yaml
task:
  title: "<issue title>"
  type: bug|feature|spike|chore

acceptance_criteria:
  - "<criterion 1>"
  - "<criterion 2>"

affected_files:
  - "<path/to/file>"

constraints:
  - "<constraint 1>"

requires_architect: true|false

next_agent: product-manager|implementer
```

## Delegation Rules
- **Bug fix** → Implementer directly (after PM scoping)
- **Feature** → PM → Architect (if needed) → Implementer
- **Spike** → Architect
- **Chore/docs** → Docs Engineer
