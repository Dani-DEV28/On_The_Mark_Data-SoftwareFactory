---
name: run-factory
description: Kick off, monitor, and control the Software Factory pipeline (the 7-agent team that fixes GitHub issues). Use when the user asks to start the factory, kick off the software team, run the pipeline, check factory status, or stop the factory.
---

# Run the Software Factory

The factory lives at `~/factory/software-factory` on this machine. It is driven by
shell scripts — you run them with your exec tool and report the output.

## Kick off the pipeline

```bash
cd ~/factory/software-factory
export PATH="$HOME/hack/.venv/bin:$HOME/.local/bin:$PATH"
./scripts/serve.sh                 # ensure llama-swap serving plane is up
nohup ./scripts/orchestrate.sh --limit 2 > evidence/orchestrate-run.log 2>&1 &
```

- To run specific katas: `./scripts/orchestrate.sh --katas <id1>,<id2> --limit 2`
- To sync fresh GitHub issues first: `./scripts/sfai.sh -repo https://github.com/onthemarkdata/petri run`
- **Single instance**: if it prints "another orchestrator is already running", one is
  active — do NOT force it; report that and show progress instead.

## Monitor

```bash
tail -20 ~/factory/software-factory/evidence/factory.log     # live team activity
~/.local/bin/kata list --label gate:review                   # PR-ready katas
python3 ~/factory/software-factory/scripts/factory/factory.py status   # board by gate
```

## Stop

```bash
cd ~/factory/software-factory && ~/.local/bin/kata create "[stop] requested via OpenClaw"
```
The TPM halts the whole pipeline at the next check. (Remove the [stop] kata to resume:
`kata delete <id> --force --confirm "DELETE <qualified-id>"`.)

## Report back

After kicking off: confirm the orchestrator started (pgrep -f orchestrate.sh), state
which katas are in flight, and tell the user to watch `evidence/factory.log`. After
status checks: summarize katas per gate in one or two sentences — don't dump raw logs.

## Stage gates (reference)

All role agents run concurrently; each kata flows through the gates in order. No role
skips a gate; only DevOps+QA touches git or the sandbox (per `tools.yaml` RBAC).

| Gate | Owner | Advances when |
|---|---|---|
| `briefed` | Tech Lead | Intake done, brief accepted |
| `scoped` | Product Manager | Prioritized katas + acceptance criteria written |
| `designed` | Architect | Design note attached; cohesion gate passed |
| `in-progress` | Implementer | Code + tests written |
| `in-review` | DevOps+QA | Tests pass in sandbox (`--network-denied`); committed |
| `documented` | Docs Engineer | README/CHANGELOG updated |
| `done` | TPM | Closed with evidence + commit SHA |
