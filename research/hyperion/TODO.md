# hyperion: open work

## Outstanding: camp damage by the nearest-champion rule (held, 2026-10-31)

orbit's tank-aware clear pricing without its middle band, on top of CHANGES 252: branch `merge/funnel` 6b0fe83
(frozen `bots/variants/merge-campdmg-6b0fe83`). Each awake monster hits the nearest champion in its reach, so a
joint clear charges us only the strikers we would stand nearest to (melee at 1, ranged at their range, ties shared by
output); only committed allies tank (claimers there by our arrival, a partner arriving with us, allies on the threat
tiles). Rule-derived, no params. Fuel bench at 100M: 52/52 identical to orbit's version on d0a8a94.
- Against 251, ladder + gen-s1 + fresh-6003..6040, real budget: 53.0% of 20,108 (52.3-53.7) vs 252's 52.3% on the same
  games; paired +0.73 points (McNemar z = 1.85).
- Head-to-head against 252, fresh-9800..9839 (unused before), real budget: **50.3% of 20,478 (49.6-51.0)**, level; 24
  of 40 suites at 50%+.
- Out-of-fuel turns: 86,095 against 252's 63,284 in the head-to-head (+36%); the bench's worst turn ~500k (252
  ~260k). `clear_fire_on_us` builds a camp list per crew evaluation.
- Held while quill's crew economics (which shares a crew's damage by tank score: the same model) is judged. Next:
  either fold the nearest-champion rule into whichever crew pricing ships, or make it cheap and A/B it again.

## Direction

- A robust, intuitive, logical bot: behaviour derived from the rules (reach, sight, cooldowns, health, walking
  distance, measured rates) over tuned constants, fixed decision orders or special cases.
- Logical changes stay even when level or slightly below 50%; drop only what is clearly worse (below ~47% over ~1100
  games) or wrong.
- No new fuel gates. Make work cheap or bounded instead; the plan is [FUEL-GATES.md](FUEL-GATES.md).
- Keep the teleport, Tavi and Willow code.

## First: two-turn loops from fuel cuts and boundaries (map fuzzer, 2026-10-31)

