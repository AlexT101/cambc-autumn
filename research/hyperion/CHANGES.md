# hyperion change log

What is in hyperion and why, oldest first. Entry numbers are stable because commits and research notes cite them;
missing numbers were reverted, superseded or cleanup, dropped in the 2026-10-22 trim. The untrimmed log is
`git show 1d5ddf0:research/hyperion/CHANGES.md`.

- hyperion was named hecate until 2026-10-21. `bots/hecate` is items 1-31 (the former hecate-v8, main b04c0e0);
  `bots/baselines/hyperion-v1` is 5d27969 (items 1-81); `bots/baselines/v37` is ladder submission v37, the
  teammate's Khaos line after v36. hyperion at 90 beat v37 51.2% of 1094 (level), each on its own draft.
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

32. Quality wave 1: small rule fixes and removals (`killable_now`, Safety::fight's exclude, the delayed tribute stun).
    48.5%, kept as fixes.
33. The periodic off-bush ward and the rally deleted (comms bit 31 free); `World::track` counts an unseen enemy's turn
    this round whatever its modelled order. 50.3%.
35. Sealed altars: `AltarAccess` (tribute tiles a walk from spawn reaches with live camps as walls) and `altar_usable`
    (believed-awake fire over tribute_turns(bag) below the carrier's health). `bankable_bag` farms a bag no altar is
    usable for as if empty, and while the team's largest bag has none, the groups sealing the altars are siege
    candidates. 49.0% (boss-battle 2/2).
36. Quality wave 2: a world phase out of fuel skips comms receive and decide; farm always evaluates; `heal_rounds`
    prices every heal trip; Safety's camp hits carry our Jungle and Durability; plus fixes. 54.5%, fresh seed 59.4%.
37. Strike search ([STRIKE-SEARCH.md](STRIKE-SEARCH.md)): `plan.cpp` searches every legal order of moves, dashes and
    strikes, camps as targets; a move only when a strike follows it, no landing that wakes a sleeping striker. Dash
    paths are blocked by visible enemy champions (probe-dash-enemy). 52.6% (582), 55.2% at 100M.
38. Strike phase 3a: an enemy Varg's splash in Reach and Strike. 51.0%.
39. Camp deaths reopen altars at once; access_fire reads every open tribute tile (was the first 64). 50.6%.
40. Farming stage 1: one heal price (`heal_rounds`), one `HomeTrip` price for every trip home, `prices()` for the next
    emblem's gain and gold in gems, `holders()` for cleared groups. 50.0%. (Stage 2 lost: EXPERIMENTS.)
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

Behaviour-identical fuel and cleanup in this stretch: 34, 39's caches, 41, 45, 51-55, 57.

## 60-81: fuel session 2026-10-22

Out-of-fuel turns were ~4.5x hecate's at the start. Net (79 against bbf6f05, main at the start): 54.2%, out-of-fuel
turns -61%; against hecate 65.7%. Wide bench at 100M: p99 106.8k -> 91.3k, turns over 100k 4147 -> 1944. Branches
are `fuel/<name>`.

Behaviour-identical: 60-62, 65, 69-71, 74-75, 78, 80 (fight simulation, strike search, Reach, farm and world caches);
63, 67, 72, 77 and 79 only merged them; 64 a bug fix.

66. want_home asks one fight: `Safety::stand()` replaces pursuit and visible_threat (enemies who can strike first,
    visible walkers joining, camps), and two fuel gates go. 52.2%; turns over 100k 3156 -> 2193.
68. Strike search commutation pruning: an order is dropped only when another has the same value and end tiles, so play
    changes only through tie order. 50.9%, out-of-fuel turns -5.8%.
73. step_guard asks the bound union fight before exact Reach exposure. 52.4%, out-of-fuel turns -20%.
76. The strike search grows at most 24 nodes (binds on 0.45% of searches, the best leaf lost on 0.07%; worst search
    158.6k -> 78.2k). 49.7%.
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
  enemies saved at turn start), else an idle value by role and health. Other champions keep the bands (until 88).
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

## 83-87: the 2026-10-22 audit

83 was behaviour-identical robustness fixes (throws, pool growth, a first-turn setup that throws part-way). 84 reads
enemies' Durability emblems (`ChampionBelief::taken`, 0.9 with one) into every basic-attack kill test, so a surviving
Durability holder is no longer dropped from the end tile's danger.

85. Logic fixes across the strike search, banking, locks, the endgame, world, comms, draft and turn order, with 84:
    51.0% of 1094 against 83 (ladder 48.6, gen 51.8, gen-s1 50.6), out-of-fuel turns 3816 vs 3612; with 86 on top,
    56.3% against 83 (ladder 44.3, gen 55.5, gen-s1 58.8). Rules it now follows: dash paths never cross the enemy
    spawn (probe-dash-spawn); a believed enemy lock is confirmed live before a tribute. The walk-only terminal leaf
    goes to any ranged champion with no reset or dash whose strikes exclude walking (Prism, now Stellar).
86. Judgment calls on top of 85: 54.9% of 1094 (ladder 58.6, gen 55.7, gen-s1 53.7), out-of-fuel turns 4000 vs 4104.
    - `game_ender` contests a winning tribute next to the enemy spawn too (a stun or a lock cancels it whatever
      healing). Generated maps keep altars 3+ from a spawn, so local A/Bs barely see it.
    - `closing()` prices a bag with no walk to an altar as `recall_turns` plus the walk from our spawn (was 0).
    - Fights drop a shield with 0 turn ends left at its owner's next turn start.
    - Camp ground casts and Heart of Ruin landings stay off tracked unseen Rens whose retaliation would kill us.
    - Farm floors a chain's trip at 0 (an emblem-completing capture could make the cycle 0 or below).
    - A carrier whose only walkable altar is the one `carry_bag` gave up on banks there again.
87. Rule fixes, level, kept: 49.1% of 1094 against 86 (ladder 45.7, gen 48.8, gen-s1 49.8), out-of-fuel turns 4428 vs
    3980. In steps: retaliation, pack zones, `lethal` and a crystal-pocket carrier recalling to bank
    by way of spawn 50.9% against 86; Durability 48.4% against those;
    stunned camps 49.8% against Durability.
    - Ren's retaliation sums over the strike plan (`Node::hurt`); a ground cast is refused on the summed retaliation.
    - Fight simulation: Durability (`Fighter::taken`) cuts each hit before the shield (probe-durability-shield).
    - Stunned camps: an awake member in sight with a stun skips the next camp phase in next-turn danger
      (`camp_damage(p, true, true)`). Fight simulations, camp exits, routing and upkeep still count it.
    - `lethal` judges our live health and shield; pack zones are rebuilt after the ward's re-read of vision.

## 88: one turn-order scale for every champion (2026-10-22)

Against 87 (4f369f9): 51.3% of 1094 (ladder 57.1, gen 51.2, gen-s1 50.6), out-of-fuel turns 4454 vs 4333. Level,
kept. Test drafts only: our own draft is all teacher champions, whose path is unchanged.

- Champions outside the teacher six take idle, dead and danger priorities from `teacher_priority::priority` (idle up
  to 12, dead 13, danger 14..23). Before, they used bands of 10000, so any of them with an enemy within 8 outranked a
  teacher in top danger.
- Protect (10000+) and kill (20000+) bids stay above the shared range, for non-teacher champions only.

## 89: enemies revealed by our own move (2026-10-22)

Against 87 (4f369f9): 51.4% of 1094 (ladder 47.1, gen 52.0, gen-s1 51.4), out-of-fuel turns 4394 vs 4277.

- The strike search after moving, farm's post-walk `strike_enemy` and Safety read only the enemies seen at turn
  start: a walk revealing one (1.6% of turns) fell through to the camp hit.
- `World::revealed(p, r)` finds an enemy unseen at turn start now in sight within r of p; `see_revealed` then re-reads
  vision and rebuilds Safety (`see_again`): after farm's walk, after the strike plan in `decide()`, and in `act()`
  before `strike_after`.
- Not caught: an enemy revealed by a failed step onto its tile; farm's post-dash path has no `strike_enemy`.

## 90: enemy ward sight per owner, bushes included (2026-10-22)

Against 87 (4f369f9): 50.8% of 1094 (ladder 54.3, gen 51.0, gen-s1 50.2), out-of-fuel turns 4286 vs 4368.

- `Reach` credits an enemy only with its own ward's sight (vision.personal), from the engine's mask
  (`sdk_ward_vision`, per owner, recast only when that ward moves; probe-ward-bush). Before, every visible enemy
  ward's walls-only shadowcast counted for every enemy.
- Known limit: a fresh enemy ward placed in its own turn is not modelled (see EXPERIMENTS).

## 91: Prism's camp stun on another harmless group (2026-10-22)

From the teammate's v37 (Khaos line). Against 90 (e14e7c3), each on its own draft: 50.7% of 1094 (ladder 54.3, gen
51.4, gen-s1 49.6), out-of-fuel turns 2303 vs 2235.

