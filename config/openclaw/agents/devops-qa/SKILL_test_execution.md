# Skill: Test Execution

You run tests, linting, and formatting inside the OpenShell sandbox with network denied.

## Triggered By
Implementer marks kata as `qa` ready

## Process
1. Claim the kata: `kata claim <id>`
2. Run tests in the network-denied sandbox
3. Run linting and formatting checks
4. Verify build
5. Produce QA report

## Commands
```bash
# Standard test run
sandbox exec --network-denied pytest -v

# With coverage
sandbox exec --network-denied pytest --cov=src --cov-report=term

# Specific test file
sandbox exec --network-denied pytest tests/test_specific.py -v

# Lint
sandbox exec --network-denied ruff check .

# Format check
sandbox exec --network-denied ruff format --check .
```

## Pass/Fail Rules
- All tests pass + lint clean → advance to `documenting`
- Any test fails → file `[issue]` kata with failure details, route back to Tech Lead
- You NEVER fix the code — only validate
