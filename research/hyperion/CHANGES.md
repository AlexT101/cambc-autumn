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

Reverted from main (2026-10-23) until it is refined; the change is commit 17cab26 (branch `strat/teleport`).

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
- Fresh suite (seed 7341, 256 general maps) against 4c4eacc: 50.2% of 512 (45.9-54.5), out-of-fuel turns 1746 vs 1703.

## 106: enemy teleports land at their destination (2026-10-23)

A seen enemy teleport (`channel_end_round`, its reserved landing) lands at its turn start in `channel_end_round` and
acts that turn; a stun or kill by us leaves it in place. Before, only tracking widened its `possible` to tiles within 3.
Developed on top of 105 (`strat/teleport2` cafa84c) and merged without it, as a bug fix, without an A/B of its own.

- Safety: its next turn starts at landing; it threatens nothing if it lands after our next turn, otherwise strikes
  from the landing tile (from its own tile when the landing is unseen).
- The fight search leaves it out until it lands; `prey` skips one we can't reach before it lands, and
  `intercept_steps` stops it by stun or hit in time or races its walk from the landing.
- A stun values cancelling a teleport like cancelling a recall; turn order offers to act first to stun one about to
  land. Tracking stops spreading its `possible` until it lands, narrowing it to its tile and the landing when known.
- Locally rare (visible enemy teleports per team-game: 0.47 ladder, 0.09 gen). With 105 and a crystal-buying rule,
  against 105 alone (8dbc020): 50.5% of 1104 (47.6-53.5), teleport class suite 50.6% of 512.

## 107: exact fixes from the 2026-10-23 code audit (2026-10-23)

TODO bugs whose fix uses information already read or a rule the bot already applies elsewhere; one A/B for the batch.

- `submit_here` judges a tribute at an altar believed locked: a melee carrier's own fifth hit on the lock no longer
  starts an unjudged tribute (or one past round 2000).
- No holding or contesting a capture whose payout falls after the last round (`pays_too_late`).
- An unseen channel's assumed end no longer replaces the last sighting (`pos`, `pos_round`), which had made
  `note_sighting` drop a teammate's sighting; a tribute's bag is emptied only when the enemy score rose
  (`update_scores`). Health still resets to full after an unseen recall.
- A visible enemy's fix is dated by its own `acted` flag (`Moment::end` once it has acted), as are `hold_start` and the
  respawn round, rather than by ranks that stale priorities can misorder.
- Heart of Ruin's landings (search and `self_abilities` dashes) keep off a seen or tracked Ren whose retaliation kills
  us (`unseen_suicidal`, `landing_suicidal`).
- Fights delay a visible ally with a stun still to serve (`stun_pending`, duration > 0) by a turn, and a teleporting
  one until it lands.
- `awake_over` checks live striking members only (`G.threat()` holds dead ones too).
- Turn order (role < 0 champions): a stun alone bids to cancel a recall; `offer_escape`/`may_escape` count our shield.
- A `set_turn_order` error no longer skips the claim and bag posts and the memory update.
- Against 90d285e: 49.7% of 1104 (46.8-52.7; ladder 42.5 of 80, gen 50.8, gen-s1 49.8), out-of-fuel turns 4973 vs
  4855. Kept as level.

## 108: audit judgment calls (2026-10-23)

Reverted from main for a ladder check (b7bfcb7), then reapplied: 107-108's 36.2% ladder deficit against 90d285e was
fuel, not logic (57.5% with 100M for both; 53.8% and 50.0% on fresh ladder mutations; research/EXPERIMENTS.md, Fuel).

The 2026-10-23 audit's items that needed a decision, each A/B'd alone against 107 (586586c), then together.

- Unseen threats measure range by Chebyshev distance from `possible` (a wall-free field), as Strike does: ground casts
  and ranged attacks across a wall line count, and `threats_at` answers the same before and after the build. 49.9%.
- A carrier drops a hold only when waiting for the payout would leave too little time to bank the bag and its share
  before the round limit, while banking now still fits (`holding_capture`). 51.0%.
- kite() stations for a unit-spell caster without a ground spell (Marcella) are tiles that see the monster
  (`member_attack_tiles` at unit range), with the distance squares as the fuel fallback. 50.3%.
- The strike search treats a target our own ward sees as attackable from any tile in range (`Search::ward_sees`).
  49.9%.
- Reach's dash paths cross live camps on bush tiles (unseen from outside their cluster), so it stays an upper bound.
  51.1% (out-of-fuel turns 4931 vs 4530), but no ladder, gen or gen-s1 map has a camp on a bush (the builder allows
  one), so it never fired: both figures are noise.
- `can_act_before` trusts only enemy priorities that can no longer change this round (test drafts only). 49.6%.
- An ally hold on a group unseen last round is dated this round, the later possibility. 50.0%.
- Together against 586586c: 50.6% of 1104 (47.7-53.6; ladder 48.8 of 80, gen 51.8, gen-s1 49.8), out-of-fuel turns
  5204 vs 4917 (+6%). Kept as level.

## 109: end-of-turn table queue (2026-10-23)

Spare fuel at the turn's end fills the terrain-only tables a fight reads (static windows, far sight masks, the search's
viewer rows), nearest tiles first: within 2 of visible enemies, then within 8 of us (20 while dead). The queue stops
once the turn has spent its real budget less a reserve, counted from the turn's start, so it fills the same at 100M
and never pushes a turn over. Each table fills as a miss would: play is unchanged (FUEL-GATES rule 3).

- 100M, byte-identical replays: 6-map test-draft screen 12/12, turns over 100k 1555 -> 1458; default bench 16/16,
  199 -> 175. Filling every tile on turn 1 (up to 41M) reaches 1427 on the screen.
- Against main a5749c4: 48.9% of 1104 (46.0-51.9), out-of-fuel turns 4610 vs 4818.