Diagnosed on fuzz L00-c1-11 (touching spawns, astraeus side B against `bots/idle`, 24 gems), but none needs touching
spawns: each needs ~4+ champions in sight (Safety is dear, so fuel cuts fire) and enemies standing near a decision
boundary (holding a capture, at an altar, on spawn). How often they bite in mirror games is unmeasured; first count
A-B-A position cycles (position at t equals t-2, differs from t-1) and `step-guard-*` shortcuts per champion turn
in real-budget games (`bench.py --fuel 0`). Judge each fix alone (repro, the fuzz run's 52 worst maps, then an A/B).
The root issue is systemic: decisions that change with the fuel left, and boundaries with no hysteresis.

1. **The step guard fails open on fuel** (combat/guard.cc ~391/467/503-507: `step-guard-entry`, `-sim`, `-look`
   return `nullptr`, no guard). Marcella's farm turns cost ~85k, so 443 of ~900 turns cut it and she steps back onto
   the tile `want_home` just fled (lost stand at (16,35), fine at (17,36)): a two-round cycle all game; none at
   100M. Fix: the FUEL-GATES plan for this gate (a measured simulation limit, independent of fuel left, with the
   fixed fallback "unsimulated tiles guarded iff `safety.lethal`"; needs cheaper sims), plus a fled-tile memory:
   when `want_home` leaves tile T with a lost stand, T stays guarded while the enemies seen then stand where they
   stood (like `camp_fled`; a few hundred fuel). Considered: failing closed on the cut with the `exposed` tiles
   already computed (free, but still a fuel-dependent choice, and more timid on every cut turn).
2. **Carry flips between bank and chain at a boundary** (economy/bank.cc:840 `carry_bag`, `may_chain` :649-652,
   `credible_enemy_may_hit_within(here, pursuit_steps)`). Ryth with 8 gems: chaining allowed at (16,46) so it farms
   south to (16,45); refused there, so it banks and the altar route steps back to (16,46), rounds ~111 to 912+.
   Fix: hysteresis, once `may_chain` refuses with a bag, keep `memory.banking` until the bag is tributed or lost or
   no credible enemy has been within reach for a while. The release rule is a policy choice (ask the user): "until
   tributed" makes small bags quit chaining after any brush. Considered: the refusing ring as part of farm's zone
   while carrying (a dilated enemy board, a few thousand fuel; can stall with the bag if no route avoids it).
3. **The strike search is capped by query count, not cost** (combat/plan.cc:192 `max_exact_queries = 10`, cap
   ~:1859). Vesper Vale on spawn with four enemies yet to act: 10 exact queries ~45k (one foe priced for two turns),
   so every other turn runs out in `decide`. Fix: cheaper queries (enemy responses memoised by tile), or a fixed
   per-search cost budget that does not read the fuel left (bounded work, not a gate).

4. **Fixes written, held for the concerns below: not A/B'd, not merged** (branch
   `held/spawn-heal-dash-cooldown` on origin, on 10aa483: da799d8a 1a, 532ffb8a 1b, 18494d5b fix 2 with CHANGES 247).
   Revisit them with items 1-3 (the same fuel and boundary problems), then A/B each alone on unused suites.
   - **1a, touching spawns:** a hurt champion never stepped home: `retreat_step` priced the damage on the way against
     current health, though a turn ended on our spawn heals to full before any enemy acts. `HomeWalk`
     (combat/fight.cc) takes the first step whose walk down the home field survives (doubled `damage_bound`
     summed against health + shield, the spawn tile against max health), ranked first; `Safety::lethal` counts full
     health on our spawn. Against idle, L00-c1-11 B 24 -> 451 gems, out-of-fuel turns 907 -> 9; Prism heals.
   - **1b:** `continue_recall` keeps an unthreatened recall within 4 steps of spawn when no walk home survives
     (`walk_home_fails`), not only when `recall_outruns`. With 1a, L00-c1-11, L00-s1-08, m-rushbait-v2-100565 and
     L00-c3-07 side B reach 1000.
   - **Fix 2, dash/walk livelock** (Heart of Ruin over a hole row, m-starvation-100582 A, 513 gems): `dash_steps` is
     V(p, c) = the rounds until the dash plus the dash-aware distance from the tiles walkable meanwhile;
     `dash_walk_cap` caps the live walk at V + 2 where walking round the lines is longer; dashers wait beside a line
     while the dash cools; `travel_dash` re-ranks its 3 best landings by V(l, 7). 513 -> 1123 gems; A-B-A cycles
     hundreds -> under 10 a champion.
   - **Concerns:**
     - Constants: `HomeWalk::max_walk` 4 (raised from the plan's 1 because Vesper dithered 3 steps out),
       `dash_walk_slack` 2, at most 64 ball tiles. They bound work but are partly empirical.
     - 1a and 1b hold enemies where they stand. Against real chasers, 1a walks through bounded damage and 1b's
       recall can be broken by an approach. Against idle, deaths rose 0 -> 1-2 a game.
     - 00rushbait-v2, a ladder map with touching spawns: the final fix 2 lost both mirror games there, which 1a+1b
       had won (14 games in all, noise; read it in the A/B).
     - Fix 2: `prepare_approach` now runs on every dasher farm turn (cached, but a new target costs a search;
       unmeasured). Dashers can wait up to 7 rounds at a line. V ignores cooldowns after the next dash, and only 3
       landings are re-ranked. Filtering landings by V instead of ranking rejected needed dashes (a 714-turn flip).
     - Not fixed: side A of the L00 family stays at 4-23 gems (items 1-2), and a Vendetta at 40 health on L00-c2-02-A
       whose own tile's threat alternates with parity.
   - Repro maps, scripts and traces: the session scratchpad `fx/` (not kept); the fuzz run in `replays/fuzz/first`.
5. Altars sealed inside a big group (the-pack mutations, galaxy) still need a siege plan; hyperion scores 0 there
   too.

## Macro (2026-10-30)

astraeus is macro-4's bot with `max_wait` 3 (CHANGES 235-241): ~60% against ef8f0b8, 83% against hyperion, 66-67%
against 54254fb at normal fuel. Four independent macro branches and a merge are summarised in EXPERIMENTS "Macro
overhaul: four parallel branches and a merge"; each agent's log is in [macro/](macro/README.md). Every gain there
came from champions spending more time working (giving way less, later recalls, recall as travel, no waiting at
respawns); coordination toward fights lost every time. Open, ranked:

1. **Camp deaths** (macro-4, macro-1): the remaining ones come from entering pockets and islands a walk cannot leave
   (dash on cooldown) and from an allied tank walking off so the camp switches to us; they rose with the bolder
   thresholds (macro-1: 1.01 against 0.67 a game). Price the way out when choosing to wake or enter a group. Same
   cause as item 9's off-foot islands (12% of deaths in 2.2% of time alive).
2. **Deaths of healthy champions** (~4 a game each side; we win 49% of games when we die first, 73% when they do).
   macro-3's death recipes: median health 82% at the first enemy hit; healthy and farming 31% (72% walking, 35%
   blind), healthy and already retreating but caught 27% (48% of victims retreated 6 of their last 8 rounds, half no
   closer to spawn); killers outnumber at the first hit in only 33%. macro-2's hold-own-side gain paid some back in
   own-side deaths. A yield that keeps farm time (only from a pack walking toward us, or the stand sim with arriving
   allies) and retreats that actually escape are both untested.
