# Software Factory in a Box

A seven-role AI software team running entirely on NVIDIA GB10 Grace Blackwell hardware. A brief goes in; working, tested, documented software comes out. Every model call, every tool call, every byte stays on hardware compliance already approved.

**Zero external network calls.** Your compliance team already approved this box. This is a dev team that never sends a byte outside it.

---

## Quick Start

```bash
# 1. Init kata workspace
cd software-factory
kata init --with-agents

# 2. Setup stack (NemoClaw preferred, fallback chain automated)
./scripts/setup.sh

# 3. Start serving plane (vLLM + llama-swap + agentgateway)
./scripts/serve.sh

# 4. Launch all 7 agent roles
./scripts/agents.sh

# 5. Run a kata through the pipeline
./scripts/run-kata.sh "Add a --timeout flag to Click commands"

# 6. Collect evidence
./scripts/evidence.sh

# 7. Teardown (tailscale logout, remove tokens)
./scripts/teardown.sh
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HUMAN LAYER                                  │
│   Pilot (primary operator)  +  Co-pilot (support, flex-swap)        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     ORCHESTRATION LAYER                              │
│  NemoClaw (preferred) → OpenShell (fallback) → OpenClaw (fallback)  │
│  Blueprints, sandboxes, hardened images, lifecycle management        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                      AGENT LAYER (7 Roles)                          │
│  Tech Lead │ PM │ Architect │ DevOps+QA │ TPM │ Implementers │ Docs │
│  Each role = OpenClaw agent entry (SOUL.md persona + kata rules)     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                    GATEWAY & GOVERNANCE                              │
│  agentgateway: per-role RBAC, LLM budgets, OpenTelemetry            │
│  katatracker: issue tracking as katas on the same board             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                    INFERENCE PLANE                                   │
│  llama-swap (hot-swap) → vLLM on GB10 (local models)               │
│  Fallback: Ollama with doc-named starters                           │
└─────────────────────────────────────────────────────────────────────┘
```

### Stack Fallback Chain

```
NemoClaw + OpenShell + OpenClaw  (full stack, preferred)
        ↓ if NemoClaw fails
OpenShell + OpenClaw              (manual sandbox, manual policies)
        ↓ if OpenShell fails
OpenClaw only                     (no sandbox, host-native, loses RBAC)
```

Only one of NemoClaw, OpenShell, or OpenClaw is required. The setup script automatically tries each in order.

---

## AI Models

### Phase 1: Walking Skeleton — One Small Model

Use a single small model for **all seven roles** to get the end-to-end pipeline working fast.

| Model | Size | Why |
|-------|------|-----|
| **Qwen 3 1.7B** (Q8_0 GGUF) | 1.7B | Fast inference, low memory, gets the skeleton walking |

All 7 roles share this model. The factory works — just slower and less capable.

### Phase 2: Scale Up — Role-Specific Models

After the skeleton walks, swap in role-optimized models:

| Model | Size | Roles |
|-------|------|-------|
| **Gemini 4** (Gemma 3 27B GGUF) | 27B | Tech Lead, PM, TPM, Docs |
| **NVIDIA Nemotron 3 Super** | 120B | Architect, DevOps+QA |
| **Qwen 3.6** (Qwen3 32B GGUF) | 32B | Implementers |

### Model Loading

Models are served via **vLLM** with **llama-swap** providing hot-swap and concurrent model matrix. With 128GB unified memory on GB10, all three can load simultaneously in Phase 2.

### Fallback Chain

```
Phase 1: small model for all roles (fast, works now)
    ↓
Phase 2: role-specific models (better quality, needs more memory)
    ↓
Phase 3: single large model for all roles (if concurrent fails)
```

**Config is in `config/llama-swap/config.yaml`.** Phase 1 models are uncommented and ready; Phase 2 models are commented out, swap in after the skeleton.

---

## The Org Chart

