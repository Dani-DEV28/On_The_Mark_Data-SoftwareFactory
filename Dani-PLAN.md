# Dani-PLAN.md — Software Factory MVP Build Plan

Target: **NVIDIA GB10 (DGX Spark)** — Linux/aarch64  
Stack fallback: NemoClaw → OpenShell → OpenClaw  
Corpus: `pallets/click`  
Issue source: KataTracker (kata CLI as issue tracker and board)  
Pipeline: Review issues → agents use kata board → fix (with stop-gap)

---

## P0 — Staging & Prep (done off-GB10, on laptop before hackathon)

### [ ] 1. Confirm model weights on GB10
- Models already loaded into `models/` on GB10
- Phase 1 small model (~1.7B) available for walking skeleton
- Phase 2 models (gemini-4, nemotron, qwen3.6) also loaded

### [ ] 2. Clone corpus repo
```bash
git clone https://github.com/pallets/click.git corpus/
```
- `corpus/` is currently empty (`.gitkeep` only)

### [ ] 3. Stage remaining binaries to `stage/`
| Binary | Source | Target |
|--------|--------|--------|
| `kata` | `pip install kata` | `stage/binaries/kata` |
| `openclaw` | `npm install -g openclaw` or `pip install openclaw` | `stage/binaries/openclaw` |
| `agentgateway` | GH release | `stage/binaries/agentgateway` |

- vLLM and llama-swap already implemented — skip staging those
- `stage/binaries/`, `stage/repos/`, `stage/weights/` are otherwise empty

### [ ] 4. Create `scripts/stage-usb.sh`
- Script referenced in `PREP.md` but does not exist
- Should rsync everything to a USB drive for air-gapped transfer to GB10

---

## P0 — Platform Setup (on GB10, day-of)

### [ ] 5. Hardware & network
- GB10 powered, Ethernet connected
- Tailscale auth key ready (or phone hotspot)
- `rsync` stage folder to GB10

### [ ] 6. Verify inference plane
- vLLM and llama-swap already implemented — confirm they're running
- **Known gap**: `serve.sh` references `config/agentgateway.yaml` — file does not exist
- **Fix needed**: Create `config/agentgateway.yaml` or remove the reference

### [ ] 7. Install kata CLI & init board
```bash
pip install kata
kata init --with-agents
```
- Creates `kata-board/` SQLite DB and `.kata.toml`

### [ ] 8. Install OpenClaw
```bash
npm install -g openclaw   # preferred
# or
pip install openclaw      # fallback
```
- Core agent framework — all 7 agents run on this
- `setup.sh` tries NemoClaw first, then OpenShell, then OpenClaw

### [ ] 9. Create `config/agentgateway.yaml`
- Referenced by `serve.sh` but missing
- Minimal config: localhost endpoint, OTel disabled for MVP, per-role model routing

---

## P1 — Stack Setup: NemoClaw / OpenShell / OpenClaw

### [ ] 10. Attempt NemoClaw (preferred)
```bash
nemoclaw onboard --non-interactive --provider ollama
```
- Uses `config/nemoclaw/blueprint.yaml` — already defined with all 7 agents
- Automatically provisions OpenShell sandbox + OpenClaw agents
- **Policy files already ready**: `network.yaml`, `filesystem.yaml`, `process.yaml`, `inference.yaml`

### [ ] 11. Fallback: OpenShell direct
```bash
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh
```
- Manual sandbox + RBAC policies (translate from NemoClaw format)
- No blueprint verification; loses NemoClaw lifecycle management

### [ ] 12. Fallback: OpenClaw only
```bash
openclaw agent start --name <role> --soul <path> --model auto
```
- No sandbox, no RBAC — agents run natively on host
- **Script gap**: `agents.sh` uses this syntax — needs verification against actual OpenClaw CLI

### [ ] 13. Wire all 7 agents
- SOUL.md files ready: `tech-lead`, `product-manager`, `architect`, `devops-qa`, `tpm`, `implementer`, `docs-engineer`
- `config/openclaw/tools.yaml` defines available tools (kata, git, sandbox, fs)
- **Verify**: each agent can start, list katas, and claim work

### [ ] 14. Fix `setup.sh` for air-gapped GB10
- Current: `curl https://www.nvidia.com/nemoclaw.sh | bash` (requires internet)
- **Need**: `--offline` flag that uses staged binaries from `stage/`
- **Need**: venv creation for python tools (kata, agentgateway)
- **Need**: fallback chain that doesn't require external DNS

