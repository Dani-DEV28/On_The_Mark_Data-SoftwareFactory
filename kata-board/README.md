# Kata Board — The Message Bus

The kata board is the coordination mechanism for the software factory. No custom queue — each work item is a kata with stable IDs.

State lives in SQLite under `KATA_HOME`. Your repo stays clean — only a small `.kata.toml` is committed.

## Setup

```bash
cd software-factory
kata init                    # bind this workspace to a kata project
kata init --with-agents      # also writes managed briefing into AGENTS.md
```

## Usage

```bash
# Create issues (prints short id, e.g. abc4)
kata create "add --timeout flag to Click commands"
kata create "fix pytest failure on Windows path separator"
kata create "investigate vLLM NVFP4 issue on GB10"

# List open work
kata list

# Inspect by short id
kata show abc4

# Claim work (agent assigns itself)
kata claim abc4

# Close with evidence (only when verified)
kata close abc4 --done \
  --message "Fixed the issue and verified tests pass." \
  --commit <sha>

# Interactive TUI (browse, triage, supervise)
kata tui
```

## Agent Output

All commands support `--json` and `--agent` flags for machine-readable output:

```bash
kata list --agent             # JSON for agent consumption
kata show abc4 --agent        # structured issue details
kata list --json              # raw JSON
```

## Issue Lifecycle

```
created → claimed → closed (with --done and evidence)
```

Closing is explicit: you must provide a `--message` explaining what was done and optionally a `--commit` SHA as proof.

## Kata Types (via description)

kata doesn't have a `--type` flag — the issue type is encoded in the description:

```bash
kata create "[feature] add --timeout flag"
kata create "[bug] fix pytest failure on Windows"
kata create "[spike] investigate vLLM NVFP4 compatibility"
```

## Role → Command Mapping

| Role | Commands |
|------|----------|
| Tech Lead | `kata create`, `kata close`, `kata show` |
| Product Manager | `kata create`, `kata list`, `kata show` |
| Architect | `kata create` (issues), `kata show`, `kata claim` |
| DevOps+QA | `kata claim`, `kata close --done --commit <sha>` |
| TPM | `kata list`, `kata tui`, `kata claim` |
| Implementer | `kata claim`, `kata close --done` |
| Docs Engineer | `kata claim`, `kata close --done` |

## For Agents

Run `kata quickstart` (alias `kata agent-instructions`) for the full operating contract:

- Search before creating (avoid duplicates)
- Pass an idempotency key on create
- Prefer `--agent` output
- Claim work with `kata claim`
- Close only when work is verified, with evidence and a substantive message
