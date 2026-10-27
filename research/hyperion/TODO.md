# hyperion: open work

## Direction

- A robust, intuitive, logical bot: behaviour derived from the rules (reach, sight, cooldowns, health, walking
  distance, measured rates) over tuned constants, fixed decision orders or special cases.
- Logical changes stay even when level or slightly below 50%; drop only what is clearly worse (below ~47% over ~1100
  games) or wrong.
- No new fuel gates. Make work cheap or bounded instead; the plan is [FUEL-GATES.md](FUEL-GATES.md).
- Keep the teleport, Tavi and Willow code.

## Next, ranked

Out-of-fuel turns are still ~1.5x hecate's in A/Bs ([EXPERIMENTS Fuel](../EXPERIMENTS.md#fuel)). Exact fuel cuts are mostly
exhausted; gate removals so far were level at 100M but 4-5x the out-of-fuel turns. CHANGES 107-108 added ~2% and
~6% in their A/Bs (the same REF reads 4530-4917 across runs). Not 108's Reach bush-camp passes (+9% alone): no
ladder or gen map has a camp on a bush, so it never fires and that +9% was noise.

1. The farm loop on many-group maps: CHANGES 175 stops it exactly once no group left in the nearest order can beat
   the best (heavy-set out-of-fuel turns 1579 -> 365), but not while banking a bag (~40% of loops on dense-camps; the
   trip there is bounded by here-group-altar, not a ring around `first`), nor in the opening or a pocket.
   `farm-partial-evaluation` still fires 20k times on the heavy set: bound the banking case, then remove pick_up's
   farm-loop gate.
   - The banking stop: trip >= r_k - D - bank_now (bank >= 0) in `beyond`, and a skipped group must not raise
     `from_altar_value` past the best (its cycle is at least the altar walk + tribute + capture). Measure first how
     often that altar half passes.
   - Done: the rated bound before facts on every turn (CHANGES 187), and plan v8's index for round 1 (188); with the
     step guard (189) out-of-fuel turns 3836 vs 4822 (EXPERIMENTS Fuel). Left from the fuel audits:
     - 187 costs +0.25% mean on rounds 300+ of the wide set, where it rarely prunes: make the check cheaper (not by
       skipping groups with read steps: dearer).
     - P5, a tighter steps bound `max(cheb, ally_steps(g) - from_ally_spawn().at(here))`, only with
       `draft_spawn_graph` and the spawn field ready. Measure first: a debug counter of Chebyshev survivors it would
       prune and `from_here` builds avoided in rounds 2-10; build only if those builds fall noticeably.
     - P6: retry F4 (drafted spawn steps for the approach cap, Warm-up 4) now that 187 stops most `from_here` rebuilds.
     - P7: a draft certificate for round 1's pre-stage (candidates and a threshold per body). First split the
       pre-stage's cost (`unweighed_beaten` against `beyond_spare`'s member loop, 24.5k on heavy maps).
     - P10: CHANGES 175's stop with the true distance from here; small after 187.
     - Rejected: draft-precomputed round-1 clears (P8) and `best_emblem` (P9): they read `World` and the last pick,
       and float exactness is unproven.
     - `crow-flies-farm` fired 5224 -> 7192 in the P1+P4 A/B (a fuel shortcut in different turns): look at why.
   - FSEED turns in nearest order with the stop (2073420c): exact, no out-of-fuel gain alone; retest with it.
