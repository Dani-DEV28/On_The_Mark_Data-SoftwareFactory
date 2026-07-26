# GAMEPLAN.md — Software Factory in a Box

*Concept locked July 25. Team entry (pilot + co-pilot). This file is a plan — all implementation happens on the day (rule 01).*

## The Product

A software factory in a box — a seven-role AI software team running entirely on the GB10, for regulated-industry engineering teams where cloud AI is banned. A brief goes in; working, tested, documented software comes out. Every model call, every tool call, every byte stays on hardware compliance already approved.

## Org Chart

Each role = an OpenClaw agent entry (persona prompt + kata claim rules). Two human operators flex-swap across roles.

| # | Role | Responsibility | Model |
|---|------|----------------|-------|
| 1 | Tech Lead | Human-facing pair partner; intake, final report | small → Gemini 4 |
| 2 | Product Manager | Brief → prioritized katas with acceptance criteria | small → Gemini 4 |
| 3 | Software Architect | Design notes per kata; cohesion/maintainability gate | small → Nemotron |
| 4 | DevOps + QA | Local git management; runs tests in sandbox (network denied) | small → Nemotron |
| 5 | Technical Project Manager | Owns the kata board: creates, assigns, tracks, unblocks | small → Gemini 4 |
| 6 | Software Implementers | Write the code | small → Qwen 3.6 |
| 7 | Docs Engineer | README/CHANGELOG/config docs after merges | small → Gemini 4 |

## Agent Stack

```
NemoClaw (orchestrator, blueprints, single-command install)
  └─► OpenShell (sandbox runtime, policy engine, RBAC)
        └─► OpenClaw (agent framework — SOUL.md config, tools, memory)
```

**Three deployment paths (one required, fallback to next):**

| Path | What you get | When to use |
|---|---|---|
| **NemoClaw** (preferred) | One command installs OpenShell + OpenClaw in hardened sandbox | Default. Fastest setup on GB10. |
| **OpenShell direct** | Manual sandbox + policies, no blueprint verification | NemoClaw bug or won't install |
| **OpenClaw only** | Run natively on host, no sandboxing | Both NemoClaw and OpenShell fail |

## Inference & Governance Plane

```
OpenClaw agents ──► OpenShell sandbox ──► agentgateway ──► llama-swap ──► vLLM on GB10
  (per-role SOUL.md)    (policy, RBAC)     (OTel, budgets)    (hot-swap)    (local models)
       ▲
       │ orchestrated by
    NemoClaw (blueprints, lifecycle, hardened image)
```