- After its basic attack at a harmless group, Prism's stun (slot 0) that would deal less than its full damage to what
  is left goes to a visible member of another live harmless group within range, if that takes more (`camp_cast`).

## 92: long winning-bag tributes wait for a safe window (2026-10-23)

From the v38 replay analysis (REPLAY-ANALYSIS A1, D2; REPLAY-FOLLOW-UPS R1-1, R2-1). Against c6bd503: 50.0% of 1104
(level on every suite; 5 of 552 map pairs played differently, none changed a result), out-of-fuel turns 4833 vs 4831.
Self-play rarely builds bags big enough; the ladder did (26 deaths and ~25k gems handed over in 19 games, mostly
01boss_battle). Replaying 76b6692e-4 with the patch: Marcella cancels her 158-turn winning channel at r948, where on
the ladder she kept it and died at r956.

- `any_risk` takes a winning bag's tribute at any risk only when its channel is `tribute_window` (6) turns or fewer;
  a longer one goes through `tribute_safe` like any bag.
- `tribute_ok` never starts or keeps a channel that cannot finish by round 2000.

## 93: dashers no longer freeze at hole lines (2026-10-23)

From the v38 replay analysis (REPLAY-ANALYSIS B2; REPLAY-FOLLOW-UPS R1-3): on the ladder, Heart of Ruin and Vesper
stood or ping-ponged at one-tile hole lines for up to 900 rounds (34.8k turns in 86 games; every 00great_wall and
01islands game). Against c6bd503: 50.2% of 1104 (ladder 53.8, gen 50.8, gen-s1 49.0), out-of-fuel turns 5022 vs
4931. In traced local games on 00great-wall and 01islands, no dasher stalls 30+ turns at a hole line (before: 297-479).