2. Cheaper fight sims: non-plain act() for shield kits (44% of sim fuel), and fights that run to the horizon (16% of
   sims, 37% of sim fuel). Needed before the step-guard and prey-cut-short gates can go. Then, by the rules:
   - Allies walking into a fight (CHANGES 180) knock sims off the plain path: +8% out-of-fuel turns alone; with
     only walks of 2+ turns delayed, the Phase 1 merge still ran x1.10 the REF's.
     `walk_allies_in` also ignores walls and the enemies' own approach, and an unseen enemy cancels every delay.
   - Heart of Ruin's passive at its health at event turns (act()'s non-quiet path); HoR sims already run out of fuel.
   - From the fight audit: F4, an event mask in `simulate`'s non-plain branch (members with no cast, shield expiry or
     arrival this turn add Strength in index order), then incremental per-side sums for `their_cap`/`overwhelmed`.
     Prototype each alone, release, queue off; keep only at -0.3% total fuel or better with replays identical. F2b,
     copying only fighters' mutable state into a sim (28 of 60 bytes): measure likewise. F8, `Reach::at` hit windows
     for sight-free ways: optional, measure likewise. F2a (a walk table for `walk_allies_in`) was dearer: dropped.
   - Deferred: F5, a damage tape per roster per turn (high effort; only if heavy turns still run out); F7, a sim mode
     that stops once self-falls settles the caller (first measure how early self-falls ends want_home and prey sims);
     F3, prey skipping a fight covered by a lost one (not exact, 10 of 1134 covered fights were not lost: A/B only).
   - Ground AoE, Varg splash, HoR landing and Ren reflection per target, not single-target.
   - Once we fall, the sim's camp hits go to our weakest, not the next-nearest champion (sound, not the rule).
3. One danger model (STRIKE-SEARCH phase 5, [DANGER-MODELS.md](DANGER-MODELS.md)): one danger pass per tile per turn
   across want_home, step_guard and the search's end tiles (the fight audit's F6: 4-8k a heavy turn). Memoising the
   current passes saves nothing (few repeats); the gain is in folding them. Fold in: dash-landing `danger`,
   `shield_if_needed` and `breach` fire from `Safety::awake_members()` (nearest-champion cut, stuns), damage-weighted;
   Reach's enemy dash paths crossing our spawn (exact) and our champions (only those the enemy sees; rare).
4. The remaining gates, one at a time with an A/B: step-guard, prey-cut-short, ward, comms-stale-vision, turn-order.
   Narrowing step-guard and prey (CHANGES 176: the gate after the bounding pass, the sticky `costliest` decayed on
   skips, lost prey fights skipped before the margin) halved step-guard firings but cost +10% out-of-fuel turns
   (step-guard part) and +16% with the prey part, on fight maps: reverted. These gates are the fight turns' brakes
   until the sims are cheaper (item 2). Measured end-of-turn costs (100M, wide):
   observe + send mean 1.9k, p99 3.8k, max 6.3k against what was a gate of 1000 a champion + 10k (CHANGES 177: 10k); `set_turn_order` p99 4.6k,
   max 23k against 10k; `ward_bushes` once clusters are found p99 7.4k against 15k. `ward-no-bushes-clusters` in
   rounds 2-10 waits on `grow_cluster`'s 2-word batch floor (~16k over its floor; a smaller one needs a minimum step).
   - `fuel_ok` could throw `StaleTurn` when fuel rose since its last read this turn, as the farm loop does (CHANGES
     178): covers prey, step-guard, ward and the queue in a stale tail.
   - Retest the step-guard gates now that the search works the guard out only when it counts (CHANGES 189), after F4.
     189 saved less than the audit's estimate: log which later reader (`step_towards`, `try_move`, `descend`,
     `dash_landings`, `guard_steps`) works out the guard after a search; if one dominates and needs few tiles, a
     per-tile query recovers the ~40% of heavy searches whose guard is read later anyway.
5. Strike phase 4a's retreat-search fuel (40.8% real, 52.6% at 100M; `orch/strike-p4a-wt` bdb5902 holds an untested
   partial fix), then 4b (`orch/strike-p4b` 6997211, untested).
6. Stellar/Ren compositions and enclosed maps (fortress, lanes, caves, maze, sparse camps): against hecate, first deaths
   came from worse fights (outnumbered, struck first), lone champions picked off in tunnels.
7. Monolith and big-group captures: more Monolith damage than hecate but fewer captures (40 vs 58); big groups woken
   and left to sleep again (archipelago, 00contest). The strike search still bans waking a Monolith: price it (the
   allies' and the farm's cost) now that the wake counts the rule's hits (CHANGES 179).
8. `tools/ab.py` fuel per side, to measure what fuel costs one bot. `tools/fuel/bench.py --release` (the fuel audits
   used a copy) and a `--no-queue` option, so fuel-only work is judged on ladder codegen.
