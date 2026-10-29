# Fuel campaign 2026-10-29: open minor items (folded into TODO.md at the end)

## From round 1 W2 (fight sims; branch worktree-agent-aaa2cfd272b35ad94, e5738a7c)
- Sim profile (4 OOF maps, 17.5k sims, ~6.2k each): event-turn act non-plain 31% (~447/call, 4.3/sim), plain 11%;
  early-end checks (their_cap/overwhelmed) 18.5% (~500 each, 2.3/sim); hurt+Ren 10.6%; play_quiet 6.5% (so a closed
  form for quiet stretches caps at ~6.5%). By caller: guard 33%, stand 40%, chase 27%. Post-fall fuel 14-19% of sims.
- F7 for step_guard when linked (Cassi & Issac): fall settles the tile but `settled` cover reads `lost`; not exact,
  needs A/B; <= ~14% of guard sim fuel.
- Incremental per-side sums for early-end checks: changes float summation order (probably identical); up to ~9% of sim fuel.
- F4 event mask in non-plain path: ~30-40% of 42% loop body at best; small additions here read dearer.
- Dropped: healer-with-no-target as non-event (+0.18%).
- Tooling: worktree benches can't build MAIN/bots/variants/astraeus-8ec2c4d (CMake cache); copy its src/ into the worktree's bots/variants/.

## From round 1 W3 (bookkeeping; branch worktree-agent-a86b640c0af2425fb, 63bc9db9 + c93d3335)
- Heavy OOF turns (>100k, mean 123k): World::update 15.6k (champions 7.3k, track 1.7k; update_camps 3.4k;
  rank_turns 2.3k, stale 95%; priorities 0.95k); comms receive 3.6k (urgency 2.4k), send ~2k; threat build 1.8k;
  decide: search 21.5k, farm 17.3k (30k/call), chase 13.7k, siege/kite 6.6k, want_home 5k, turn order 4.3k.
  100x100 heavy: farm 37k, update 15.6k, unseen enemies 5.5k. Round 1: farm 63k, build_static 37k, siege 16.6k, ward 9.4k.
- Windowed dilation for track on 100x100 (WASM per-chunk-word over bounding chunks): 2-4k/heavy turn on 100x100; hours.
- Comms urgency: per-mate precompute + stop at best=0: ~-1k on heavy OOF turns.
- update_camps single awake-board read (A2): < 1k.
- rank_turns passes 2-3 reuse: < 1k, rare.
- Real-budget OOF on gen-shared-gems-8280101604 is bimodal: a rerouted game flips 1.3k <-> 2.4k OOF. Judge OOF without it too.

## From round 1 W1 (streaks; branch worktree-agent-a204160a3a1942825, e0d7f225 + 05ea78d7)
- Streak = Vesper kite hold at shared gem camp (8280201605 B champ 6): kite() step_towards spell stations unreachable;
  route() forced step_guard (~51k) each turn. In 8280101604, strike-search "price" includes resolve_guard (~44k).
- Threshold 15k for the unguarded/covered probe searches; 10k might win back OOF >100k (one wide + one OOF run).
- e0d7f225 alone gave OOF >100k 10603 (vs 11037 with the threshold) at +0.28% wide.
- step_guard_costliest() now has a second (non-deciding) reader: keep in mind when deleting the estimator with its gate.

## From round 2 W4 (farm loop; nothing merged; banking stop parked on fuel/farm-bank-stop a6035eda)
- Profile (heavy set, 8 maps 28-106 groups from replays/fuel/gates/base-heavy-100M.json): banking calls ~40% of calls,
  ~50% of loop fuel, 48k/call, all 74-79 groups reach facts; non-banking 27.5k/call. Pruned group ~230-300, faced
  group ~600-900. Round 1: 24-28k pre-loop + ~50k loop; round 2: 13-15k + 49-55k.
- Banking stop (exact, a6035eda): +0.18% wide (codegen of flattened farm_turn; dense-camps -1.2M/game). Retry with the
  banking branch out of line.
