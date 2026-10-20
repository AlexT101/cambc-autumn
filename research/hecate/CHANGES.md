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