## 110: step_guard on first need (2026-10-23)

The guard is set with the inputs that change mid-turn (our tile, the dash radius) and built when a step, a dash or a
moving search first reads it; an anchored search (its own tile the only end) no longer reads it. Turns that never
step skip it: holding, a ranged champion that attacked, the guard after the search when the goal stays.

- 100M, byte-identical: screen 12/12, turns over 100k 1458 -> 1334 (p99 -2.4%, turns over 120k -6k); default bench
  175 -> 159.
- 109 + 110 against main a5749c4: 49.4% of 1104 (ladder 45.0 of 80, gen 49.6, gen-s1 49.8), out-of-fuel turns 3822 vs
  5058 (-24%).

## 111: an ally's stun read with its stats (2026-10-23)

An ally's stun is read with its stats when first seen in a round and kept on the belief. Safety read it live, and once
our move hid a believed-visible ally (vision is personal) the read threw and lost the rest of the turn.

- Against main, ladder + gen: 50.0% of 592 (ladder 48.8 of 80, gen 50.2), out-of-fuel turns 2339 vs 2481.

## 112: a retreat step out of every reach (2026-10-23)

When no step that keeps or shortens the walk home leaves every reach (`damage_bound` 0, camps included), `retreat_step`
also takes one that lengthens it and does. A step that only lowers the exposure stays excluded: a pursuer takes it
back (`fu/retreat`).

- Against main c71be8c: 49.7% of 1104 (46.8-52.7; ladder 48.8, gen 49.4, gen-s1 50.2), out-of-fuel turns 3813 vs 3956.

## 113: a shield-absorbed hit priced with Durability (astraeus, 2026-10-24)

The strike search priced a spell or Heart of Ruin landing that a shield fully absorbs at `min(raw, shield)`; the
shield drains by the reduced damage, so it is now `min(raw * taken, shield)`. The fallback for an unreadable target
counts the shield and Durability too.

- Against v47: 50.1% of 1104 (47.1-53.0; ladder 51.2, gen 50.4, gen-s1 49.6), out-of-fuel turns 2475 vs 2473.

## 114: dashers' altar distances by their own graph (astraeus, 2026-10-24)

`Pathing::centre_to_altar` took the draft's walking steps for every champion; a dasher on a map with crossable tiles
now reads its own `to_any_altar()` field, as farm's spawn steps already did (`draft_spawn_graph`).

- Against 113: 51.6% of 1104 (48.7-54.6; ladder 55.0, gen 51.0, gen-s1 51.8), out-of-fuel turns 2569 vs 2497.

## 115: captures left to allies free to take them (astraeus, 2026-10-24)

`capture_taken` (siege and kite captures of a cleared big group) counted every visible ally nearer the group as a
holder. An ally not on its tiles now counts only if it is not bound elsewhere: tributing, on a recall kept through a
turn (`kept_recall`), or claiming another group.

- Against 114: 50.1% of 1104 (47.1-53.0; ladder 51.2, gen 50.0, gen-s1 50.0), out-of-fuel turns 2896 vs 2706.

## 116: a mid-turn kill read as a death (astraeus, 2026-10-24)

Only a full update read liveness, so an enemy we killed became, after `observe()` (`see_again`), an unseen enemy
around its last tile. `observe()` now reads `engine::alive` for an enemy seen this turn and now out of sight, and
marks a dead one as the full update does (respawn from this round).

- Against 115: 50.0% of 1104 (47.1-52.9; ladder 50.0, gen 49.8, gen-s1 50.2), out-of-fuel turns 2783 vs 2789.

## 117: a hold yields to the damage it takes; respawning tiles left free (astraeus, 2026-10-24)

`want_home`'s low-health exemption for a capture hold now lasts only while the health we lost last round, repeated
to the payout (+1), stays below our health: camps hit from out of sight and bush attackers are unseen, so the
fight sim never saw them. The approach to a respawning group (`search_approach`, no live member) drops the group's
own tiles from its goals, since a group returns only once its tiles are empty.

- Against 116: 50.8% of 1104 (47.9-53.8; ladder 47.5, gen 50.0, gen-s1 52.1), out-of-fuel turns 2823 vs 2804.

## 118: a retreat steps or dashes to a sure kill (astraeus, 2026-10-24)

A leave turn (`want_home`) never runs the strike search, and `retreat` took a sure kill only from where we stood. It
now also takes one from a tile a step away (melee only: a ranged walk spends the attack) or a ready dash away, when
nothing but the victim reaches that tile (`only_threat`); the dash lands nearest our spawn (`dash_onto`).

- Against 116: 50.2% of 1104 (47.2-53.1; ladder 50.0, gen 50.0, gen-s1 50.4), out-of-fuel turns 2810 vs 2802.

## 119: a carrier on our own ground checks for pursuers (astraeus, 2026-10-24)