- A dash that hits where it lands (Heart of Ruin) paths on `landing_dash_walls`: no hole crossing within 2 of a camp
  group that can hit back, matching `dash_across`, which refuses any landing that would wake one. Before, its fields
  counted crossings the move code never takes. It detours around crossings beside such groups even while they are dead.
- `search_approach` aims at tiles in range of live members only (all members if none is known alive). In range of a
  dead member, a Vesper's approach read 0 steps, `dash_across` saw no gain and the walk could not cross.

## 94: recalls kept only when they can land; capture rides bank their share (2026-10-23)

From the v38 replay analysis (REPLAY-ANALYSIS B4a, B4b; REPLAY-FOLLOW-UPS R1-5, R1-8, R2-6, R2-7). Both together
against f07babf: 51.4% of 1104 (ladder 51.2, gen 50.4, gen-s1 52.3), out-of-fuel turns 4985 vs 5069.

- A champion that wants home keeps a shop or bank recall only if `recall_outruns` holds, the home keep's own test.
  Before, a refused home keep fell through to the shop/bank keep, alternating a retreat step with a standing turn on a
  recall the pursuer cancelled (ladder: 61 deaths, 1,477 gems in 57 games).
- `capture_recall` sets `memory.banking` when it keeps a ride to bank the share. `hold_start` guesses the later payout
  when a hold changed hands, so the ride can land a round late, off the hold; `recall_to_bank` then cancelled it with
  one turn left and the bot restarted it (ladder: 1,962 wasted channel turns in 276 games).

## 95: an enemy's second turn counts what comes ready by then (2026-10-23)