3. **Who to chase** (macro-2): no chase walks lost ~7 points, chasing wider lost; better prey choice is untested.
4. **Fewer, fuller trips** (macro-1, macro-3): one home visit that heals, shops and banks; crews that commit only when
   their arrival meets the respawn (pairs camping a respawn cost ~40 champion-rounds an Elk); interrupted clears
   (13% of Elk and 24% of Golem clears, at a third of the gems a round). Two-emblem shop trips alone were level.
5. **Claim churn** (macro-3): trips dropped before the first hit are ~7.6% of champion time. Arbitration by arrival
   was level (50.4% of 3212); macro-1's claim board (with ETAs) lost on macro-4's base. An ETA added to macro-4's
   per-ally claim field is untested.
6. **Strong groups** (macro-4): bold chips are right, but chips are still a third of strong-group visits; a second
   champion joining an awake chip (ranged behind a melee tank) without the old conservative budget is untested.
7. **Coordination that saves farm time** (macro-2): who holds a capture, who banks, joint clears valued at honest
   long-run rates. The burst op failed on its valuation (instant solo rate against long-run rate), not execution.
8. Smaller: Monolith bursts (eris +4.4 on Monolith maps, ~10-12% of dev maps); symmetric contest standoffs that still
   freeze (gift-wrapping 4v4, the-line and stalactites 1v1; macro-1); Prism formation, allies farming near the
   carrier (macro-3; Prism as carrier was level).

Settled, don't retry without a new reason (numbers in EXPERIMENTS): hunts, burst ops, duos, distress and assist,
tank formation, team ops for strong groups, cohesion bonuses; enemy sightings in comms (-2); walk-only or slower
recall banking; a Prism bag cap; camp_risk below 0.35 on this base; the cycle horizon (level on macro-4); altar-lock
wear-down and stall breakers (level on macro-1, +160 lines for the locks); recall lines below 0.25 with or without an
enemy check (macro-2's D1, macro-4's uniform 0.15/0.20). `max_wait` 0 read +2.3 on dev but level held out; 3 read 51.2% against 5. Drafting: draft2's counter
terms (at most ~0.012 logit) lost 1.6 points, so astraeus drafts without them; retry `--counters` only if a refit
finds larger counters.

**Labs (2026-10-30):** both tables were learned on ef8f0b8's play and the old maps. Emblem round 3, then draft3
(25 map features, no counters, from scratch): round 3 running since 2026-10-30 23:54, draft3 next; [PLAN-draft3.md](../../tools/draftlab/PLAN-draft3.md).

## Next, ranked