- Centre fields finish late on big maps (dense-camps r210-470, star r117-250): steps 17.7k/call before r300 vs 5.5k after.
  Ideas: capped from_here that grows its cap; build centre fields nearest-first earlier. Several k/call in rounds 2-300.
- farm-partial-evaluation removal blocked: 60-80 groups touched at 300-900 each.

## From round 2 W5 (end-of-turn; branch worktree-agent-af14ee7544f959eef, 7997a9ed: may_escape lazy camp_damage, comms urgency lazy + stop at 0, ward_bushes bush check first)
- Ward gate removal on top: OOF +6% (w/o bimodal), turn-order +15%, prey-cut-short +23%. Not kept.
- set_turn_order tails: find_members ~10k as first caller; offer_escape threats_at full Reaches for one tile (max 13k);
  offer_kills (14k) / offer_heal (11.5k) via side_damage next_strike/strike. Bound these before the turn-order gate.
- Comms urgency pair loop ~1.2k/turn on fight maps (SoA loop -0.5-0.8k); receive outside urgency ~1.5k; observe 1.9k.

## Merge round 1 (CHANGES 214-215; frozen bots/variants/astraeus-m1, -m1b)
- A/B m1 vs 8ec2c4d: OOF 15809 vs 19568 (w/o shared-gems pair 8342 vs 8760). m1b vs m1: 18590 vs 18754 (8104 vs 7970).
- The same build reads ~5% differently depending on the opponent: sub-1% fuel cuts won't show in OOF counts.
  To halve OOF we need ~20-25k off heavy turns (mean ~123k): structural (one danger pass, TODO 3) rather than trims.

## Orchestrator finding (m1b A/B): real-budget livelocks
- 37k OOF; 40 champion-games with >=50 OOF hold 64%; ~8 champion-games ~2000 each (shared-gems maps).
- e.g. 8280201605-12 team b champ 6: last D/SRCH in r83, then OOF in decide every round r85-end (1745). The champion
  never finishes a turn, never moves, and the same over-budget turn repeats. Assigned to round 2 W9.
- W8 (find_members / turn-order tails) paused at its start (agent aae33a7b702857c54, worktree kept); resume later.

## From round 2 W7 (strike search; no commits)
- Heavy searches (>60k, mean 94k): step guard 61k (65%; resolve_guard in price 53.5k, guard/cover in read 7.7k). Own work ~33k.
  All searches mean 21.5k: guard 8.4k (39%).
- 69% of searches end empty (57% of search fuel); can't skip (sets `searched`).
- Minor: exact price skip for start-tile-only/one candidate ~1.5k on ~35% of searches (part moves Reach builds later);
  per-turn viewers() Grid cache <=1.4k/heavy search; cheaper camp_at in price prep ~0.5-1k.
- Dropped: undo only live health slots in grow (+307/search; SIMD copies are cheap).

## From round 2 W6 (step_guard; branch worktree-agent-af42f57f0256e2040, 783c917e lazy fight keys in the bound loop, exact; on top of merge b1b42c23 of W1+W2)
- Guard phases: ctor 1.4k, bound loop 7.5-8k (keys ~3k, now lazy), U1 sim 7.7-9.9k, exposures 7k, final loop 8.9k.
  Stage 2 (U1 won, empty guard) = half of guard fuel. route() 55M, resolve_guard (plan.cc:1852) 31M, steppable 16M of 109M.
- Per-tile query not viable exactly: 94% of priced tiles pass local filters; exactness needs U1/U2 + settle chain.
- Next design: lazy guard object (A: bound+U1, B: exposures+U2 full on first query; final sorted loop only up to the
  queried tile); check std::sort determinism for <=24. Saves ~9-14k/1852 call when no later full read.
- Dropped: failing-route memo for kite (no hits; loosened +0.34%).
- siege.cc:279 forces guard to test own tile (never guarded when here==guard_here_): <0.05%.

