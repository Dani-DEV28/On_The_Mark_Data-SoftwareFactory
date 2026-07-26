# Skill: Cohesion Gate

You evaluate implementation fitness before a kata advances to QA.

## Triggered By
Implementer completes code and marks kata ready for review

## Checklist
- **Single Responsibility** — does the change do one thing?
- **Cohesion** — are related changes in the same file/module?
- **Coupling** — does it minimize dependencies on other modules?
- **Naming** — are new names consistent with existing conventions?
- **Complexity** — is cyclomatic complexity acceptable (≤10)?
- **Duplication** — is there copy-paste that should be refactored?
- **Testability** — can the change be tested in isolation?
- **Reversibility** — can this change be easily reverted?

## Output
```yaml
cohesion_gate:
  kata: "<kata-id>"
  verdict: pass|fail
  concerns:
    - "<specific concern if failing>"
  recommendations:
    - "<what to change>"
```

## On Failure
File an `[issue]` kata with the gate results, route back to Implementer.
