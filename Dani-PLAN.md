# Dani-PLAN.md — Software Factory MVP Build Plan

Target: **NVIDIA GB10 (DGX Spark)** — Linux/aarch64  
Stack fallback: NemoClaw → OpenShell → OpenClaw  
Corpus: `onthemarkdata/petri`  
CLI: `sfai -repo <url> run` — single entry point for the factory  
Pipeline: `sfai run` → fetch issues → create katas → agents fix → close (with stop-gap)

---

## P0 — Staging & Prep (done off-GB10, on laptop before hackathon)

### [ ] 1. Confirm model weights on GB10
- Models already loaded into `models/` on GB10
- Phase 1 small model (~1.7B) available for walking skeleton
- Phase 2 models (gemini-4, nemotron, qwen3.6) also loaded

### [ ] 2. Clone corpus repo
```bash
git clone https://github.com/onthemarkdata/petri.git corpus/
```
- `corpus/` is currently empty (`.gitkeep` only)
- The petri repo is both the source of issues AND the target to fix

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

### [ ] 10. Create `scripts/sfai.sh` CLI tool
- Bash script — single entry point for the factory
- Usage: `./sfai.sh -repo "https://github.com/onthemarkdata/petri" run`
- Subcommands: `run`, `status`, `help`
- MVP: simple bash, expandable later

---

## P1 — Stack Setup: NemoClaw / OpenShell / OpenClaw

### [ ] 11. Attempt NemoClaw (preferred)
```bash
nemoclaw onboard --non-interactive --provider ollama
```
- Uses `config/nemoclaw/blueprint.yaml` — already defined with all 7 agents
- Automatically provisions OpenShell sandbox + OpenClaw agents
- **Policy files already ready**: `network.yaml`, `filesystem.yaml`, `process.yaml`, `inference.yaml`

### [ ] 12. Fallback: OpenShell direct
```bash
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh
```
- Manual sandbox + RBAC policies (translate from NemoClaw format)
- No blueprint verification; loses NemoClaw lifecycle management

### [ ] 13. Fallback: OpenClaw only
```bash
openclaw agent start --name <role> --soul <path> --model auto
```
- No sandbox, no RBAC — agents run natively on host
- **Script gap**: `agents.sh` uses this syntax — needs verification against actual OpenClaw CLI

### [ ] 14. Wire all 7 agents
- SOUL.md files ready: `tech-lead`, `product-manager`, `architect`, `devops-qa`, `tpm`, `implementer`, `docs-engineer`
- `config/openclaw/tools.yaml` defines available tools (kata, git, sandbox, fs)
- **Verify**: each agent can start, list katas, and claim work

### [ ] 15. Fix `setup.sh` for air-gapped GB10
- Current: `curl https://www.nvidia.com/nemoclaw.sh | bash` (requires internet)
- **Need**: `--offline` flag that uses staged binaries from `stage/`
- **Need**: venv creation for python tools (kata, agentgateway)
- **Need**: fallback chain that doesn't require external DNS

---

## P2 — MVP Pipeline: Issue Review → Fix

### [ ] 16. Issue intake via GitHub API on petri repo
**Issues come from the petri repo's GitHub Issues API.** The `sfai` CLI fetches them and creates katas.

`sfai run` flow:
1. Clone/fetch `https://github.com/onthemarkdata/petri` into `corpus/`
2. Call `GET https://api.github.com/repos/onthemarkdata/petri/issues` to fetch open issues
3. For each issue, create a kata: `kata create "[bug] <title from GitHub>"`
4. The kata board now holds all issues as work items

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

### [ ] 17. Implement stop-gap mechanism
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

### [ ] 18. Build agent orchestration
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

### [ ] 19. Wire end-to-end pipeline
```bash
# Single command does it all:
./sfai.sh -repo "https://github.com/onthemarkdata/petri" run
```
What `sfai run` does:
1. Clones petri to `corpus/` if not present
2. Fetches open issues from GitHub Issues API
3. Creates katas: `kata create "[bug] <title>"`
4. Starts agent orchestration loop (agents claim, fix, test, close)
5. Runs stop-gap checks at each transition
6. Prints summary when all katas are done

### [ ] 20. Add stop-gap checkpoints
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
| 6 | `ISSUES.md` is template only | `ISSUES.md` | Populate with 5-10 real issues from onthemarkdata/petri |
| 7 | `scripts/stage-usb.sh` missing | referenced in PREP.md | Create for USB staging |
| 8 | Agent CLI syntax unverified | `agents.sh` | Test against actual `openclaw --help` output |
| 9 | No venv for python deps | `setup.sh` | Create `.venv` for kata, agentgateway, etc. |
| 10 | Evidence collection uses shell templating | `scripts/evidence.sh` | Use kata --agent JSON for real metrics |

---

## P4 — Evidence & Baseline

### [ ] 21. Run walking skeleton
```bash
./sfai.sh -repo "https://github.com/onthemarkdata/petri" run
# Watch the pipeline: fetch issues → create katas → agents fix petri → close
```

### [ ] 22. Collect evidence
```bash
./scripts/evidence.sh
```
- Currently writes a template to `evidence/evidence-table.md`
- **Enhance**: pull real data from `kata list --agent --json` and agentgateway OTel

### [ ] 23. Baseline comparison
```bash
./scripts/baseline.sh -repo "https://github.com/onthemarkdata/petri"
```
- Single agent, no org, same issues
- Compare cycle time, quality, tokens vs factory

---

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/sfai.sh` | **Main CLI tool** — `sfai -repo <url> run` entry point |
| `config/agentgateway.yaml` | Gateway config (referenced, missing) |
| `config/stop-gap.yaml` | Stop-gap thresholds (default: 3 failures, 3 rework loops) |
| `scripts/stop-gap.sh` | Central stop-gap check — polls `[stop]` katas on the board |
| `scripts/orchestrate.sh` | Agent orchestration loop |
| `scripts/advance-gate.sh` | Advance katas through one gate |
| `scripts/stage-usb.sh` | Stage binaries/weights/repos to USB |

## Files to Modify

| File | Change |
|------|--------|
| `scripts/sfai.sh` | **Create** — main CLI entry point for the factory |
| `scripts/setup.sh` | Add `--offline` flag, venv creation, fix URLs |
| `scripts/run-kata.sh` | Replace with orchestrate.sh + stop-gap + sfai integration |
| `scripts/serve.sh` | Gate agentgateway.yaml reference behind file existence check |
| `scripts/agents.sh` | Verify CLI syntax matches actual OpenClaw |
| `ISSUES.md` | Populate with 5-10 real issues from onthemarkdata/petri |
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
09:15 — Verify vLLM + llama-swap already running
09:30 — Start agentgateway (serve.sh), create missing configs
10:00 — kata init + OpenClaw install
10:30 — NemoClaw install (or fallback)
11:00 — Wire 7 agents, test agent start/stop
11:30 — Build `scripts/sfai.sh` CLI, create config/agentgateway.yaml, config/stop-gap.yaml
12:00 — Walking skeleton: `./sfai.sh -repo "https://github.com/onthemarkdata/petri" run`
12:30 — Verify: issues fetched, katas created, agents fixing petri
13:00 — Stop-gap test (force a failure, verify halt)
14:00 — Small-sample run (sfai on petri with 5 katas)
15:00 — Baseline comparison
16:00 — Evidence collection
17:00 — Code freeze
```