**Where out-of-fuel turns stand** (fuel campaign 2026-10-29, CHANGES 214-230; EXPERIMENTS "Fuel round 6 (final)" and
"Fuel phase 2"; every finding and dropped attempt: [fuel-campaign/](fuel-campaign/README.md)).
Against hecate on test drafts, 8ec2c4d's 11101 fell to 7325 at m6 (-34%), still ~2.7x hecate's ~2.7k. The
shared-gem livelocks are gone (217); the rest is diffuse (~2/3 in champion-games under 10) and ~2/3 in rounds 300+.
The fuel census (`tools/fuel/census`, 28 heavy maps, real budget): 83% of run-outs are a streak's first, 93% inside
`decide`. Fight turns 51-60% (strike search 32-38k against 19k on heavy finished turns, plus want_home/stand 17.5k;
both in 47% of all run-outs); quiet farm turns 24-32% (farm.loop 33k + farm.post 17-20k against 9k finished;
farm.post is where fuel most often runs out); round 1 6-7%. Heart of Ruin holds 31-36% of first run-outs. World
update is a flat ~14-15k. Halving needs ~20-25k off a heavy turn (mean ~123k): structural work (items 1-3), not
trims. Sub-1% cuts don't show in A/B out-of-fuel counts (one build reads ~5% apart against different opponents, and
gen-shared-gems-8280101604 flips 1.3k <-> 2.4k with one rerouted game): judge with `tools/fuel/oof_bot.py`, without
shared-gem maps too, and on the 100M bench's turns over 100k.

1. The farm loop on many-group maps: CHANGES 175 stops it exactly once no group left in the nearest order can beat
   the best (heavy-set out-of-fuel turns 1579 -> 365), but not while banking a bag (~40% of loops on dense-camps; the
   trip there is bounded by here-group-altar, not a ring around `first`), nor in the opening or a pocket.
   `farm-partial-evaluation` still fires 20k times on the heavy set: bound the banking case, then remove pick_up's
   farm-loop gate (removing it now: +90% out-of-fuel turns on the wide set; 60-80 groups at 300-900 each).
   - The banking stop: trip >= r_k - D - bank_now (bank >= 0) in `beyond`, and a skipped group must not raise
     `from_altar_value` past the best (its cycle is at least the altar walk + tribute + capture). Banking calls are
     a third to 40% of calls and ~half the loop's fuel (~48k each; every one of 74-96 groups reaches facts). Done
     (CHANGES 226), with banking calls in an out-of-line `farm_turn<false, true>`: many-group turns over 100k -4.7%,
     wide/OOF total +0.01-0.02%. Next: pick_up's farm-loop gate, retested with an A/B.
   - The non-banking stop never fires on dense-camps in rounds 11-300 (farm ~50k a call, all 96 groups): its suffix
     bound omits clearing time. An exact clearing-aware stop (cd1e6ef5, reverted) cut heads 73 -> 31 a call but its
     `stop_from` cost 12.5k (class tables per `first` 4.2k, hurt scan 2.1k, class search 6.2k): +0.6..+1.1%. To pay:
     class tables per map, a world-kept hurt bitmask, the check only at the old stop; ceiling ~11k a call. A stronger
     stop when far from `first` (20-30k in round 2, ~10k in rounds 3-10) is not exact as is (tie order).
   - farm.post (the walk after the loop) 17-20k on out-of-fuel turns; `room()`'s reserve (`walk_reserve` +
     `search_cost_estimate`) underestimates it on mazes. Smaller: the loop head ~250-400 a pruned group (~30% of
     8-15k on heavy turns); `nearest_groups` rebuilt on each target change (61 x 12.2k in a dense-camps game, ~110 a
     group unexplained) and 12.5-14k for `first` in round 2.
   - Round 1 (6-7% of run-outs): world construction is still >200k on ~100-group maps (CHANGES 219: 325.6k ->
     306.1k mandatory; ~145 instructions a member, not host calls), so round 1 always runs out there. Then
     `prices()`' first call 14.6k (`best_emblem`), the post-loop 40k (attack tiles 13k). Small: `ChampionBelief() {}`
     ~1.2k, the plan section's eager `fixed_steps(0)` decode 15k on 102 groups.
   - Dropped (2026-10-29): a tighter skip loop (+1.9%, codegen); too small: a `nearest_groups` rewrite (-0.05%), the
     help group only from ally claims (-0.02%).
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
2. Cheaper fight sims: non-plain act() for non-plain kits, and fights that run to the horizon (16% of sims, 37% of
   sim fuel). Needed before the step-guard and prey-cut-short gates can go. Profile after CHANGES 220 (test-draft OOF
   set): non-plain act 29% of sim fuel (~480 a call, 3.6 a sim), early-end checks 13.5%, plain act 7.9%,
   `play_quiet` 6.5% (the ceiling for a closed form of quiet stretches); by caller stand 40%, guard 33%, chase 27%;
   14-19% after our fall. Sims cost ~6-9k each, Heart of Ruin's like Ren's, Stellar's and Ryth's. Then, by the rules:
   - Allies walking in (CHANGES 180) no longer knock plain kits off the plain path (220). `walk_allies_in` still
     ignores walls and the enemies' own approach, and an unseen enemy cancels every delay.
   - Heart of Ruin's passive at its health at event turns (act()'s non-quiet path). HoR holds 31-36% of first
     run-outs: its fight work runs twice as often and costs ~20k a call more (search, sims, stand, want_home).
   - From the fight audit: F4, an event mask in `simulate`'s non-plain branch (members with no cast, shield expiry or
     arrival this turn add Strength in index order): ~30-40% of the 42% loop body at best, and small additions there
     read dearer. Incremental per-side sums for `their_cap`/`overwhelmed`: casts are summed lazily (220); the rest
     changes float summation order (probably identical), up to ~9% of sim fuel.
     Prototype each alone, release, queue off; keep only at -0.3% total fuel or better with replays identical. F2b,
     copying only fighters' mutable state into a sim (28 of 60 bytes, ~200 a sim): measure likewise. F8, `Reach::at`
     hit windows for sight-free ways: optional, measure likewise. Small: Ren in `play_quiet` (1-2% of sim fuel on Ren
     maps); merging `our_strength` and `side_health`. Dropped: F2a (a walk table for `walk_allies_in`, dearer), a
     healer with no target as a non-event (+0.18%).
   - F7, a sim that stops once our fall settles the caller: done for want_home's stand and prey (CHANGES 214). Left:
     step_guard with links (Cassi and Issac), where the fall settles the tile but the `settled` cover reads `lost`:
     not exact, A/B only; at most ~14% of guard sim fuel.
   - Deferred: F5, a damage tape per roster per turn (high effort; only if heavy turns still run out); F3, prey
     skipping a fight covered by a lost one (not exact, 10 of 1134 covered fights were not lost: A/B only).
   - Ground AoE, Varg splash, HoR landing and Ren reflection per target, not single-target.
   - Once we fall, the sim's camp hits go to our weakest, not the next-nearest champion (sound, not the rule).
