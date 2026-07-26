# Skill: README Documentation

You update README documentation after successful implementation and QA validation.

## Triggered By
Kata advances to `documenting` status after QA passes

## Process
1. Claim the kata: `kata claim <id>`
2. Read the implementation summary and test results
3. Identify what changed from a user perspective
4. Update the corpus repo's README accordingly

## README Structure (match existing corpus style)
```markdown
# Project Name

One-line description.

## Installation
```bash
pip install -e .
```

## Usage
<!-- Code examples showing the new/changed functionality -->

## Configuration
<!-- New CLI flags, env vars, config options -->

## Development
```bash
pytest
```
```

## Rules
1. Match the existing README style of the corpus repo
2. Include installation, usage, and development sections as needed
3. Code examples must be runnable
4. No external links (offline constraint)
5. Only update sections relevant to the change
