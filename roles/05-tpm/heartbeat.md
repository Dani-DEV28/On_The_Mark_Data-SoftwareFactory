# Heartbeat Configuration — TPM

## Cron Schedule

Every 15 minutes during factory operation:

```
*/15 * * * * /path/to/scripts/heartbeat.sh
```

## Heartbeat Script Logic

```bash
#!/usr/bin/env bash
# Heartbeat — run every 15 minutes

# 1. Count katas per status
echo "=== Factory Heartbeat ==="
echo "Briefed:    $(kata list --status briefed --count)"
echo "Scoped:     $(kata list --status scoped --count)"
echo "Designed:   $(kata list --status designed --count)"
echo "InProgress: $(kata list --status in-progress --count)"
echo "InReview:   $(kata list --status in-review --count)"
echo "Documented: $(kata list --status documented --count)"
echo "Done:       $(kata list --status done --count)"

# 2. Check for stalled katas
echo ""
echo "=== Stalled (>30 min) ==="
kata list --all --stalled --minutes 30

# 3. Triage new issues
echo ""
echo "=== New Issues ==="
kata list --type issue --status identified

# 4. Velocity
echo ""
echo "=== Today's Velocity ==="
echo "Completed: $(kata list --status done --count)"
echo "Issues:    $(kata list --type issue --count)"
```