3. One danger model (STRIKE-SEARCH phase 5, [DANGER-MODELS.md](DANGER-MODELS.md)): one danger pass per tile per turn
   across want_home, step_guard and the search's end tiles (the fight audit's F6: 4-8k a heavy turn). Memoising the
   current passes saves nothing (few repeats); the gain is in folding them. Fold in: dash-landing `danger`,
   `shield_if_needed` and `breach` fire from `Safety::awake_members()` (nearest-champion cut, stuns), damage-weighted;
   Reach's enemy dash paths crossing our spawn (exact) and our champions (only those the enemy sees; rare).
   The fight turn is half the run-outs (census above). Measured 2026-10-29, after CHANGES 218:
   - Heavy strike searches: price 24.3k (mostly `resolve_guard`; the step guard is 65% of the fuel of searches over
     60k), read 11k (`read_geometry` 5-6k, of which guard cover 2.4k; dash-path blockers only on a turn that can
     dash since CHANGES 225), grow 9.5k. 69% of searches end empty (57% of search fuel) and
     can't be skipped (they set `searched`): can emptiness be proven cheaply and exactly? The search never sims our
     start tile.
   - want_home ~24k a heavy turn: outmatched 3.9k, camp_trapped 2.4k, lethal 6.5k (4.8k first-touch Reach builds),
     stand 10.1k (its walkers/camp trade sim 7.3k mean, 15.3k when run, in 28% of calls: a fight nobody else asks;
     settling it from the guard's fights is not exact, the sim is not monotone). Sharing want_home's lethal/stand with
     the search's lethal/damage bound: 2-4k on HoR heavy turns.
   - prey 28.7k a heavy turn: `fight_key` 10.9k (first-touch Reach 4.5k and Safety caches), sims 13.7k for ~1
     candidate (0.93 sims a call).
   - Step guard builds: 2.8% of all fuel; U1 wins 54% at ~17k, a full build 52.5k (bound 9k, U1 sim 11.6k, exposures
     16k, final loop 14.8k); the U1 sim 9-11k on ~70% of builds, memo hits 15 of 635. The bound phase's own ~2.5k a
     build (ctor `strike_of`, `fight_cost_estimate`, `fight_enemies_any`) could be ~1k cached per turn. A per-tile
     guard query is not exact (94% of priced tiles pass the local filters; exactness needs U1/U2 and the settle chain).
   - Idle searches (no enemy within reach of a hit, landing or unit cast; no heal, shield, splash, Vendetta, ranged
     walk or excl ground cast) skip read/grow/price exactly: CHANGES 222, ~35% of searches at ~11.2k each, -0.9%
     wide and -1.25% OOF set over m4 at 100M, all identical; reverted: its A/B gave +5.9% out-of-fuel turns
     (+2.7% without shared-gems, rounds 300+ and long run-outs up). Unexplained (untested guess: the saved fuel lets
     gated work run that then runs out, the gates as brakes, item 4). Retry once that is understood.
   - Smaller: an exact price skip for a start-tile-only or one-candidate search (~1.5k on ~35% of searches); a per-turn
     `viewers()` grid (<= 1.4k a heavy search); `camp_at` in price prep (0.5-1k); price's own ~7k; kite's `make_way`
     `know_failure` 8.5k (~30 turns a game; needs a narrower design; a repeated failed search now reuses its labels,
     CHANGES 224, and `make_centre` no longer doubles capped tries, 223).
   - Dropped: a lazy step guard (~0.01%), undoing only live health slots in grow (+307 a search), sharing the cover
     between search and route (+0.01%), a failing-route memo for kite (no hits).
4. The remaining gates, one at a time with an A/B: step-guard, prey-cut-short, ward, comms-stale-vision, turn-order.
   Narrowing step-guard and prey (CHANGES 176: the gate after the bounding pass, the sticky `costliest` decayed on
   skips, lost prey fights skipped before the margin) halved step-guard firings but cost +10% out-of-fuel turns
   (step-guard part) and +16% with the prey part, on fight maps: reverted. These gates are the fight turns' brakes
   until the sims are cheaper (item 2). Retested after the late finish (CHANGES 217): all removed gave 6.0x/4.1x the
   out-of-fuel turns, each alone up to +143%; ward alone was level (A/B 49.9%, no gain). The gates are real brakes
   even without livelocks ([FUEL-GATES.md](FUEL-GATES.md) has the table). Next: one combined A/B removing ward,
   fight-cut and siege-route-fuel (expect no win gain); turn-order once its offers are bounded (below).
   Measured end-of-turn costs (100M, wide):
   observe + send mean 1.9k, p99 3.8k, max 6.3k against what was a gate of 1000 a champion + 10k (CHANGES 177: 10k); `set_turn_order` p99 4.6k,
   max 23k against 10k; `ward_bushes` once clusters are found p99 7.4k against 15k. `ward-no-bushes-clusters` in
   rounds 2-10 waits on `grow_cluster`'s 2-word batch floor (~16k over its floor; a smaller one needs a minimum step).
   - `fuel_ok` could throw `StaleTurn` when fuel rose since its last read this turn, as the farm loop does (CHANGES
     178): covers prey, step-guard, ward and the queue in a stale tail.
   - Step guard: a per-tile query to recover searches whose guard is read later anyway is not exact (item 3). Routes
     skip a guard that cannot change them while `step_guard_costliest()` >= 15k (CHANGES 215); 10k might win back
     turns over 100k (without the threshold, the OOF set at 100M had 10603 against 11037, at +0.28% wide fuel).
   - turn-order: its tail is the offers, not `find_members` (~4% of its calls start there): `offer_escape`'s
     `threats_at` Reaches 9-14.5k (a one-tile blow helper outside Reach would bound it), `offer_kills` up to 10k,
     `offer_heal` 5-11.5k (both via `side_damage`), `may_escape`'s `strike_of` per enemy 2-4.7k (a cached reach/damage
     table, 1-3k). Smaller: `find_members`' per-member host calls ~300 a member (stun buff only for visible near
     members, up to ~2k on arena turns). Dropped: lazy Reaches in `offer_escape` (+0.5% turn-order fuel,
     unexplained), shared turn ranks (+0.02%), a box filter for all groups.
