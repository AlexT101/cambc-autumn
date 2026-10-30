# Macro overhaul notes (2026-10-30)

Four agents rebuilt astraeus's macro independently from ef8f0b84 (branches `macro-1`..`macro-4`), and a fifth merged
them (`macro-5`). The branches were local and deleted after the merge (tips: macro-1 81560eb5, macro-2 92369660,
macro-3 21f775af, macro-4 1f90e8fb, which is in main's history, macro-5 6c58e01b). The other final bots survive only
as the git-ignored frozen copies in `bots/variants/` named in EXPERIMENTS. Results and the cross-branch reading:
EXPERIMENTS "Macro overhaul: four parallel branches and a merge". Main ships macro-4's bot with `max_wait` 3
(CHANGES 235-241).

| File | Branch | Final bot | Result vs ef8f0b8 (normal fuel, 10,240 games) |
|---|---|---|---|
| [macro-1.md](macro-1.md) | `macro-1` | 95500f74 | 59.5% |
| [macro-2.md](macro-2.md) | `macro-2` | d8821f97 | 52.7% |
| [macro-3.md](macro-3.md) | `macro-3` | 77e54381 | level (50.0% held-out, unlimited fuel) |
| [macro-4.md](macro-4.md) | `macro-4` | 83804615 (shipped) | 59.9% |
| [macro-5-merge.md](macro-5-merge.md) | `macro-5` | 532f164b | 59.6% |

Each file is that agent's own running log, unedited except links: its replay measurements, designs, every A/B and
its open ideas. [scratch.tar.gz](scratch.tar.gz) holds the one-off analysis scripts, reports and patches the agents
left in their shared session scratchpad (macro-1 `replay-study/`, macro-2 `scripts/`, the rest mixed at the top
level, `m1/tank.patch` the tank formation); unreviewed, with hard-coded paths. The supported tools are
`tools/replay/macro_stats.py` (macro-4), `turn_budget.py` and `walk_audit.py` (macro-3).
