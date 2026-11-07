# hyperion: open work

Open work for astraeus, by theme. Audit-level fixes (one function, one rule) are in [DIRECTIONS.md](DIRECTIONS.md);
results in [EXPERIMENTS.md](../EXPERIMENTS.md). Closed items are removed (last pruned 2026-11-02, through CHANGES
288; earlier text is in git history). An item tried and dropped is closed too: remove it and record the result in
EXPERIMENTS.

## Direction

- A robust, intuitive, logical bot: behaviour derived from the rules (reach, sight, cooldowns, health, walking
  distance, measured rates) over tuned constants, fixed decision orders or special cases.
- Logical changes stay even when level or slightly below 50%; drop only what is clearly worse (below ~47% over ~1100
  games) or wrong.
- No new fuel gates. Make work cheap or bounded instead; the plan is [FUEL-GATES.md](FUEL-GATES.md).
- Keep the teleport, Tavi and Willow code.

## Ocean fuel target (2026-11-07)

CHANGES 455 reduces out-of-fuel turns by 3.5% on standard and fresh suites; the requested **20% reduction remains
open**. [Campaign 13](fuel-campaign-13/NOTES.md) records the exact changes, rejected experiments, profiles and
cache-readiness divergences. Start from the applied bundle and its matching draft7 baseline; do not repeat the
level cache/sort/loop experiments without a new mechanism.

## Turn order and ally coordination (2026-11-02)

- **Enemy order is adversarial**: assume every enemy changes priority, from round 1; never fall back to a default or
  last-read enemy order. An enemy's next priority is final only once it has acted this round and we read it after.
  Relax the worst case only by what the rules force: ranks are a permutation (one enemy per rank), settled enemies
  keep their order among themselves, and at our rank k at most k enemies (k + 1 in rounds they start) act before us.
  "One or the other" forks come from that last rule.
- **Act late when nothing needs you early**: idle allies nearer an enemy act later (CHANGES 293). Only champions with a
  need take early seats.
- Kept: kill bids are kept, made at the real distance, and not while channelling (CHANGES 295).
- Held, level: worst-case enemy order (`ast-pwc`, +21% out-of-fuel turns) and the joint per-tile bound (`ast-safety`,
  correct but 2.1x out-of-fuel turns; next: pick the m worst enemies from Strike's distance tables), ally seat
  commitment v2. Dropped: predicted enemy order, strike-pledge readers, kill-now value. The kill gap is reach (33% of
  turns near a low enemy) and Safety's lost stands (20%), not choice. Notes in
  [turn-order-2026-11-02/](../turn-order-2026-11-02/).

## Held branches

Built and judged; each is level in play or costs fuel. Revive with the "Next", or drop.

- **Camp damage by the nearest-champion rule** (`merge/funnel` 6b0fe83, frozen `bots/variants/merge-campdmg-6b0fe83`):
  a joint clear charges us only the strikers we'd stand nearest (melee at 1, ranged at their range, ties shared by
  output); only committed allies tank. Rule-derived, no params. Against 251: 53.0% of 20,108 against 252's 52.3% on
  the same games (paired +0.73, z 1.85); head to head against 252 on unused suites: 50.3% of 20,478, level;
  out-of-fuel turns +36% (`clear_fire_on_us` builds a camp list per crew evaluation). 256's `share_damage` already
  models the same rule by tank score. Retried 2026-11-06 as one model for every camp-damage reading
  (`bots/variants/astraeus-campdmg2`, `model/camp_target.h`; enemies absorb fire only if held until the camp phase,
  ties by turn order): level, 50.4% of 20,480 and 50.0% of 81,920 against 0305953, out-of-fuel turns +6-7%
  (EXPERIMENTS "Camp damage by the nearest-champion rule, retried"). Combined with the clear estimate's area hits and
  stuns and the attack-count fix (`bots/variants/astraeus-combo3`) and SPSA-retuned with a control: 48.0% of 20,480
  against astraeus tuned the same way, 2 points down on ocean and the panel (research/tune-combo3-2026-11-06.md).
  Dropped; revive only with a change to what the farm does with cheaper clears (big packs), not a retune.
