# hecate: open work

## Direction

- A robust, intuitive, logical bot: behaviour derived from the rules (reach, sight, cooldowns, health, walking
  distance, measured rates) over tuned constants, fixed decision orders or special cases.
- Logical changes stay even when level or slightly below 50%; drop only what is clearly worse (below ~47% over 1102
  games) or wrong.
- No new fuel gates. Make work cheap or bounded instead; the plan is [FUEL-GATES.md](FUEL-GATES.md).
- Keep the teleport, Tavi and Willow code.

## Next, ranked

From [SESSION-2026-10-21.md](SESSION-2026-10-21.md); main's out-of-fuel turns are ~5x hecate-v8's.

1. Strike phase 4a's retreat-search fuel (40.8% real, 52.6% at 100M; `orch/strike-p4a-wt` bdb5902 holds an untested
   partial fix), then 4b (`orch/strike-p4b` 6997211, untested).
2. The fight simulation's cost per half-turn (~370 fuel; a sim averages ~6.3k since bounded decide's 17-turn horizon):
   a cheaper act(), not fewer duplicate calls.
3. Stellar/Ren compositions and enclosed maps (fortress, lanes, caves, maze, sparse camps; GAPS.md).
4. Monolith and big-group captures: more damage than v8, fewer captures (40 vs 58).
5. STRIKE-SEARCH phase 5 design (one danger model; health in the fight memo key first).
6. `tools/ab.py` fuel per side, to measure what fuel costs one bot.

## Candidates

Each needs an A/B (see [../EXPERIMENTS.md](../EXPERIMENTS.md) first). Bundle removals and keep them if level.

- Removals: `keep_walk`'s free-stun logic in `enemy_cast` (still used by retreat and the game-ender intercept),
  replaced by a plain threshold; ground casts at unseen enemies (`max_unseen_tiles`).
- Behaviour: one `run_home()` for `retreat()` and `carry_bag`'s retreat; give kite's stations line of sight, as
  `spell_clear` has; drop kite's contested branch; pack-zone ratio `(home || hurt) ? 2.0 : none`;
  walk to lock an altar where a visible
  enemy tributes a big bag (`Altar::lock_tiles()` as goals); spell-clear pricing (`spell_clear_rounds`) tested both
  ways; probabilistic `threatened()` removed (risky: it gates recalls). Ren's specials change only on ladder evidence.

## Don't remove

These have evidence behind them: `step_guard`, `pursuit`, `threat_strike`; Monolith sieges; kite on shared-gem maps.
