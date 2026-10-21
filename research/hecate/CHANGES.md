# hecate change log

hecate starts as nemesis 2dba924 (frozen as bots/baselines/nemesis-v2). Results are hecate's win rate vs
nemesis-v2, all maps both sides (main = replays/allmaps 390 games; fresh = replays/fresh 356 games).

1. Camp stuns and Monolith range-4 sieges (from bots/variants/hx-casts5b).
   - abilities.cpp camp_cast: a stun is worth the member's Strength when any visible ally is within its reach;
     a damage-free stun that keeps the walk (Cassi) is cast at value >= 1.
   - bot.cpp siege(): a ranged caster with no melee ally next to the Monolith casts from range 4, out of reach.
   - Monolith-only maps 70.7% (184 games); elsewhere level (main 54.4%, fresh 52.2%, extra fresh 46.1%).
2. Shared-gem maps: kite the shared block (from bots/variants/hx-maps2).
   - bot.cpp shared_gems_map() (every gem source a big non-Monolith group or a Monolith); kite() replaces siege()
     there: everyone to tiles within 4 of the block's hitting monsters but out of their reach, casters cast on
     cooldown (cast_at_camp any_value), ranged basic-attack harmless clusters safely, set out for a respawning
     block within kite_early 10 rounds of arrival, nearest 3 capture, contest an enemy hold (contesting()).
   - Spell users build Focus and skip Jungle there (spell_builds).
   - Shared-gem maps 77.3% (132 games), fresh shared seeds 73.3% (60); all maps 55.1% vs nemesis, 60.5% vs rival.
3. Farming throughput (from bots/variants/hx-farm8b, merged by patch).
   - emblem_gain_rounds(): rounds the next emblem saves before the race ends; capture_recall shops with a bag only
     if that beats the bag's extra walk via spawn; wants_shop goes empty-handed only if it beats recall + walk back,
     or below shop_heal_fraction 0.6 health.
   - A capture holder hits other harmless or already-awake groups in reach; a melee champion whose hit clears a group
     steps onto its tile the same turn.
   - On plain nemesis: 55.6% main, 56.2% fresh, 55.7% extra suite vs nemesis; 63.6% vs rival; captured gems +2.9%.
4. Camp stun edit (1) limited to Monolith groups: on other camps it cost ~2.5% (hecate 55.3% -> 57.9% on main+fresh+
   fresh-hf without it). hx-c4: 57.0% over 1366 games (main 56.9, fresh 58.1, fresh-hf 58.0, hx-fresh2 55.3).
5. Death avoidance (from bots/variants/hx-s3t, merged by patch; hx-c5 = merged state).
   - step_guard(): tiles a step or ready dash could end on where want_home would leave at once (fight lost with
     them striking first, lethal and we fall, or a Cassi/Issac body falls) are off limits to pathing (set_guard).
   - Safety::pursuit(): we strike first, visible enemies within pursuit_steps 3 of their reach join as they arrive,
     camp damage counts; lost (or a linked body falls) -> want_home, except healthy on own ground or paying soon.
   - threat_strike(): an enemy with two turns before our next gets one more step of reach or a second basic attack
     (Strike::max_reach 5 -> 6; pack-zone radius kept at 7).
   - On plain nemesis: 55.2% over 1102 games, our deaths ~-29%. Merged hecate (hx-c5): 60.0% over 1366 games
     (main 59.7, fresh 58.7, fresh-hf 60.2, hx-fresh2 61.5); vs rival 66.9%.
6. Contest enemy captures (from bots/variants/hx-mid2; hx-c6 = merged state).
   - contest_capture(): a cleared group of contest_gems 40+ in sight that the enemy holds or stands on, reachable
     before the hold pays: step onto a free tile of it; contesting() keeps us there for any such group.
   - 60.3% over 1722 games (6 suites incl. fresh3 seeds 7301/7302) vs 59.0% before, no suite worse.
7. Teammate's nemesis fixes 1-3 (commit 5ef5601 "Khaos v22"): bag_at_stake() for the farm pack zone and the pack
   brake, no emblem capture-recall while closing(), no siege heal trip while holding a capture. Level (59.6% vs
   60.3% over 1722 games; with fix 4, the funded siege route, also 59.6%); kept as sound fixes matching nemesis.