## From round 2 W9 (livelocks; branch worktree-agent-afdaa0fd4e2a53fb5, e78239e6 + fca0b3bd: finish_late)
- Root cause: CHANGES 59's replay-from-scratch after OOF; replays as dear as the original livelock forever.
- Livelocked turn (3 enemies close): update 12-17k, comms 3k, want_home 35-40k (outmatched 4k, camp_trapped 7-8k,
  lethal 5-10k, stand 11-18k), search read 15-17k + grow 7-9k; ~110k total. -> want_home assigned to W11.
- Remaining shared-gem streaks alternate OOF/late finish (60-250 per champion-game).

## From round 2 W8 (find_members; branch worktree-agent-aae33a7b702857c54 = main + W5 merge fff7b06a + 3c5a62ce per-group member boxes, exact, -0.07%)
- Only ~4% of find_members calls start in set_turn_order. Turn-order tail is its own: offer_escape threats_at Reaches
  9-14.5k, may_escape strike_of per enemy 2-4.7k, offer_kills up to 10k, offer_heal 5-11.5k.
- One-tile blow helper outside Reach (bounds offer_escape 9-14k worst); cached reach/damage table for may_escape (1-3k);
  find_members per-member host calls ~300/member (stun buff only for visible near members, up to ~2k arena turns).
- Dropped: lazy Reaches in offer_escape (+0.5% turn-order fuel, unexplained), shared turn ranks (+0.02%), box filter for all groups.

## From round 2 W10 (opening; no commits)
- Round-1 OOF ~20-24/map on many-group fresh maps; world construction 145-162k before decide on ~100-group maps
  (close-spawns-8280304800: build_static 106k = camp-group member loop 70k + crossings 12k; init_beliefs 31k; mandatory 325k).
  -> assigned to W13.
- Round 1 decide: prices() first call 14.6k (best_emblem), farm loop head ~300/group, post-loop 40k (attack tiles 13k).
- Round 2 heavy: loop head 35-41k (83-98 groups at ~400), nearest_groups(first) 12.5-14k (queue had no fuel in r1), steps 8-18k.
- Capped growing from_here: 3-8k per moving turn on big maps until centre fields warm (exactness needs care; costliest_field side effects).
- Stronger stop bound when far from `first` (r_k - offset collapses): 20-30k r2, ~10k r3-10; not exact as is (tie order).
- Cheaper loop head per pruned group (~250-400): ~30% of 8-15k/turn heavy maps; nearest_groups distance loop vectorisation ~3-4k.
- Dropped: help group only from ally claims (-0.02%).

## From round 3 W11 (want_home; branch worktree-agent-afcba93f54b6dcad8, 1e6c47ef camp_exit_rounds per-tile test dropped, df81e4b3 in_pack_zone by sums; exact; OOF >100k -12%, p99 -8.2%)
- want_home ~24k/heavy turn: outmatched 3.9k (pack boxes 3.4k), camp_trapped 2.4k (find_members first touch),
  lethal 6.5k (4.8k first-touch Reach builds), stand 10.1k (trade sim 7.3k avg, 15.3k when run; threat build 1.3k).
- stand's walking/camp trade sim 15.3k: sim internals. Reach builds 5.8k/heavy turn (shared).
- Pack-box enumeration 2-4k/round when pack_zone/pack_covers asks: direct per-tile test <= 2k.

## Merge round 2 (CHANGES 216-217; frozen astraeus-m2a, astraeus-m2)
- A/B m2 vs m1b 49.6% (47.3-52.0); OOF per bot (all phases, scratchpad/oofbot.py) 7815 vs 9192; w/o shared-gems 6777 vs 7609.
- Real budget: wide OOF 1247 (base) -> 666; OOF set 8339 -> 2423; shortcuts wide 18883 -> 12688, OOF set 46248 -> 35376.
- Late-finish caveats: OOF phase labels shift to 'queue' (artifact); 78 second run-outs; cleared_by_us stamps round R.
- OOF counts depend on the opponent (livelocks are mutual): compare final main vs 8ec2c4d in one A/B for the headline.

## From round 3 W12 (step_guard; branch worktree-agent-a313d77b56e5a8a11, 51e4c733 bound pass by per-foe cell masks, exact; OOF >100k -9.5%)
- Lazy guard measured: ~0.01% (dropped). Pricing builds: U1-won 54% at ~17k; full 52.5k (bound 9k, U1 sim 11.6k,
  exposures 16k Reach::at, final loop 14.8k). Guard builds 2.8% of all fuel.