---

## P2 — MVP Pipeline: Issue Review → Fix

### [ ] 15. Issue intake via KataTracker
**KataTracker is the issue tracker.** The kata board IS the message bus — no separate issue database.

Issues enter the board via one of:
1. **Human creates** a kata: `kata create "[bug] environment variable fails on Windows"`
2. **Agent discovers** an issue during work and files it: `kata create "[issue] QA failed: test_core.py regression"`
3. **Intake script** reads a source (ISSUES.md, GitHub API) and creates katas for seed data

All issues and features live on the same board. Agents organize by polling the board:

```bash
kata list                          # find work
kata list --agent --json           # machine-readable for agents
kata show <id>                     # inspect details
kata claim <id>                    # claim work
kata close <id> --done --message "Fixed" --commit <sha>  # close with evidence
```

**Issue types** encoded in kata description prefix:
| Prefix | Type | Agent routing |
|--------|------|---------------|
| `[bug]` | Bug fix | Implementer → DevOps+QA |
| `[feature]` | New feature | PM → Architect → Implementer → DevOps+QA → Docs |
| `[issue]` | Problem found | TPM triages → routes to appropriate agent |
| `[spike]` | Investigation | Architect |
| `[docs]` | Documentation | Docs Engineer |
| `[stop]` | Manual stop-gap | Halts pipeline |

### [ ] 16. Implement stop-gap mechanism
**Central stop-gap module**: `scripts/stop-gap.sh`

Checked at each pipeline gate. Halts pipeline if:
- **Test failures**: >N consecutive failures (configurable, default 3)
- **Rework loops**: >N rework cycles on same kata (default 3)
- **Critical error**: agent returns unparseable output, tool call fails
- **Manual override**: human creates a `[stop]` kata on the board → all agents see it and halt

```bash
./scripts/stop-gap.sh check --gate <gate-name> --kata <id>
# Returns: PASS | FAIL | HALT
```

**Stop-gap config**: `config/stop-gap.yaml`
```yaml
max_test_failures: 3
max_rework_loops: 3
halt_on_critical_error: true
manual_override: false
```

### [ ] 17. Build agent orchestration
**Replace `run-kata.sh`** (currently serial bash with no real agent coordination).

**Pull model** — the kata board is the organizing backbone. All agents use `kata` CLI to find, claim, and advance work:

1. **TPM heartbeat** runs every 5min: `kata list --agent --json` → inspects all statuses, checks for stalled items
2. **Each agent polls** for katas at its gate using `kata list` + `kata show`:
   - PM polls `briefed` → creates sub-katas with `kata create`, advances to `scoped`
   - Architect polls `scoped` → writes design notes, advances to `designed`
   - Implementer polls `designed` → writes code + tests with `kata claim`, advances to `in-progress`
   - DevOps+QA polls `in-progress` → runs tests with `sandbox exec`, advances to `in-review` or files `[issue]` kata
   - Docs polls `in-review` → writes docs with `kata claim`, advances to `done`
3. **Stop-gap check** at each transition — polls for `[stop]` katas on the board

**Orchestrator script**: `scripts/orchestrate.sh`
```bash
# Main loop
while true; do
  for gate in briefed scoped designed in-progress in-review; do
    ./scripts/advance-gate.sh --gate "$gate"
    ./scripts/stop-gap.sh check --gate "$gate"
  done
  sleep 60
done
```

### [ ] 18. Wire end-to-end pipeline
```bash
# Full flow:
./scripts/orchestrate.sh                          # agent orchestration loop
# In another terminal — seed the board with issues:
kata create "[bug] environment variable override not working on Windows"
kata create "[feature] add --timeout flag to Click commands"
# Or batch from a file:
kata create --batch issues.txt
# Watch agents pick up katas and advance them through gates
```

### [ ] 19. Add stop-gap checkpoints
Checkpoint at each stage transition:
- `briefed → scoped`: intake parsed correctly?
- `scoped → designed`: design is feasible?
- `designed → in-progress`: tests compile?
- `in-progress → in-review`: tests pass?
- `in-review → done`: docs complete?

---

