# Skill: Stop Conditions & Incident Reports

You enforce operational limits and produce Factory Incident Reports when execution stops.

## Stop Conditions Config
```yaml
stop_conditions:
  max_attempts: 5
  max_runtime: 45m
  no_progress_cycles: 4
  identical_failures: 3
  max_failed_agents: 2
```

## Check
Run after every heartbeat and before any kata status transition:

```bash
./scripts/stop-gap.sh check --kata <id>
# Returns: PASS | FAIL | HALT (with reason)
```

## On Halt — Factory Incident Report
```yaml
Factory Incident Report

Issue:
  #<kata-id>

Status:
  Stopped

Reason:
  <which condition was exceeded>

Attempts:
  <count>

Elapsed:
  <minutes>

Agents:
  - <list of agents that touched this kata>

Timeline:
  - Analysis Complete
  - Planning Complete
  - <...each step with status>

Observed Errors:
  - <first error>
  - <second error>

Repeated Failure:
  <test name if applicable>

Artifacts:
  - QA logs
  - Patch diff
  - Test results

Recommendation:
  Human intervention required.
```

## Rules
- The TPM enforces stop conditions — NOT the Tech Lead
- The Tech Lead decides technical strategy; the TPM decides whether execution should continue
- Always generate a complete incident report on halt