5. Strike phase 4a's retreat-search fuel (40.8% real, 52.6% at 100M; `orch/strike-p4a-wt` bdb5902 holds an untested
   partial fix), then 4b (`orch/strike-p4b` 6997211, untested).
6. Stellar/Ren compositions and enclosed maps (fortress, lanes, caves, maze, sparse camps): against hecate, first deaths
   came from worse fights (outnumbered, struck first), lone champions picked off in tunnels.
7. Monolith and big-group captures: more Monolith damage than hecate but fewer captures (40 vs 58); big groups woken
   and left to sleep again (archipelago, 00contest). The strike search still bans waking a Monolith: price it (the
   allies' and the farm's cost) now that the wake counts the rule's hits (CHANGES 179).
8. `tools/ab.py` fuel per side, to measure what fuel costs one bot (out-of-fuel turns per bot: `tools/fuel/oof_bot.py`,
   since 2026-10-29). `tools/fuel/bench.py --release` (the fuel audits
   used a copy) and a `--no-queue` option, so fuel-only work is judged on ladder codegen.
9. Edge-case maps (EXPERIMENTS "Edge-case maps"): stalls left after CHANGES 145-147, by `tools/replay/stalls.py`.
   Farm starved of fuel on big mazes: the width + height search cap is fixed (CHANGES 158); what stays is serpentines
   of 600+ layers whose estimate never fits a turn ([portals.md](draft-compute/portals.md)). 1v1 contest standoffs;
   farm hops' pocket deaths (no retreat from a pocket), no gold for a crystal while an ally takes the gold camps, a
   crystal rebought on every spawn visit.
   - Off-foot islands (crystal or dash) hold 12% of champion deaths in 2.2% of the time alive (x21.8); walkable
     dead-end pockets die at the base rate. Champions know these regions (`StaticMap::hops()`): price the hops and
     farming there ([chokepoints.md](draft-compute/chokepoints.md)).