- Rest of bound phase ~2.5k/build (ctor strike_of 0.9k, fight_cost_estimate 0.7k, fight_enemies_any 1k): ~1k if cached per turn.
- U1 sim 9-11k on ~70% of builds, memo hit 15/635: fight-sim side.

## Checkpoint A/B m2 vs 8ec2c4d (04:25): 50.4% (48.0-52.7); OOF 8270 vs 9803 (same A/B). Baseline A/B HEAD-src read 17282.
- Livelocks are mutual, so REF's count drops too. Headline measure: both vs hecate on test drafts
  (orch-base-vs-hecate running; final-vs-hecate at the end).

## From round 3 W15 (prey/kite; branch worktree-agent-a6c67db5faec2b916, 1a94a726 route() keeps step_guard_cover per round, exact; OOF >100k -6.4%)
- prey on heavy turns 28.7k: fight_key 10.9k (first-touch Reach 4.5k + Safety caches), sims 13.7k, own ~3k. ~1 candidate, 0.93 sims/call.
- kite standoff 44-47k: cover recomputed per route() ~9k x 2.7 (fixed); make_way know_failure 8.5k (narrower design needed, ~8k on ~30 turns/game).
- base-vs-hecate (test drafts) A/B: 8ec2c4d OOF 11101, hecate 2848, win 89.9%.