9. Edge-case maps (EXPERIMENTS "Edge-case maps"): stalls left after CHANGES 145-147, by `tools/replay/stalls.py`.
   Farm starved of fuel on big mazes: the width + height search cap is fixed (CHANGES 158); what stays is serpentines
   of 600+ layers whose estimate never fits a turn ([portals.md](draft-compute/portals.md)). 1v1 contest standoffs;
   farm hops' pocket deaths (no retreat from a pocket), no gold for a crystal while an ally takes the gold camps, a
   crystal rebought on every spawn visit.
   - Off-foot islands (crystal or dash) hold 12% of champion deaths in 2.2% of the time alive (x21.8); walkable
     dead-end pockets die at the base rate. Champions know these regions (`StaticMap::hops()`): price the hops and
     farming there ([chokepoints.md](draft-compute/chokepoints.md)).

10. Bookkeeping outside `decide` (the arch audit; ~25k of a 126k heavy turn):
    - A2: profile round 2's `World::update` plus track (33k on heavy maps), `update_camps`, `rank_turns` and comms on
      the heavy and fight sets with in-bot aggregation (not per-turn printf: the 1 MiB cap loses ~45% of turns); then
      prototype one `board_awake_camp_occupancy` read a turn (CAMP-AWAKE-MISMATCH makes it exact).
    - A3/A4: exact sim memos across a stale turn, filled by queue speculation. First measure, at the real budget on
      gen-chambers, the share of a post-out-of-fuel turn's sim keys (absolute rounds) that match the abandoned turn's.
    - A6: a cheaper `StaleTurn` unwind (catch near `play_turn`, fewer RAII frames). Measure the throw depth first.
    - After the unity build (CHANGES 190): `[[gnu::always_inline]]` on hot cross-file helpers the inliner still
      declines (`-mllvm -inline-threshold=1000` was -0.8%, unshippable), and recheck the `[[gnu::flatten]]`s
      (farm_turn, wants_shop, update_camps, comms), which now reach across files.

## Warm-up follow-ups (CHANGES 164-169)

The warm-up and end-of-turn queue no longer change play (52/52 bench replays identical with the queue off). Left:

1. **Early out-of-fuel turns since CHANGES 166.** Against f9d2e26b (before 166), rounds 2-10 ran out ~500 times
   against ~280 (A/B `wq-head-vs-f9d2`); overall ~7-10% more, across runs. Not cold centre fields: CHANGES 169 warmed
   them by round 6 (median, was 41) and rounds 2-10 stayed 507 vs 505. They cascade: most round-2 cases follow a
   round-1 one, and round 3 follows round 2 twice as often as before. Next: a fuel-exact trace
   ([tools/replay/harness](../../tools/replay/harness/README.md)) of a few round 2-4 turns that run out, on
   gen-dense-camps, gen-archipelago and gen-city, to see which build spends the fuel. Suspects: reads that now build
   inside `decide` (centre fields in `approach_steps` and `walk_on`, the spawn-centre field in `centre_to_spawn`, group
   hops on round 2), and `prepare_walk` running every turn without its 40k floor (CHANGES 167). Finer `OOF` phase
   names inside `decide` (farm-loop, farm-walk, approach, ward, turn-order) would make these traces readable.
2. **Shortcuts firing more often.** In CHANGES 168's A/B: `crow-flies-farm` 4856 vs 45 in rounds 61+ (1838 on
   gen-gem-centre), `farm-partial-evaluation` 58k vs 38k, `ward-no-bushes-clusters` 2802 vs 2368 in rounds 2-10.
   Recount after 169 (`py tools/replay/debug_lines.py SHORTCUT -- <batch>`); what remains is fuel changing play.
3. A caught `engine error 5` in the queue's `prepare` on gen-labyrinth-102106300, side b, round 756 (since 9be0f154).
   No play change seen; find the call.
4. Centre fields (p1 W1, `orch/p1-w1-fuel-full`): drafted spawn steps before the centre field (F4) and `from_here` as
   a Pathing slot (F5) pay only once the farm loop has a cheap lasting source off spawn; where the queue never warms
   centres (gen-gem-centre) the loop rebuilds `from_here` (~34k) every turn. Building `to_any_altar` and the
   spawn-centre field early in the queue delayed centre fields (rounds 3-30 worse).

