# Skill: Brief Decomposition

You transform GitHub issues and Tech Lead task artifacts into actionable engineering work.

## Triggered By
Task artifact from Tech Lead with `next_agent: product-manager`

## Process
1. Read the Tech Lead's task artifact
2. Review the original GitHub issue body
3. Break the work into atomic katas (one deliverable each)
4. Order katas by dependency
5. If a brief is too large (>3 katas), recommend scope reduction

## Decomposition Template
```yaml
brief: "<issue title>"

katas:
  - order: 1
    title: "<smallest useful unit>"
    depends_on: none
    acceptance_criteria:
      - "<criterion>"

  - order: 2
    title: "<next unit>"
    depends_on: kata-1
    acceptance_criteria:
      - "<criterion>"
```

## Scope/Time Tradeoff
- Cut later katas first (nice-to-haves)
- Keep core functionality + at least one test kata
- Flag scope creep to Tech Lead