- **vLLM** serves models; **llama-swap** puts them behind one OpenAI-compatible endpoint with hot-swap / concurrent-model matrix
- **agentgateway** (Apache-2.0) fronts everything: per-role LLM budgets, MCP gateway for tools with **per-role RBAC** (PM can't push code; only DevOps+QA touches git or sandbox), and **OpenTelemetry** on every call
- Fallback inference route: Ollama with doc-named starters (staged)
- Declared OSS stack: NemoClaw, OpenClaw, OpenShell, kata, llama-swap, agentgateway, vLLM, corpus repo + licenses

## The Spine: Kata Board as Message Bus

No custom queue. Each work item is a kata; statuses are the stage gates:

```
briefed → scoped → designed → in-progress → in-review → documented → done
```

Each role polls/claims katas at its gate, writes its artifact, advances the status. TPM's heartbeat (OpenClaw cron) is the factory clock. The board is both the coordination mechanism and the demo visual.

## Issue Tracking (katatracker)

Issues are filed as special katas on the same board:

| Kata Type | Purpose | Lifecycle |
|-----------|---------|-----------|
| `feature` | Normal work item | briefed → done |
| `issue` | Bug, blocker, rework | identified → closed |
| `spike` | Investigation / research | identified → closed |

TPM triages issues at standup. katatracker `--agent` JSON feeds the evidence table. No separate tracker needed — the board is the bus.

## Work Substrate

A famous permissive OSS repo — default: **`pallets/click`** (BSD-3, small, fast pytest suite; override with `CORPUS_REPO=`). Demo briefs are realistic maintenance work. Declare repo + license in the writeup.

## Build Order

### Phase 1: Walking Skeleton (target ~noon)
1. **09:00–09:50:** Physical setup (power, Ethernet, Tailscale, rsync)
2. **10:00:** Stack install (NemoClaw preferred → fallback chain)
3. **10:00–10:30:** Parallel — pilot: serving plane; co-pilot: agent stack
4. **10:30–11:00:** Decision gate: which stack path works?
5. **11:00–12:00:** Wire up 7 roles with SOUL.md
6. **~12:00:** ONE kata flows through all 7 gates

### Phase 2: Small-Sample Run
7. 5–10 katas through the floor
8. First evidence snapshot
9. Issue tracking via katatracker activated

### Phase 3: Iterate Depth
10. Parallel implementers
11. Architect rejection loop
12. QA fail → rework path
13. Richer PM decomposition

### Phase 4: Large-Sample Run
14. 15+ katas through the floor
15. Full evidence table
16. Baseline comparison (same briefs → lone agent, no org)

### Phase 5: Freeze & Submit
17. **17:00** — Code freeze, 1 hr buffer
18. **17:00–18:00** — Write milestone submission (evidence-led)
19. **18:00** — Submit
20. **If top 8:** 19:00–21:00 → build 5-min pitch

## Day Timeline

| Time | Pilot | Co-pilot |
|------|-------|----------|
| 09:00–09:50 | Power, Ethernet, GB10 setup | rsync stage folder, Tailscale, verify credentials |
| 10:00–10:30 | vLLM + llama-swap + agentgateway | NemoClaw install → verify sandbox |
| 10:30–11:00 | Serve plane debugging | Agent stack debugging |
| 11:00–12:00 | Wire roles (SOUL.md, tools) | Wire roles (SOUL.md, tools) |
| 12:00 | Walking skeleton demo | Walking skeleton demo |
| 12:00–13:00 | Lunch + status check | Lunch + status check |
| 13:00–15:00 | Small-sample run (5-10 katas) | Baseline runs |
| 15:00–17:00 | Large-sample run | Evidence collection |
| 17:00–18:00 | Milestone submission | Evidence table finalization |

## Evidence Plan

| Metric | Factory | Baseline (lone agent) |
|--------|---------|----------------------|
| Katas delivered | — | — |
| QA pass rate | — | — |
| Rework loops | — | — |
| Cycle time per kata | — | — |
| Tokens per delivered kata | — | — |
| Human interventions | ~1 (the brief) | — |
| **External network calls** | **0** | 0 |
| Issues filed | — | — |
| Issue resolution time | — | — |

## 5-Minute Pitch Shape

Org chart slide → live: brief in, kata board flows across seven roles, QA verifies in a network-denied sandbox, git log + docs diff as receipts → evidence table vs lone-agent baseline → close: *"Your compliance team already approved this box. This is a dev team that never sends a byte outside it."*

## Risks

| Risk | Mitigation |
|------|------------|
| NemoClaw k3s bug #878 on GB10 | PREP.md troubleshooting ladder; fallback to OpenShell direct |
| OpenShell alpha APIs break | Fallback to OpenClaw only (loses sandboxing, keeps factory) |
| Two-person coordination overhead | Clear phase ownership; pilot = serving, co-pilot = agents |
| Model swap latency (20GB+ models) | llama-swap concurrent matrix in 128GB unified memory |
| llama-swap/agentgateway droppable | Collapses to "vLLM serves one model" / "roles call directly" |
| Stock vLLM NVFP4 issue on Spark | Ollama fallback stays staged |
| Seven thin roles by noon | Ruthless thinness first; depth after skeleton walks |

## Tonight (Allowed Prep)

- [ ] Run `./stage-usb.sh`
- [ ] Download model weights (all three)
- [ ] Confirm corpus repo choice (`pallets/click`)
- [ ] Pre-generate Tailscale auth key; phone hotspot ready
- [ ] HF token + NGC key
- [ ] Pack: laptop, charger, power strip, USB-C→Ethernet + cable
- [ ] Confirm second person's laptop/accessories
- [ ] Pair-programming setup tested
