# Kata Board Operations — TPM

## Heartbeat (Factory Clock)

The TPM runs a heartbeat via OpenClaw cron every 15 minutes:

```bash
# Check all katas
kata list --all --agent

# Identify stalled katas (no status change in >30 min)
kata list --all --stalled --minutes 30

# Triage new issues
kata list --type issue --status identified

# Report
kata list --all --status in-progress --count
kata list --all --status in-review --count
kata list --all --status done --count
```

## Board Operations

| Action | Command |
|--------|---------|
| Create feature | `kata create --type feature --brief "..."` |
| Create issue | `kata create --type issue --brief "..."` |
| Create spike | `kata create --type spike --brief "..."` |
| Claim | `kata claim <id> --agent <role>` |
| Advance | `kata advance <id> --to <status>` |
| List all | `kata list --all` |
| List by status | `kata list --status <status>` |
| List by type | `kata list --type <type>` |
| Get JSON | `kata list --all --agent` |

## Unblocking Rules

1. Kata stalled >30 min → alert the assigned role
2. Kata stalled >60 min → reassign or file issue
3. Issue kata open >2 hours → escalate to Tech Lead
4. Multiple issues on same kata → consider spike for investigation