- **The fight play-out with reach** (`held/reach-playout` cb2328dd): each fighter strikes only the opposing members
  within its reach once it has walked the gap. Better calibrated (EXPERIMENTS "Fight play-out with reach"), level in
  play (+0.5 on 6,144 games), out-of-fuel turns +15-22%. Next: a placing kept per roster for the turn, or reach only
  where it changes a target (Cassi and Issac, allies that never arrive).

## Play

### Macro (2026-10-30)

Every macro gain came from champions spending more time working (giving way less, later recalls, recall as travel,
no waiting at respawns); coordination toward fights lost every time. Logs in [macro/](macro/README.md). Ranked:

1. **Fewer, fuller trips**: one home visit that heals, shops and banks; interrupted clears (13% of Elk, 24% of Golem
   clears); crews that commit only when their arrival meets the respawn (pairs camping a respawn cost ~40
   champion-rounds an Elk; crews changed with 256). Two-emblem shop trips alone were level.
2. **Strong groups**: bold chips are right, but still a third of strong-group visits. 256's crews cover planned
   joint clears; a second champion joining an awake chip (ranged behind a melee tank) is untested.
3. **Coordination that saves farm time**: who holds a capture (252) and joint clears (256) shipped; who banks is
   open. The burst op failed on its valuation (instant solo rate against long-run rate), not execution.
4. **Smaller**: Monolith bursts (+4.4 on Monolith maps; 256 added Monolith crews); symmetric contest standoffs that
   freeze (gift-wrapping, the-line, stalactites); altars sealed inside a big group (the-pack mutations, galaxy:
   hyperion scores 0 too); Prism formation and allies farming near the carrier.

Settled, don't retry without a new reason (numbers in EXPERIMENTS): hunts, burst ops, duos, distress and assist,
tank formation, team ops for strong groups, cohesion bonuses; enemy sightings in comms (-2); walk-only or slower
recall banking; a Prism bag cap; camp_risk below 0.35; the cycle horizon; altar-lock wear-down and stall breakers;
recall lines below 0.25 with or without an enemy check; `max_wait` 0 (level held out); draft counter terms (lost 1.6
points; retry `--counters` only if a refit finds larger counters).

### Other play

- **Edge-case maps** (EXPERIMENTS "Edge-case maps", `tools/replay/stalls.py`): serpentines of 600+ layers whose
  search estimate never fits a turn ([portals.md](draft-compute/portals.md)); 1v1 contest standoffs; pocket deaths on
  farm hops; no gold for a crystal while an ally takes the gold camps; a crystal rebought on every spawn visit;
  dash-only pockets once an enemy bars the dash (CHANGES 274: the champion waits there).
- **Stellar/Ren compositions and enclosed maps** (fortress, lanes, caves, maze, sparse camps): against hecate, worse
  fights (outnumbered, struck first), lone champions picked off in tunnels.
