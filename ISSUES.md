# ISSUES — Real work items from onthemarkdata/petri

Live board: run `kata list` (89 petri issues imported; `kata show <id>` for full context).
These are representative non-epic items the factory works on, in rough size order:

| kata | GitHub | Title | Why it's factory-suitable |
|------|--------|-------|---------------------------|
| `asjx` | [#117](https://github.com/onthemarkdata/petri/issues/117) | Wire `petri --version` into the CLI | Small, self-contained — the walking-skeleton kata |
| `p8s3` | [#96](https://github.com/onthemarkdata/petri/issues/96) | Archive merged worktrees and record corpus provenance | Clear AC, single module |
| `zgx5` | [#91](https://github.com/onthemarkdata/petri/issues/91) | Compute edge-intelligence metrics from the dish graph | Well-scoped compute + tests |
| `chbm` | [#90](https://github.com/onthemarkdata/petri/issues/90) | Extend the edge registry with dish-level graph queries | API addition — triggers the Architect gate |
| `zm67` | [#92](https://github.com/onthemarkdata/petri/issues/92) | Surface edge intelligence in CLI and dashboard | Cross-module — triggers the Architect gate |
| `v9z7` | [#93](https://github.com/onthemarkdata/petri/issues/93) | Opt-in convergence-point priority in grow scheduling | Feature with edge cases for the PM |
| `amxp` | [#94](https://github.com/onthemarkdata/petri/issues/94) | Add a read-only Analyst for research-health flags | New agent role in petri itself |
| `t8tj` | [#87](https://github.com/onthemarkdata/petri/issues/87) | Add the re-decomposition approval gate to petri grow | Workflow change, QA-heavy |

Epics (`[EPIC]` in the title) stay on the board as context but are excluded from
factory intake — agents work leaf issues, humans work epics.

Manual stop: `kata create "[stop] <reason>"` halts the whole pipeline at the next
TPM check (see `config/stop-gap.yaml`).