From the v38 replay analysis (REPLAY-ANALYSIS A3a: 203 deaths, mostly one-cast Marcella kills; REPLAY-FOLLOW-UPS
R1-4, R2-5). The narrowed form of w2-chain (EXPERIMENTS): one cast across both turns, no two-slot chaining. Against
6410707: 50.1% of 1104 (ladder 55.0, gen 49.4, gen-s1 50.0); deaths 6734 vs 6879 (ladder suite 625 vs 724, to
Marcella 1129 vs 1205); out-of-fuel turns 4984 vs 4688 (+6%, from more tiles reading dangerous, not the check's cost).

- `Reach::build`: an enemy acting twice before our turn checks readiness at `turn_round + 1` for its walk-then-act
  moves, and builds dash tiles if the dash is ready on either turn. Its move sets are cached by both turns'
  readiness (18 entries).
- `threat_strike`'s walk-then-strike term uses `strike_memo(c, round + 1)`, keeping the `Strike` bound that caps
  `Reach` valid (REACH-BOUND fired 0 times).

## 96: a spell clear finishes an attacker under the camp value floor (2026-10-23)

From the v38 replay analysis (REPLAY-ANALYSIS B1; REPLAY-FOLLOW-UPS R1-2, R2-2): on the ladder a Prism stood idle for
up to 940 rounds beside a camp attacker with under 50 health (20.6k turns in 56 games, 4.6k gems held untributed).
Against c6bd503: 50.4% of 1104 (ladder 51.2, gen 50.4, gen-s1 50.2); with each bot's own draft (Prism in every game)
51.3%. Out-of-fuel turns level. Local self-play never shows the freeze (0 runs in the reference), so only the ladder
can measure it.

- In `camp_cast`'s `attackers_only` mode (only `spell_clear`), the value floor is the lower of `min_camp_value` and
  the weakest live attacker's health. A cast is worth at most what it can remove, so the 50 floor refused every cast
  at an attacker under 50, while the clear stood out of basic-attack range. Every damage spell's raw exceeds 50, so
  only finishing casts pass. Covers Stellar, Tavi and Cassi on the same path.

## 97: a sure kill before retreating (2026-10-23)

From the v38 replay analysis (REPLAY-ANALYSIS C1: 119 retreat turns in 90 games walked away from a one-hit kill;
REPLAY-FOLLOW-UPS R1-6, R2-4). Against 04d5464: 50.4% of 1104 (ladder 47.5, gen 51.2, gen-s1 50.0), out-of-fuel turns
4898 vs 4926. About 0.1 kill-first turns a game locally.

- `retreat()` first attacks a visible enemy in range that one basic attack kills (health and shield, `taken`, Ren's
  retaliation guarded). A ranged champion, whose attack spends the walk, takes it only where nothing else can hit
  its tile next turn or a ready dash still lands out of every reach (`dash_clears`).
- `dash_away` leaves the just-killed enemy out of its threats.
- Melee: a kill one step off waits for the step, and an attack still unspent after the step is used on an enemy.

## 98: an unseen bush is not cover from an enemy whose ward we do not see (2026-10-23)

From the v38 replay analysis (REPLAY-ANALYSIS A4: 196 ladder deaths on bush tiles whose cluster held an enemy ward we
had not seen; REPLAY-FOLLOW-UPS R1-7). Against d474506: 50.3% of 1104 (ladder 52.5, gen 50.6, gen-s1 49.6),
out-of-fuel turns 5063 vs 5109. In the A/B replays, deaths on stepping into a bush 63 vs 81; turns in bushes equal.

- `Reach::at`: when we do not see an enemy's ward, a bush tile we cannot see counts as seen by that enemy from
  anywhere, since a ward hidden in the cluster sees all of it. Bushes we stand in or watch are judged as before.

## 99: altar_access floods the static walk only when needed (2026-10-23)

Fuel only: `tools/fuel/bench.py` wide set with test drafts at 100M, 52 of 52 replays identical. Against 0ba0eba: 50.0%
of 1104 (ladder 47.5, gen 50.8, gen-s1 49.6), out-of-fuel turns 5144 vs 5335 (-3.6%). On the opening maps at the
real budget (big-world, ambush, yellow-brick-road, starvation, reverse-spiral) 39 vs 72, in round 1 4 vs 24.

- `altar_access` read `pathing.foot()` every call, a flood of ~28k on 100x100 until the warm-up caches it; round 1 on
  those maps cost ~275k against 200k. It now reads it only when a tribute tile lies off our walk (where it can change
  `open`) or none is open (for `opened`).
- Where the fuel goes on turns over 100k (own cost a turn): fight sims 24.6k (~6.9 at 3.6k), step_guard 11k,
  update_camps 8.3k, Reach and threat builds 7.4k, blow 7.1k, Search::read 7k, camp_damage 5.9k, grow 5.1k.

## 100: a crew's hit cap credits the claimer only for work the camp shows (2026-10-23)

From the v38 replay analysis (REPLAY-ANALYSIS B3: farm targets flipping, 37k loop turns in 451 ladder games). The
cause is neither reading in REPLAY-FOLLOW-UPS: in both cases (2612381c-5 r457-463, 33916129-4 r401-406) nobody was in
sight, so no visibility changed. Against 138ed97: 50.0% of 1104 (ladder 50.0, gen 50.0, gen-s1 50.0), out-of-fuel
turns 5075 vs 4976; the first version (no claimer credit at all, d79cf52) 49.3%.

- `pick_up`'s claimed branch caps the hits we would take joining a crew. Our share credited the claimer with work
  during our walk from the current round; with the camp not really worked, that credit was re-made every turn, so each
  step closer raised our share past `spare_health` and the step back lowered it (00expanse group 9, r715-722: hits 177
  -> 190 -> 177 against a spare of 189). Unless the camp's health is seen falling (`last_damaged_round >= round - 1`),
  our share is now `strength / (strength + others)`, as if the claimer did nothing before we arrive.

Cumulative check (2026-10-23): 92-99 (bc7fd2e) and v38 (c6bd503), each against `bots/baselines/v37` on its own draft
(`--no-test-draft`, 1104 games): 57.2% (54.3-60.1; ladder 55.0, gen 61.3, gen-s1 53.5) against 54.8% (51.9-57.7;
ladder 61.2, gen 56.4, gen-s1 52.1). Against our own v38 the same changes were 51.3% (92-96, f19997a). Self-play
shows these ladder fixes as level; an outside opponent shows them ahead, within overlapping intervals.

## 101: Treasure emblem first (2026-10-23)

From the v38 ladder games (624 distinct, both teams): the opponents' extra gold is almost all the Treasure emblem.
Base capture gold is level (4,823 ours vs 4,750 a game); their bonus on top is +16.2% (+772) against our +1.6% (+75).
About 75% of opponent Heart of Ruin, Marcella, Ryth, Vendetta and Vesper builds include Treasure, usually first,
completed around r190-280; 16 of 18 top teams use it; we never bought it. Our champions earn 750-1,330 capture and
kill gold after r220, so +20% is 150-265 gold each, 5-8 shards, against one shard given up next to Power. (Opponents
opening Treasure do not beat us more often than others of the same type: confounded by team strength.)

Against dd3f481: 52.5% of 1104 (ladder 53.8, gen 53.5, gen-s1 51.4), out-of-fuel turns 4687 vs 4732; fresh suite
(seed 5291) 52.7% of 512; pooled ~52.6% of 1616 (~50.1-55.0). Against `bots/baselines/v37` on its own draft: 59.1%
(56.1-61.9; ladder 65.0, gen 62.3, gen-s1 54.9), where 92-99 scored 57.2%.

- `best_emblem`: until a champion owns a Treasure emblem it builds Treasure, in the stat the emblem model would pick
  (or the one it has begun), priced as the emblem it delays. `emblem_begun` counts Treasure shards. Prism's Focus
  build is unchanged.
- Untried: Treasure in Health, which most opponents use on champions other than Vesper; our Prism carries ~180
  unspent gold at r1000 against 66 for opponents' Prisms.

## 102: 4-pick maps draft Heart of Ruin over Ryth/Vendetta (2026-10-23)

From the v38 ladder games against the top 20 (624 distinct): we won 63% of 3-pick and 60% of 5-pick games but 43%
of 4-pick games (49/115, CI 34-52), the only count whose draft (the teacher draft truncated: Prism, Vesper, Marcella,
Ryth/Vendetta) has no Heart of Ruin. Each opponent's own 5-pick rate predicts 55.4% there (z -2.86; odds ratio 0.54
for opponent and side), against top-10 (36% vs 52%) and ranks 11-20 (55% vs 70%) alike. Pick order cannot matter:
picks are simultaneous and both teams may take the same champion.

