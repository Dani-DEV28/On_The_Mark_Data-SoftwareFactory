# Brief-to-Katas Decomposition — Product Manager

## Rules

1. Every brief gets decomposed into **atomic katas** (one deliverable each)
2. Each kata must have **clear acceptance criteria**
3. Katas are ordered by **dependency** (what must come first)
4. If a brief is too large (>3 katas), recommend scope reduction

## Decomposition Template

### Brief: [Title]

**Kata 1:** [smallest useful unit]
- Acceptance criteria:
  - [ ] Criterion 1
  - [ ] Criterion 2
- Depends on: None

**Kata 2:** [next unit]
- Acceptance criteria:
  - [ ] Criterion 1
  - [ ] Criterion 2
- Depends on: Kata 1

## Scope/Time Tradeoff

If time is short:
- Cut Kata 3+ first (nice-to-haves)
- Keep Kata 1+2 (core functionality)
- Always keep at least one test kata