| # | Role | Responsibility | Model (Phase 1 → Phase 2) | Git? | Sandbox? |
|---|------|----------------|---------------------------|------|----------|
| 1 | **Tech Lead** | Human-facing pair partner; intake, final report | small → Gemini 4 | No | No |
| 2 | **Product Manager** | Brief → prioritized katas with acceptance criteria | small → Gemini 4 | No | No |
| 3 | **Software Architect** | Design notes per kata; cohesion/maintainability gate | small → Nemotron | No | No |
| 4 | **DevOps + QA** | Local git management; runs tests in sandbox (network denied) | small → Nemotron | **Yes** | **Yes** |
| 5 | **Technical Project Manager** | Owns kata board: creates, assigns, tracks, unblocks | small → Gemini 4 | No | No |
| 6 | **Software Implementers** | Write the code | small → Qwen 3.6 | No | No |
| 7 | **Docs Engineer** | README/CHANGELOG/config docs after merges | small → Gemini 4 | No | No |

**RBAC enforced by OpenShell policies:** PM can't push code. Only DevOps+QA touches git or the sandbox.

---

## The Kata Board (Message Bus)

No custom queue. Each work item is a kata with stable IDs. State lives in SQLite under `KATA_HOME` — your repo stays clean.

### Issue Lifecycle

```
created → claimed → closed (with --done and evidence)
```

### Commands

```bash
kata init                              # bind workspace
kata create "add CLI timeout flag"     # create issue (prints short id)
kata list                              # list open work
kata show abc4                         # inspect by short id
kata claim abc4                        # claim work
kata close abc4 --done --message "Fixed it" --commit <sha>  # close with evidence
kata tui                               # interactive browser
kata quickstart                        # agent operating contract
```

All commands support `--agent` and `--json` flags for machine-readable output.

---

## Directory Structure

```
software-factory/
├── README.md                          # This file
├── GAMEPLAN.md                        # Locked gameplan
├── PREP.md                            # Night-before checklist
├── ISSUES.md                          # Issue log (katatracker summary)
│
├── config/
│   ├── nemoclaw/                      # NemoClaw blueprints & policies
│   │   ├── blueprint.yaml             # Versioned blueprint
│   │   └── policies/                  # network, filesystem, process, inference
│   ├── openclaw/                      # Agent configs
│   │   ├── agents/                    # 7 SOUL.md persona files
│   │   ├── tools.yaml                 # Tool definitions (kata, git, sandbox)
│   │   └── memory/                    # Persistent agent memory
│   └── llama-swap/
│       └── config.yaml                # Model hot-swap matrix
│
├── models/
│   ├── small/                         # Qwen3 1.7B (Phase 1 — all roles)
│   ├── gemini-4/                      # Gemma 3 27B GGUF (Phase 2)
│   ├── nemotron/                      # Nemotron 3 Super 120B (Phase 2)
│   └── qwen3.6/                       # Qwen3 32B GGUF (Phase 2)
│
├── roles/                             # Role templates & checklists
│   ├── 01-tech-lead/                  # intake + final report
│   ├── 02-product-manager/            # decomposition + AC
│   ├── 03-architect/                  # design notes + cohesion gate
│   ├── 04-devops-qa/                  # git workflow, test runner, QA
│   ├── 05-tpm/                        # board ops + heartbeat
│   ├── 06-implementer/                # coding standards + tests
│   └── 07-docs-engineer/              # README + CHANGELOG templates
│
├── kata-board/                        # The message bus (created by kata init)
│
├── corpus/                            # Target OSS repo (pallets/click)
├── evidence/                          # Evidence table & snapshots
│   ├── baseline/                      # Lone-agent baseline
│   └── factory/                       # Factory run snapshots
├── scripts/                           # setup, serve, agents, run-kata, etc.
└── stage/                             # Pre-staged binaries & weights (USB)
```

---

## Tech Stack