10. Bookkeeping outside `decide` (the arch audit; ~25k of a 126k heavy turn; ~19k now):
    - Profiled (2026-10-29, heavy turns in rounds 300+): `World::update` 14k (enemies 4.9k, of which track 3.4k;
      allies 2.25k; `update_camps` 3.4k; `rank_turns` 1.66k, stale on 95% of turns; priorities 0.84k; altars 0.38k),
      comms receive 2.57k (urgency 1.19k, sightings 0.83k), send 2.07k with observe 0.75k. `rank_turns` per team,
      allies' payload-only changes skipped: CHANGES 221 (exact, -0.6..-0.7% total).
    - Biggest left: windowed dilation for track on 100x100 (WASM per chunk word over the bounding chunks), 2-4k a heavy
      turn there; hours. Each < 1k: one `board_awake_camp_occupancy` read a turn in `update_camps` (A2;
      CAMP-AWAKE-MISMATCH makes it exact), a settled-check cache there (~0.3k), merging `rank_turns`' passes 0/2 and
      1/3 when keys equal (~0.5k), urgency as SoA (~0.3-0.5k), ally emblem reads (~0.1k an ally).
    - A3/A4: exact sim memos across a stale turn, filled by queue speculation. First measure, at the real budget on
      gen-chambers, the share of a post-out-of-fuel turn's sim keys (absolute rounds) that match the abandoned turn's.
    - A6: a cheaper `StaleTurn` unwind (catch near `play_turn`, fewer RAII frames). Measure the throw depth first.
    - After the unity build (CHANGES 190): `[[gnu::always_inline]]` on hot cross-file helpers the inliner still
      declines (`-mllvm -inline-threshold=1000` was -0.8%, unshippable), and recheck the `[[gnu::flatten]]`s
      (farm_turn, wants_shop, update_camps, comms), which now reach across files.
