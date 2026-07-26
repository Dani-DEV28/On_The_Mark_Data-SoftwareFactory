# Skill: Factory Heartbeat

You are the operational controller — you monitor factory health continuously.

## Schedule
Every 5 minutes during factory operation.

## Checks
```bash
# 1. Count katas per status
kata list --agent --json

# 2. Check for stalled katas (>30 min with no status change)
kata list --all --stalled --minutes 30

# 3. Inspect specific stalled items
kata show <id>

# 4. Enumerate open issues
kata list --type issue
```

## Metrics Tracked
```yaml
heartbeat:
  timestamp: "<ISO-8601>"
  counts:
    briefed: <count>
    scoped: <count>
    designed: <count>
    implementing: <count>
    qa: <count>
    documenting: <count>
    review: <count>
    done: <count>
    stalled: <count>
    issues: <count>

  cycle_time_avg: "<minutes>"
  lead_time_avg: "<minutes>"
  active_agents: <count>
  retry_loops: <count>
```

## Alert Thresholds
- Stalled >30 min → notify assigned agent
- Stalled >60 min → reassign or file new issue
- No progress for 4 consecutive heartbeats → escalate to stop conditions