Each on its own draft (`--no-test-draft`; test drafts hide draft changes) against c986e10: 53.0% of 1104 (50.0-55.9;
ladder 52.5, gen 53.1, gen-s1 52.9), 4-pick maps 60.0% of 330 (54.6-65.1), the rest identical. Fresh suite (seed 9417):
54.1% of 512, 4-pick 62.5% of 168. Against `bots/baselines/v37`: 60.1% (57.2-63.0), 4-pick 66.1%, where c986e10 had
57.2% and 57.6%. Out-of-fuel turns 2858 vs 2533 (Heart of Ruin's turns cost more).

- `draft_order()`: with 4 picks, the fourth pick is Heart of Ruin, swapped with the Ryth/Vendetta role.
- With 101 merged, against e2ad48c (101 alone), own drafts: 52.4% of 1104 (49.5-55.4; ladder 48.8, gen 52.1, gen-s1 53.3).

## 103: Bruiser emblems in the emblem model (2026-10-23)

From the v38 ladder games (624 distinct, both teams' purchases): the opponents' extra health is Bruiser. Their most
common completed builds on Ryth (136), Vendetta (121), Vesper (113) and Marcella (106) are Treasure > Jungle > Bruiser;
Bruiser is 66% of opponent Marcella's spending and 38-56% on Heart of Ruin, Ryth, Vendetta and Prism, in the main stat
and Health about equally. A Bruiser emblem is 7 shards' stats for 5 (Power's 6); `best_emblem` never priced it.

Against e2ad48c (101): 56.2% of 1104 (53.2-59.1; ladder 51.2, gen 56.1, gen-s1 57.0), out-of-fuel turns 4969 vs 4751;
fresh suite (seed 8431) 54.5% of 512 (50.2-58.8); pooled ~55.7% of 1616.

- `best_emblem` also prices Bruiser in the main stat and in Health (Prism: Health and Focus); Treasure still comes
  first, in the stat the model picks. A begun Bruiser is finished first; `emblem_begun` counts its shards.
- `add_completion` gives a completed emblem its extra stats (Power's sixth shard, Bruiser's other two), used by
  `value()`, `buy_shards` and `affordable_prefix`.
- Prism's mean ~180 unspent gold at r1000 is a tail (median 20): Prisms holding 200-365 gems that rarely go home.
- With 101-103 merged, against `bots/baselines/v37` on own drafts: ~65% of 1616 (ladder 66.2, gen 65.0, gen-s1 65.0,
  gen-s8431 65.2), out-of-fuel turns 4011 vs 5858. Before: v38 54.8%, 92-99 57.2%, 101 59.1%, 102 alone 60.1%.

## 104: farm values gold as paid to us, with our bonuses (2026-10-23)

A consistency fix for 101: `farm` priced a group's base gold, though our share is paid with our bonuses (rules:
"Gold bonuses add together and apply to each capture share and to kill gold"), so Treasure's +20% and Vesper Vale's
+33% were left out. Against d7917a8: 51.3% of 1104 (48.3-54.2; ladder 56.2, gen 51.0, gen-s1 50.8), out-of-fuel turns
4956 vs 4763. Against `bots/baselines/v37` on own drafts: 67.3% (64.5-70.0), where 103 scored ~65%.