11. Melee kiting (CHANGES 201): verify it or generalise it. Verify: an A/B on a second fresh shared-gem set
    (`mapgen gen shared-gems`, new seeds; the first set gave 59.2% of 120) and a full-suite check that off shared-gem
    maps it is level (the logic is gated, but the unity build's fuel shifts changed 41 of 1164 games). Generalise: the
    same rule (spells out-damaging basic attacks) wherever melee champions choose between casting from range and
    meleeing, e.g. siege and farm on every map, and Ryth's camp damage collapse on starvation, road-of-riches,
    reverse-spiral, shortcut, oasis and gold-rush (night1), none of which is a shared-gem map, so 201 cannot explain
    it.

## Warm-up follow-ups (CHANGES 164-169)

The warm-up and end-of-turn queue no longer change play (52/52 bench replays identical with the queue off). Left:

1. **Early out-of-fuel turns since CHANGES 166.** Against f9d2e26b (before 166), rounds 2-10 ran out ~500 times
   against ~280 (A/B `wq-head-vs-f9d2`); overall ~7-10% more, across runs. Not cold centre fields: CHANGES 169 warmed
   them by round 6 (median, was 41) and rounds 2-10 stayed 507 vs 505. They cascade: most round-2 cases follow a
   round-1 one, and round 3 follows round 2 twice as often as before. Next: a fuel-exact trace
   ([tools/replay/harness](../../tools/replay/harness/README.md)) of a few round 2-4 turns that run out, on
   gen-dense-camps, gen-archipelago and gen-city, to see which build spends the fuel. Suspects: reads that now build
   inside `decide` (centre fields in `approach_steps` and `walk_on`, the spawn-centre field in `centre_to_spawn`, group
   hops on round 2), and `prepare_walk` running every turn without its 40k floor (CHANGES 167). The fuel census
   (`tools/fuel/census`) now records the scopes open where fuel ran out; rounds 2-10 are ~7% of run-outs at m4.
2. **Shortcuts firing more often.** In CHANGES 168's A/B: `crow-flies-farm` 4856 vs 45 in rounds 61+ (1838 on
   gen-gem-centre), `farm-partial-evaluation` 58k vs 38k, `ward-no-bushes-clusters` 2802 vs 2368 in rounds 2-10.
   Recount after 169 (`py tools/replay/debug_lines.py SHORTCUT -- <batch>`); what remains is fuel changing play.
3. A caught `engine error 5` in the queue's `prepare` on gen-labyrinth-102106300, side b, round 756 (since 9be0f154).
   No play change seen; find the call.
4. Centre fields (p1 W1, `orch/p1-w1-fuel-full`): drafted spawn steps before the centre field (F4) and `from_here` as
   a Pathing slot (F5) pay only once the farm loop has a cheap lasting source off spawn; where the queue never warms
   centres (gen-gem-centre) the loop rebuilds `from_here` (~34k) every turn. Building `to_any_altar` and the
   spawn-centre field early in the queue delayed centre fields (rounds 3-30 worse).
   - Centre fields still finish late on big maps (dense-camps rounds 210-470, star 117-250): farm steps 17.7k a call
     before round 300 against 5.5k after. A capped `from_here` that grows its cap (W18,
     `worktree-agent-ae9b0e21ac339dae6` 856d37cf + 17c14370, exact, not merged): many-group rounds 2-10 over 100k
     373 -> 269 (-0.56%), but wide and OOF set +0.05% and their rounds 2-10 over 100k 153 -> 203 and 136 -> 196
     (untraced: queue drift or regrowth). Trace that before retrying; building centre fields nearest-first earlier is
     the alternative.

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
- Assumption audit leftovers (EXPERIMENTS "Assumption audit, batches 1-2"): batch 2's P3a (`cb821d93`, shared
  clears by stand-tile fire), P3b/P4 (`793e3f38`, fire handed to teammates in steps; lethal camp tiles in retreat)
  and P5 (`2d5ae48c`, Heart of Ruin's scaling in Trade) lost together: ladder -8 points, out-of-fuel turns +40%.
  Branch `audit/batch2` (origin) holds them rebased (`c5b48d34`, `b63665a2`, `908ac3a4`). Split them one at a time
  on the ladder, bench P5 first (it keeps Heart of Ruin fights off `play_quiet`), then fix or drop each. Also: P3a
  prices heal trips only for shared clears; a narrower `recall_outruns` camp check (C, reverted).
- Known bugs, unverified: retreat_step walks back into an Elk's reach when the way home passes it (`recall_outruns`
  ignores camps; P4 above tried a fix); idle turns under a Golem (dense-camps).
