# Test Writing — Software Implementer

## Rules

1. Every feature kata must include tests
2. Tests go in `tests/` directory
3. Mirror the source file structure
4. One test function per behavior

## Test Structure

```python
# tests/test_feature.py
import pytest
from click import testing

def test_feature_basic():
    """Test basic functionality."""
    runner = testing.CliRunner()
    # ...

def test_feature_edge_case():
    """Test edge case."""
    # ...

def test_feature_error():
    """Test error handling."""
    # ...
```

## Coverage Targets

- New code: 80%+ coverage
- Critical paths: 100% coverage
- Edge cases: explicit tests

## Naming

- `test_<function>_<scenario>` format
- Descriptive docstrings
- Group related tests in classes