## P3 — Fix Project Issues

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 1 | `config/agentgateway.yaml` missing | `serve.sh:38` | Create config with localhost endpoint, per-role models, OTel off |
| 2 | No offline install path in setup.sh | `setup.sh:23` | Add `--offline` flag, use `stage/binaries/` |
| 3 | `run-kata.sh` is serial bash, not agent-driven | `scripts/run-kata.sh` | Replace with `orchestrate.sh` + `advance-gate.sh` |
| 4 | No issue intake via kata CLI | missing | Use `kata create` directly — agents file issues as katas |
| 5 | No stop-gap mechanism | missing | New `scripts/stop-gap.sh` + `config/stop-gap.yaml` |
| 6 | `ISSUES.md` is template only | `ISSUES.md` | Populate with 5-10 real issues from pallets/click |
| 7 | `scripts/stage-usb.sh` missing | referenced in PREP.md | Create for USB staging |
| 8 | Agent CLI syntax unverified | `agents.sh` | Test against actual `openclaw --help` output |
| 9 | No venv for python deps | `setup.sh` | Create `.venv` for kata, agentgateway, etc. |
| 10 | Evidence collection uses shell templating | `scripts/evidence.sh` | Use kata --agent JSON for real metrics |

---

## P4 — Evidence & Baseline

### [ ] 20. Run walking skeleton
```bash
./scripts/orchestrate.sh &
sleep 5
kata create "[feature] add --timeout flag to Click commands"
# Watch one full kata flow through all 7 gates on the kata board
```

### [ ] 21. Collect evidence
```bash
./scripts/evidence.sh
```
- Currently writes a template to `evidence/evidence-table.md`
- **Enhance**: pull real data from `kata list --agent --json` and agentgateway OTel

### [ ] 22. Baseline comparison
```bash
./scripts/baseline.sh "Add --timeout flag to Click commands"
```
- Currently writes a template to `evidence/baseline/`
- Single agent, no org, same issue
- Compare cycle time, quality, tokens

---

## Files to Create

| File | Purpose |
|------|---------|
| `config/agentgateway.yaml` | Gateway config (referenced, missing) |
| `config/stop-gap.yaml` | Stop-gap thresholds (default: 3 failures, 3 rework loops) |
| `scripts/stop-gap.sh` | Central stop-gap check — polls `[stop]` katas on the board |
| `scripts/orchestrate.sh` | Agent orchestration loop |
| `scripts/advance-gate.sh` | Advance katas through one gate |
| `scripts/stage-usb.sh` | Stage binaries/weights/repos to USB |

## Files to Modify

| File | Change |
|------|--------|
| `scripts/setup.sh` | Add `--offline` flag, venv creation, fix URLs |
| `scripts/run-kata.sh` | Replace with agent orchestration + stop-gap |
| `scripts/serve.sh` | Gate agentgateway.yaml reference behind file existence check |
| `scripts/agents.sh` | Verify CLI syntax matches actual OpenClaw |
| `ISSUES.md` | Populate with real corpus issues (seed data for kata intake) |
| `scripts/evidence.sh` | Real data from kata --agent JSON |

## What's Already Ready (no changes needed)

- **vLLM** — already implemented
- **llama-swap** — already implemented
- **Model weights** — already loaded in `models/` (Phase 1 + Phase 2)
- 7 SOUL.md personas in `config/openclaw/agents/*/SOUL.md`
- `config/openclaw/tools.yaml`
- `config/nemoclaw/blueprint.yaml`
- 4 policy YAMLs (`network.yaml`, `filesystem.yaml`, `process.yaml`, `inference.yaml`)
- `config/llama-swap/config.yaml` (Phase 1 active, Phase 2 commented)
- All role templates in `roles/`
- `kata-board/README.md`
- `GAMEPLAN.md`, `PREP.md`, `README.md`
- `.gitignore`

---

## Build Order (Day-of Execution)

```
09:00 — Hardware setup + rsync stage → GB10
09:15 — Verify vLLM + llama-swap already running (already implemented)
09:30 — Start agentgateway (serve.sh), create missing configs
10:00 — kata init + OpenClaw install
10:30 — NemoClaw install (or fallback)
11:00 — Wire 7 agents, test agent start/stop
11:30 — Create config/agentgateway.yaml, config/stop-gap.yaml
12:00 — Walking skeleton: 1 kata through all gates
12:30 — Seed the kata board: `kata create "[bug] ..."`, run full pipeline
13:00 — Stop-gap test (force a failure, verify halt)
14:00 — Small-sample run (5 katas)
15:00 — Baseline comparison
16:00 — Evidence collection
17:00 — Code freeze
```