- **Chase persistence** (EXPERIMENTS "Chases and leaves on the ladder"): top teams kill hurt targets twice as often
  as we do, and alone too (41% against 22%). CHANGES 290-291 keep pressed fights as chases; overriding the stand or
  pack zone lost (-2 each); ranged retreat firing was level again. Open: what makes a lone ladder pursuer twice as
  lethal on the same steps (contact time, the target's choices), and cohesion (3+ allies near 27% vs 14%).
- **Cohesion** (EXPERIMENTS "Cohesion, four parallel attempts"): CHANGES 292's step tie-breaks close ~20% of the
  allies-within-8 gap for free in choices but +17-24% out-of-fuel turns, from farm and carry turns near allies. Make
  those cheaper. Leans that change choices lost or were level in all four attempts (farm weights, stand radius,
  rallies); B's fight posts were level on 292. The lever left is execution: with an ally near, top teams' death
  rate at contact falls 16 -> 5% and their first strikes kill ~30%; ours stay ~18% and ~20% whatever the count.
- **Next draft lab: `narrow` and `sight_gap`** (left out of CHANGES 261 on first-turn fuel: a dash-lattice at 9.17M
  of 10M). Make them cheaper or relax the 8.5M bar, then A/B 25 features against 23; expect ~0.15 points
  (EXPERIMENTS "Draft lab draft3").

- **Spawn healing, open** (CHANGES 328, EXPERIMENTS "Healing on our own spawn"): out-of-fuel turns +8.5%, mostly
  unattributed (`stand_reach` builds ~500 and `min_camp_damage` ~570 more a call on 00lanes round 1). Not yet
  integrated: the draft's heal price (draft.cc, recall + walk), kite on shared-gem maps, Willow's heal value, groups
  with more than 32 strikers. The gain is as large on maps with no camp near spawn (51.0%) as near (51.3%):
  find which part carries it.

## Patch 4.0.0 (cambc 5.0.0, 2026-11-05)

- Rules and stat tables are updated (CHANGES 389); nothing tuned for them yet. Pre-patch numbers that still steer play:
  the draft model (`draft_model.h`, fit on pre-patch games) and per-pick-count tables, the emblem lab table
  (CHANGES 233; Skirmish is now x1.10, Greed 40 shards' stats), diana's SPSA constants, and every A/B baseline.
- Vendetta (900 health, 65 Strength), Vesper (35 Strength) and Marcella (weaker growth) are weaker; Stellar, Prism
  (+15, +10 Focus) and Varg (+5 Strength) stronger; Heart of Ruin loses Focus. Re-run the draft lab on 5.0.0.

## Bugs

Logic fixes: A/B each, keep if level.

1. **Mid-turn state after our own hits**. A kill we make is read as a death (CHANGES 116) and a stun we cast is read
   (128). Not read until the next full update: camp members we kill stay in `Pathing::live_camps()` (since 242 they
   also wall routes) and `blocked_` survives attacks; our fighters keep turn-start health, shields and cooldowns
   (`Safety::made_`). Re-reading everything lost (47.3%, lean 49.3%, both more out-of-fuel turns; `p1a-state`,
   `bots/variants/p1-final`): retry with only the reads that change a decision.
2. **An emblem bought mid-turn updates only our own camp output** (CHANGES 181; 185 closed the other gaps).
3. A caught `engine error 5` in the queue's `prepare` (gen-labyrinth-102106300, side b, round 756): no play change
   seen; find the call.
4. Unverified: idle turns under a Golem (dense-camps).
5. **Shared-gem standoff** (EXPERIMENTS "Last-minute bug fixes", dropped B): on gen-shared-gems-600101605 a big
   group leaves one safe station; a guard holds it and every other champion walks at it all game (0-0, both sides).
   Yielding `kite()` to farm when every station is held (worktree commit 4ed5bfc8) was level (50.0% of 10,240) but
   on that map the yielders died to camps for nothing and lost both games. Fix where farm and kite choose the group
   (stations a guard doesn't take from casters), not with a yield.
6. **The stand reads unseen enemies from a point, not from `possible`** (CHANGES 337). `Safety::stand_reach` and
   `want_home`'s early return (`enemy_believed`) count an enemy out of sight only if it was seen last round
   (`age <= 1`), as a walker from its last tile (`walk_in`: `enemy_reach::distance` from `e.pos`). The damage side
   (`threats`, `lethal`, `unseen_blow`) and chase read `ChampionBelief::possible` instead, weighted by
   |square(tile, reach) ∩ possible| / |possible| and dropped below `credible_weight`. So two models of one enemy
   disagree: the point is a turn stale, and at age 2 the enemy leaves the stand while the threat model still weights
   it, which can bring back the retreat, lose sight, step back in cycle a round later. Consolidate: the stand's walk
   from `possible` (one distance field from p, min over each enemy's tiles, shared by every unseen enemy), included
   by the threat model's credibility weight, not an age cutoff. Open: how a wide stale set counts (nearest tile is
   pessimistic; the damage model scales by overlap).

## Candidates

Each needs an A/B (check EXPERIMENTS first). Bundle removals and keep them if level.

- **Removals:** `keep_walk`'s free-stun logic in `enemy_cast` (still used by retreat and the game-ender intercept),
  replaced by a plain threshold; ground casts at unseen enemies (`max_unseen_tiles`); kite's contested branch;
  probabilistic `threatened()` (risky: it gates recalls). Ren's specials change only on ladder evidence.
- **Behaviour:** walk to lock an altar where a visible enemy tributes a big bag (`Altar::lock_tiles()` as goals);
  `spell_clear_rounds` pricing tested both ways.
- **Farm and capture pricing** (judgement calls): an enemy hold that pays before we arrive priced as respawning at
  payout + respawn (skipping it lost, CHANGES 181); an empty cleared group unseen for capture + respawn rounds as
  probably taken; `stun_worth` counting a tributer's whole bag though a cancel only delays it; `gems_short` minus
  allies' bags (endgame); `help_radius` from the ally's rounds to its recall line; altar-lock "our side" by walking
  distance; `pick_up`'s 4-step cut-off from the payout round; the protected mate by a rule, not Prism.
- **Emblems:** the lab table (CHANGES 233) decides ~42% of new emblems; elsewhere `income_prior`'s constants (4.5
  rounds a gem, 0.005 kills and 0.015 Tribute turns a gem, weight 30 gems) are measured, never tuned. An ally's
  Capture already covers holds we share (W1-C, not run). Hunter is almost never chosen. The low captures-per-gem
  tercile (big groups) was level (Capture first lost there): check what the model buys on those maps.

## Fuel

Latest census: fuel-campaign-3 [NOTES.md](fuel-campaign-3/NOTES.md) "Where late run-outs go now" (strike search in
88% of fight-set first run-outs, Heart of Ruin 60% of them; on a late set farm 45%). The 2026-10-29 profiles behind
items 2-7 (sim, search, want_home, prey, turn-order costs) are in [OPEN-ITEMS.md](fuel-campaign/OPEN-ITEMS.md);
later rounds in fuel-campaign-2's and -3's NOTES. Sub-1% cuts don't show in A/B out-of-fuel
counts (shared-gem maps swing by thousands): judge with `tools/fuel/oof_bot.py`, also without shared-gem maps, and on
the 100M bench's turns over 100k.

1. **Dash travel's out-of-fuel tail** (CHANGES 274): +26-28% out-of-fuel turns (mean fuel +2%), mostly hole-heavy
   maps (topo, mega-groups, huge), ~2/3 with the crossing logic. A logic pass (c00b84de) moved it 1 point. Next: the
   fuel census on those turns against the reference before more guessing.
2. **Cheaper fight sims**, needed before the step-guard and prey-cut-short gates can go: non-plain `act()` for
   non-plain kits and fights that run to the horizon. Ideas, each kept only at -0.3% total fuel or better with
   replays identical: incremental per-side sums for `their_cap` / `overwhelmed`, F2b (copy only fighters' mutable
   state), Ren in `play_quiet`. Not exact, A/B only: F7 for step_guard with links (Cassi and Issac); F3 (prey
   skipping a fight a lost one covers). Deferred: F5, a damage tape per roster per turn. By the rules, still
   single-target or simplified: ground AoE, Varg's splash, HoR's landing and Ren's reflection; HoR's passive at event
   turns; once we fall, camp hits go to our weakest, not the next-nearest; `walk_allies_in` ignores walls and the
   enemies' approach, and an unseen enemy cancels every delay.
3. **One danger model** (STRIKE-SEARCH phase 5, [DANGER-MODELS.md](DANGER-MODELS.md)): one danger pass per tile per
   turn across want_home, step_guard and the search's end tiles; the gain is folding them, not memoising. Fold in
   dash-landing `danger`, `shield_if_needed` and `breach` fire from `Safety::awake_members()`. Sharing want_home's
   lethal and stand with the search's: 2-4k on HoR heavy turns.
   Smaller: a start-tile-only or one-candidate price skip; a per-turn `viewers()` grid; kite's `make_way`
   `know_failure` (8.5k, ~30 turns a game).
4. **The farm loop**: CHANGES 175 and 226 stop it exactly once no group left can beat the best (banking too), but
   `farm-partial-evaluation` still fires (20k times on the heavy set, 2026-10-29). Next: pick_up's farm-loop gate,
   retested with an A/B (removing it before 226: +90%). The non-banking stop never fires on dense-camps in rounds 11-300
   (its bound omits clearing time; an exact clearing-aware stop cost 12.5k: needs per-map class tables and a world-kept
   hurt mask). farm.post (17-20k on out-of-fuel turns): `room()`'s reserve underestimates it on mazes, and farm's walk
   runs two route searches after a check that reserves one (fuel-campaign-2 NOTES "quill: run-out forensics"). P5 (a
   tighter steps bound), P6 (F4's drafted spawn steps), P7 (a round-1 draft certificate; split the pre-stage's cost
   first), P10 (175's stop with the true distance). `crow-flies-farm` fired 5224 -> 7192 in the P1+P4 A/B: look at why.
5. **Round 1**: world construction is still >200k on ~100-group maps (~145 instructions a member), so round 1 runs
   out there and finishes in round 2 (CHANGES 230); then `prices()`' first call 14.6k, the post-loop 40k.
6. **The remaining gates**, one at a time with an A/B ([FUEL-GATES.md](FUEL-GATES.md)): step-guard, prey-cut-short,
   siege-route-fuel, comms-stale-vision (its removal with farm-no-route raised rounds 1-10 out-of-fuel turns, CHANGES
   250), turn-order (251 skips champions out of strike reach; bound its offers first, costs before 251: `offer_escape`'s
   `threats_at` 9-14.5k, `offer_kills` up to 10k, `offer_heal` 5-11.5k, `may_escape`'s `strike_of` 2-4.7k). These gates
   are brakes until the sims are cheaper. `fuel_ok` could throw `StaleTurn` when fuel rose since its last read this
   turn, covering a stale tail.
7. **Bookkeeping outside `decide`** (~19k of a heavy turn): windowed dilation for track on 100x100 (2-4k there); one
   `board_awake_camp_occupancy` read a turn in `update_camps` (A2); exact sim memos across a stale turn (A3/A4: first
   measure how many keys match the abandoned turn's); a cheaper `StaleTurn` unwind (A6); `always_inline` on hot
   cross-file helpers and a recheck of the `[[gnu::flatten]]`s after the unity build.
8. **Warm-up follow-ups** (CHANGES 164-169): centre fields still finish late on big maps (dense-camps rounds 210-470),
   where farm steps cost 17.7k a call before round 300 against 5.5k after; where the queue never warms centres
   (gen-gem-centre) the loop rebuilds `from_here` (~34k) every turn. A capped `from_here` that grows its cap (W18) was
   mixed and its commits are gone; building centre fields nearest-first earlier is the alternative. Recount
   `crow-flies-farm`, `farm-partial-evaluation` and `ward-no-bushes-clusters` (`py tools/replay/debug_lines.py SHORTCUT
   -- <batch>`).
9. **Strike phase 4a/4b** ([STRIKE-SEARCH.md](STRIKE-SEARCH.md)): the retreat search's fuel (40.8% real, 52.6% at
   100M); the partial-fix branches are gone.
10. **Tools**: `tools/ab.py` fuel per side; `tools/fuel/bench.py --release` and `--no-queue`, so fuel-only work is
    judged on ladder codegen.