## From round 3 W14 (Reach; branch worktree-agent-aa616359e302c254c, 323326fe cheaper Reach builds, exact; >100k -2.1%)
- ~3.5 builds/heavy turn at ~1.6k; at() ~11/heavy turn at ~600 (sight lookup ~175, ward check ~90).
- Minor: sight lookup ~500/heavy turn; ward check ~300; ~430 unexplained build setup (objdump); recipe table at compile time ~400.
- threats_at in turn order built ~0 Reaches on these maps (W8's 9-14k tail must be elsewhere/rare).

## Headline checkpoint vs hecate (test drafts, 1676 games): 8ec2c4d 11101 OOF -> m2 8701 (-22%); hecate 2848 / 2738; win 89.9 -> 90.0%.
- m2's OOF: rounds 300+ 5495 (63%); champion-game sizes <10: 4970, 10-49: 3106, >=50: 625 (base 2129). Diffuse now.
- 100M per-round: over-100k 4-5.5% from r61 on (OOF set), no late-game growth. p90 ~87-89k everywhere = the turn-end
  queue filling spare fuel (mean/p90 metrics include it by design; OOF and >100k are the real measures).

## From round 3 W13 (world construction; branch worktree-agent-afd8584b6a21ebdc4, 6 commits b73d505b..917c15ed, exact; many-group r1 mandatory 325.6k -> 306.1k)
- Cost is WASM instruction count (~145 instr/member, ~250/group overhead), not host calls.
- Still >200k on ~100-group maps: round 1 always runs out there. Round-2 mandatory 167k (deferred fields, dash foot).
- Minor: ChampionBelief() {} (~1.2k r1); plan section 15k on 102 groups (fixed_steps(0) eager decode).
- "OOF 2 queue": probably the late-finish label artifact (the OOF line names the last phase reached). Tooling item:
  record the phase where fuel ran out, not the phase at the turn's end.

## Merge round 3 (CHANGES 218; frozen astraeus-m3): 100M OOF set >100k 11851 -> 9061, p99 147.3k -> 133.5k; wide >100k 3615 -> 3300.
- A/B m3 vs m2 50.3%; OOF 6775 vs 7511 (w/o shared-gems 5945 vs 6597). Real budget OOF set 1948 (m2 2423, base 8339).
- Pending for round 4: W13 b73d505b..917c15ed (world construction).

## From round 3 W16 (sims pass 2; branch worktree-agent-a19ec20ca399a8469: 132b0be0 Ren quiet path, 7e889309 plain path takes arrivals, b6442279 lazy cast sum in their_cap; exact; p99 -0.5..-0.8%)
- Sim profile (test-draft OOF set): non-plain act on non-plain kits 29% (~480/call, 3.6/sim), early-end 13.5%, plain act 7.9%.
- Minor: Ren in play_quiet (1-2% sim fuel on Ren maps); F2b ~200/sim; merge our_strength+side_health.
- Pending round 4: W13 (6 commits), W16 (3 commits).

## From round 4 W18 (big-map farm; branch worktree-agent-ae9b0e21ac339dae6, 856d37cf + 17c14370 capped growing from_here; exact but NOT merged)
- Many-group r2-10 >100k 373 -> 269, -0.56%; but wide/OOF +0.05%, r2-10 >100k 153 -> 203 / 136 -> 196 (untraced: queue stats
  drift or regrowth). Real-budget many-group OOF 130 -> 133.
- dense-camps rounds 11-300: farm ~50k/call, loop visits all 96 groups; the stop bound never fires (suffix bound omits
  clearing time). Head ~265/group -> 12-20k/call. Bound incl. clearing time = biggest farm lever (hours, codegen-sensitive).
- nearest_groups rebuilt on target change: 61 x 12.2k in a game; ~110/group unexplained.
- Dropped: tight skip loop (+1.9% codegen), nearest_groups rewrite (-0.05%).

## From round 3 W17 (gate retest after finish_late; nothing kept)
- Real budget vs m2 (wide/OOF/OOF w/o shared-gems; base 666/2423/1178): all gates removed 6.0x/4.1x/4.4x, OOF-set wins 11/32 vs 17/32.
  turn-order +81/+45/+33%; prey-cut-short +55/+68/+72%; step-guard-* +143/+95/+122%; farm-partial-evaluation +90% wide;
  comms-stale-vision +26/+14/-7%; static-descend +3/+33/+15%; siege-route-fuel ~level but step-guard-entry 3231 -> 6081;
  fight-cut level (rare); farm-no-route/crow/kept +18/-12/-5%; ward level -> A/B 49.9%, OOF +2.1% -> dropped.
- Conclusion: gates are real brakes even without livelocks; removing one shifts the shortfall to the next.
  Candidates for a later combined A/B: ward + fight-cut + siege-route-fuel (expect no win gain).

## OOF census (round 4 W19; tools in replays/fuel/orch/census/, worktree-agent-a487f682c5c4181ed tools/fuel/census/ uncommitted)
- 83% of OOF are first-in-streak; 93% in decide. Classes: fight turns 51-60% (search 32-38k vs 19k on heavy
  finished turns + want_home/stand 17.5k; together in 47% of all OOF), quiet farm turns 24-32% (farm.loop 33k + farm.post 17-20k
  vs 9k finished; farm.post = most common exhaustion point), round 1 6-7%. HoR 31-36% of OOF-first.
- World update flat ~15k (enemies 4.9k, camps 5.0k, rank_turns 2.4k on 89% of turns, allies 2.3k, track 3.8k).
- farm room() reserve (walk_reserve + search_cost_estimate) underestimates the post-loop walk on mazes.
- -> W21 (world update, informed), W22 (search + stand). farm.post next.
- Census tooling should be committed to tools/fuel/census/ at the end (useful for future fuel work).

## From round 4 W22 (search + stand; nothing committed)
- Search never sims our start tile (price = Reach blow + resolve_guard). stand's own sim (walkers/camp; 28% of calls,
  ~10.4k) is a fight nobody else asks; cross-settling vs guard fights not exact (sim not monotone).
- Heavy searches: read 11k (read_geometry 6.2k: guard cover 2.4k, blocked 0.9k), grow 9.5k, price 24.3k (resolve_guard).
- Dropped: sharing the cover between search and route (+0.01%).

## Merge round 4 (CHANGES 219-220; frozen astraeus-m4). vs 8ec2c4d at 100M: OOF set >100k 11851 -> 8827, p99 147.3k -> 132.5k, total -2.47%;
  wide >100k 3615 -> 3220, total -0.77%; round 1 mean many-group 330.5k -> 311.1k.
