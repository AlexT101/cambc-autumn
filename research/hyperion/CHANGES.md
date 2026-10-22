# hyperion change log

What is in hyperion and why, oldest first. Entry numbers are stable because commits and research notes cite them;
missing numbers were reverted, superseded or cleanup, dropped in the 2026-10-22 trim. The untrimmed log is
`git show 1d5ddf0:research/hyperion/CHANGES.md`.

- hyperion was named hecate until 2026-10-21. `bots/hecate` is items 1-31 (the former hecate-v8, main b04c0e0);
  `bots/baselines/hyperion-v1` is 5d27969 (items 1-81).
- Results are win rates against the bot before the change, all maps from both sides at the real fuel budget, unless
  noted. 1094 games is ladder + `maps/gen` + fresh `maps/gen-s1`; earlier entries used smaller suites.
- "Behaviour-identical" means the fuel bench's replays are byte-identical at 100M fuel.

## 1-31: the reference bot (`bots/hecate`, 2026-10-17..21)

hecate began as nemesis 2dba924; results up to 6 are against nemesis.

1. Monolith sieges: a ranged caster with no melee ally next to the Monolith casts from range 4, out of reach. Camp
   stuns are worth the member's Strength when a visible ally is in its reach, on Monolith groups only (4: elsewhere
   they cost ~2.5%). Monolith-only maps 70.7%.
2. Shared-gem maps (every gem source a big group or a Monolith): `kite()` replaces siege (stand within 4 of the
   block's hitting monsters but out of their reach, casters cast on cooldown, nearest 3 capture, contest an enemy
   hold), and spell users build Focus and skip Jungle. Shared-gem maps 77.3%.
3. A capture holder hits other harmless or already-awake groups in reach; a melee champion whose hit clears a group
   steps onto it the same turn. 55.6%.
5. Death avoidance: `step_guard()` keeps pathing off tiles where want_home would make us leave at once (fight lost,
   lethal, a Cassi/Issac body falls); `threat_strike()` gives an enemy with two turns before our next one more step of
   reach or a second attack; a lost pursuit sends us home (now `Safety::stand`, 66). Deaths ~-29%; 60.0% (1366).
6. `contest_capture()`: step onto a cleared group of contest_gems 40+ in sight that the enemy holds, if reachable
   before it pays. 60.3% vs 59.0% (1722).
10. Cassi and Issac: basic attacks pick the pair with the weakest body, and damage counts only once it takes a body
    below its partner (`useful_damage`); Cassi farms gold (gold_farmer_weight 4). Level.
11. siege() and kite() walk with `step_towards_funded` (on swirl a lake made the capped route fail and the team stood
    still ~1200 rounds); `tribute_safe()` judges the next tribute_window (6) turns, not the whole channel. 52.3%.
14. Farm clears with spells from outside the camps' reach (`spell_clear`) and first picks up a cleared group in sight
    (`pick_up`, one taker per group). 51.0%.
15. The 2026-10-19 overnight session (58.0% vs hecate-v2, 1102), still live: carriers chased when the bag can be
    intercepted (`intercept_steps`), `stop_game_ender`, contesting any gem capture; `Reach` (enemy movement over open
    tiles and dashes, attacks needing sight); emblems by measured value; banking by our measured tribute rate
    (`closing()`); passing hits only on harmless groups, ones an ally clears or (melee) awake ones; the lighter bag
    yields in an ally corridor deadlock. Its strike planner was replaced by 37.
18. A stunned turn runs the whole decision path (only the refused recall attempt is skipped). Skipping it was
    byte-identical locally but went 26-49 against 30-45 in ladder scrims vs the top 5.
21. From koi: a farm cycle is worth `worth / (cycle (1 + cycle / H))`, H = 100 x max(1, longer side / 50), on every
    farm value including bank-then-farm (discounting one side only made carriers bank early); `step_towards` searches
    to here + 6 x max_detour round live camps when the funded search and descent fail; an enemy on a cleared group
    counts its gems as its bag in `prey()`. 51.9% (2698).
22. champions.h holds the stat table compiled in: reading it from the engine played identically but cost ~11k fuel in
    round 1 and ~110 a turn (lost constant folding).
23. Camp reach from the camp designs (wolf 3, elk and golem 4, Monolith 5) everywhere a monster's reach is used. 54.3%.
24. Gem limits for the week 2 rewards: big_gems 55, chain_bag_limit 30, brake_bag 11. 52.8%. Since 26, big_gems only
    picks the maps that are kited.
