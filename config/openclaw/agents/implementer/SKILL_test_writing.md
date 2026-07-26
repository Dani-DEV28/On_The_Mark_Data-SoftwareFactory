# Skill: Test Writing

You write unit tests alongside every code change.

## Rules
1. Every feature kata must include tests
2. Tests go in `tests/` directory
3. Mirror the source file structure
4. One test function per behavior

## Test Structure
```python
# tests/test_feature.py
def test_feature_basic():
    """Test basic functionality."""
    ...

def test_feature_edge_case():
    """Test edge case."""
    ...

def test_feature_error():
    """Test error handling."""
    ...
```

## Coverage Targets
- New code: 80%+ coverage
- Critical paths: 100% coverage
- Edge cases: explicit tests

## Naming
- `test_<function>_<scenario>` format
- Descriptive docstrings
- Group related tests using classes where appropriate

## Test Framework
- Use the corpus repo's existing test framework (pytest for click/petri)
- Use `click.testing.CliRunner` for CLI tests in click-based repos
