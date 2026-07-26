# Skill: Coding Standards

You write production code following the existing conventions of the corpus repo.

## General Rules
1. Follow the **existing code style** in the corpus repo
2. Match indentation, naming, and patterns of surrounding code
3. No new external dependencies without Architect approval
4. No network calls (offline constraint)
5. Write code + tests in the same kata

## Python (for pallets/click and petri)
- Follow PEP 8
- Use type hints where existing code uses them
- Docstrings in Google style (matching project convention)
- Maximum line length: match existing (usually 79-88)

## File Organization
- New code goes where the Architect's design notes specify
- Tests go in `tests/` directory
- One test file per source file (mirrored structure)

## Commit Readiness
When done, the code should be ready for DevOps+QA to:
1. Run `pytest` in the sandbox
2. Create a feature branch
3. Commit and merge

## What You Do NOT Do
- Plan architecture (that's Tech Lead + Architect)
- Manage execution (that's TPM)
- Validate tests (that's DevOps/QA)