25. Heart of Ruin played and modelled: its dash landing priced in the planner, enemy casts and camp casts; the
    missing-health passive in our damage and kill checks; enemy landings in Strike, Reach and the fight kit; active
    shields read from buffs and counted as health. 70.8% in the HoR-draft mirror, level in the normal-draft mirror.
26. Big non-Monolith groups are not sieged off shared-gem maps (corridors' 58- and 60-gem lane groups pulled the whole
    team: 812-1026 vs rival before, 1012-484 after), and `holders()` splits a capture only until each share's tribute
    fits tribute_window turns. 54.7%.
27. Sieging the camp that gates every altar (boss-battle): reverted the same day, replaced by 35.
28. Teleport crystals to altars no walk reaches (`StaticMap::hops`: collision's vault, islands' inner altars); a crystal
    is bought only once a hop would have won. 52.2%.
29. Dashers cross one-tile hole and altar lines (`StaticMap::crossable`, `dash_across`); walks from spawn shorten
    51-60% on fracture, concentrated-wealth and gold-rush. 52.0%.
30. Week 2 draft ([DRAFT.md](DRAFT.md)): Heart of Ruin, Marcella, Vesper, Ryth, Stellar; 69.3% vs the previous draft
    on a fresh suite. Superseded by 82's draft.
31. Monsters sleep one by one: a group is awake while any striker is, and strikers read asleep stay asleep inside an
    awake group until hit; danger counts them only while another champion is within 4. Level.

## 32-59: 2026-10-21/22

32. Quality wave 1: fixes (a shield read in its last round, crossable diagonal ties by row parity, asleep camps stirred
    only by champions yet to act, live max health, ...) and removals (`killable_now`, Safety::fight's exclude, the
    delayed tribute stun). 48.5%, kept as fixes.
33. The periodic off-bush ward and the rally deleted (comms bit 31 free); `World::track` counts an unseen enemy's turn
    this round whatever its modelled order. 50.3%.
35. Sealed altars: `AltarAccess` (tribute tiles a walk from spawn reaches with live camps as walls) and `altar_usable`
    (believed-awake fire over tribute_turns(bag) below the carrier's health). `bankable_bag` farms a bag no altar is
    usable for as if empty, and while the team's largest bag has none, the groups sealing the altars are siege
    candidates. 49.0% (boss-battle 2/2).
36. Quality wave 2 fixes: a world phase out of fuel skips comms receive and decide; farm always evaluates; act errors
    still post claim, bag and health; `heal_rounds` prices every heal trip; Safety's camp hits carry our Jungle and
    Durability. 54.5%, fresh seed 59.4%.
37. Strike search ([STRIKE-SEARCH.md](STRIKE-SEARCH.md)): `plan.cpp` searches every legal order of moves, dashes and
    strikes, camps as targets; a move only when a strike follows it, no landing that wakes a sleeping striker. Dash
    paths are blocked by visible enemy champions (probe-dash-enemy). 52.6% (582), 55.2% at 100M.
38. Strike phase 3a: an enemy Varg's splash in Reach and Strike. 51.0%.
39. Camp deaths reopen altars at once; access_fire reads every open tribute tile (was the first 64). 50.6%.
40. Farming stage 1 ([FARMING.md](FARMING.md)): one heal price (`heal_rounds`), one `HomeTrip` price for every trip
    home, `prices()` for the next emblem's gain and gold in gems, `holders()` for cleared groups. 50.0%, kept as the
    base for stage 2.
42. Strike phase 2: heal and shield as search options; decide and act() skip their own heal and shield on turns the
    search priced exactly. 50.0%.
43. Strike phase 3b: killed and (one-turn) stunned enemies leave the end tile's danger. 48.9%, 51.0% at 100M.
44. Main stat by counted use: Focus when the counted casts' Focus gain beats the counted attacks' Strength gain; a begun
    emblem is finished first. 56.4% (ladder 65.7).
46. Turn-start ward, placed right after continue_recall cancels our recall (ward and recall share one channel), from
    bush clusters already found; Safety and occupancy are rebuilt after it. 50.7%.
47. The ward moves only to a cluster with strictly more tiles within ability_range of here plus of the work tile. 50.6%.
48. Fights simulate 17 own turns (2 x cooldown + 1) instead of 24, with exact early ends. 49.8%, decide -6.7% fuel.
49. Camp flight prices each step by the camp hits still to come before leaving every awake camp's reach (one step's
    damage tied, and champions circled Elks and Golems). 49.9%; camp deaths 1 vs 7 on 4 games.
