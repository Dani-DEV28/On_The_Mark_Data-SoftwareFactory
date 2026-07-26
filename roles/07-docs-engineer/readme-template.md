# README Template — Docs Engineer

## Structure

```markdown
# Project Name

One-line description.

## Installation

\`\`\`bash
pip install -e .
\`\`\`

## Usage

\`\`\`python
import click

@click.command()
def hello():
    """Simple example."""
    click.echo("Hello!")
\`\`\`

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `--flag` | `false` | Enables feature X |

## Development

\`\`\`bash
# Run tests
pytest

# Run with coverage
pytest --cov=src
\`\`\`

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for details.
```

## Rules

1. Match the existing README style of the corpus repo
2. Include installation, usage, and development sections
3. Code examples must be runnable
4. No external links (offline constraint)
