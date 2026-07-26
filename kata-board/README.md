# Kata Board — The Message Bus

The kata board is the coordination mechanism for the software factory. No custom queue — each work item is a kata with stable IDs.

## Usage

```bash
# Create a feature kata
kata create --type feature --brief "Add CLI timeout flag with tests"

# Create an issue kata
kata create --type issue --brief "pytest fails on Windows: path separator"

# Create a spike kata
kata create --type spike --brief "Investigate vLLM NVFP4 issue on GB10"

# Claim a kata
kata claim <id> --agent <role>

# Check status
kata status <id>

# Advance to next gate
kata advance <id> --to <status>

# List all katas
kata list --all

# List by status
kata list --status in-progress

# Get JSON output (for evidence table)
kata list --all --agent
```

## Status Flow (Feature)

```
briefed → scoped → designed → in-progress → in-review → documented → done
```

## Status Flow (Issue)

```
identified → triaged → in-progress → resolved → closed
```

## Kata Types

| Type | Purpose | Example |
|------|---------|---------|
| `feature` | Normal work item | "Add CLI timeout flag with tests" |
| `issue` | Bug, blocker, rework | "pytest fails on Windows" |
| `spike` | Investigation | "Test vLLM NVFP4 compatibility" |

## Role → Gate Mapping

| Role | Claims at gate |
|------|---------------|
| Tech Lead | `documented` (final review) |
| Product Manager | `briefed` (decompose) |
| Architect | `scoped` (design) |
| Implementer | `in-progress` (code) |
| DevOps+QA | `in-review` (test) |
| TPM | Any (heartbeat, triage) |
| Docs Engineer | `documented` (docs) |

## JSON Output (for Evidence)

```json
{
  "id": "KATA-001",
  "type": "feature",
  "status": "done",
  "brief": "Add CLI timeout flag with tests",
  "created_at": "2026-07-26T10:00:00Z",
  "completed_at": "2026-07-26T11:30:00Z",
  "assigned_to": "devops-qa",
  "rework_count": 1,
  "issue_count": 2,
  "cycle_time_minutes": 90,
  "tokens_used": 15420
}
```