`want_home` skipped the pursuit steps for a healthy champion on our own ground ("they have no reason to come for
us"). A kill takes the whole bag, so a carrier of `brake_bag` or more (both bags for Cassi and Issac) now runs
`stand(here, pursuit_steps)` there too; the fight sim still reads Prism's live Focus, so a winning fight still stays.

- Against 118: 51.4% of 1104 (48.4-54.3; ladder 55.0, gen 51.2, gen-s1 51.0), out-of-fuel turns 2733 vs 2745.
  Against 116: 51.1%, gems lost on death -5.4%, tributed +1.4%.

## 120: joining an enemy Monolith siege (astraeus, 2026-10-24)

Off Monolith-only maps `siege_candidate` passed a live Monolith only when it sealed the altars. An awake Monolith
with a visible enemy in its reach (or one that is already our siege claim, or an ally's) is now a candidate
(`enemy_in_reach`). `siege_ready` judges it by its current health within `siege_rounds`, without the health-pool
check while an enemy is in its reach, since the nearest champion takes its hits. The rest of `siege()` is unchanged.

- Against a proxy that sieges Monoliths on every map (mixed-Monolith maps only): 58.6% of 268 vs REF's 55.2%; on a
  fresh suite 54.4% of 272 vs 50.0%. Our Monolith captures there went from 11 to 33.
- Against 4d08241 on the full suites: 49.9% of 1104 (47.0-52.9; ladder 50.0, gen 50.0, gen-s1 49.8), out-of-fuel
  turns 2779 vs 2743. Against hyperion: 50.5%.

## 121: Willow takes no chase (astraeus, 2026-10-24)

`prey()` returns null for Willow: `want_home` sends it home whenever an enemy is likely to hit it ("Willow holds no
fight"), so a chase walked it into that reach to leave the next turn (1,214 chases in a trace, 85% never landed a hit,
0.9% of our kills). Willow is drafted only on 5-pick maps.

- Against d3cc38f on the 190 five-pick maps of `maps/`, `maps/gen`, `maps/gen-s1`: 49.5% of 380 (44.5-54.5),
  out-of-fuel turns 1814 vs 1903. Bundled with a Vesper retreat change on the full suites, the 5-pick maps read 50.0%
  of 380.

## 122: enemies who walk into a fight join its verdict (astraeus, 2026-10-24)

The fight sim was calibrated when every enemy was already in reach (1.4% of "won" verdicts died), but when more
enemies arrived than it counted, 9.3% died. `Safety::late(p, key)` lists the visible enemies outside a fight's key
who walk into reach of p within `pursuit_steps` (off their spawn), joining at `arrives_at = approach()`; the fight
memo is keyed by (key, late).
- `want_home`: `stand()` takes them (`joined`) once a visible enemy hits us, even where pursuit is skipped (healthy,
  no bag, on our own ground, or a capture paying soon): pursuit is a reason to come, but a fight already on draws them.
- `prey`: `chase_trade` at the target's tile takes them.
- Against d3cc38f: 50.9% of 1104 (48.0-53.8; ladder 50.0, gen 50.0, gen-s1 52.0), out-of-fuel turns 2573 vs 2778.
  Fresh suite (seed 7321): 52.1% of 512 (47.8-56.4), 1240 vs 1208. Against hyperion: 53.4% of 1104 (50.5-56.4;
  CHANGES 120's bot read 50.5%).
- Also through `step_guard` (each tile's key with every late enemy at its earliest arrival over the guard, so a
  larger key is still a worse fight): 50.2% of 1104, out-of-fuel turns 2813 vs 2596. Not kept.

## 123: a shop trip is priced by everything the gold buys (astraeus, 2026-10-24)

`wants_shop` (and Prism's capture-hold recall) priced a trip by the next emblem only (`affordable_prefix` stopped at
its 5 shards), so a healthy champion that never died never went home: on the ladder our Prism held 300+ gold for
100+ rounds in 138 of 299 games, and teams ended with ~1000 gold unspent against opponents' ~350.
`affordable_prefix` now walks the whole purchase as `buy_shards` makes it (`best_emblem` over the items it would own),
prices it with `upkeep_cost`, and keeps the saving while our gold (in shards) and stats hold. Non-Prism champions
still need the next emblem affordable before going. The code landed inside adbdfcf6 (CHANGES 122's commit staged the
file while it was being applied); this entry is its record.
- Against 5d43ecf: 52.4% of 1104 (49.4-55.3; ladder 55.0, gen 50.8, gen-s1 53.5), out-of-fuel turns 2708 vs 2532
  (per game 2.45 vs 2.29). Fresh suite (seed 7331): 50.6% of 512 (46.3-54.9), 943 vs 957. Against hyperion: 53.9% of
  1104 (50.9-56.8; CHANGES 120's bot read 50.5%).
- Ladder suite, Prism: mean gold held 146 → 95, at game end 299 → 167, rounds at 300+ gold 159 → 119. Other
  champions about unchanged.

## 124: enemies in bushes first in the shared sighting (astraeus, 2026-10-24)

`comms::send` posts the one sighting a round for a visible enemy on a bush first, then round-robin as before: a bush
tile cannot be seen from outside its cluster, so only whoever shares it sees that enemy, while one in the open is
seen by any teammate near enough. In a trace, 208k of 607k damage from unseen attackers came from ones a teammate had
seen that round or the one before, 931 of those 1,418 hits from bushes.

- Against d3cc38f: 49.7% of 1104 (46.8-52.7; ladder 50.0, gen 50.6, gen-s1 48.8), out-of-fuel turns 2573 vs 2564.

## 125: a kill read as a death before the escape (astraeus, 2026-10-24)

After `retreat`'s hits, an enemy we killed stayed alive in World, so `dash_away`'s threats (all but a sure kill's
`dead` tile), `landing_suicidal` and `retreat_step`'s gap still counted it around its tile; a kill by the reset after
the escape dash came after `refresh()` had read it alive, so Safety counted it too. `see_kills` re-reads vision
(`see_again`) when a visible enemy is no longer alive, else refreshes as before; it runs after the hits and after
that reset.

- Against acbcbcb: 49.9% of 1104 (47.0-52.9; ladder 50.0, gen 50.0, gen-s1 49.8), out-of-fuel turns
  2298 vs 2296.

## 126: our winning bag no longer blocks interception (astraeus, 2026-10-24)

Ported from `p2/intercept-first-main` (99248f8, hyperion). While our bag would win, `game_ender` returned null and
`continue_tribute` never cancelled, whatever the enemy's winning tribute's end. Now our tribute waits for a stun or a
lock only if theirs lands before our win (`win_lands`: our channel's end, or a walk to the nearest altar and a whole
channel), unless a visible ally acting in time can stop it alone (`ally_stops`: a ready stun in reach, or a carried
lock within 2 of an altar not ours); `game_ender` pursues only a tribute that lands first.

- Against d16e9e9: 49.4% of 1104 (46.4-52.3; ladder 48.8, gen 49.4, gen-s1 49.4), out-of-fuel turns 2403 vs 2364.
  Both teams near 1000 at once is rare locally: a logic fix, level.

## 127: a visible enemy's stun takes its next turn in Safety (astraeus, 2026-10-24)

World read the pending stun (`stun_pending`) only for allies; Safety counted a stunned enemy's next turn as if it
acted (the planner read the stun only for `stunnable`). Now a visible enemy's pending stun takes one turn from
`turns_before_ours` and moves `next_turn_round` to its first real turn; with none left before ours its threat strike
is empty (as for a teleport), so per-tile damage, lethal, recall and tribute safety and the step guard ignore it. It
still fights: fight keys, `late`, `stand` and `turns_to_kill_idle` take it in by its first turn's reach
(`fight_reach`, `lost_in_reach`), arriving a turn late as a stunned ally does; doubled bounds no longer double it.
Stuns we cast mid-turn are still not read (bug 1).

- Against d16e9e9: 51.1% of 1104 (48.1-54.0; ladder 50.0, gen 52.1, gen-s1 50.2), out-of-fuel turns 2349 vs 2293.

## 128: a stun we cast is read mid-turn (astraeus, 2026-10-24)

CHANGES 127 read `stun_pending` at turn start only, so the rest of the turn after our own stun (Prism's, Ryth's
ground stun, Heart of Ruin's landing, Marcella's attack after her reset) still counted the target's next turn.
`World::read_stuns` reads it again, once a turn after the stunning slot was cast (for Marcella, once her attack is
spent too), for visible enemies within the stun's reach + 1 of us; if one changed, Safety starts again. It runs in
`see_kills`, after `retreat`'s escape dash, after the strike plan in `decide()`, and before `set_turn_order`. Allies
acting later this round read it at their own turn start.

- Against 2b34c2f (CHANGES 127): 50.5% of 1104 (47.6-53.5; ladder 53.8, gen 50.8, gen-s1 49.8), out-of-fuel turns
  2438 vs 2305. It changed a belief ~30 times in a debug game.

## 129: an enemy revealed by a refused step (astraeus, 2026-10-24)

A move refused by a hidden unit reveals its tile for the round, but `World::revealed` returns early at the tile vision
was last read from, so when no other step went through, `see_revealed` never rebuilt Safety around the enemy. Pathing
now flags a refused move (`take_bump`), and `revealed` then checks for enemies even there.

- Against 2b34c2f: 49.6% of 1104 (46.7-52.6; ladder 50.0, gen 49.2, gen-s1 50.0), out-of-fuel turns 2377 vs 2428.
  Rare: one reveal in two debug games.

## 130: camp stuns read by their timer; three thrown errors avoided (astraeus, 2026-10-24)

A camp's stun buff stays listed at timer 0 after the camp phase it skipped, until the next (`probe-campstun`), so at
our turn start `camp_stunned` dropped a member that would hit us (12 of 12 such turns in the batch 5 bug hunt). Both
copies now need timer > 0; a stun cast on a timer-0 camp still skips its next attack, so `camp_cast`'s stun value
counts it. Errors no longer thrown (~3.9k fuel each): `submit_here` while stunned; `place_lock` at an altar our team
already locks out of sight (`own_lock_round`: from a placement or the engine's refusal, until the altar is seen after
that round); `start_recall` a second time in a round, after a turn that ran out of fuel started one in its resumed
tail.

- Against 298cff1: 50.5% of 1104 (47.5-53.4; ladder 52.5, gen 51.8, gen-s1 48.8), out-of-fuel turns 2389 vs 2544.

## 131: a walk out of a closed pocket is not searched every turn (astraeus, 2026-10-24)

A route search grows from the goals until it reaches us, so with no walking way out (a dasher's hole island, units) it
fails only at its cap, after labelling the whole map. On the ladder (9bce3341-2, 01big_world) our Vesper on a 4-tile
hole island ran out of fuel on 197 turns in a row, r488-712: `retreat_step`'s last `step_towards(home)` searched at
cap 112 (22k) and at 192 (31k), both failing; the resumed tail finished the search and the fresh turn repeated it.
After a search fails at its cap, `Pathing::enclosed` floods from us (radius 16 and 17, flat host calls, ~1.1k): a
closed region with no goal and no ally beside us (`make_way`'s case) cannot reach one at any cap, so the search
counts as exhausted (no wider retry) and that tile is tested first on later searches.

- Against 298cff1: 49.6% of 1104 (46.7-52.6; ladder 50.0, gen 49.6, gen-s1 49.6), out-of-fuel turns 2400 vs 2404.
- 100M bench: identical replays (wide set 52/52, fuel +0.09%; 01big_world, 00lost_world, 01islands 6/6, -0.2%).
  Real budget on those three maps: 25 out-of-fuel turns vs 33.
- v47 harness re-run of 9bce3341-2 with the fix live from r488 (free before, so the game matches the ladder until
  then): 5 of our turns at the full budget vs 203.

## 132: a turn that ran out of fuel does not act in the next round (astraeus, 2026-10-24)

A turn that runs out of fuel resumes as the next round's turn and was abandoned only at the next costly step
(`throw_if_stale`), so its tail could still walk, attack, cast or start a recall in the new round before the fresh
turn planned without knowing: a second recall start (rc 113, which CHANGES 130's same-round guard in `start_recall`
only saved the throw of) or an exclusive cast after a walk (rc 126). Every action (walk, attack, cast, recall start
and cancel, tribute start and cancel, ward, lock, crystal, shop, priority) now calls `throw_if_stale` first (~18 fuel),
so the fresh turn is the only one that acts; CHANGES 130's recall guard is removed as redundant. Debug REF on the
ladder maps (80 games): 61 actions in 47 of 230 out-of-fuel turns (39 walks, 9 attacks, 9 recall starts, 4 casts).

- Against e2deee3: 49.5% of 1104 (46.5-52.4; ladder 48.8, gen 49.8, gen-s1 49.2), out-of-fuel turns 2502 vs 2537.
- 100M bench: identical replays (wide set 52/52, fuel +0.01%).

## 133: a small bag chains past distant enemies, up to 45 gems (astraeus, 2026-10-24)

`may_chain` sent a bag home whenever any credible enemy was anywhere on the map (`any_threat`); on the ladder that
started 44% of our bank trips, and our non-Prism tribute bags were about half the top teams'. It now refuses only for
a credible enemy within `pursuit_steps` of our reach (`credible_enemy_may_hit_within`), and `chain_bag_limit` is 45
(was 30). CHANGES 119's carrier pursuit check covers chained bags from `brake_bag` (11). Kept on the ladder argument:
locally fewer, bigger tributes but more gems lost on death, and banking time level (chained bags start home farther).

- Against c2f1350: 51.4% of 1104 (48.5-54.4; ladder 53.8, gen 55.1, gen-s1 47.5), out-of-fuel turns 2367 vs 2446;
  fresh suite (seed 7511) 49.2% of 512. Against hyperion 54.7% of 1104 (REF 53.1%).

## 134: 3-pick maps draft Marcella, Vendetta, Heart of Ruin (astraeus, 2026-10-24)

The draft is now one table per pick count (`params::draft_three/four/five`, replacing the camp-count roles of
`draft_selection.h`) plus `draft_counters`, empty. 3 picks: Marcella, Vendetta, HoR replaces Prism, Vesper, HoR; 4 and 5
picks are unchanged. Search and per-team results in [DRAFT.md](DRAFT.md#astraeus-draft-search-2026-10-24).

- Against proxies of 8 top-10 teams on every 3-pick map: 63.7% vs 47.3% for the old draft (+16.5 ±6.5, 364 games);
  fresh suite (seed 4242) 60.1% vs 42.9% (+17.3 ±10.4, 168).
- Head to head against astraeus c0de6b4 on 3-pick maps: 61.5% of 532 (all maps 59.9% of 364, fresh 64.9% of 168).
- Other pick counts play identically (the old tables reproduce c0de6b4's games).

## 135: a kill in the strike search opens its tile (astraeus, 2026-10-24)

The strike search fixed its free and dash-passable tiles at the start (`read_geometry`), so a unit it killed still
blocked every later move in the sequence (hyperion TODO bug #2): no melee kill then a walk onto the tile, no Vesper or
Heart of Ruin kill then a dash through it. Each node now records the tiles opened by kills before its walk
(`open_w`) and before its dash (`open_d`); the walk, dash and landing domains add them (`free_n_at`, `landings_at`,
`land_here_at`). A tile a kill opens counts only for moves after the kill, and not on the enemy spawn.

- Against c0de6b4 (as `bots/variants/p1-ref`): 50.8% of 592 (46.8-54.9; ladder 51.2 of 80, fresh suite seed 8821
  50.8 of 512), out-of-fuel turns 1416 vs 1280.
- 100M bench, wide set: identical replays 52/52, fuel +0.06% (p99 +0.2%). The new sequences were never chosen there:
  it rarely fires.

## 136: a spent stun is not a pending one; Marcella's tribute gold in farm worth (astraeus, 2026-10-24)

A stun buff at 0 turn ends left has already taken its turn, and a new stun takes the following one. `has_stun` read
any stun buff as active, so for about a round after every stun the strike search, `enemy_cast`, `attack_target`'s
stunnable test, `ally_stops` and the turn-order danger read that enemy as stunned: no stun value, no danger removed by
stunning it, and `enemy_cast` left it out of the enemies that could reach us next turn (a "free" stun could spend the
walk while it could still hit us). They now read `stun_pending` (duration > 0), as Safety already did. Marcella's
passive pays 2 gold per gem she tributes, with no gold bonus; farm worth now counts it for her.

- Against 00fd51c: 50.7% of 592 (46.7-54.7; ladder 43.8 of 80, fresh suite seed 8821 51.8 of 512), out-of-fuel turns
  1471 vs 1619.

## 137: Vendetta's Treasure in Health; a Vendetta ally's arrival (astraeus, 2026-10-24)

Vendetta's first emblem, Treasure, goes in Health instead of the model's stat (always Strength for Vendetta, which has
no Focus-scaled ability), as 74% of ladder Vendettas build it; `best_emblem` prices Health only by heal trips. Vendetta
is drafted on every 3-pick map since CHANGES 134. A claimed camp's crew timing (`earliest_work_delay`) had a Vendetta
ally dash every turn on its way, as if each turn made a kill: now one out of sight has its dash ready (an unseen kill
may have readied it), then the usual cooldown; one in sight uses its known cooldown. Other Vendetta fixes tried with
these lost ([EXPERIMENTS](../EXPERIMENTS.md#vendetta-2026-10-24-astraeus-on-its-3-pick-draft-marcella-vendetta-hor)).

- Treasure in Health alone, against 72de514 on the 3-pick maps (own drafts; other pick counts play identically): 53.8%
  of 364 (48.7-58.9; ladder 58.3 of 12, gen 53.6, gen-s1 53.8), fresh suite seed 9137 54.1% of 170; out-of-fuel turns
  612 vs 643.
- The arrival fix alone: 49.5% of 364, level; kept as a model correction. The two were not played together.

## 138: Vendetta's Monster emblem (astraeus, 2026-10-24)

`best_emblem` offers Vendetta a Monster emblem in Strength (+10% damage to camps), priced by the model like the others:
with its base Strength of 70, +10% on camps outweighs Power's sixth shard. A begun Monster emblem is finished first
and counts in `emblem_begun`. Camp kill tests count the bonus (`camp_dealt_factor`): the strike search's camp targets,
the reset kept for a camp kill, and the station simulation. In the earlier Vendetta bundle it looked like a loss; on
its own it wins ([EXPERIMENTS](../EXPERIMENTS.md#vendetta-2026-10-24-astraeus-on-its-3-pick-draft-marcella-vendetta-hor)).

- Against 065f2631 on the 3-pick maps (own drafts; other pick counts play identically): fresh suites seeds 5171 and
  6203, 54.5% of 312 (48.9-59.9); ladder, gen and gen-s1, 54.1% of 364 (49.0-59.2); 54.3% of 676, out-of-fuel turns
  level (1070 vs 1072).

## 139: stall guards for unseen maps: crystal-only altars, unreachable altars, a camp over our spawn (astraeus, 2026-10-24)

A pre-tournament audit traced astraeus through edge-case maps for stalls. Repro maps and their generator are in
[repro-maps/](repro-maps/) (outside `maps/`, so no A/B suite reads them).

- **Crystal-only altars** (`crystalaltar`: every altar behind a 2-wide hole moat): unpatched, every champion stood
  still from about round 150, holding 18-57 gems, 0-0 at round 2000. `recall_to_bank` priced the trip home on foot,
  and from spawn walking reaches no altar either, so nobody went home to buy a crystal; those with 0 gold
  (gem-only farming) could not buy one anyway. Now `recall_to_bank` also keeps the recall when walking reaches no
  altar, a hop is wanted and we can buy a crystal; a bag that only a crystal could bank counts as unbankable while
  we hold none and cannot buy one, so we farm the gold first (only on maps with hops); and the crystal is bought
  before shards, on spawn and while dead. Patched: a 1000-gem win at round 1506.
- **Altars no one can reach**: `altar_access` counted every tribute tile off our walk as a crystal's. It now keeps
  one only if `StaticMap::hops` has a hop to its altar, so a bag no altar can bank is held back (farm and shop as if
  empty-handed) rather than carried to the 45-gem limit and stood on.
- **A camp whose reach covers our spawn**: a champion hurt on spawn took the heal branch (`mend`) every turn while
  the awake camp hit it, and never left. `mend` now skips when a camp can hit our tile (only on maps where a camp
  member's reach covers our spawn, read once). Not reproduced: our all-melee 3-pick team cannot wake a camp it
  cannot reach, so the pin needs an enemy or a ranged ally to wake it.

- Against 72de514: 49.2% of 1104 (46.2-52.1; ladder 47.5 of 80, gen 50.6, gen-s1 48.0), 0 failed, out-of-fuel turns
  3312 vs 3120. 100M bench (wide set): identical replays 52/52, fuel +0.16% (~70 a turn), so the ladder and suite
  differences come from fuel only.
- Repro maps, patched against itself: crystalaltar ends in a 1000-gem win at round 1506 (unpatched 0-0 at 2000);
  spawnpin, spawnpin-golem and deadaltar play normally either way.

## 140: Marcella's tribute gold gets our gold bonus in farm worth (astraeus, 2026-10-24)

`probe-marcella-gold` found the engine applies gold bonuses to Marcella's 2 gold per tributed gem (with a Treasure
emblem a 29-gem tribute paid 69.6, not 58; the fraction carries over; paid when the channel completes), which the
rules YAML said only for capture shares and kill gold (fixed there). CHANGES 136's farm-worth term for it now uses our
bonus rate (`paid`), as capture gold does: with Treasure, her tribute gold is worth 20% more. Not A/B'd: it changes
only Marcella's farm worth once she owns Treasure, by 20% of a term that is itself small.

## 141: comms packed by map, priority payloads, a second sighting (astraeus, 2026-10-25)

The 8 shared bytes hold each record as one mixed-radix number sized from the map and both teams' sizes (a sighting's
tile index, enemy and health as one value; bag and claim times the team size with the writer's index; a capture's
respawn round mod the group's respawn + 17, decoded from the reader's previous turn). Priorities are renumbered by an
order-preserving 12-bit rank code, then 7 - ally index, then a 16-bit payload; raw 0 stays 0 and the sign is kept,
since bots read a champion they have not seen as priority 0. The payload carries the claim and the Prism/Willow support
intents, so an ally in sight always reads our current claim, and support leaves shared memory. Where the layout has
room, the camp slot carries a second enemy sighting (a capture wins it), two sightings a round instead of one.
49.9% of 1104 against 2289c90a (47.0-52.9), out-of-fuel turns 2831 vs 2699: kept as the base for vision changes
([EXPERIMENTS.md](../EXPERIMENTS.md#comms-packing-2026-10-25-astraeus)).

## 142: rules and formulas for magic numbers and special cases (astraeus, 2026-10-25)

An audit for literals standing in for rules and for per-champion or per-map exceptions. Same play (100M bench, wide
set, own and test drafts: 104/104 replays identical, fuel level):
- Rule constants named once and used everywhere: dash, ability, melee and ranged ranges, the ground cast's 3x3, Varg's
  splash (`ChampionFacts::basic_reach`), the lock, submit and ward ranges, shards per emblem, the Jungle, Durability,
  Monster and Treasure factors (their literals were repeated up to 8 times), Ryth's ratio, `recall_turns()` for any
  champion, the teacher priority's kit table (now read from `champion_table`) and its rank code bounds, a turn's fuel.
- Champion checks by type read the rule they stand for: `heals()` for Willow, `Passive::gem_focus` for Prism,
  `tribute_gold_per_gem()` for Marcella; `plan.cpp`'s grid sizes come from the dash and ability ranges.
- `tribute_turns` keeps the rules' 10 gems a turn as a constant: reading the engine's settings at run time cost
  +0.3% fuel a turn (the farm loop calls it per group, and the division no longer folds).

Changed play, each against 9328116 over 1104 games (ladder, gen, gen-s1), all level:
- Corrections (49.5%): Prism's capture gold share takes the remainder and the full gold bonus (it floored Treasure's
  20% and dropped Vesper's); woken camp hits in the strike search count our Jungle and Durability; Vendetta's
  dash-to-kill and the reset's may-kill test count the target's shield and Durability; the pack zone's healthy ratio
  of 100 ("too high to trigger") is gone: only hurt (2.5) or at home (2.0) does a pack send us back early.
- Arrival tests (51.1% and 50.9%): a capture is finished while it pays before any enemy seen this round or last could
  walk into reach (was: none within 3 and payout within 2); camp casts and the camp reset are held while a visible
  enemy is within a step of our cast (or basic) reach or of its own strike (`engagement_near`; was 6 and range + 2).
- Special cases generalised (49.8%): a camp stun credits sparing any ally in the monster's reach (was Monolith only);
  the Monolith-only floor for a damage-free stun is gone; any unit cast overkilling a harmless group retargets (was
  Prism's slot 0); approach casts for any ranged champion whose casts outreach its attack (was Prism); every
  champion's basic attack target takes the most value, kills first (was Varg only).
- Values (50.3%): a stun is worth the target's damage a turn (`output`, was 80), a stopped game-winning tribute the
  game's gems (was 5000), and the camp-cast floor is the cast's cooldown cost (`cast_cost`, shared with the strike
  search; was 50).
- Holders and handoff (49.8%): a Monolith splits by the tribute window like any group (3 holders, was 2); any dasher
  paid more gold takes a one-holder gold capture from a higher-id ally paid less (was Vesper from Heart of Ruin).

All together: 49.9% of 1616 (47.4-52.3; ladder 45.0, gen 46.9, gen-s1 54.5, fresh suite seed 7319 49.0), out-of-fuel
turns 4325 vs 4048 ([EXPERIMENTS.md](../EXPERIMENTS.md#magic-numbers-and-special-cases-2026-10-25-astraeus)).

## 143: hits short of a kill priced by kill progress (astraeus, 2026-10-25)

From the 2026-10-24 ladder ([ladder-analysis](../ladder-analysis-2026-10-24.md)): we hit the lowest-hp enemy in range
64-65% of the time (top teams 78-91%) and killed 19% of the enemies we brought below 25% (IF 27%, CM 31%). A hit short
of a kill was worth its damage whatever the target's health. Now every hit is worth the fall in `kill_distance`:
0.4 x health + (0.6 x full + life + bag) x sqrt(health / full) (`params::chip_value` 0.4), in `plan.cpp` and the casts'
`hit_worth` alike. A kill from full health is worth full + life + bag as before; chip damage counts ~0.8x at full
health and ~1.3x at 20%, and the worths of a foe's hits sum the same in any order, as the strike search assumes.

- Against 3f8e75e: 52.4% of 1104 (49.4-55.3; ladder 62.5, gen 50.4, gen-s1 52.7); fresh suite seed 4417 49.0% of 512;
  pooled 51.3% of 1616. Ladder maps and their `mut-*` mutations 56.8% of 278, other generated maps 50.1%. Deaths a game
  4.77 against 5.29. Out-of-fuel turns +9% (2814 against 2577).

## 144: a low Monolith burst on mixed maps; no siege heal trip once the group is cleared (astraeus, 2026-10-25)

On Monolith maps the top teams captured one in 53-55% of ladder games, we in 17%: off Monolith-only maps
`siege_candidate` took a live Monolith only when it sealed the altars or the enemy was on it. Now one whose known
health the team clears within `params::burst_rounds` (20) is sieged too, through the usual health-pool check and
staging. `siege_heal_trip` no longer keeps a recall once the besieged group is cleared: in a smoke game all three
of ours recalled after the clear and the enemy took the game-winning capture.

- Against 3f8e75e: 50.5% of 1104 (47.6-53.5), Monolith maps 53.0% of 270; fresh Monolith maps (seeds 4417 and 6151,
  130 maps) 51.2% of 260. Monolith captures 208 against 121. A solo chip on top lost ([EXPERIMENTS](../EXPERIMENTS.md#ladder-analysis-ideas-2026-10-25-astraeus)).
- 143 and 144 were each A/B'd alone; together they were only smoke-tested (8 games).

## 145: blocked ways: camps in the way are breached, sieges stage by any member, crystal altars need a live way to a source (astraeus, 2026-10-25)

Stalls found on the 2026-10-25 suites (champions on one tile for 300+ rounds, alive and off spawn: 35 in 1104 games
against astraeus 71e3e19), each the whole team on some maps, both bots alike:
- **A camp on the only way on.** Static fields count camps as cleared, so a bank, shop or hop walk could end beside a
  live camp holding a 1-wide corridor and stand there (gen-archipelago-103002023: HoR with 50 gems beside a gem
  cluster for 1850 rounds, two allies queued behind it). `step_safely` now hits the weakest such member in reach
  (`breach`) when every step down the field is onto a live camp, if we outlast the fire of its group's members that
  reach us for as many turns as our basic attacks take to kill it (camps never regenerate, so a retreat and return
  still progress).
- **A crystal's altar counted open while a camp cut us off from every hop source.** `altar_access` now keeps a hop
  altar's tribute tiles open only if a source is on our live walk (camps as walls), so a plug that seals the walk to
  every altar makes the existing sealed-altar siege target it.
- **A siege that never starts.** Staging walks to tiles within reach + 2 of any live member, but counted a champion as
  staged only that near the strongest member, so a team staged beside a wolf at the edge of an elk plug never
  engaged nor started the wait limit (gen-fortress-102902207: both teams' 5 champions for ~1770 rounds, 74-0 at round
  2000). Staging now counts any live member, as the tiles do.
- **A bag only a crystal can bank, the altar locked.** `hop_route` skipped enemy-locked altars, so with the map's only
  altar locked a carrier stood still (gen-atoll-103001900: Marcella with 58 gems, 845 rounds). A locked hop altar now
  costs its lock's hits, as on foot, and the walk in breaks it.

- Against 71e3e19: 50.5% of 1104 (47.5-53.4; ladder 51.2, gen 50.0, gen-s1 50.8), out-of-fuel turns 3347 vs 3314.
  Stalls of 300+ rounds: 26 vs 35 (29.7k champion-rounds vs 40.5k); the cited games no longer stall.

## 146: a contest needs only a hold's holders, who may move between its tiles (astraeus, 2026-10-25)

`contesting()` held every ally on a cleared group's tiles while an enemy stood on another, anchored to its tile, so
with both teams on a shared group nothing ever paid and only a fight could end it, which the anchor ruled out
(gen-shared-gems-102901602: all 5 champions from r165 to r2000, 0-0). Allies already on the tiles that make
`holders(G)` (lower ids, if we stand on one) now man the contest (`contest_manned`): `contesting`, `contest_capture`
and kite's choice skip it, and the rest farm and fight. A contester's strike search may walk or dash to any of the
group's tiles (`Intent::hold`), so the two sides can fight for them; only while contested (on every hold, the
standard class read 47.2%).

- Against 71e3e19: 49.8% of 1104 (46.9-52.8; ladder 48.8, gen 49.8, gen-s1 50.0), out-of-fuel turns 3576 vs 3441.
  shared-gems maps no longer reach round 2000 (8 games; 50% before).
- With 145, against 71e3e19: 50.1% of 1104 (47.1-53.0; ladder 50.0, gen 49.6, gen-s1 50.6); against v44 56.8%
  (baseline 56.3%).

## 147: farm hops into crystal-only regions (astraeus, 2026-10-25)

Farm skipped any group no walk reaches, so walkers never left their region: on gen-atoll-103001919 a single-hole line
cut our spawn side (with its own altar) off the centre, and Prism and Marcella collected 0 gems all game. Once the
warm-up has run, `StaticMap::hops()` also holds a hop per walk region with a farmed group that is off our walk, within
crystal range of it and not the enemy's walk region (they come and go there, and no walk takes us out):
`group_hop(g)`.
- Farm prices such a group by the walk to a source, the channel, the walk from the landing (`from_landings`) and a
  recall out when the region has no altar; from our spawn when a crystal must be bought (its 10 gold off the value);
  with no crystal and under 10 gold it is no option. In a pocket, any other group costs a recall first.
- Travel reuses `take_hop` and `buy_crystal`. A farm hop lands only out of the strike of every visible enemy that could
  close in during the channel, else that hop is set aside for 16 rounds. `continue_recall` keeps the turn-end recall
  out of a pocket unless our farm choice or bank is in it.
- Home-ground weight measures a group off our walk from both spawns as the crow flies (it counted in full at the
  enemy's door).
- Against 71e3e19 alone: 51.3% of 1104 (48.3-54.2; ladder 48.8, gen 50.8, gen-s1 52.1), out-of-fuel turns 3554 vs
  3309; teleport-access maps 54.4% (68), dash 62.5% (64). On the non-walk maps, 1582 captures of groups no walk
  reaches vs 580.

145-147 together (as shipped), against 71e3e19: 50.7% of 1104 (47.8-53.7; ladder 46.2, gen 49.2, gen-s1 52.9),
out-of-fuel turns 3630 vs 3572; teleport 55.9%, dash 62.5%. Fresh suite seed 61025: 50.0% of 512 (teleport 58.3% of 36,
dash 65.0% of 40, walk 47.9% of 436). Against v44: 58.2% of 1104 (55.2-61.0; ladder 53.8, gen 58.8, gen-s1 58.2),
from 56.3% (ladder 53.8); teleport 64.7% (was 50.0), dash 62.5% (60.9). The ladder maps with group hops are
01shortcut, 01big-world, 01islands and 01fracture; the other ladder flips between runs went both ways
([EXPERIMENTS.md](../EXPERIMENTS.md#edge-case-maps-2026-10-25-astraeus)).

## 148: patch 2.0.0 rules: stats, emblem values, enemy Skirmish and Collectors, engine capture timers (astraeus, 2026-10-25)

- `champion_table` takes 2.0.0's stats and the Ren (1.1) and Tavi (1.6) stun multipliers; Monster is 1.15, Treasure 0.1.
  Hyperion gets the same; hecate only the table, as it never modelled emblems.
- An enemy's Skirmish (x1.05) and Collectors (x1.01 per family) emblems, read with Home and Durability, multiply its
  `scale`, so every fight estimate counts them. Camp estimates read `scale` too, a little high for a Skirmish owner.
- A visible cleared group's `capture_state()` dates its hold: payout is at round + timer, an enemy Capture emblem's
  cap included. In a debug game against hyperion it corrected 34 of 927 readings, holds the old dating placed late
  after an unseen round.
- Not A/B'd yet.

## 149: 2.0.0 emblem infrastructure, nothing new bought yet (astraeus, 2026-10-25)

- `best_emblem` and `emblem_begun` finish a begun shard of any 2.0.0 family; buying and quotes count Greed's 25 shards
  and its 35 shards' stats. No new family is a candidate yet, so the shards bought are unchanged.
- Owned emblems now count where the bot models them: our Tribute in `tribute_turns`, our Capture in `capture_rounds`
  (an ally's on the same hold is not counted), Collectors in camp damage (`camp_dealt_with`), Prospector in capture
  shares and farm values (`CampGroup::cluster_gems` / `cluster_gold`, from the rules' cluster rewards), and an enemy's
  Tribute in interception timing. Each is read with the emblems `update_champion` already reads.
- Stale 1.x comments (Monster +10%, Treasure +20%) corrected.