- A/B m4 vs m3 50.7%; OOF 6703 vs 6805 (w/o sg 5597 vs 5859); round 1 483 vs 603.
- Real budget OOF set 1732 (base 8339), wide 710 (base 1247); shortcuts OOF set 30430 (46248), wide 14239 (18883).

## From round 4 W21 (bookkeeping 2; branch worktree-agent-aaf29e6613c7f2451, b2e0de09 rank_turns per team, ally payload bits ignored; exact; total -0.58/-0.72%, heavy -140)
- Heavy r300+ bookkeeping: World::update 14k (enemies 4.9k: track 3.4k; allies 2.25k; update_camps 3.4k; ranks 1.66k;
  priorities 0.84k; altars 0.38k); receive 2.57k (urgency 1.19k, sightings 0.83k); send 2.07k incl. observe 0.75k.
- Minor: merge rank passes 0/2 and 1/3 when keys equal next (~0.5k); update_camps settled-check cache (~0.3k);
  urgency SoA (~0.3-0.5k); ally emblem reads (~0.1k/ally); windowed track dilation on 100x100 (biggest, hours).

## Checkpoint m4 vs hecate (06:30): OOF 7897 (base 11101, -28.9%); win 91.5% (base 89.9%). Buckets 300+ 5249 (7455), r1 396 (528).
- Next: empty strike searches (69% of searches, 57% of search fuel; W7) - can emptiness be proven cheaply and exactly?

## From round 4 W20 (farm stop bound with clearing time; cd1e6ef5 reverted; not merged)
- Exact clearing-aware stop: heads 73 -> 31/call on dense-camps, but stop_from 12.5k (class tables per `first` 4.2k,
  hurt scan 2.1k, class search 6.2k) > savings: +0.6..+1.1% mean. best_value is final at position ~5.4.
- To pay: tables per map not per `first`; world-maintained hurt bitmask; check the bound only at the old stop. Ceiling ~11k/call.
- Banking calls (~1/3, ~49k each, 96 heads + 93.7 bodies) have no bound: the bigger farm target.

## From round 5 W24 (Heart of Ruin; nothing committed; scripts scratchpad/hor/)
- HoR heavy turns: decide 93.5k vs 89k others; extra is fight work (search 21.9k vs 14.4k, sims 16.8k vs 13.6k, stand
  10.5k vs 7.3k, want_home 8.1k vs 3.9k: ~20k/call, run twice as often). HoR sims ~8.5-9.3k each, like Ren/Stellar/Ryth.
- HoR search 42.9k (read 11.9k, grow 11.2k at ~1.2k/node over 9 nodes, price 19.2k mostly Reach blow). Landings cheap.
- Scaling already fixed per fighter at build. Open: want_home lethal/stand vs search lethal/damage_bound sharing (2-4k
  on HoR heavy turns); read_geometry ~5k/search (all types); price's own ~7k (inst4.py ready); act micro-cuts.

## From round 5 W23 (farm.post; nothing committed; scratchpad/post/)
- farm.post mean 8k; >=10k turns 15.9k (route() 8.2k, host search 5.2k); quiet 17-20k turns = one live route search
  (step_towards(off_zone(goals)) farm.cc ~1185, 9-13k at 35-58 layers). Turn-start field not reusable (ignores units).
- kept_steps rejections: goals differ 2781 (repeated failures), new wall below steps 1170, >4 changed tiles 866, ...
- >=30k turns: failure cascade (attack-tile route fails -> adjacent fails -> walk_on approach field -> descend fails ->
  field route fails -> wide route fails), ~36k/turn repeated while blocked (labyrinth 49-53k/turn). -> W27.
- Dropped: exact failed-search cache (no gain: walls include all visible units).
- Minor: kept_steps 4-tile limit tied to search_cost_estimate (0.3-0.5k maze turns); walk_on centre-field doubling (41k once).