8. Finish a kill before retreating (from bots/variants/hx-kill2).
   - killable_now(): a visible enemy our basic attack + best ready cast kills this turn, after which the rest and the
     camps could not kill us before our next turn. It overrides the low-health retreat, and the fight-lost retreat is
     judged with that enemy left out (Safety::fight exclude); then no pursuit retreat that turn.
   - Fires ~0.15 times a game (390 games: 51 low-health bypasses, target killed 37, we died within 3 rounds 4;
     9 fight bypasses, all 9 kills). Level on win rate (60.5% main); kept as sound.
9. Fuel (from bots/variants/hx-fuel, hand-merged with item 8's exclude parameter; hx-c7 = merged state):
   Safety::strike_of (per-turn strike cache) in step_guard and visible_threat, cheap tile tests first, known_fight
   memo lookup before the fuel gate, lethal() only when it decides, one-pass fight_key. 100M bench: 16/16 identical,
   mean -0.5%, p99 -1.9%.
10. Ladder-driven changes from the Intercontinental Fish analysis ([../FISH.md](../FISH.md)); frozen
   baseline before them: bots/baselines/hecate-v1. Submitted as version 19.
   - Draft copied from the top ladder teams: Ren, Stellar, Cassi, Ryth, Varg (Tavi last). Ren builds Focus (its
     stun and retaliation scale with it), and solo camp estimates count its retaliation on each monster that hits it.
   - From v17: spell-station clears for ranged champions and pickup of a freshly cleared group in sight
     (local_spell_plan, collect_local_reward), with the farm evaluation's fuel kept clear of the pickup.
   - Cassi farms gold: gold_farmer_weight 4 on its gold value, and it hits harmless gold-only groups in passing.
   - Cassi and Issac: basic attacks pick the pair with the weakest body, and damage only counts once it takes a body
     below its partner (useful_damage).
   - Locally all level: 48.7% vs hecate-v1; without the v17 port and gold farmer 46.2%; hecate-v1 plus only the
     Cassi/Issac targeting 51.3%. Ladder scrims vs the top 5 on the same maps: 27-48, against 20-55 for version 18.
11. Version 20, from replay reviews of version 19 on the ladder.
   - siege() and kite() walk with Pathing::step_towards_funded (from v17: the search is capped by fuel, not by
     distance + max_detour). On swirl a lake made the route longer than the cap and the team stood still for ~1200
     rounds; failed siege walks there fell from 1836 to 76.
   - tribute_safe() judges the next params::tribute_window (6) turns instead of the whole channel, so a 200+ bag no
     longer waits on any enemy in sight; the per-turn re-check cancels if a threat closes in.
   - Waiting out a spell cooldown at a spell station, hit any harmless camp in reach.
   - 52.3% vs version 19 locally; ladder scrims vs the top 5 on the same maps 28-47 (v19 27-48).
12. Version 21: big-bag escort. A carrier with bag_at_stake >= escort_bag (150) waits (up to escort_max_wait 20
   rounds, unless hit, winning, closing or in the endgame) until escort_count (2) allies are within escort_radius
   (5); empty-handed allies within escort_reach (18) go and stand by it (escort()). 51.3% vs version 20 locally; on
   Monolith-only maps big bags lost to deaths 7 vs 14 in the same 32 games; vs a carrier-hunting copy 15/20 vs 13/20.
13. Version 22 (item 12 without the escort on shared-gem maps) and the revert. Ladder scrims vs the top 5 on the
   same seeded maps, paired: version 20 28-47, version 21 26-49, version 22 24-51 (vs version 20: 6 flips up, 10
   down); against the top 10 version 22 went 55-95. The escort halved big bags lost locally but did not help on the
   ladder (contest still 1-9 vs the top 10), so hecate is back to version 20 (item 11), which is the active
   submission again. The escort code is in history: version 21 = 26e6920, version 22 = 33d61fd.
14. Cleanup and fixes (2026-10-19, in version 25).
   - Fuel savings and dead-code cleanup, byte-identical at 100M fuel: 8970 to 8621 lines, fuel -1.4% beyond
     0306608's -1.6%. Against main's hecate at the real budget 47.4% (fuel-only changes reroute games; EXPERIMENTS.md).
   - Bug fixes from the 2026-10-18 review: 51.3% for the bundle and for the dash-landing fix alone, each vs the cleaned bot.
   - v17 port replaced: farm carries out its own spell clears (`spell_clear`) and picks up cleared groups first
     (`pick_up`, one taker per group); `local_spell_plan`, `collect_local_reward` and both v17 spend caps gone.
     51.0% vs the bot before it; 8374 lines.
15. Overnight orchestrated session (2026-10-19, 6a78b0c..4b5217e, version 25 = hecate-v4). Parallel agents in worktrees, each
   change A/B tested on ladder + maps/gen + maps/gen-central (regenerated, seeds 6401/6402) plus two fresh suites
   (1102 games); details and every dropped attempt in [EXPERIMENTS.md](../EXPERIMENTS.md). Merged, in order:
   - Logical bug fixes: fight sim (Ren reflection, stuns on arrived fighters, idle sim joins enemies fully), a
     teammate's sighting fixes the enemy at its tile, comms group fields 8 bits, emblem pricing, siege candidates,
     unified contest timing, our own Home emblem read, waiting at an unsafe altar bounded by the walk to the next.
   - Fuel round 1 (byte-identical at 100M, -11% per turn) and fuel round 2 (measured-cost estimates, bush clusters in
     the warm-up); gate work (turn order without a threat build, an out-of-fuel cascade breaker, fight memo 32).
   - Strike planner (plan.cpp): every legal walk/dash/attack/reset/cast sequence priced in enemy health points,
     replacing decide()'s fixed fight order: 54.4% vs its parent (frozen as bots/baselines/hecate-v3).
   - Carrier chasing when the bag can be intercepted, a game-ender stop, contesting any gem capture.
   - Reach (safety.cpp): enemy movement over open tiles and dashes, attacks needing sight; level in play, its fuel
     cost cut by half in a second round.
   - Siege heal trips no longer flip recall/cancel; siege membership persists across fight turns; emblems chosen
     by measured value (forward-looking on Monolith-only maps); begun emblems priced by the shards left.
   - Banking by our measured tribute rate instead of fixed margins; hits in passing only on groups that are
     harmless, being cleared by an ally, or (melee) already awake; exact cheaper fight simulation; an ally
     corridor deadlock resolved by the lighter bag yielding.
   - Result (4b5217e): 58.0% vs hecate-v2 (639/1102, maps won from both sides 177 vs 89), 61.9% vs nemesis-v2
     (hecate-v2 55.6%), 70.9% vs rival at 85047a7 (hecate-v2 64.1%). Out-of-fuel turns 56/49 per 16 bench games
     vs rival/nemesis-v2, above hecate-v3's 28/21: Reach and the planner on fight turns. Unmerged: the retreat
     planner (branch plan3), level but out-of-fuel turns ~2.5x main's.
16. After version 25 (2026-10-19, not yet submitted). Fuel round 3 (-17.7% a turn, byte-identical at 100M) with
   step_guard's fuel reserve and the late-turn skips (frozen with the rest as bots/baselines/hecate-v5); a stunned turn
   only sets the turn order; the cast, route-retry, kite and travel-dash fuel gates removed (level, 49.7% vs
   hecate-v5). Details in [../EXPERIMENTS.md](../EXPERIMENTS.md) and [FUEL-GATES.md](FUEL-GATES.md).
17. 2026-10-19 (not yet submitted; baseline bots/baselines/hecate-v6 is hecate at 1a80ff8). On shared-gem maps the
   draft picks from `draft_preference_spells` (Stellar, Ryth, Prism, Ren, Cassi and Issac, Varg, ...): 63.3% on 120
   shared-gem games vs hecate-v6, byte-identical elsewhere. Ten other changes tried that day were level or lost; see
   [../EXPERIMENTS.md](../EXPERIMENTS.md).
18. 2026-10-19 (not yet submitted). The stunned-turn skip from item 16 reverted: a stunned turn runs the whole
   decision path again (its claim, banking and siege state move on as on any turn) and only the refused recall
   attempt is skipped. Ladder scrims vs the top 5 on the same maps put the skip at 26-49 (version 27) against 30-45
   without it (version 28) and 31-44 for version 25; see [../SUBMISSIONS.md](../SUBMISSIONS.md).
19. 2026-10-19 (not yet submitted). The shared-gem caster draft of item 17 reverted: on the ladder version 29 (with
   it) was level with version 28 (without it), 29-46 vs 30-45, and 2-3 on stampede against 3-2. The 63% local
   result stands in EXPERIMENTS.md for anyone who wants to retry it with ladder evidence.
20. 2026-10-20 (not yet submitted). Fuel rounds 4-9, byte-identical at 100M (46 bench games vs rival and nemesis, and
   40 games on 20 held-out maps/gen and maps/gen-central maps): -18% fuel a turn (-21% on heavy maps), p99 -20%,
   turns over 100k -71 to -79%, round 1 -9%, no turn dearer. At the real budget on the bench: out-of-fuel turns 6 -> 0,
   fuel-gate shortcuts 6765 -> 2234. No fuel gate, reserve or estimate changed. Fight path: Reach::at, step_guard,
   an exact-sum fast turn in simulate, memoised strikes and kits, per-turn enemy masks, known cases inline with the
   work out of line; world and economy: farm inlined, raw host calls through util.h helpers, camp visibility reused,
   no ward attempt on a stunned turn. Details per round in [../EXPERIMENTS.md](../EXPERIMENTS.md).
21. 2026-10-20 (not yet submitted). Three changes ported from koi ([../koi/README.md](../koi/README.md)), A/B against
   hecate at 3e8dfa0 (bots/baselines/hecate-v7) over 2698 games (ladder, gen, central and 12 fresh-seed suites from
   replays/koi-maps): 51.9%; fresh gen 51.9% (1848), central level (49.8%, 552); out-of-fuel turns 24 vs 17 in 390.
   - bot.cpp rate(): a farm cycle is worth `worth / (cycle (1 + cycle / H))`, H = 100 x max(1, longer side / 50), so
     long cycles count for less; applied to every farm value, the bank-then-farm one included. Discounting only the
     farm side (as koi does) also made carriers bank early: 50.2% over 850 games against 52.0% for both sides, and
     discounting only the bank test was 49.8%.
   - pathing.cpp step_towards(Field): when the funded search and the descent both fail, a search to here + 6 x
     max_detour walks round live camps that block the static way (a body otherwise sat 90 rounds in a dead-end
     pocket). No new fuel gate: it runs only after the funded search.
   - bot.cpp prey(): an enemy standing on a cleared group counts the group's gems as its bag, so it is chased on its
     own ground and is worth more to kill (koi: +1.7 on 1010 games).
22. 2026-10-20 (not yet submitted). SDK 3.0.1 / week 2 patch (Heart of Ruin, golem, new stats).
   - champions.h: table updated to the new stats, with a Heart of Ruin row (it read past the 12-row table). Read from
     the engine at start-up instead, it played identically but cost ~11k fuel in round 1 and ~110 a turn (+0.4%), all
     from lost constant folding (a mutable copy of the constexpr table costs the same), so it stays compiled in.
   - world.cpp: the camp-design cache grows to fit the camp type (it had 5 slots; golem is type 5 and wrote past it).
   - draft.cpp: Heart of Ruin is in the fallback order.
23. 2026-10-20 (not yet submitted). Camp reach from the camp designs (wolf 3, elk and golem 4, monolith 5) instead of 3
   for every monster: CampMember::reach, CampGroup::reach and StaticMap::max_camp_reach feed threat(), Safety's camp
   members, wake risk, camp stun value, dash threats, the shield trigger, spell clears (none while an attacker reaches
   as far as our spells), kiting, siege staging (group reach + 2) and its low-health rule, and the camp exit search.
   54.3% vs hecate-v7 (398 games: ladder 57.1, gen 51.9, central 59.8).
24. 2026-10-20 (not yet submitted). Gem limits rescaled to the new rewards by stampede's block (360 -> 132 gems):
   big_gems 150 -> 55 (no ladder group reached 150, which turned the big-group and shared-gem code off; 55 keeps the
   old big/not-big split of every ladder group but one), chain_bag_limit 80 -> 30, brake_bag 30 -> 11. 52.8% vs 23
   (ladder 42.9, gen 56.1, central 47.8), 52.3% on a fresh suite (seed 7101). gem_value 15 -> 40 on top: 50.8%;
   life_value 300 -> 400: no game changed.
   Settled after 26 (2026-10-20, all vs the bot with 26-28): brake_bag 30 50.9% (ladder 22-20, gen 260-252),
   chain_bag_limit 80 52.7% (ladder 18-24, gen 274-238, not confirmed on a fresh suite), both bag limits at
   life_value / gem_value = 20 ladder 22-20. Since 26, big_gems only sets which maps are kited and is no longer a
   siege trigger. Values kept as above.
25. 2026-10-20 (not yet submitted). Heart of Ruin played as itself, and modelled as an enemy. HoR draft below is
   heart_of_ruin, stellar, cassi_and_issac, ryth, varg (Ren swapped out); pre = hecate 1251236.
   - champions.h: AbilityFacts::radius and lands() for a dash whose landing damages and stuns (HoR: 1.75 x Focus,
     stun, radius 1; reach 3); damage_scale() for the missing-health passive (x (1 + 0.5 x missing fraction)).
   - Own HoR: plan.cpp prices each dash landing within 2 that hits a visible enemy (damage via damage_amount, stun via
     abilities.cpp stun_worth, a held tributer only if killed, Ren's retaliation) plus the basic attack after it, or
     for melee the attack from here first; cast_at_enemies lands only for keep_walk_value (a kill or a cancelled
     tribute: game enders, retreats, after the walk); cast_at_camp lands on the farmed group, never off a cleared
     group we hold, onto another group's members or into another group's reach. Travel, chase and escape dashes keep
     off landings next to sleeping groups that strike. The early shield waits for the plan while a landing is ready
     (like the reset); the shield itself is shield_if_needed, as for Varg. Our basic-attack kill checks, output(),
     killable_now and the fight kit scale by the passive at current health. A landing cast outside Pathing bumps
     outside_dashes(), after which Pathing rereads our tile.
   - Enemy HoR: Strike, Reach and the fight kit add the landing (walk + dash + radius, 1.75 x Focus, stun; plus the
     basic attack beside it), all its damage scaled by its last-read health; its kit already shields.
   - Active shields (enemy Varg and HoR, and our own) are read from the buffs while the cast is under 5 turns old:
     the fight sim starts them shielded, and the planner, attack_target and killable_now count a shield as health.
   - HoR draft vs pre with the same HoR draft: 70.8% (554 games: ladder 64.3, gen 71.3). Normal draft vs pre normal:
     49.8% (level). Against the pre HoR draft: 54.7% vs pre's 52.0%; against the new HoR draft: 37.7% vs pre's 34.7%.
     The new HoR draft beats the normal draft 62.3% (the draft is unchanged here). Fuel at 100M: +3.9% a turn mean
     vs pre on the bench (+1.4% for the HoR draft); at the real budget 0 out-of-fuel turns either way, shortcuts
     1174 -> 1137.
26. 2026-10-20 (not yet submitted). corridors (1-10 on the ladder): with big_gems 55 (item 24) its 58- and 60-gem
   lane groups were "big", so siege() sent the whole team after them: 62% of champion turns were siege staging (G)
   and corridors went 812-1026 and 741-1048 against rival. Big groups are no longer sieged off shared-gem maps (siege()
   takes Monoliths only; kite() still handles big groups where they are the only gems; big_rounds and
   big_respawn_wait removed), and holders() splits a capture only until each share's tribute fits tribute_window (6)
   turns, in absolute gems: 58 or 60 gems get one holder, elk-arena's 72 two, stampede's 132 three (Monoliths keep
   monolith_holders). corridors vs rival 1012-484 and 1032-122. 54.7% vs hecate 1251236 (554: ladder 57.1, gen
   54.5); collision, corridors, eight, fracture and islands, the ladder maps with a 55+ gem group, all won from both
   sides.
27. 2026-10-20 (not yet submitted). boss-battle (1-8): its only altar sits behind the shared Monolith pair, whose tile
   (24, 20) is the only one in tribute range, so hecate tributed nothing and lost on gold (no teleport helps: a crystal
   cannot land on a camp tile; `mapgen check` calls it teleport-only because its closure walks camp tiles).
   StaticMap::gate is a group that stands between our spawn and every altar (host floods with live camps as walls),
   gate_keys its members whose death alone opens one. The gate is a siege candidate on any map with the
   Monolith-only siege limits, its key member is hit first, and until it falls bags are not banked (bankable_bag):
   champions farm and shop as if empty-handed. Against the pre-change bot boss-battle went 1002-0 and 640-109
   (first key kill around round 1100); full A/B 50.2% (ladder 57.1 with boss-battle 2/2, gen 49.6: no generated map
   has a gate, so the rest is fuel noise). Reverted the same day: against submission 31 boss-battle went 1/2 (0-0 on
   gold, 90-334), since killing the key left its tile in the other Monolith's reach and the held-back bags (400-875)
   could not be banked; ladder teams that score there kill both Monoliths and hold the tile (EXPERIMENTS.md).
28. 2026-10-20 (not yet submitted). Teleport crystals to altars no walk reaches. StaticMap::foot is the walkable region
   from our spawn (camps counted as cleared), StaticMap::hops each altar outside it that one crystal reaches: landing
   tiles in its pocket within 3 of foot, and the foot tiles they are reached from. bank_gems takes the hop when the
   walk to a source + tp_crystal_time + the walk from the best landing + the recall out (no walk leaves the pocket)
   beats walking to an unlocked altar, or when every walkable altar is avoided; carry_bag's wait at an unsafe altar
   is bounded by it too; continue_recall keeps the recall in a pocket once the bag is in. A crystal (10 gold) is
   bought on spawn or while dead only once a hop would have won (Memory::wants_crystal). Only collision (its vault
   altar) and islands (4 inner altars) have hops; no generated map does. Ignoring the recall out, carriers hopped
   into collision's vault too often; a first version bought a crystal every life (52.0%, islands 0/2). Full A/B 52.2% (ladder
   47.6, gen 52.5 with no hop maps); collision and islands 1/2 each. Camps reachable only by crystal (ambush,
   big-world, fracture: 7-21 gems) are not farmed.
29. 2026-10-20 (not yet submitted). Dashers cross one-tile hole and altar lines. StaticMap::crossable holds the
   holes and altars with standable tiles on two opposite sides (host shifts, once); dash_walls is blocked_for_us
   without them, so a dasher's cached, approach, centre and spawn fields price a crossing at the dash's two steps.
   No two crossable tiles touch (every other tile along a line, the lowest of diagonal neighbours), else a field
   walks along the line; camp tiles do not count as standable, else a field reaches gem clusters ringed by holes
   that no dash can land beside. Approach goals stay on standable tiles. Beside a crossable tile on a farm walk
   or a bank walk, dash_across dashes where the field gains, with enemies near too as long as the landing is no
   deeper in their reach (the travel dash's 10-tile clearance stalled dashers at crossings). StaticMap::dash_foot
   replaces foot for dashers, so a dasher across a line is not taken for one in a crystal pocket and recalled.
   First version (3d837e6) left Ren and Issac standing still most of the game on big-world and islands. Full
   A/B 52.0% vs the pre-dash bot (554: ladder 47.6, gen 52.3); on islands, big-world, fracture, gold-rush,
   concentrated-wealth and ambush dashers cross dozens to hundreds of times a game. Two crossings within 8 turns
   still wait out the cooldown. Fuel at the real budget: +1.2% a play turn on the bench, out-of-fuel turns 1 -> 1.
30. 2026-10-20 (not yet submitted). Draft for the week 2 patch and the Heart of Ruin nerf (SDK 3.0.2): Heart of
   Ruin, Marcella, Vesper, Ryth, Stellar, then Willow, Cassi and Issac, Varg, Ren, Vendetta, Tavi, Prism (was Ren,
   Stellar, Cassi, Ryth, Varg, ...). Each pick chosen on maps of its size, hecate vs hecate with only the draft
   changed ([DRAFT.md](DRAFT.md)): the trio beats Ren/Stellar/Cassi 72.5% on all 3-pick maps; Ryth as 4th 53.2%
   over Cassi on 4-pick maps; Stellar as 5th 57.9% over Cassi on 5-pick maps. On a fresh-seed suite (8101, 512
   games) the new draft beats the old 69.3% (3-pick 71.1, 4-pick 63.1, 5-pick 73.8). Submitted as version 32.
31. 2026-10-21 (not yet submitted). Monsters sleep one by one: a camp group is awake while any striker is (5a33e52),
   and CampBelief::asleep keeps the strikers read asleep inside an awake group until a hit wakes them. Danger
   (Safety's camp members, awake_over, dash and shield hazards) leaves those out unless another champion is within 4
   of the group; passing and capture-hold hits count as free only once no striker is asleep; landing_wakes and
   wake_risk ask about the asleep members. 50.0% vs hecate-v7 (582), out-of-fuel turns 1125 vs 1224.
32. 2026-10-21 (not yet submitted). Quality wave 1. Behaviour-identical cleanups (dead code in World, Safety and
   bot.cpp; send reuses receive's read; one approach estimate per search; searches skipped after a dry route; danger
   walls kept per tile): fuel -0.54% on the bench. Fixes: read_shield reads a shield in its last round; crossable
   diagonal ties keep the even-row tile, so staircase rivers keep every other crossing (fracture, shortcut,
   starvation +2-3); an asleep camp is stirred only by champions yet to act within 5; camp members with reach 0
   dropped; submit_here runs tribute_ok at an altar carry_bag gave up waiting at; siege_load counts a cleared group's
   health as 0; offer_channel ignores stuns for Marcella's tribute; live_self's max health from the live record;
   step_closer skips guard and avoid tiles (crow-flies farm passes the zone). Removed killable_now, Safety::fight's
   exclude and the delayed tribute stun (tribute_to_stun_later, decision D, the hold parameter). 48.5% vs main (582,
   ladder 42.9, gen 49.2), out-of-fuel turns 1078 vs 1147.
33. 2026-10-21 (not yet submitted). Deletions and a world-model fix. place_ward is the guards plus ward_bushes: the
   periodic off-bush ward (params::ward_period, Pathing::ward_targets) is gone. The rally is gone (post_rally,
   sight_fight; comms bit 31 free), so sightings rotate on fight turns too. World::track counts an unseen enemy's
   turn this round whatever its modelled order, and dates `possible` after that turn so it is never counted twice
   (turns_between now includes `to`'s slot). 50.3% vs main (582, ladder 50.0, gen 50.4), out-of-fuel turns 983 vs
   1116.
34. 2026-10-21 (not yet submitted). Quality wave 2, behaviour-identical (bench 16/16 identical at 100M; real-budget
   out-of-fuel turns 8 -> 8, round-1 mean 182k -> 179k). Bush clusters grow in bounded, resumable steps; foot,
   dash_foot and hops are built lazily. bank_gems skips altars whose crow-flies bound cannot beat the best so far;
   ward_bushes reads only clusters already found. make_way reads the failed route's field instead of a search per
   adjacent ally; the per-altar fields are warmed before the attack tiles.
35. 2026-10-21 (not yet submitted). Sealed altars (COORDINATION 1). AltarAccess: the tribute tiles a walk from our spawn
   reaches with live camps as walls, rebuilt when the live camps change (camps that only died leave an open altar
   open). altar_usable: the believed-awake fire on the best open tile times tribute_turns(bag) stays below the
   carrier's health. bankable_bag replaces my_gems() in decide, pick_up's chaining, wants_shop, retreat's banking and
   the siege reset: a bag no altar is usable for is farmed and shopped on as if empty. While no altar is usable for
   the team's largest bag, the live groups beside our walk in the cut-off area and those with an awake member in reach
   of a tribute are siege candidates with the Monolith-only limits (replaces 27's gate). chase returns false when it
   can neither step nor hit. 49.0% vs main (582, ladder 51.4 with boss-battle 2/2, gen 48.6), out-of-fuel turns 2145
   vs 1004 (EXPERIMENTS.md).
36. 2026-10-21 (not yet submitted). Quality wave 2 fixes. A world phase that ran out of fuel skips comms receive and
   decide; comms send observes before marking any camp, claim or bag posted and stops if the turn went stale. farm
   always evaluates (farm_evaluation_affordable and the nearest-group fallback deleted; a field from here only if a
   full field fits, else the loop stops, and a loop cut before last turn's choice walks on to it). An error in act
   still posts the turn order, claim, bag and health. heal_rounds (a heal trip's price, as upkeep_cost has it) prices
   the heal in recall_to_bank, capture_recall and wants_shop (recall_heal_bonus and the 0.6 shop bypass removed).
   Safety's camp hits carry our Jungle and Durability emblems; an asleep group is stirred only by a champion yet to act
   within its own strike's reach. 54.5% vs main (582, ladder 50.0, gen 55.1), fresh seed 9421 59.4% (512);
   out-of-fuel turns 1136 vs 914 (fresh 945 vs 731).
37. 2026-10-21 (not yet submitted). Strike search phase 1 (STRIKE-SEARCH.md, strike-notes.md): plan.cpp searches
   every legal order of moves, dashes and strikes, camps as targets with the bans, scored as before; a move is offered
   only when a strike follows it, no landing wakes a sleeping striker or hits only camps, a woken striker is priced per
   camp phase in its reach. Dash paths are blocked by visible enemy champions (probe-dash-enemy; cambc-rules.yaml
   corrected), in the search and in dash_landings_from. 52.6% vs main (582, ladder 54.3, gen 52.3), 55.2% at 100M;
   out-of-fuel turns 3441 vs 1191 (99.5% in decide), to be brought down by a fuel-only follow-up.
38. 2026-10-21 (not yet submitted). Strike search phase 3a: Varg's splash in Reach and Strike. An enemy Varg's basic
   attack reaches a tile through a unit beside it (our visible champions but us, live camp members) that it can see;
   compute_strike and threat_strike add 1 to Varg's basic reach so Strike still bounds Reach (debug check
   REACH-BOUND). 51.0% vs main (1094, ladder 50.0, gen 50.6, fresh 51.6), 51.4% at 100M; out-of-fuel turns 6551 vs
   6471.
39. 2026-10-21 (not yet submitted). Quality wave 3. Behaviour-identical (bench 16/16 identical at 100M each): farm and
   altar access fuel (fuel -0.35%; real-budget out-of-fuel turns 69 -> 55 on the bench): a group's `fastest` is keyed
   on strength as well as belief version, the Chebyshev prune runs only before a field from here, groups near an altar
   are flagged lazily, and altar_access keeps `ours` exact by pocket floods for deaths and ring checks for respawns;
   live_camps writes only the member bits that flip (-0.001%). Fixes on top: camp deaths reopen altars at once (no
   deferral while an altar is open), and access_fire reads every open tribute tile (was the first 64). 50.6% vs main
   (1094, ladder 48.6, gen 51.4, fresh 50.2); out-of-fuel turns 6276 vs 6106.
40. 2026-10-21 (not yet submitted). Farming stage 1, shared prices (FARMING.md, farming-notes.md). heal_rounds(damage,
   out) is the one heal price; HomeTrip prices every trip home (farm's bank trips, recall_to_bank, capture_recall,
   wants_shop): a recall wins when its arrival less the heal and, once the gold completes it, the next emblem's gain
   beats the walk, never past the bag's tribute deadline and worth nothing once closing. prices() holds the next emblem,
   its gain and gold in gems from gems_share (capped by gems short, the enemy's distance, tribute rate and our pace
   over bag_rounds_left). closing covers endgame(); too_late applies at any horizon; holders() replaces the single
   taker in ally_holding, step_onto_cleared and pick_up. The clearing share counts from one turn in one, so gold has a
   price before the first camp hit. Deleted gold_worth, endgame, emblem_gain_rounds, params clear_share,
   endgame_shop_rounds, endgame_horizon. 50.0% vs main (1094, ladder 47.1, gen 51.0, fresh 49.4); out-of-fuel turns
   7156 vs 6606.
41. 2026-10-21 (not yet submitted). Strike search fuel, same choices (bench 16/16 identical at 100M): ground centres
   and camp touches scattered once with hashed dedup, wake at the start tile memoised by touched set, landing groups
   memoised and shared by nodes with the same landings and foes alive, each dashed end's first mid in one pass,
   attack_viewers cached per tile by window row, our record read once, a landing reads only foes within its radius.
   Measured vs main: 51.5% (1094, ladder 54.3, gen 52.5, fresh 50.0); out-of-fuel turns 6139 vs 6545.
42. 2026-10-21 (not yet submitted). Strike search phase 2: heal and shield as search options (strike-notes.md). A
   leaf whose cast is unused is offered with the best heal from the start or end tile (min(amount, missing health,
   cooldown x damage_bound at the ally), heal_ally's threshold) and with a shield priced as min(amount, duration x
   damage_bound) at its end tile. `Planned::searched` (an exactly priced tile was carried out) makes decide skip its
   post-plan heal and act() its end-of-turn heal and shield unless the goal walked or hit afterwards; decide's early
   heal, shield and reset_may_kill/landing_ready gate run only on turns the search does not plan. 50.0% vs main (1094,
   ladder 44.3, gen 52.0, fresh 48.8), 51.1% at 100M; out-of-fuel turns 7041 vs 6256.
43. 2026-10-21 (not yet submitted). Strike search phase 3b: killed and stunned enemies leave the end tile's danger
   (strike-notes.md). A killed foe drops out with its Cassi/Issac partner, even an unseen one; a stunned foe only if
   stunnable with exactly one turn before ours (stun_worth stays 80). Per end tile the search keeps the best leaf per
   removed set, less any another beats while removing a superset; pricing queries Reach only for foes some candidate
   still faces. 48.9% vs main (1094, ladder 51.4, gen 47.9, fresh 49.6), 51.0% at 100M; out-of-fuel turns 8663 vs 8071.
44. 2026-10-21 (not yet submitted). Main stat by counted use (GAPS.md). bot.cpp counts our basic attacks and casts per
   slot at each turn's end (count_use: a slot whose cooldown is still 8 was cast this turn; attacks = attack spent +
   resets - a ranged walk without a dash). main_stat picks Focus when focus.growth x sum(multiplier x casts) over
   damage or landing slots beats strength.growth x attacks, falling back to the old per-cooldown formula until both
   counts are non-zero; best_emblem finishes any begun Jungle/Power (either stat) or Durability emblem first; prices()
   keys on main_stat. 56.4% vs main (1094, ladder 65.7, gen 54.7, fresh 56.8); out-of-fuel turns 9427 vs 8471.
45. 2026-10-21 (not yet submitted). Strike search fuel 2, same choices (bench 16/16 identical at 100M): find_centres
   takes each point's 3x3 as a row mask less the centres already added, and clears the whole near table when over 8
   points would clear around themselves. Measured vs main: 50.2% (1094, ladder 48.6, gen 50.0, fresh 50.6); out-of-fuel
   turns 6900 vs 6865 (level).