## Bugs, ranked

Rechecked in code 2026-10-26. Logic fixes: A/B each, keep if level.

1. **Mid-turn state after our own hits.** A kill we make is read as a death (CHANGES 116) and a stun we cast is read
   (CHANGES 128). Still not read until the next full update:
   - camps we wake (`World::note_stirring` runs only in `update_camps` and captures);
   - camp members we kill stay in `Pathing::live_camps()`, and `blocked_` survives attacks;
   - our fighters keep turn-start health, shields and cooldowns (`Safety::made_`).

   Re-reading after our hits lost: 47.3%, a lean version 49.3%, both with more out-of-fuel turns (EXPERIMENTS
   `p1a-state`, held in `bots/variants/p1-final`). Retry narrowed to the reads that change a decision, or once fuel
   work frees room.
2. Varg's fallback attacks (`camp_attack_targets`, champion splash) wake neighbouring sleeping groups, unpriced
   (test drafts only).
3. An emblem bought mid-turn updates only our own camp output (CHANGES 181); the other gaps 179/181 left are
   CHANGES 185.

## Candidates

Each needs an A/B (see [../EXPERIMENTS.md](../EXPERIMENTS.md) first). Bundle removals and keep them if level.

- Removals: `keep_walk`'s free-stun logic in `enemy_cast` (still used by retreat and the game-ender intercept),
  replaced by a plain threshold; ground casts at unseen enemies (`max_unseen_tiles`).
- Behaviour: drop kite's contested branch; walk to lock an altar where a visible enemy tributes a big bag (`Altar::lock_tiles()` as goals); spell-clear pricing (`spell_clear_rounds`) tested both
  ways; probabilistic `threatened()` removed (risky: it gates recalls). Ren's specials change only on ladder evidence.
- The enemy's two-turn chain (both slots across two turns, slots readied for turn 2): lost as w2-chain (47.1%,
  ladder 52.9, out-of-fuel turns +20%). Retry only once fuel work frees room, or narrowed to slots readied for turn 2.
- Farm and capture pricing (p1 plan, judgement calls): price an enemy hold that pays before we arrive as respawning
  at payout + respawn (skipping it lost, CHANGES 181); shared-clear camp fire to the nearest champion (one takes 98%;
  keep `beyond_spare`/`partner_part` exact); an empty cleared group unseen for capture + respawn rounds as probably
  taken; `stun_worth` counts a tributer's whole bag though a cancel only delays it (<1 a game); `gems_short` minus
  allies' carried bags (endgame); `help_radius` from the ally's rounds to its recall line (prune-coupled); altar-lock
  "our side" by walking distance; `pick_up`'s 4-step cut-off from the payout round; the protected mate by a rule, not
  Prism (test drafts).
- Emblems (CHANGES 183-184, EXPERIMENTS "Phase 2"):
  - `income_prior`'s constants (4.5 rounds a gem, 0.005 kills and 0.015 Tribute turns a gem, weight 30 gems) were
    measured on ladder own drafts and never tuned.
  - Capture shared among allies: an ally's Capture already covers holds we share (W1-C, not run).
  - The low captures-per-gem tercile (big groups) is level (48.2 merged; Capture first lost there): check what the
    model buys on those maps.
  - Hunter is almost never chosen, even by Prism; Collectors and Greed were level (p2w2-sinks): retry only with a
    fight term (Collectors' and Skirmish's champion damage).
  - Fresh 1302's extra out-of-fuel turns (rounds 61+, gen-arena-130202620 209 vs 86, mut-stampede 213 vs 118): the
    main suites were level.
- Drafts ([DRAFT.md](DRAFT.md#phase-3-draft-search-2026-10-27-astraeus-3ff5e55)):
  - Vendetta for Vesper on 5 picks is the closest lead (+3.7 ±4.7 pooled, head to head level): retest after play
    changes (`tools/variants/ds_run.py run --picks 5 --cands vend-vesp`, a new source bot).
- Known bugs, unverified: retreat_step walks back into an Elk's reach when the way home passes it (`recall_outruns`
  ignores camps); idle turns under a Golem (dense-camps).