## From round 5 W27 (cascade; branch worktree-agent-ac170d8185cca389c, addc3f50 + a0b14c30 failed-search memo, exact)
- Cascade repeats are exact duplicates (same goals/walls/tile), not goal subsets. Maze set >100k -2.4%, p99 -0.7%, 7.7k
  saved on 434 cascade turns; wide flat, OOF +0.03%. For the final merge (worst-case priority).
- Open: wide probe at here+96 (82 x ~16k on 4 games; needs a resumable deeper search); grow_centre doubling cap (~13k once/group on mazes).

## From round 5 W26 (windowed track dilation; 8efece83 WIP reverted by 17cd4b18; nothing merged)
- Grow cost: 0.4-1.2k on 36-wide, 0.9-3.3k on 68-80 wide; ~1/3 of grows on big maps span the whole map after a recall.
- Host board op ~1/chunk + 15; capped field ~20/chunk; WASM dilation ~45-50/chunk/step: window wins only under ~13-22 chunks.
- NOT exact: host boards carry padding bits (edge-chunk padding + extra stride column). open_for_them/land/unseen_ have
  padding set; shifts treat padding as tiles and MAY leak it back onto the top/right edge (possible existing over-approximation
  in dilate; unconfirmed). Fields/ReachableMask fill padding inconsistently. Needs a probe (tools/probes) before any windowed version.
- Partial win: window only on maps with no padding (dims multiple of 8, stride == chunked_width).

## From round 5 W28 (banking stop out of line; branch worktree-agent-acbabc9c6b80564b1, 8eaeb92e + 14a5d420, exact)
- >100k: many-group 3707 -> 3533, OOF 8827 -> 8822, wide 3220 -> 3205; total +0.01/+0.02% wide/OOF, -0.40% many-group;
  many-group p99 +0.7%. Included in the final merge (worst-case priority).
- Minor: pass prologue values to the banking instance (few hundred/banking call); tighter altar bound needed for the stop to bite.

## Probe (branch worktree-agent-a437e03490d68af60, a8b354f8 probe-padding + README): padding NEVER leaks onto the map via
  host ops (shifts drop off-map sources); count/is_empty/==/positions_into ignore padding; fill/~/reachable_tiles/
  distance_field visited write padding; clear/shadow_cast/draw_chebyshev/set leave it clear. No tracking bug. A windowed
  grow must mirror padding writes to be byte-identical (or compare on-map bits only where nothing reads raw words).

## From round 5 W30 (branch worktree-agent-a6f347f86b02d271f, b11385be make_centre one uncapped search, exact; labyrinth first-approach turns -20..-25k)
- Open: warm_centres' gated doubling tries waste failed tries too (~20k/group in the queue); a cap bound changes real-budget timing (A/B).
- Final merge queue: W27 addc3f50+a0b14c30, W28 8eaeb92e+14a5d420, W30 b11385be, probe a8b354f8, W29 (pending).

## Merge round 5 (CHANGES 221-222; m5a = rank_turns only = main's bot)
- Idle strike-search skip (0e04ac6d): exact at 100M (wide >100k -8%, OOF -6%) but A/B OOF +5.9% (7053 vs 6657; w/o sg up too);
  reverted. Hypothesis: freed fuel lets gated work run then run out. Exact cuts need the A/B too.
- m5a vs m4: 50.4%, OOF 6453 vs 6658 (-3.1%).

## Phase 2 D (round 1; branch worktree-agent-ae38953db5d45c2ed, 315b96cd `late` starts true: round-1 late finish)
- BEHAVIOUR CHANGE at real budget (identical at 100M, +15 fuel round 1). Many-group real: OOF 222 -> 177, r2 53 -> 0,
  all round-1 run-outs act by r3. OOF set 1977 -> 1954. Needs its own A/B before merge.
- Round 1 needs ~-110k to fit; lazy camp layout only ~20k+23k; draft certificate per-group not sound (nearest-first order + stop index is).
- Open: stale check after farm post-processing (stale tails waste up to ~75k for non-dashers); build nearest_groups in the
  late-finished round-2 queue.

