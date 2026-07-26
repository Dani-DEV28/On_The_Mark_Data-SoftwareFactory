# Dani-PLAN.md — Software Factory MVP Build Plan

> **STATUS 2026-07-26 (evening):** P0–P4 ALL DONE — pipeline verified end-to-end.
> Walking skeleton: kata `asjx` (petri #117) went intake→review PR-ready in 5m20s,
> branch `factory/asjx` passes 526/526 tests. Stop-gap drill verified (per-kata HALT
> rc=2 + incident report; manual [stop] rc=3). `sfai create artifact` live.
> Original status: P0 and P1 DONE (commit 7c9ac2e). Rule change: only
> the LLM must be local — internet calls are allowed, so all air-gap/USB staging
> items are dropped. agentgateway is dropped too (llama-swap routes by model
> name; OpenShell gateway handles sandbox policy). Next: P2 orchestration.

---

## Design Philosophy

The factory follows three principles:

- **Specialized Agents** — Every agent owns one responsibility.
- **Structured Orchestration** — Agents exchange machine-readable YAML task artifacts instead of free-form conversations.
- **Human-in-the-Loop** — The Human Lead remains the final authority for architecture, scope changes, and merge approval.

The factory separates **technical decision-making** from **operational execution**:
- The **Tech Lead** determines *how* software should be built.
- The **TPM** determines *whether* execution is progressing effectively.
- Specialized agents perform focused engineering tasks.
- The **Human Lead** retains final authority over significant technical and product decisions.

## System Architecture

```text
                    Human Lead
                         │
          Technical Direction & Approval
                         │
                  Tech Lead Agent
        (Technical Planning & Delegation)
                         │
        ┌────────────────┴────────────────┐
        │                                 │
 Product Manager                     Technical PM
 Requirements                    Workflow Orchestration
        │                                 │
        └──────────────┬──────────────────┘
                       │
                 Architect (optional)
              (API changes, DB migrations,
               cross-module refactors only)
                       │
                 Implementation
                       │
                  DevOps / QA
                       │
                 Documentation
                       │
                 Pull Request Ready
                       │
                    Human Review
```

## Workflow

```
GitHub Issue
      │
      ▼
Tech Lead Analysis ───→ TPM creates kata on board
      │
      ▼
Product Manager (acceptance criteria, edge cases, task breakdown)
      │
      ▼
Architecture Review (optional — only for API/DB/cross-module changes)
      │
      ▼
Implementation (Implementer)
      │
      ▼
QA Validation (DevOps/QA — never fixes code, only validates)
      │
      ├───────────────┐
      │               │
      ▼               │
Documentation         │
      │               │
      ▼               │
PR Ready              │
                      │
              QA Failure ──→ Tech Lead Review ──→ New Implementation
```

## Agent Responsibilities

| Role | Answers | Key Responsibility |
|------|---------|-------------------|
| Tech Lead | "How should we build this?" | Analyze issues, delegate, review, decide pivots |
| Product Manager | "What exactly needs to be delivered?" | Requirements, AC, edge cases, task breakdown |
| Architect | "Is this the correct design?" | Optional — API changes, DB migrations, refactors |
| DevOps/QA | "Does the implementation pass?" | Tests, lint, formatting, build — never fixes code |
| TPM | "Is the factory making forward progress?" | Board, heartbeat, retries, deadlock detection, stop conditions |
| Implementer | "Can I implement this?" | Code, tests, refactor — never plans architecture |
| Docs Engineer | "Is the change documented?" | README, CHANGELOG, API docs — only after QA passes |

## Agent Communication

Agents exchange **structured YAML task artifacts** instead of conversational context:

```yaml
# Example task passed between agents
task:
  title: Implement OAuth refresh token support

acceptance_criteria:
  - Existing login flow remains functional
  - Refresh token expires correctly
  - Unit tests pass

affected_files:
  auth/
  tests/auth/

constraints:
  No breaking API changes
```

```yaml
# Example completion artifact
status: Complete

summary:
  Refresh token support implemented.

artifacts:
  Patch
  Tests
  Notes

next_agent: QA
```

This approach reduces prompt drift and improves reproducibility across model swaps.

---

Target: **NVIDIA GB10 (DGX Spark)** — Linux/aarch64  
Stack fallback: NemoClaw → OpenShell → OpenClaw  
Corpus: `onthemarkdata/petri`  
CLI: `sfai -repo <url> run` — entry point for the factory  
CLI: `sfai create artifact -p "prompt" [-t tag]` — Tech Lead builds HTML visualization  
Pipeline: `sfai run` → fetch issues → Tech Lead analyzes → TPM creates katas → agents fix → close (with stop-gap)

---

## P0 — Staging & Prep (done off-GB10, on laptop before hackathon)

### [x] 1. Confirm model weights on GB10 — DONE (no ~1.7B small model and no gemini-4 on disk; available: nemotron-nano-30b, nemotron-super-120b, qwen3.6-27b, qwen3.6-35b-a3b-fp8, bge-large)
- Models already loaded into `models/` on GB10
- Phase 1 small model (~1.7B) available for walking skeleton
- Phase 2 models (gemini-4, nemotron, qwen3.6) also loaded

### [x] 2. Clone corpus repo — DONE (`corpus/` = petri clone on GB10)
```bash
git clone https://github.com/onthemarkdata/petri.git corpus/
```
- `corpus/` is currently empty (`.gitkeep` only)
- The petri repo is both the source of issues AND the target to fix

### [x] 3. Binaries — DONE, simplified (internet allowed; installed directly: kata v0.12.1 from kenn-io/kata release binary — NOT the abandoned PyPI `kata` package — and openclaw via npm; agentgateway dropped)
| Binary | Source | Target |
|--------|--------|--------|
| `kata` | `pip install kata` | `stage/binaries/kata` |
| `openclaw` | `npm install -g openclaw` or `pip install openclaw` | `stage/binaries/openclaw` |
| `agentgateway` | GH release | `stage/binaries/agentgateway` |

- vLLM and llama-swap already implemented — skip staging those
- `stage/binaries/`, `stage/repos/`, `stage/weights/` are otherwise empty

### [—] 4. ~~Create `scripts/stage-usb.sh`~~ — DROPPED (no air-gap requirement)
- Script referenced in `PREP.md` but does not exist
- Should rsync everything to a USB drive for air-gapped transfer to GB10

---

## P0 — Platform Setup (on GB10, day-of)

### [x] 5. Hardware & network — DONE via Tailscale (venue Wi-Fi isolates clients in both directions; hotspot NAT also fails — tailnet is the reliable path)
- GB10 powered, Ethernet connected
- Tailscale auth key ready (or phone hotspot)
- `rsync` stage folder to GB10

### [x] 6. Verify inference plane — DONE (llama-swap v243 + vLLM containers on :9292 serving all 4 models; Qwen3.6 needs `vllm/vllm-openai:latest` — its qwen3_5_moe arch is too new for the NVIDIA 26.01 image, which still serves the Nemotrons)
- vLLM and llama-swap already implemented — confirm they're running
- **Known gap**: `serve.sh` references `config/agentgateway.yaml` — file does not exist
- **Fix needed**: Create `config/agentgateway.yaml` or remove the reference

### [x] 7. Install kata CLI & init board — DONE (board live; smoke kata + 89 petri issues loaded)
```bash
pip install kata
kata init --with-agents
```
- Creates `kata-board/` SQLite DB and `.kata.toml`

### [x] 8. Install OpenClaw — DONE (host CLI via npm; sandbox runs OpenClaw 2026.5.27 via NemoClaw)
```bash
npm install -g openclaw   # preferred
# or
pip install openclaw      # fallback
```
- Core agent framework — all 7 agents run on this
- `setup.sh` tries NemoClaw first, then OpenShell, then OpenClaw

### [—] 9. ~~Create `config/agentgateway.yaml`~~ — DROPPED (agentgateway removed from serve.sh; llama-swap routes by model name, OpenShell gateway covers policy)
- Referenced by `serve.sh` but missing
- Minimal config: localhost endpoint, OTel disabled for MVP, per-role model routing

### [x] 10. Create `scripts/sfai.sh` CLI tool — DONE (run/status/create artifact/help; `run` fetches GitHub issues → creates katas; `create artifact` invokes Tech Lead to build HTML visualization)
- Bash script — single entry point for the factory
- Usage: `./sfai.sh -repo "https://github.com/onthemarkdata/petri" run`
- Usage: `./sfai.sh create artifact -p "Show current progress" -t "progress-dashboard"`
- Subcommands: `run`, `status`, `create artifact`, `help`
- MVP: simple bash, expandable later

---

## P1 — Stack Setup: NemoClaw / OpenShell / OpenClaw

### [x] 11. NemoClaw — DONE. Working invocation (NOT `--provider ollama`):
```bash
NEMOCLAW_ONBOARD_VALIDATION_TIMEOUT_SECONDS=300 NEMOCLAW_PROVIDER=custom \
NEMOCLAW_ENDPOINT_URL=http://172.18.0.1:9292/v1 NEMOCLAW_MODEL=qwen3.6-35b-a3b-fp8 \
COMPATIBLE_API_KEY=unused nemoclaw onboard --non-interactive -y --no-gpu --name local-pm-os-agent
```
Gotchas: endpoint must use the docker-bridge IP (localhost inside a sandbox is the sandbox); pre-warm the model first — validation times out during a cold llama-swap model load.
```bash
nemoclaw onboard --non-interactive --provider ollama
```
- Uses `config/nemoclaw/blueprint.yaml` — already defined with all 7 agents
- Automatically provisions OpenShell sandbox + OpenClaw agents
- **Policy files already ready**: `network.yaml`, `filesystem.yaml`, `process.yaml`, `inference.yaml`

### [—] 12. Fallback: OpenShell direct — NOT NEEDED (preferred path works)
```bash
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh
```
- Manual sandbox + RBAC policies (translate from NemoClaw format)
- No blueprint verification; loses NemoClaw lifecycle management

### [—] 13. Fallback: OpenClaw only — NOT NEEDED
```bash
openclaw agent start --name <role> --soul <path> --model auto
```
- No sandbox, no RBAC — agents run natively on host
- **Script gap**: `agents.sh` uses this syntax — needs verification against actual OpenClaw CLI

### [x] 14. Wire all 7 agents — DONE (7/7 via rewritten agents.sh using the real CLI `openclaw agents add <name> --model inference/qwen3.6-35b-a3b-fp8 --workspace ... --non-interactive`; the old `openclaw agent start --soul` syntax does not exist). All roles on qwen3.6-35b-a3b-fp8 — mixed per-role models would thrash llama-swap (one model loaded at a time, ~minutes per swap)
- SOUL.md files ready: `tech-lead`, `product-manager`, `architect`, `devops-qa`, `tpm`, `implementer`, `docs-engineer`
- `config/openclaw/tools.yaml` defines available tools (kata, git, sandbox, fs)
- **Verify**: each agent can start, list katas, and claim work

### [x] 15. Fix `setup.sh` — DONE, simplified (no air-gap: verified install path, venv, correct corpus URL, correct onboarding env vars)
- Current: `curl https://www.nvidia.com/nemoclaw.sh | bash` (requires internet)
- **Need**: `--offline` flag that uses staged binaries from `stage/`
- **Need**: venv creation for python tools (kata, agentgateway)
- **Need**: fallback chain that doesn't require external DNS

---

## P2 — MVP Pipeline: Issue Review → Fix

### [x] 16. Issue intake via GitHub API — DONE (sfai run imports issues with full bodies + idempotency keys; Tech Lead analysis happens at the intake gate)
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
| Prefix | Type | Pipeline |
|--------|------|----------|
| `[bug]` | Bug fix | Tech Lead → Implementer → QA → Docs → PR |
| `[feature]` | New feature | Tech Lead → PM → Architect (optional) → Implementer → QA → Docs → PR |
| `[issue]` | Problem found | Tech Lead → TPM triages → routes to appropriate agent |
| `[spike]` | Investigation | Tech Lead → Architect |
| `[docs]` | Documentation | Docs Engineer |
| `[stop]` | Manual stop-gap | TPM halts pipeline |
| `[artifact]` | Visualization | Tech Lead produces HTML artifact |

### [x] 17. Stop conditions & Factory Incident Report — DONE & DRILL-TESTED (config/stop-gap.yaml per spec; stop-gap.sh: 0=PASS, 2=per-kata HALT+quarantine+report, 3=manual [stop] full stop; incident report verified against spec fields)
**The TPM enforces stop conditions** — not the Tech Lead. The TPM continuously monitors execution and halts when predefined operational limits are reached.

**Stop conditions config**: `config/stop-gap.yaml`
```yaml
stop_conditions:
  max_attempts: 5            # total retries on a kata
  max_runtime: 45m           # wall-clock limit per kata
  no_progress_cycles: 4      # heartbeat ticks with no status change
  identical_failures: 3      # same QA failure repeated
  max_failed_agents: 2       # distinct agents that have failed
```

**Central stop-gap module**: `scripts/stop-gap.sh`

```bash
./scripts/stop-gap.sh check --kata <id>
# Returns: PASS | FAIL | HALT (with reason)
```

When execution stops, the TPM generates a **Factory Incident Report**:

```yaml
Factory Incident Report

Issue:
  #<kata-id>

Status:
  Stopped

Reason:
  Retry budget exceeded

Attempts:
  5

Elapsed:
  38 minutes

Agents:
  Tech Lead
  Product Manager
  Architect
  Implementer
  QA

Timeline:
  Analysis Complete
  Planning Complete
  Architecture Complete
  Implementation Attempt 1
  QA Failed
  Retry
  QA Failed
  Retry
  QA Failed

Observed Errors:
  Circular dependency
  Migration timeout
  Authentication regression

Repeated Failure:
  tests/auth/test_refresh.py

Artifacts:
  QA logs
  Patch diff
  Test results
  Architecture notes

Recommendation:
  Human intervention required.
```

This report provides the Human Lead with a complete audit trail of what the swarm attempted before halting.

### [x] 18. Agent orchestration — DONE (scripts/orchestrate.sh + advance-gate.sh + scripts/factory/factory.py: TPM pull model over kata labels gate:*, YAML artifacts in evidence/artifacts/<kata>/ mirrored as kata comments, Architect gated on needs-architect, QA runs targeted + FULL suite and never fixes code)
**Replace `run-kata.sh`** with a TPM-driven pull model. Agents exchange structured YAML task artifacts.

**Workflow order** (each step advances kata status on the board):

```
GitHub Issue
      │
      ▼
Tech Lead (analyzes → produces task artifact → delegates)
      │
      ▼
TPM (creates kata on board from Tech Lead's analysis)
      │
      ▼
PM (acceptance criteria, edge cases, sub-tasks)
      │
      ▼
Architect (optional — only if scope triggers it)
      │
      ▼
Implementer (code + tests, guided by task artifact)
      │
      ▼
DevOps/QA (tests, lint, build — never fixes code)
      │
      ├───────────────┐
      │               │
      ▼               │
Documentation         │
      │               │
      ▼               │
PR Ready              │
                      │
              QA Failure ──→ Tech Lead Review ──→ New task artifact ──→ Implementer retry
```

**Pull model** — the kata board is the organizing backbone. All agents use `kata` CLI to find, claim, and advance work:

1. **TPM heartbeat** runs every 5min: `kata list --agent --json` → inspects all statuses, checks for stalled items, enforces stop conditions, runs deadlock detection
2. **Tech Lead** polls `intaken` → analyzes issue, produces YAML task artifact, delegates to TPM
3. **TPM** creates katas from Tech Lead's delegation, sets status to `scoped`
4. **PM** polls `scoped` → writes AC and sub-tasks, advances to `designed`
5. **Architect** polls `designed` (only if scope label present) → design notes or skip, advances to `implementing`
6. **Implementer** polls `implementing` → reads task artifact, writes code + tests with `kata claim`, advances to `qa`
7. **DevOps/QA** polls `qa` → runs tests with `sandbox exec`, advances to `documenting` or files `[issue]` kata back to Tech Lead
8. **Docs** polls `documenting` → writes docs with `kata claim`, advances to `review`
9. **Human** reviews PR, closes kata

**Stop-gap check** at every transition — TPM monitors all conditions.

**Orchestrator script**: `scripts/orchestrate.sh`
```bash
# Main loop
while true; do
  ./scripts/advance-gate.sh --gate intake    # Tech Lead
  ./scripts/advance-gate.sh --gate scoped    # PM
  ./scripts/advance-gate.sh --gate designed  # Architect (optional)
  ./scripts/advance-gate.sh --gate implement # Implementer
  ./scripts/advance-gate.sh --gate qa        # DevOps/QA
  ./scripts/advance-gate.sh --gate docs      # Docs
  ./scripts/stop-gap.sh check                # TPM checks all conditions
  sleep 60
done
```

### [x] 19. End-to-end pipeline — DONE (sfai run → intake → orchestrate; verified on kata asjx: 7 gates, PR-ready branch factory/asjx, 526/526 tests)
```bash
# Single command does it all:
./sfai.sh -repo "https://github.com/onthemarkdata/petri" run
```
What `sfai run` does:
1. Clones petri to `corpus/` if not present
2. Fetches open issues from GitHub Issues API
3. Tech Lead analyzes each issue → produces YAML task artifact
4. TPM creates katas on the board from Tech Lead's delegation
5. Agents flow through: PM → Architect(opt) → Implementer → QA → Docs
6. TPM monitors heartbeat, enforces stop conditions at every gate
7. On halt: TPM generates Factory Incident Report
8. Prints summary when all katas are done or stopped

### [x] 20. Tech Lead artifact creation — DONE (sfai create artifact -p "..." -t tag → self-contained dark-theme HTML in evidence/artifacts/<tag>-<ts>.html; [artifact] katas excluded from code intake; SKILL_*.md files now feed agent prompts)
**The Tech Lead produces visual HTML documents** on demand via:

```bash
./sfai.sh create artifact -p "Show current progress of all open katas" -t "progress-dashboard"
```

Flow:
1. `sfai` gathers context (kata board state, git log, corpus diff stats)
2. Sends context + user prompt to the Tech Lead's model via llama-swap
3. Tech Lead generates a self-contained HTML document (offline-ready, dark theme, embedded CSS/JS, no external deps)
4. Output saved to `evidence/artifacts/<tag>-<timestamp>.html`

Tech Lead SOUL.md updated to include artifact creation as a core responsibility.

### [x] 21. TPM checkpoints — DONE (stop-gap check runs after every gate in the orchestrate loop; gate transitions only happen on validated artifacts)
Checkpoint at each stage transition — TPM evaluates before allowing advance:
- `intaken → scoped`: Tech Lead analysis complete, task artifact valid?
- `scoped → designed`: PM acceptance criteria defined?
- `designed → implementing`: Architect sign-off (or skip)?
- `implementing → qa`: Code compiles, tests written?
- `qa → documenting`: All tests pass?
- `qa → failed`: QA failure — Tech Lead reviews, produces new task artifact
- `documenting → review`: Docs written?
- `review → done`: Human approved PR merge?

---

## P3 — Fix Project Issues

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 1 | Workflow skips Tech Lead analysis | `sfai.sh`, `orchestrate.sh` | Tech Lead must analyze each issue first, produce YAML task artifact, then TPM creates katas |
| 2 | Architect always-on but should be optional | `orchestrate.sh` | Gate Architect behind scope check (API/DB/cross-module) |
| 3 | Agent communication is unstructured | `orchestrate.sh` | Agents exchange structured YAML task artifacts, not free-form text |
| 4 | TPM lacks operational scope | `scripts/stop-gap.sh` | TPM owns: retry budgets, deadlock detection, Factory Incident Report |
| 5 | Stop conditions too simple | `config/stop-gap.yaml` | Replace with comprehensive `stop_conditions` (max_attempts, max_runtime, no_progress_cycles, identical_failures, max_failed_agents) |
| 6 | No Factory Incident Report on halt | TPM module | TPM generates full audit trail when execution stops |
| 7 | `run-kata.sh` is serial bash, not agent-driven | `scripts/run-kata.sh` | Replace with TPM-driven pull model |
| 8 | `ISSUES.md` is template only | `ISSUES.md` | Populate with 5-10 real issues from onthemarkdata/petri |
| 9 | Agent CLI syntax unverified | `agents.sh` | Test against actual `openclaw --help` output |
| 10 | Evidence collection uses shell templating | `scripts/evidence.sh` | Use kata --agent JSON for real metrics |

---

## P4 — Evidence & Baseline

### [x] 22. Walking skeleton — DONE (asjx: intake 22:41:30 → PR-ready 22:46:50; Architect correctly skipped; zero regressions)
```bash
./sfai.sh -repo "https://github.com/onthemarkdata/petri" run
# Watch the pipeline: fetch issues → create katas → agents fix petri → close
```

### [x] 23. Collect evidence — DONE (evidence.sh → evidence/evidence-table.md from kata timelines + evidence/usage.jsonl token/latency log; no agentgateway needed)
```bash
./scripts/evidence.sh
```
- Currently writes a template to `evidence/evidence-table.md`
- **Enhance**: pull real data from `kata list --agent --json` and agentgateway OTel

### [x] 24. Baseline comparison — DONE (baseline.sh --kata <id>: single generalist agent, no gates, branch baseline/<id>; results in evidence/baseline/)
```bash
./scripts/baseline.sh -repo "https://github.com/onthemarkdata/petri"
```
- Single agent, no org, same issues
- Compare cycle time, quality, tokens vs factory

---

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/sfai.sh` | **Main CLI tool** — `sfai -repo <url> run` + `sfai create artifact -p "..."` |
| `config/stop-gap.yaml` | Stop conditions (max_attempts: 5, max_runtime: 45m, etc.) |
| `scripts/stop-gap.sh` | TPM stop condition checks + Factory Incident Report generation |
| `scripts/orchestrate.sh` | TPM-driven agent orchestration loop |
| `scripts/advance-gate.sh` | Advance katas through one gate with YAML task artifacts |
| `evidence/artifacts/` | Output directory for Tech Lead HTML visualizations (created by sfai) |

## Files to Modify

| File | Change |
|------|--------|
| `scripts/sfai.sh` | Add Tech Lead analysis step before TPM kata creation; produce YAML task artifacts |
| `scripts/run-kata.sh` | Replace with orchestrate.sh + TPM pull model + stop conditions |
| `scripts/orchestrate.sh` | Implement new workflow order (Tech Lead → PM → Architect opt → Impl → QA → Docs); structured YAML artifacts; Architect gating |
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
11:30 — Build `scripts/sfai.sh` CLI, create config/stop-gap.yaml
11:45 — Test: `./sfai.sh create artifact -p "Show current board state" -t "test"`
12:00 — Walking skeleton: `./sfai.sh -repo "https://github.com/onthemarkdata/petri" run`
12:30 — Verify: issues fetched, katas created, agents fixing petri
13:00 — Stop-gap test (force a failure, verify halt)
13:30 — Tech Lead artifact: `./sfai.sh create artifact -p "Progress report" -t "daily"`
14:00 — Small-sample run (sfai on petri with 5 katas)
15:00 — Baseline comparison
16:00 — Evidence collection
17:00 — Code freeze
```
