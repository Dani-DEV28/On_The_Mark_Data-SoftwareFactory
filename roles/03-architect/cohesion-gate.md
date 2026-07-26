# Cohesion/Maintainability Gate — Software Architect

## Checklist

Before a kata advances to `in-review`:

- [ ] **Single Responsibility:** Does the change do one thing?
- [ ] **Cohesion:** Are related changes in the same file/module?
- [ ] **Coupling:** Does it minimize dependencies on other modules?
- [ ] **Naming:** Are new names consistent with existing conventions?
- [ ] **Complexity:** Is cyclomatic complexity acceptable (≤10)?
- [ ] **Duplication:** Is there copy-paste that should be refactored?
- [ ] **Testability:** Can the change be tested in isolation?
- [ ] **Reversibility:** Can this change be easily reverted if needed?

## Verdict

- [ ] **PASS** — advance to `in-review`
- [ ] **FAIL** — file issue kata, return to `in-progress`

## Notes
<!-- Explain the verdict and any concerns -->
