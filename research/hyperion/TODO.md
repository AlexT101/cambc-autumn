# hyperion: open work

## Direction

- A robust, intuitive, logical bot: behaviour derived from the rules (reach, sight, cooldowns, health, walking
  distance, measured rates) over tuned constants, fixed decision orders or special cases.
- Logical changes stay even when level or slightly below 50%; drop only what is clearly worse (below ~47% over 1102
  games) or wrong.
- No new fuel gates. Make work cheap or bounded instead; the plan is [FUEL-GATES.md](FUEL-GATES.md).
- Keep the teleport, Tavi and Willow code.

## Next, ranked

From [SESSION-2026-10-22.md](SESSION-2026-10-22.md); out-of-fuel turns are ~1.5x hecate's (65.7% against it).
Exact fuel cuts are mostly exhausted; gate removals so far were level at 100M but 4-5x the out-of-fuel turns.

1. The farm loop on many-group maps (132 groups: 44k a call, ~300 per pruned group): spatial buckets or an order kept
   across turns so pruned groups are never touched; then remove pick_up's farm-loop gate (farm-partial-evaluation).
2. Cheaper fight sims: non-plain act() for shield kits (44% of sim fuel), and fights that run to the horizon (16% of
   sims, 37% of sim fuel). Needed before the step-guard and prey-cut-short gates can go.
3. One danger model (OOF-ANATOMY proposal 2; STRIKE-SEARCH phase 5): one danger pass per tile per turn across
   want_home, step_guard and the search's end tiles; byte-identical first steps (turn memo for `lethal`, step_guard's
   keys kept across its two calls, a wider Reach memo) first.
4. The remaining gates, one at a time with an A/B: step-guard, prey-cut-short, ward, comms-stale-vision, turn-order.
5. Strike phase 4a's retreat-search fuel (40.8% real, 52.6% at 100M; `orch/strike-p4a-wt` bdb5902 holds an untested
   partial fix), then 4b (`orch/strike-p4b` 6997211, untested).
6. Stellar/Ren compositions and enclosed maps (fortress, lanes, caves, maze, sparse camps; GAPS.md).
7. Monolith and big-group captures: more damage than v8, fewer captures (40 vs 58).
8. `tools/ab.py` fuel per side, to measure what fuel costs one bot.

## Candidates

Each needs an A/B (see [../EXPERIMENTS.md](../EXPERIMENTS.md) first). Bundle removals and keep them if level.

- Removals: `keep_walk`'s free-stun logic in `enemy_cast` (still used by retreat and the game-ender intercept),
  replaced by a plain threshold; ground casts at unseen enemies (`max_unseen_tiles`).
- Behaviour: one `run_home()` for `retreat()` and `carry_bag`'s retreat; give kite's stations line of sight, as
  `spell_clear` has; drop kite's contested branch; pack-zone ratio `(home || hurt) ? 2.0 : none`;
  walk to lock an altar where a visible
  enemy tributes a big bag (`Altar::lock_tiles()` as goals); spell-clear pricing (`spell_clear_rounds`) tested both
  ways; probabilistic `threatened()` removed (risky: it gates recalls). Ren's specials change only on ladder evidence.

- Open from the 2026-10-22 audit (CHANGES 83-87): enemies revealed by our own walk (strike_after and farm's
  strike_enemy read only turn-start sightings; measure the fuel); capture_taken counting allies bound elsewhere;
  camps killed mid-turn still walls in approach fields; Varg's splash waking camps, priced; enemy stun status and our
  own mid-turn health in Safety's fights; per-owner enemy ward sight through `sdk_wards`/`sdk_ward_vision`.

## Don't remove

These have evidence behind them: `step_guard`, `pursuit`, `threat_strike`; Monolith sieges; kite on shared-gem maps.
