# hyperion: open work

Open work for astraeus, by theme. Audit-level fixes (one function, one rule) are in [DIRECTIONS.md](DIRECTIONS.md);
results in [EXPERIMENTS.md](../EXPERIMENTS.md). Closed items are removed (last pruned 2026-11-02, through CHANGES
274; earlier text is in git history).

## Direction

- A robust, intuitive, logical bot: behaviour derived from the rules (reach, sight, cooldowns, health, walking
  distance, measured rates) over tuned constants, fixed decision orders or special cases.
- Logical changes stay even when level or slightly below 50%; drop only what is clearly worse (below ~47% over ~1100
  games) or wrong.
- No new fuel gates. Make work cheap or bounded instead; the plan is [FUEL-GATES.md](FUEL-GATES.md).
- Keep the teleport, Tavi and Willow code.

## Held branches

Built and judged; each is level in play or costs fuel. Revive with the "Next", or drop.

- **Camp damage by the nearest-champion rule** (`merge/funnel` 6b0fe83, frozen `bots/variants/merge-campdmg-6b0fe83`):
  a joint clear charges us only the strikers we'd stand nearest (melee at 1, ranged at their range, ties shared by
  output); only committed allies tank. Rule-derived, no params. Against 251: 53.0% of 20,108 against 252's 52.3% on
  the same games (paired +0.73, z 1.85); head to head against 252 on unused suites: 50.3% of 20,478, level;
  out-of-fuel turns +36% (`clear_fire_on_us` builds a camp list per crew evaluation). 256's `share_damage` already
  models the same rule by tank score. Next: fold the nearest-champion stands into `share_damage`, or make 6b0fe83
  cheap and A/B it on top of 256.
- **The gap deadlock fix** (`fix/necks-gap` a40a0980, its CHANGES 263 on that branch only): two allies head-on in a
  one-tile neck with a free tile between them never yield (make_way sees only adjacent allies; gen-topo-necks-600107008
  161-953). `Pathing::gap_line` walks up to 8 tiles through allies and sealed free tiles, and the ally beyond yields by
  the gem rule (necks game 1013-636). 49.6% of 10,240, level; out-of-fuel turns +10%, mostly gen-dash-lattice-966507608,
  a standoff where, suspected but not traced, every stood-still champion whose route fails pays gap_line's ~10k walk
  each turn. Next: keep the "no way" answer across turns while its inputs stand, trace, A/B again. Also: two champions
  oscillate ~500 rounds in a corridor on gen-gem-drought-600105818 (backed off, then the dasher's field descent walks it
  back). Rebase onto CHANGES 274's pathing first.
- **The fight play-out with reach** (`held/reach-playout` cb2328dd): each fighter strikes only the opposing members
  within its reach once it has walked the gap. Better calibrated (EXPERIMENTS "Fight play-out with reach"), level in
  play (+0.5 on 6,144 games), out-of-fuel turns +15-22%. Next: a placing kept per roster for the turn, or reach only
  where it changes a target (Cassi and Issac, allies that never arrive).
- **Spawn heal and recall near spawn** (`held/spawn-heal-dash-cooldown` on origin; fuzz map L00-c1-11 and family):
  1a (da799d8a) takes the first home step whose walk down the home field survives, counting the spawn's turn-end
  heal (`HomeWalk`; `Safety::lethal` counts full health on spawn); 1b (532ffb8a) keeps an unthreatened recall within
  4 steps of spawn when no walk home survives. Against idle, L00-c1-11 side B 24 -> 451 gems. Concerns: `max_walk` 4
  is empirical; both treat enemies as standing still (deaths 0 -> 1-2 a game against idle). Fix 2 on that branch is
  superseded by CHANGES 274. A/B of all three on 258 (`held-on-main` 7703c9f5): 50.1% of 20,478, out-of-fuel turns
  +79% (fix 2). Next: 1a + 1b alone. Side A of the L00 family stays at 4-23 gems (Loops 1-2 below).
- **Stands lost only to pursuers, in the work guard**: 269's work guard misses tiles want_home would leave on a stand
  lost to pursuers within `pursuit_steps` (~19% of step-then-retreat turns). Pricing it per tile cost x2.3
  out-of-fuel turns for no gain (EXPERIMENTS "Hold rule and the work guard"). Next: a stand memo kept across turns
  while its fighters stand, or pricing only the tile the step takes (a lazy veto in `try_move`).