- `gold_paid()`: 1.2 with a Treasure emblem, plus Vesper Vale's bonus. `pick_up` multiplies `per_gold` by it, and the
  gold that completes an emblem on the way home (`trip_home`, `capture_recall`) counts it.
- Weighting gold more lost before (3x 46.9%, front-loaded 45.6-47.2%) because the value model already prices gold by
  what the next emblem saves (`per_gold = share x saved / cost`), and gems are the score; we capture more base gold
  than top teams in every round bucket (r400-800: 1808 vs 1744). Treasure's price also adding its +20% return on our
  share's gold (03366f6): 50.7%, out-of-fuel turns +24%; dropped.

Cumulative check (2026-10-23): 92-104 (07d4261) against v38 (c6bd503), test drafts (so without 102's draft): 61.1% of
1104 (58.1-63.9; ladder 63.8, gen 62.7, gen-s1 59.0), out-of-fuel turns 5128 vs 4506 (+14%).

## 105: teleport crystals for travel (2026-10-23)

From the v38 ladder games: top teams teleport ~4 times a game (12 of 18 teams, median 35 steps saved), and on the maps
where they do we win ~19 points less against teams that teleport than against teams that don't; we only hopped to
altars no walk reaches (EXPERIMENTS "Teleport crystals for travel"). Measured on its map class: the 9 ladder maps where
opponents' teleports save 300+ steps a game (road_of_riches, starvation, shortcut, pilgrimage, concentrated_wealth,
fracture, gold_rush, reverse_spiral, great_wall; about a fifth of the ladder pool), as 256 `mapgen mutate` variants
(seed 2310) keeping 75%+ of each map's crystal value. Against 07d4261 there: 55.7% of 512 (51.3-59.9), 8 of 9 source
maps positive, 10.8 uses a game. Standard suites: 51.1% of 1104 (48.1-54.0; ladder 50.0, gen 50.6, gen-s1 51.8), 1.9
uses a game, out-of-fuel turns 4949 vs 4747 (+4%).

- Always carry a crystal. While farming, banking or walking home to shop, use it where a landing beats the walk by 6+
  steps, with no enemy in sight of either end and no awake camp at the landing.
