# Test Runner — DevOps + QA

## Running Tests

All tests run inside the OpenShell sandbox with network denied:

```bash
# Standard test run
sandbox exec --network-denied pytest -v

# With coverage
sandbox exec --network-denied pytest --cov=src --cov-report=term

# Specific test file
sandbox exec --network-denied pytest tests/test_specific.py -v

# Collect tests only (no execution)
sandbox exec --network-denied pytest --co
```

## Sandbox Constraints

- **Network:** DENIED (all outbound blocked)
- **Filesystem:** Read/write only in `/workspace/corpus`
- **Processes:** Max 512, no privilege escalation
- **Timeout:** 120s per test run

## Pass/Fail Criteria

- All tests pass: advance kata to `documented`
- Any test fails: file issue kata, return to `in-progress`
- New tests required for new functionality
- No regressions in existing tests

## Pytest Config

```ini
# pytest.ini (in corpus repo)
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```