## Phase 2 A (sims/guard; branch worktree-agent-a7053cae46ab286c8, 27d4c9bd tools/fuel/simprof only; no bot change)
- Heavy turns ~2.3 sims (16-20k). Share of sim fuel: stand own 37%, guard U1 18%, chase fight_of 18%, chase own 13.5%,
  guard tile 9.6%. Identical sims within a turn 0.6-0.9%; same roster diverges at half-turn 0 (95%); per-side reuse <18%.
- Dropped (exact, dearer): "we wipe them first" bound (+0.27%, p99 +1.8%; casts and deaths decide fights);
  re-running early checks as horizon shrinks (+0.05%).
- Next: resumable fight memo (0.6-0.9%); F4 event mask in non-plain act (only lever >1k/heavy turn); fewer stand sims
  (decision-level, A/B).

## Phase 2 B (the CHANGES 222 puzzle; no commits; worktree-agent-a653d7d8603d5bbe1)
- Idle-skip turns almost never run out (62 of 148k). The extra OOF is on non-idle turns and all in streaks (>=10/champion-game:
  +784, CI [+281, +1341]); scattered OOF fell (-184). Reproducible across m5-derived variants (not noise).
- Rejected: freed fuel feeding gates (V5 phantom-fuel variant: no change); step_guard_costliest decay (V1/V3: no change).
- Found: every real search costs +365 more (+667 after an idle turn: cold terrain_grid/viewer_rows caches), all in
  read(), from the read_self/idle/foe_read restructure. So the cut moves cost onto fight turns, the only ones that run
  out. Mechanism not fully proven (+400 seems small for +6-10%; maybe amplified via late-finish streaks).
- Lesson: judge exact cuts also by the turns that got DEARER (bench compare "cheaper N, dearer M"), especially fight turns.
- Candidate V6 (worktree bots/variants/astraeus-m5-v6): idle test inside the original read(); 16/16 identical, mean
  -0.5%, p99 -1.6%, non-idle overhead +140. Next: warm the per-tile caches on idle turns, cheaper idle(), then A/B vs m5a.

## Phase 2 C (farm; branch worktree-agent-a107cc154e7147021, 992b9ad3 clearing stop + revert 6d5c0160; no net change)
- Farm loops ~29% of fuel on many-group maps. Non-banking: 71 heads (~330) + 9.6 bodies (~1.6k), 32k/call; banking:
  83 heads + 83 cached bodies (~570), 50k/call.
- Clearing stop (classes per map, cached full-health flag, search past help_radius): heads 71 -> 42, many-group -1.3..-1.5%
  but wide +0.5%, OOF +0.25% from flattened farm_turn codegen (stop present but off: still +0.54%). Real many-group OOF 109 -> 183 (12 games).
- Banking bounds: bodies 83 -> 13 but loop fuel up (check costs as much as a cached body). Tighter altar bound ~-0.5k/call.
- Next: keep the hot loop's code literally unchanged (stop inside out-of-line stop_from), or tame [[gnu::flatten]]; cache near
  bodies (~1.6k: min_camp_damage, spell_clear_rounds, steps) per belief version.
- Trap: cambc run rebuilds per game; bench frozen copies, never the live bots/astraeus.

## Phase 2 E (small leads; branch worktree-agent-a6f9f633399bc0c19: 2149caa9 warm_centres one capped field per try, 6400ac27 emblem reads from counts; exact)
- 100M: wide -0.12%, OOF -0.17%, >100k 3121 -> 3105 / 8557 -> 8502. Real OOF set (vs m7 run 1939): 1767 (-8.9%), shortcuts -3.5%.
- Dropped: windowed track dilation (now exact via on-map source masking; but kernel ~400/call + 180/chunk/step: +1.1%);
  kite know_failure (1-4 times a game; exact cut changes guard deferral); comms urgency.
## Phase 2 A/B checks: m7 vs 3938c0f 50.8%, OOF 3576 vs 4635; 8ec2c4d vs 3938c0f 50.4%, OOF 4721 vs 4627 (fuel work -24% vs a fixed ref).
  Ladder 42.1% (m7) vs 49.3% (8ec2c4d), 140 games each (~1.2 SE): check with a fresh ladder-mutation suite.
