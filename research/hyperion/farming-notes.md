# Farming handoff notes (workstream B)

Spec: [FARMING.md](FARMING.md). Newest stage first.

## Stage 1: shared prices (branch orch/farm-s1, from main 4771e9d)

**Built** (bots/hyperion/src/bot.cpp):
- `heal_rounds(world, damage, out)`: one price (usable health, recall + `out`); farm's `heal` lambda only finds `out`.
- `HomeTrip` / `home_trip(world, pathing, channel, wins)`: `rounds(walk, overlap, gold_in)` = min(walk, max(0,
  channel − overlap) + hurt + spawn→altar − value(gold_in)), value = heal + the next emblem once the gold completes
  it, 0 once the bag wins. Used by farm's bank trips (`bank_now`, per-group `back`, kept out of the group cache),
  `recall_to_bank`, `capture_recall` (one branch now; its emblem guards `lands − payout ≤ 1` and `!closing` are
  gone) and `wants_shop` (`value(0)` against min(back, channel + hurt) + back).
- `gems_share` is bounded by `ally_rate × bag_rounds_left` (no bound while the rate is 0, as `race_left`).
- `prices(world)`: the next emblem, its gain in rounds, and gold in gems = `gems_share(short, saved / cost)`, kept
  while gems short, enemy score and our stats hold.
- `closing` = `bag_rounds_left` ≤ walk + tribute + `endgame_margin`; `too_late` at any horizon.
- `holders(G)` in `ally_holding`, `step_onto_cleared`, `pick_up`.
- Deleted: `gold_worth`, `endgame()`, `emblem_gain_rounds`, params `clear_share`, `endgame_shop_rounds`,
  `endgame_horizon`. Net about +10 lines, not −30: the shared structs cost what the merges save.

**Two fixes the spec did not foresee:**
- Cold start: `upkeep_cost`'s clearing share was camp_turns / turns, 0 before the first camp hit, so gold priced 0
  and a champion with only gold-only groups to farm (stampede, where kite holds the gem block) idled all game (0
  gold, lost on gold tiebreak). Now (camp_turns + 1) / (turns + 1).
- `too_late` treats an unknown altar walk (centre_to_altar unreachable) as no deadline; before, it skipped the
  group, and only in the last 400 rounds.

**Screen** (9 games new vs old, both with debug prints; scripts s1_screen.py and s1_pergame.py in the worktree's replays/orch/research/;
6 planned on stampede, monolith, big-world, then 3 to confirm the stampede fix):
- per_gold new / old: median 2.2x (p10 0.34, p90 4.6) before the cold-start fix; outside the ±30% FARMING.md
  expected. Measured clearing + heal share (~0.3) is about twice the old 0.15. Expect more weight on gold groups.
- Bag recalls up: recall_to_bank episodes 33 vs 17 (it now counts the emblem when the gold is in hand); capture
  recalls level on Monolith/big-world (28/28 vs 24/28, 31/39 vs 23/25).
- Out-of-fuel turns: all in `decide`; big-world 9 vs 5 and 2 vs 2, stampede 2 vs 1: one game each, judge on the A/B.
- Games against old: monolith 1-1 and big-world 0-2 (before the cold-start fix), stampede 0-4 idle before it and
  1-0 after. Noise, apart from the idling.

**Not done:** the 582-game A/B (integrator only). Judge against 4771e9d: keep if ≥ 47% and OOF not up.
**Risks:** per_gold 2x; the cold-start prior also lifts early emblem gains a little (buy order unchanged once camps
are hit).