## Play

### Two-turn loops from fuel cuts and boundaries (map fuzzer, 2026-10-31)

Seen with ~4+ champions in sight (fuel cuts fire) and enemies near a decision boundary. How often they bite in mirror
games is unmeasured: first count A-B-A position cycles and `step-guard-*` shortcuts per champion turn in real-budget
games (`bench.py --fuel 0`). Judge each fix alone (repro, the fuzz run's 52 worst maps in `replays/fuzz/first`, A/B).
The root issue is systemic: decisions that change with the fuel left, and boundaries with no hysteresis.

1. **The step guard fails open on fuel** (DIRECTIONS guard 1): Marcella's ~85k farm turns cut it on 443 of ~900
   turns, and she steps back onto the tile want_home just fled, all game; none at 100M. Fix: the FUEL-GATES plan (a
   measured sim limit, fallback "unsimulated tiles guarded iff `safety.lethal`"), plus a fled-tile memory (like
   `camp_fled`: the tile stays guarded while the enemies seen then stand where they stood).
2. **Carry flips between bank and chain** (`carry_bag`, `may_chain`): Ryth with 8 gems farms one step south when
   chaining is allowed, banks when refused there, and steps back, rounds ~111-912. Fix: once `may_chain` refuses
   with a bag, keep `memory.banking` until the bag is tributed or lost, or no credible enemy has been in reach for a
   while. The release rule is a policy choice: ask the user.
3. **The strike search is capped by query count, not cost** (`max_exact_queries` 10): Vesper on spawn with four
   unacted enemies spends ~45k on 10 queries and runs out every other turn. Fix: cheaper queries (enemy responses
   memoised by tile), or a fixed per-search cost budget.

### Macro (2026-10-30)

Every macro gain came from champions spending more time working (giving way less, later recalls, recall as travel,
no waiting at respawns); coordination toward fights lost every time. Logs in [macro/](macro/README.md). Ranked:

1. **Camp deaths**: entering pockets and islands a walk can't leave (dash on cooldown), and an allied tank walking
   off so the camp switches to us. Off-foot islands hold 12% of deaths in 2.2% of time alive; walkable dead ends die
   at the base rate. Price the way out when choosing to wake or enter a group (`StaticMap::hops()`;
   [chokepoints.md](draft-compute/chokepoints.md)).
2. **Deaths of healthy champions** (~4 a game each side; we win 49% when we die first, 73% when they do): median
   health 82% at the first hit; 31% healthy and farming, 27% already retreating but caught; killers outnumber at the
   first hit in only 33%. Untested: a yield only from a pack walking toward us (or the stand sim with arriving
   allies), and retreats that actually escape.
3. **Who to chase**: no chase walks lost ~7 points, chasing wider lost; better prey choice is untested.
4. **Fewer, fuller trips**: one home visit that heals, shops and banks; interrupted clears (13% of Elk, 24% of Golem
   clears); crews that commit only when their arrival meets the respawn (pairs camping a respawn cost ~40
   champion-rounds an Elk; crews changed with 256). Two-emblem shop trips alone were level.
5. **Claim churn**: trips dropped before the first hit are ~7.6% of champion time. Arbitration by arrival was level;
   an ETA in the per-ally claim field is untested.
6. **Strong groups**: bold chips are right, but still a third of strong-group visits. 256's crews cover planned
   joint clears; a second champion joining an awake chip (ranged behind a melee tank) is untested.
7. **Coordination that saves farm time**: who holds a capture (252) and joint clears (256) shipped; who banks is
   open. The burst op failed on its valuation (instant solo rate against long-run rate), not execution.
8. **Smaller**: Monolith bursts (+4.4 on Monolith maps; 256 added Monolith crews); symmetric contest standoffs that
   freeze (gift-wrapping, the-line, stalactites); altars sealed inside a big group (the-pack mutations, galaxy:
   hyperion scores 0 too); Prism formation and allies farming near the carrier.

Settled, don't retry without a new reason (numbers in EXPERIMENTS): hunts, burst ops, duos, distress and assist,
tank formation, team ops for strong groups, cohesion bonuses; enemy sightings in comms (-2); walk-only or slower
recall banking; a Prism bag cap; camp_risk below 0.35; the cycle horizon; altar-lock wear-down and stall breakers;
recall lines below 0.25 with or without an enemy check; `max_wait` 0 (level held out); draft counter terms (lost 1.6
points; retry `--counters` only if a refit finds larger counters).

### Other play

- **The middle band** (CHANGES 264, +1.1 points over 41k games) is four tuned numbers; its plateau is what pays, and
  denial pricing didn't reproduce it (50.3%). Next, any of: re-derive `home_ground`'s falloff and drop the band; a
  10-20k sweep of its height and bounds; denial only on the enemy's half, or weighted by the enemy's score.
- **Melee kiting** (CHANGES 201, DIRECTIONS camps 4): verify on a second fresh shared-gem set (the first gave 59.2%
  of 120) and check it's level off them; then generalise the rule (spells out-damage basic attacks) to siege and
  farm everywhere. Ryth's camp damage collapse on starvation, road-of-riches, reverse-spiral, shortcut, oasis and
  gold-rush (none shared-gem) is unexplained.
- **Monolith and big-group captures**: big groups woken and left to sleep again (archipelago, 00contest); the strike
  search still bans waking a Monolith (DIRECTIONS plan 2).
- **Edge-case maps** (EXPERIMENTS "Edge-case maps", `tools/replay/stalls.py`): serpentines of 600+ layers whose
  search estimate never fits a turn ([portals.md](draft-compute/portals.md)); 1v1 contest standoffs; pocket deaths on
  farm hops; no gold for a crystal while an ally takes the gold camps; a crystal rebought on every spawn visit;
  dash-only pockets once an enemy bars the dash (CHANGES 274: the champion waits there).
- **Stellar/Ren compositions and enclosed maps** (fortress, lanes, caves, maze, sparse camps): against hecate, worse
  fights (outnumbered, struck first), lone champions picked off in tunnels.
- **Next draft lab: `narrow` and `sight_gap`** (left out of CHANGES 261 on first-turn fuel: a dash-lattice at 9.17M
  of 10M). Make them cheaper or relax the 8.5M bar, then A/B 25 features against 23; expect ~0.15 points
  (EXPERIMENTS "Draft lab draft3").

## Bugs

Logic fixes: A/B each, keep if level.

1. **Mid-turn state after our own hits** (DIRECTIONS safety 2 for camps). A kill we make is read as a death (CHANGES
   116) and a stun we cast is read (128). Not read until the next full update: camps we wake (`note_stirring` runs
   only in `update_camps` and captures); camp members we kill stay in `Pathing::live_camps()` (since 242 they also
   wall routes) and `blocked_` survives attacks; our fighters keep turn-start health, shields and cooldowns
   (`Safety::made_`). Re-reading everything lost (47.3%, lean 49.3%, both more out-of-fuel turns; `p1a-state`,
   `bots/variants/p1-final`): retry with only the reads that change a decision.
2. **An emblem bought mid-turn updates only our own camp output** (CHANGES 181; 185 closed the other gaps).
3. A caught `engine error 5` in the queue's `prepare` (gen-labyrinth-102106300, side b, round 756): no play change
   seen; find the call.
4. Unverified: `retreat_step` walking back into an Elk's reach on the way home (`recall_outruns` ignores camps;
   recheck after 237's camp exits); idle turns under a Golem (dense-camps).

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
   replays identical: F4 (an event mask in `simulate`'s non-plain branch), incremental per-side sums for
   `their_cap` / `overwhelmed`, F2b (copy only fighters' mutable state), F8 (`Reach::at` hit windows), Ren in
   `play_quiet`. Not exact, A/B only: F7 for step_guard with links (Cassi and Issac); F3 (prey skipping a fight a lost
   one covers). Deferred: F5, a damage tape per roster per turn. By the rules, still single-target or simplified:
   ground AoE, Varg's splash, HoR's landing and Ren's reflection; HoR's passive at event turns; once we fall, camp hits
   go to our weakest, not the next-nearest; `walk_allies_in` ignores walls and the enemies' approach, and an unseen
   enemy cancels every delay.
3. **One danger model** (STRIKE-SEARCH phase 5, [DANGER-MODELS.md](DANGER-MODELS.md)): one danger pass per tile per
   turn across want_home, step_guard and the search's end tiles; the gain is folding them, not memoising. Fold in
   dash-landing `danger`, `shield_if_needed` and `breach` fire from `Safety::awake_members()`; Reach's enemy dash
   paths crossing our spawn. Sharing want_home's lethal and stand with the search's: 2-4k on HoR heavy turns.
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
