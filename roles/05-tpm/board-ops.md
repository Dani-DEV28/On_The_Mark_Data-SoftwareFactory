# Kata Board Operations — TPM

## Heartbeat (Factory Clock)

The TPM runs a heartbeat via OpenClaw cron every 15 minutes:

```bash
# Check all open issues
kata list

# Get structured output
kata list --agent

# Inspect specific issue
kata show <id>
```

## Board Operations

| Action | Command |
|--------|---------|
| Init workspace | `kata init` |
| Create issue | `kata create "<description>"` |
| List open | `kata list` |
| Show issue | `kata show <id>` |
| Claim issue | `kata claim <id>` |
| Close issue | `kata close <id> --done --message "..." --commit <sha>` |
| Interactive | `kata tui` |
| Agent contract | `kata quickstart` |

## Unblocking Rules

1. Issue stalled >30 min → alert the assigned agent
2. Issue stalled >60 min → reassign or file a new issue
3. Issue open >2 hours → escalate to Tech Lead
4. Multiple failures on same issue → consider investigation