50. A carrier's step is the farm step (`farm_step_value`), so walk-blocking casts fire while carrying (Stellar's nuke
    never did); `cast_at_enemies` takes the walk's worth. 52.1%.
56. After the goal, `strike_after` runs the strike search again from where the goal left us while a hit is possible
    (Marcella's armed stun, Vendetta's refresh, Varg's splash count after the goal).
58. The strike search's moves may pass guarded tiles: step_guard drops end tiles only and is placed again where the
    search left us. 48.9%, kept as logical.
59. A turn that ran out of fuel and resumed next round is abandoned (StaleTurn; `throw_if_stale` in search nodes, priced
    tiles and every 8 fight half-turns) and the round replayed. Not A/B'd: it raised out-of-fuel turns in long fights
    (419 vs 138 on 32 games); kept for after the fuel work.

Behaviour-identical fuel and cleanup in this stretch: 34 (lazy bush clusters, foot and hops), 39's caches, 41 and 45
(strike search), 51-52 and 57 (unused code, the search's debug checks), 53 (raw engine reads instead of
`cambc::champion`, -1.12%), 54 (dazzling-mccarthy's three fuel commits, -0.92%), 55 (continue_tribute keeps
want_home's answer).

## 60-81: fuel session 2026-10-22

Out-of-fuel turns were ~4.5x hecate's at the start. Net (79 against bbf6f05, main at the start): 54.2%, out-of-fuel
turns -61%; against hecate 65.7%. Wide bench at 100M: p99 106.8k -> 91.3k, turns over 100k 4147 -> 1944. Entries
without a result are behaviour-identical; branches are `fuel/<name>`. Merges 63, 67, 72, 77 and 79 only combined them.

60. Fight simulation: one damage cap for their side; callers that only ask whether a fight is lost may end early.
61. Strike search and Reach: lazy scratch arrays, per-tile camp member lists, memoised `groups_near` and `threatened()`.
62. Farm and world: altar access, approach fields and routes skip their diffs while no live-camp tile flips; farm
    refreshes only what changed. -2.98%.
64. Bug fix: a Cassi/Issac body killed in its own turn read (-1,-1) and threw engine error 5, skipping the rest of the
    turn.
65. Strike search: landing-cell classes once per search; nodes carry a dead mask.
66. want_home asks one fight: `Safety::stand()` replaces pursuit and visible_threat (enemies who can strike first,
    visible walkers joining, camps), and two fuel gates go. 52.2%; turns over 100k 3156 -> 2193.
68. Strike search commutation pruning: an order is dropped only when another has the same value and end tiles, so play
    changes only through tie order. 50.9%, out-of-fuel turns -5.8%.
69-71. Strike leaves in int8 cells; possible sets grown by `reachable_tiles` per tile; turn order folded (`may_escape`).
73. step_guard asks the bound union fight before exact Reach exposure. 52.4%, out-of-fuel turns -20%.
74-75. Farm worst cases; `find_members` skips clusters.
76. The strike search grows at most 24 nodes (binds on 0.45% of searches, the best leaf lost on 0.07%; worst search
    158.6k -> 78.2k). 49.7%.
78. Strike pricing: the goal field only when two end tiles compete; foes every candidate removes are skipped.
80. Fight simulation: quiet half-turns continue with a shielded weakest (`play_shielded`).
81. Farm walks on after a fight's search: on turns the strike search ran, farm skips its evaluation and walks on to last
    turn's choice (or banks). 53.7%, out-of-fuel turns level. The same skip with the farm-loop gate removed won 54.2%
    but had 2.6x the out-of-fuel turns.

## 82: Khaos's changes (2026-10-22)

A teammate's bots/khaos_v26 (hyperion 184fdba plus ~1.2k lines) merged with hyperion's 40 later commits. Against
5d27969, each on its own draft (`--no-test-draft`): 61.5% (ladder 55.7, gen 63.5, gen-s1 60.4), out-of-fuel turns 1950
vs 1685. Draft and play are not separated; untested on shared test drafts. Several parts copy a "teacher" bot's
observed behaviour, with fitted constants.

- Draft: on 4-5 pick maps Prism, Vesper Vale, Marcella, Vendetta or Ryth, Heart of Ruin (Vendetta when camps average
  over 10/3 members a group); `draft_preference` starts Prism, Vesper Vale, Heart of Ruin, Marcella (3-pick maps).
  `draft_order()` runs on every first draft turn; test_draft still takes precedence.
- Turn order: Prism, Vesper Vale, Ryth, Vendetta, Marcella and Heart of Ruin skip the priority bands: 14 + floor(10 x
  danger) when danger > 0 (the larger of our best strike over an enemy's health + shield and theirs over ours, from the
  enemies saved at turn start), else an idle value by role and health. Other champions keep the bands.
- Prism keeps its gems (`retaining_gems`) and takes captures (`prism_capture_holder`; allies `yield_capture`). It
  shops the affordable shards of the next emblem when they plus the heal outweigh the trip home; emblem choice for
  gem_focus prices Monster and Home too, and the shared upkeep model now prices them for everyone.
- Vesper Vale dashes onto a gold group a higher-id Heart of Ruin holds alone the round its claim clears
  (`take_capture_handoff`).
- Camp casts: Prism casts on the approach to an awake group (`cast_at_camp_on_approach`); after the basic attack, a
  cast that finishes a group's last visible member needs no minimum value.
- Farm: `prefer_partial` (a ranged farmer whose hit would wake a sleeping group hits a damaged harmless cluster
  instead); crew work counts a claimed ally's damage only from its earliest arrival (`work_arrival`); the loop starts
  at the nearest group when there is no previous choice; dashers skip drafted_spawn_steps on maps with crossable lines.
- Movement: equally short first steps go nearest the target group's centre; after a travel dash farm walks on down that
  dash's field.
- Kiting with ground casters: stations are tiles from which a cast reaches a striking member;
  `kite_productive_action` steps or fires from inside a monster's reach when two turns' damage outweighs the heal time.
- Chase: `prey` asks `Safety::chase_trade` (allies that cannot hit next turn arrive a turn late).
- Strike search: Prism gets the walk alone as a terminal leaf. New debug traces: FPARTIAL, FSEED, FCDELAY, FCWINDOW,
  FCPARTNER, DASH-FOLLOW, HANDOFF, CHASE-AVAIL.

## 83: robustness fixes from the 2026-10-22 audit (behaviour-identical)

- `groups_near` reuses an evicted answer's pool range when the new one fits: the pool grew all match, as callers ask
  about 6 radii and each tile keeps 2.
- A first-turn setup that throws part-way empties the ally list, so `ready()` is false and the next turn starts over
  (before, `me_` stayed null and `camps` empty).
- Killed during our own turn (Ren's retaliation): `ward_bushes` no longer tests the off-map tile (a ~3.9k throw that
  skipped the rest of `act()`), and main.cpp does not count the move as one that needs vision re-read.
- `yield_capture` and `take_capture_handoff` record the move in memory before the stale-turn check.
- Plan execution stops between actions once out of fuel, instead of finishing last round's plan in the next round.
- Dead code (turn_order.cpp's idle fallback, unreachable) and four comments that contradicted the code.

## 84: enemy Durability in basic-attack kills (2026-10-22 audit)

Enemies' Durability emblems are read with their Home emblem (`ChampionBelief::taken`, 0.9 with one). Basic attacks
deal Strength times that in the strike search (`hit_unit`, splash included), `strike_enemy`, `reset_may_kill`,
`attack_target` and `reset_and_attack_enemy`'s kill test, and turn order's kill bid (`offer_kills`). Spells already
went through the engine's `damage_against`. Before, a 100-Strength hit was counted as killing a 95-health Durability
holder, and the planner dropped that surviving enemy from its end tile's danger. Not A/B tested.

## 85: logic fixes from the 2026-10-22 audit (phase 1b)

With 84 (Durability), against 83: 51.0% of 1094 (ladder 48.6, gen 51.8, gen-s1 50.6), out-of-fuel turns 3816 vs
3612. Seven judgment calls from the same batch, layered on top separately, took the batch to 56.3% (ladder 44.3,
gen 55.5, gen-s1 58.8).

- Strike search and dashes:
  - Dash paths never cross the enemy spawn (probe-dash-spawn): `dash_landings_from` and the search's `pass_`.
  - A hidden blocker's re-plan skips tiles rejected as lethal, unpriced tiles 3 away, and dashes whose only way
    through is the revealed tile.
  - A reset then an attack on a champion is planned once the attack is spent (`strike_after`).
  - The walk-only terminal leaf goes to any ranged champion with no reset or dash whose strikes exclude walking
    (Prism, now Stellar).
  - Dash-then-walk legality respects the dash tiles still allowed, as `settle` does.
  - Spell scoring subtracts Ren's retaliation, as attacks and landings do.
  - Enemy shields are read live in basic-attack kills; our slots' readiness is read live (Vendetta's refresh).
- Banking, locks and the endgame (bot.cpp):
  - siege resets `staged_since` when allies take the capture.
  - `submit_here` confirms a believed enemy lock live (gone after break_lock's last hit).
  - `bank_gems`' pack-zone branch uses the lock- and avoid-aware altar choice and breaks locks.
  - `game_ender` judges a tributing enemy by its own bag (not Cassi's and Issac's together).
  - `intercept_steps` counts the rounds we act before a tribute completes, by turn order.
  - `place_lock` prefers the altar with an enemy tribute, and locks over an ally's tribute only against a winning
    enemy tribute and when the ally's would not win first.
  - `race_left` uses visible allies' live bags; `spell_clear` avoids every member's reach.
- World, comms, draft, turn order:
  - Allies' emblems are read too, so Willow's heal sees a Home ally's 3-turn recall.
  - Next round's turn order ranks by `next_priority` (`next_rank`).
  - The draft fallback follows `draft_order()`, then `draft_preference`.
  - Turn order: `offer_heal` caps the heal at max health, `offer_kills` counts shields, escape does not double a strike
    that already covers two turns; the teacher priority skips enemies killed this turn.

## 86: judgment calls from the 2026-10-22 audit, on top of 85

Against 85: 54.9% of 1094 (ladder 58.6, gen 55.7, gen-s1 53.7), out-of-fuel turns 4000 vs 4104. Seven commits, not
separated by A/B:

- `game_ender` contests a winning tribute next to the enemy spawn too (a stun or a lock cancels it whatever healing;
  `intercept_steps` still requires reaching it in time). Walking carriers there are still skipped. Generated maps keep
  altars 3+ from a spawn, so it fires only where an altar is within 2 of one.
- `closing()` prices a bag with no walk to an altar as `recall_turns` plus the walk from our spawn (was 0).
- Fights drop a shield with 0 turn ends left at its owner's next turn start (`shield_until = shield_turns`, was at
  least 1, which kept it through an extra enemy volley).
- Camp ground casts and Heart of Ruin landings stay off tracked unseen Rens whose retaliation would kill us, as
  `enemy_cast` does (binds only near death: retaliation is 0.2 x Focus, ~20-40).
- Farm floors a chain's trip at 0: a capture's gold that completes an emblem shortened the trip home while worth
  counted it too, so the cycle could reach 0 or below (a negative rate rejected the best chains, and the pre-filters
  disagreed with the rate). `rate()` keeps a 1-round floor as a guard.
- A carrier whose only walkable altar is the one `carry_bag` gave up on stops avoiding it and banks there again
  (`submit_here` judges it again); `carry_bag`'s crystal-hop alternative never leads back to the altar it leaves.

## 87: phase 2-3 audit fixes (2026-10-22): retaliation sums, Durability and stunned camps in danger

Against 86: 49.1% of 1094 (ladder 45.7, gen 48.8, gen-s1 49.8), out-of-fuel turns 4428 vs 3980. In steps: the first
four items 50.9% against 86 (3888 vs 3810); Durability 48.4% against those (4364 vs 3947); stunned camps 49.8% against
Durability (4358 vs 4151). Level, kept as rule fixes. On the 100M wide bench Durability costs +0.01% on the 11 of 52
games it leaves identical; the extra out-of-fuel turns come from changed play.

- Strike search: Ren's retaliation sums over the plan (`Node::hurt`). Attacks, unit and ground casts, landings and
  woken camps' hits are each checked against health less what the plan has taken; a ground cast is refused on the
  summed retaliation of all it hits. A cast at an unseen enemy subtracts its retaliation from the worth (a suicidal
  one is a flag, no longer a negative worth).
- Pack zones are rebuilt after the ward's re-read of vision: continue_recall's want_home had built them before it on
  most turns.
- A carrier with no walk to an altar (a crystal's pocket) recalls to bank by way of spawn.
- `lethal` judges against our live health and shield, re-read after each refresh (it read turn-start health, no
  shield).
- Fight simulation: Durability (`Fighter::taken`) cuts each hit before the shield (probe-durability-shield), in
  hurt/spill and the quiet paths; `overwhelmed`'s lower bound scales by our side's lowest taken; camp damage is kept
  before our Durability, which hurt() applies. No early-exit mismatches over the 52 bench games.
- Stunned camps: an awake member in sight with a stun skips the next camp phase in next-turn danger
  (`camp_damage(p, true, true)`: damage_bound, damage_ceiling, worst_damage, threatened, turn order's escape, the
  search's end-tile camp price), read again after our casts in refresh(). Fight simulations, camp exits, routing and
  upkeep still count it.

## 88: one turn-order scale for every champion (2026-10-22)

Against 87 (4f369f9): 51.3% of 1094 (ladder 57.1, gen 51.2, gen-s1 50.6), out-of-fuel turns 4454 vs 4333. Level,
kept. Test drafts only: our own draft is all teacher champions, whose path is unchanged.

- Champions outside the teacher six take idle, dead and danger priorities from `teacher_priority::priority` (idle up
  to 12, dead 13, danger 14..23). Before, they used bands of 10000, so any of them with an enemy within 8 (the
  engaged band, 10001+) outranked a teacher in top danger.
- The engaged band (`offer_engaged`) and the duplicate role table are gone; protect (10000+) and kill (20000+) bids
  stay above the shared range, for non-teacher champions only.

## 89: enemies revealed by our own move (2026-10-22)

Against 87 (4f369f9): 51.4% of 1094 (ladder 47.1, gen 52.0, gen-s1 51.4), out-of-fuel turns 4394 vs 4277. Fuel +0.4%
mean on the wide bench; on the 11 games it leaves identical ~190 a turn (the check), the re-read firing on 0.45% of
turns.

- Before, the strike search after moving, farm's post-walk `strike_enemy` and Safety read only the enemies seen at
  turn start: a walk revealing one (1.6% of turns, ~8 a game we could hit at once) fell through to the camp hit.
- `World::revealed(p, r)`: an enemy unseen at turn start now in sight within r of p (one `in_sight` host call per
  hidden enemy; false at the tile vision was last read from or last found clear).
- `see_revealed` re-reads vision and rebuilds Safety (`see_again`, shared with the ward path) when one is within
  `Strike::max_reach`: after farm's walk before its attack, after the strike plan in `decide()`, and in `act()` before
  `strike_after`; the end-of-turn heal and shield are judged again.
- Not caught: an enemy revealed by a failed step onto its tile (we did not move); farm's post-dash path has no
  `strike_enemy` at all.

## 90: enemy ward sight per owner, bushes included (2026-10-22)

Against 87 (4f369f9): 50.8% of 1094 (ladder 54.3, gen 51.0, gen-s1 50.2), out-of-fuel turns 4286 vs 4368. +0.05%
fuel on the 24 bench games it leaves identical.

- `Reach` credits an enemy only with its own ward's sight (vision.personal). Before, every visible enemy ward's
  walls-only shadowcast counted for every enemy, seeing into bushes no ward off them sees.
- `Wards` (safety.cpp) keeps one mask per enemy: `sdk_wards` (wards in our sight, with owner handles, ~20 fuel) and
  `sdk_ward_vision` (the engine's mask, ~350), cast again only when that owner's ward moves; looked up on a Reach's
  first sight query.
- probe-ward-bush: ward sight follows the bush rules, and `sdk_ward_vision` matches them exactly (cambc-rules.yaml
  `wards.vision` clarified).
- Known limit: a fresh enemy ward placed in its own turn is not modelled (see EXPERIMENTS).

## 91: Prism's camp stun on another harmless group (2026-10-22)

From the teammate's v37 (Khaos line). Against 90 (e14e7c3), each on its own draft: 50.7% of 1094 (ladder 54.3, gen
51.4, gen-s1 49.6), out-of-fuel turns 2303 vs 2235.

- After its basic attack at a harmless group, Prism's stun (slot 0) that would deal less than its full damage to what
  is left goes to a visible member of another live harmless group within range, if that takes more (`camp_cast`).