| Component | Role | License | Required? |
|-----------|------|---------|-----------|
| [NemoClaw](https://github.com/NVIDIA/NemoClaw) | Orchestration, blueprints | Apache 2.0 | No (preferred) |
| [OpenShell](https://github.com/NVIDIA/OpenShell) | Sandbox runtime, RBAC | Apache 2.0 | No (fallback) |
| [OpenClaw](https://github.com/openclaw/openclaw) | Agent framework | MIT | Yes (one required) |
| agentgateway | LLM gateway, OTel, budgets | Apache 2.0 | Recommended |
| llama-swap | Model hot-swap, concurrent matrix | Apache 2.0 | Recommended |
| vLLM | Local model serving | Apache 2.0 | Recommended |
| [kata](https://github.com/kenn-io/kata) | Local-first issue tracker (CLI + TUI) | MIT | Required |
| [pallets/click](https://github.com/pallets/click) | Corpus repo (BSD-3) | BSD-3 | Default target |

---

## Evidence Table

The factory produces a quantitative evidence table comparing factory output vs. a lone-agent baseline:

| Metric | Factory | Baseline |
|--------|---------|----------|
| Katas delivered | — | — |
| QA pass rate | — | — |
| Rework loops | — | — |
| Cycle time per kata | — | — |
| Tokens per delivered kata | — | — |
| Human interventions | ~1 (the brief) | — |
| **External network calls** | **0** | 0 |
| Issues filed | — | — |
| Issue resolution time | — | — |

Collect with: `./scripts/evidence.sh`

---

## Work Substrate

Default corpus: **[pallets/click](https://github.com/pallets/click)** (BSD-3, small, fast pytest suite). Override with `CORPUS_REPO=` environment variable.

### Demo Briefs

Realistic maintenance work for `pallets/click`:

1. Add a `--timeout` flag to Click commands with configurable default
2. Fix environment variable override not working on Windows
3. Add type hints to the `core.py` module
4. Improve error messages for invalid parameter types
5. Add a `--version` flag helper to Click groups
6. Write integration tests for the `MultiCommand` class
7. Refactor `utils.py` to reduce cyclomatic complexity
8. Add a `CHANGES.md` documenting recent API changes
9. Fix deprecation warning in Python 3.12 compatibility
10. Add a `--verbose` flag that controls logging level

---

## Day Timeline

| Time | Pilot | Co-pilot |
|------|-------|----------|
| 09:00–09:50 | Power, Ethernet, GB10 setup | rsync stage, Tailscale, verify creds |
| 10:00–10:30 | vLLM + llama-swap + agentgateway | NemoClaw install → verify sandbox |
| 10:30–11:00 | Serve plane debugging | Agent stack debugging |
| 11:00–12:00 | Wire roles (SOUL.md, tools) | Wire roles (SOUL.md, tools) |
| **~12:00** | **Walking skeleton demo** | **Walking skeleton demo** |
| 13:00–15:00 | Small-sample run (5–10 katas) | Baseline runs |
| 15:00–17:00 | Large-sample run | Evidence collection |
| **17:00** | **Code freeze** | **Evidence finalization** |
| 17:00–18:00 | Milestone submission | — |
| If top 8 | 19:00–21:00: build 5-min pitch | — |

---

## 5-Minute Pitch

> Org chart slide → live: brief in, kata board flows across seven roles, QA verifies in a network-denied sandbox, git log + docs diff as receipts → evidence table vs lone-agent baseline → close: **"Your compliance team already approved this box. This is a dev team that never sends a byte outside it."**

---

## Risks

| Risk | Mitigation |
|------|------------|
| NemoClaw install fails on GB10 | Fallback to OpenShell direct |
| OpenShell alpha APIs break | Fallback to OpenClaw only |
| Model swap latency (20GB+ models) | llama-swap concurrent matrix in 128GB |
| Seven roles by noon (two people) | Ruthless thinness first; depth after skeleton |
| Stock vLLM NVFP4 issue on Spark | Ollama fallback staged |

---

## License

This project uses the following open-source components:

- **OpenClaw** — MIT License
- **OpenShell** — Apache License 2.0
- **NemoClaw** — Apache License 2.0
- **vLLM** — Apache License 2.0
- **llama-swap** — Apache License 2.0
- **agentgateway** — Apache License 2.0
- **pallets/click** (corpus) — BSD-3-Clause License

See `docs/licenses.md` for full license texts.
