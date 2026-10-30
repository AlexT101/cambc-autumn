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
- REPLAY-ANALYSIS and REPLAY-FOLLOW-UPS (cited by 92-100) were deleted once acted on: `git show
  c6bd5030:research/hyperion/REPLAY-FOLLOW-UPS.md`, and `REPLAY-ANALYSIS.md` at the same commit.

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

## 150: draft plan v3, a bit stream that fits every map (astraeus, 2026-10-26)

- Steps to each group are Rice-coded residuals over a Chebyshev lower bound (the spawn's box; none for altars). On
  mirrored maps a group's enemy steps are a zigzag difference from its mirror group's ally steps. Spawn-tile offsets
  are one bit when they match the no-wall guess. Attack tiles are one flag bit per member; off bushes champions
  rebuild them with one shadowcast (`sight_off_bushes`, which the draft checks); flagged members add a bit per open
  bush tile in their range-3 square only. Range 1's bush tiles are those within 1, which the draft checks and
  `probe-shadowcast` shows always holds.
- The plan uses 12-219 bytes of 1004 on the 26 bench maps (median ~60). v2 truncated attack tiles on maps such as
  00lanes, which needed ~1030 bytes.
- Fuel-only: the wide bench's replays are byte-identical. Champions' first turn costs +11k on average (decode
  4-34k, the rest the attack-tile index), and play turns are flat ([EXPERIMENTS](../EXPERIMENTS.md#fuel)).

## 151: bush clusters by run labelling (astraeus, 2026-10-26)

- One union-find pass over the bush runs of the exported row-major board labels every cluster. Each cluster is then
  built from its ring of runs when first asked for. This replaces a host flood per cluster (~4k on 100×100 whatever
  the cluster's size) and the WASM edge regrow for diagonal-only links.
- Bounded: labelling covers only the words the fuel above the floor pays for at worst (32 runs a word). A cluster the
  fuel can't cover whole is built in resumable batches, and joins `bush_clusters_` only once complete.
- Fuel-only: the wide bench's replays are byte-identical. Round 1 -2.3% on average (p90 -3.6%); per champion ambush
  -57k, monolith-heavy -54k, caves -51k, huge-shared -49k; small maps up to +3k (01hooks)
  ([EXPERIMENTS](../EXPERIMENTS.md#fuel)).

## 152: grid and window sizes derived, landing ranks compared by field (astraeus, 2026-10-26)

Phase 1 of the magic-number follow-up: no play change.
- The strike search's grid size comes from its radius (`grid_cells`, replacing 21 literal 49s and the row mask
  0x7F), as do its ground-cast window (`max_centres`) and the viewer rows (`view_n`).
- `Reach::Window` owns its size (`radius`, `width`, `cells`, `at(x, y)`); safety's tables, `hi_mask`, plan.cpp's
  viewer rows and bot.cpp's support and heal views read it instead of 9, 4, 17 and 0x1FF.
- Dash landings are ranked by a `Rank` compared field by field (out of range, danger, steps) instead of ints
  packed as 1000000 / 1000 / 999. Steps are no longer capped at 999, which only matters 999+ steps from spawn.
- Comments: `cast_cost` is a tuned flat value, not worked out from the cooldown; `camp_risk` and
  `recall_health_fraction` are unrelated, though both are 0.35.

100M bench, wide set, own and test drafts, against 25d45679: identical replays 104/104, fuel level (-0.00%).

## 153: Willow's heal step charges the basics it gives up (astraeus, 2026-10-26)

`willow_independent_heal_step` stepped to heal only for a gain above 3 basic attacks, even with the reset cooling.
By the rules a ranged walk spends the attack and the heal takes the turn's one cast, so the step gives up the attack
and the ready reset's attack, each only with a camp in reach to hit, plus a possible step back's: 1 to 3 basics.

- Against 25d45679 (on CHANGES 152): 50.0% of 1164 (47.1-52.9; ladder, gen and gen-s1 each 50.0), out-of-fuel turns
  3882 vs 3889. It rarely fires: Willow is drafted only on 5-pick maps
  ([EXPERIMENTS](../EXPERIMENTS.md#magic-numbers-phase-2-rule-derived-fixes-2026-10-26-astraeus)).

## 154: the walk out of camp reach goes around walls and units (astraeus, 2026-10-26)

`camp_exit_rounds` (under `camp_trapped`, in `want_home`) searched square rings for a standable tile no awake camp
hits, so a tile behind a wall counted as one step out. It now floods the walk (`reachable_tiles` over
`Pathing::blocked`) a step at a time; a newly reached tile outside `Safety::camp_area` ends it at once, and only those
inside get the exact `camp_damage` test. A closed pocket reads as no exit. The `1.5x` escape-damage factor is unchanged.

- Against 25d45679 (on CHANGES 152): 51.2% of 1164 (48.3-54.1; ladder 50.0, gen 51.4, gen-s1 51.4), out-of-fuel turns
  3974 vs 3924 ([EXPERIMENTS](../EXPERIMENTS.md#magic-numbers-phase-2-rule-derived-fixes-2026-10-26-astraeus)).
- 153 and 154 were each A/B'd alone on CHANGES 152, not together.

## 155: draft plan v4, a 76-bit header over one 1024-byte bit stream (astraeus, 2026-10-26)

- The plan is one bit stream over all 1024 bytes. `PlanHeader` takes its first 76 bits (v3's header was 160): a
  16-bit check (a hash of the version and the map's size, group count and first ally spawn tile; 0 is no plan) in
  place of the version and map fields, `field_layers` 14, `steps` / `mirrored` / `spawn_offsets` 1 each, three 3-bit
  Rice parameters (k up to 7), `attack_groups` 8, and 13-bit offsets `distances_at` and `schedule_at` for the lazily
  read sections to come (0: absent). Sections decoded at build follow one another: the attack tiles start where the
  steps end, so `attack_start` is gone.
- `PlanReader` keeps a 57-bit window and refills it only when it runs out: a Rice value costs ~80 rather than ~100.
- Fuel-only: the wide bench's 52 replays are byte-identical against f3f47ea; round 1 -0.2% (-1.3k a champion; decode
  -0.6k on 00ambush, -2.8k on 00lanes), play turns level ([EXPERIMENTS](../EXPERIMENTS.md#fuel)).

## 156: first-turn fuel cuts (astraeus, 2026-10-26)

Six fuel-only cuts to a champion's round-1 start-up and `decide`
([first-turn.md](draft-compute/first-turn.md) has the phase-by-phase profile):
- Hole and altar crossings (`crossable`, `near_crossable`, `dash_walls`, `landing_dash_walls`) are built only for a
  champion with a dash, and the draft bot: every reader checks the dash first. -12.6k for a non-dasher.
- `Pathing::live_camps`' first build copies `camp_tiles` and flips only dead members, out of line (a set per member
  cost ~60). `live_flips_` counts from another start; it is only compared with its own snapshots.
- `StaticMap::build`'s camp-group loop keeps its sums in locals, camp designs in a fixed array, and finds the centre
  in place (same tie-break as `central_tile`).
- `altar_access` floods the live walk first and reads the static walk (`Pathing::foot`) only for tribute tiles off
  it: live camps only add walls, so the live walk lies inside the static one. Siege -7.6k on the mean.
- Camp members and camp healths are `StaticArray`s (one `static_alloc`, fixed size, copies share elements; nothing
  copies them) in place of vectors over the bump allocator, whose reserve/assign cost ~150 each.
- Wide bench, test drafts, 100M, on 155: 52/52 replays identical; round 1 mean -18.6k (-3.5%), play turns -92 (-0.2%).
  Profiled mandatory round-1 work (start-up to the end of `decide`) 244.0k -> 221.0k. At the real budget, round-1
  turns that ran out in `decide` went 59 -> 50 of 241.

## 157: the farm loop visits groups nearest last turn's choice first (astraeus, 2026-10-26)

- `pick_up`'s farm loop visits last turn's choice, then the other groups by Chebyshev distance between centres (ties
  by index), in place of index order from the choice. A loop cut short has weighed the likeliest groups, and an early
  good best sends more groups out at the cheap prune. With no choice yet, or over 256 groups, the order is as before.
- `StaticMap::nearest_groups` makes the order by counting sort (~50 fuel a group), cached per group;
  `prepare_next_turn` makes the choice's at turn end when fuel is spare. No draft data; `distances_at` stays 0.
- A/B, own drafts, against 801ed7da: 51.6% of 1164 (48.8-54.5; ladder 50.7, gen 51.8, gen-s1 51.8); out-of-fuel turns
  4718 vs 4681. 58-62% on maps of 40+ groups, level under 20; a fresh many-group suite read 49.4% of 180.
- Wide bench, test drafts, 100M: play turns mean -0.3%, p99 -1.8%; round 1 +0.8% (+4.0k a champion, the turn-end
  order).
- The drafted version (06654719, not merged) ordered by walking steps from one field per group in the draft, sent as a
  plan section: 51.4% of 1164 against 801ed7da, and 49.2% of 356 head to head against this Chebyshev order on fresh
  many-group suites. Walking distance added nothing for the farm order, so the section was dropped
  ([distances.md](draft-compute/distances.md)).

## 158: the uninformed approach search's cap doubles when it is cut off (astraeus, 2026-10-26)

- With no field bounding the walk, `search_approach` was capped at width + height layers, and `approach_steps`
  clamped known steps to it. Two maps walk farther (gen-s1/gen-gem-centre-120205105, 221 layers; gen/gen-dense-camps-120105502,
  210): the search failed every turn at ~31k, the champion stood in a crow-flies local minimum all game and the
  centre-field warm-up never finished.
- `Pathing::walk_cap()` starts at width + height and doubles, up to width x height, when an uninformed search is cut
  off at the cap; one that runs dry (unreachable) leaves it. It persists for the game. `approach_steps`' clamp,
  `approach_cost` and `prepare_approach`'s estimate use it. No fuel read added; maps whose walks fit width + height
  are unchanged.
- A/B, own drafts, against 3b2677b: 50.3% of 1164 (47.5-53.2; ladder 48.6, gen 50.8, gen-s1 50.4); out-of-fuel turns
  4606 vs 4566. A 96-game winding-map suite: 50.0%; crow-flies-farm lines 22,780 -> 8,263, stalled champion-games
  17 -> 8 (the rest are 87-94 tile serpentines whose grown cap's estimate never fits a turn).
- DRAFT-COMPUTE #3, maze portals, was not built: only 1 of 582 maps has a full field over ~40k
  ([portals.md](draft-compute/portals.md)).

## 159: a ward plan in the draft, plan v5 (astraeus, 2026-10-26)

- The draft picks one ward tile per work site (each camp group, then each altar) from the tiles within placement range
  (2) of its camp tiles or tribute tiles, never a wall, hole, altar or their spawn. Each candidate is one radius-6
  shadow cast (from a bush, its own cluster transparent), scored by enemy-standable tiles a champion at the site's
  centre cannot see: twice within 4 of the stand tiles, once within 8. Ties go nearest the centre; score 0 is none.
- `place_ward` places the planned tile for our work (claimed group, else waited-at altar) once within 2, keeps it while
  that work lasts, skips a tile with a visible allied ward, and otherwise falls back to the greedy bush ward.
- Plan v5: the header stays 76 bits, with `distances_at` (always 0 since CHANGES 157) renamed `wards_at`. The section
  follows the attack tiles: a 4-bit code width w, then w bits a site, 0 for none, else 1 + the tile's row-major index
  in the site's box (the camp tiles' bounding box, or the altar's 3x3, widened by 2 and clipped to the map). Codes
  that do not fit are cut and read as none; the writer round-trips the codes. Only sites that fit are searched, each
  after its bush clusters are grown under the draft's fuel floor ([wards.md](draft-compute/wards.md)).
- A/B, own drafts, against 80db5f7: 52.1% of 1164 (49.2-54.9; ladder 50.7, gen 53.7, gen-s1 50.8); an unused suite
  (seed 61026) 52.5% of 512. Out-of-fuel turns 4658 vs 4637, but 2090 vs 1952 (+7%) on the unused suite, untraced.
- In those games: wards a champion a game 18.0 -> 28.2 (27% off bushes); champions never warding 18% -> 2%;
  surprise deaths 0.109 -> 0.082 a champion a game.
- Fuel: draft round 0 median 0.56M -> 1.38M, peaking at ~5.0M of 10M on the many-group maps; no random drafts. With
  the search forced into the 100k draft turns, every turn still picked with 35k or more left. Champions' round 1
  +0.5k (the first lookup). The merge's header and draft changes left the wide bench's 52 replays byte-identical.

## 160: first-turn fuel cuts, pass 2, and three plan facts, plan v6 (astraeus, 2026-10-26)

Five fuel-only cuts to a champion's round 1 ([first-turn.md](draft-compute/first-turn.md), Pass 2). The header grows
76 -> 79 bits, so `current_version` is 6:
- `tributes_walked` (1 bit): every tribute tile is off the camp tiles and walkable from our first spawn tile with all
  camps standing. Live camps are a subset of the camp tiles, and a dash's walls a subset of walking's, so every
  tribute tile is on `altar_access`'s live walk; its first build skips the flood. The walk is flooded when a camp
  change needs it or from spare fuel in `prepare_next_turn`. True on 222 of 241 bench instances.
- `dash_spawn_steps`, `dash_altar_steps` (1 bit each): a field on `dash_walls` from each ally spawn tile, and from the
  tribute tiles, gives every group the drafted walking steps. Landing-dash walls lie between, so they agree too.
  Dashers then read the drafted steps in the farm loop and `centre_to_altar` in place of their own fields.
- Drafted attack tiles are indexed only up to the group asked for, resuming from there.
- The enemy steps are decoded on first ask (`enemy_steps`). The build skips their codes, at Rice parameter 0 by
  counting zero bits. `get_rice` is inlined into the decode loops.
- `Pathing::live_camps`' first build skips camp beliefs still at version 0 (every member alive, as drawn).
- Wide bench, test drafts, 100M, against df3b03e: 52/52 replays identical. Round 1 mean 523.6k -> 516.8k (-1.3%,
  p90 -2.2%); play turns 49,200 -> 49,184 (total -0.04%). Profiled mandatory round-1 work 212.0k -> 193.4k (draft
  decode 11.8k -> 8.3k, `altar_access` 18.2k -> 8.5k). At the real budget, round-1 turns that ran out fell from 48 to
  28 of 241, and round-1 decides that finished rose from 194 to 215.

## 161: first-turn fuel cuts, pass 3 (astraeus, 2026-10-26)

Four fuel-only cuts to a champion's round 1 ([first-turn.md](draft-compute/first-turn.md), Pass 3):
- Camp members (`StaticMap::build`), and camp healths and their rounds (`init_beliefs`), each come from one
  `StaticArray` allocation, every group taking a slice. Nothing resizes them, and copies share the elements as before.
- Allies' beliefs get no `possible`/`undashed` storage: every read of those boards is of an enemy (loops over
  `World::enemies`, Safety's foes, World's tracking behind an enemy check or `tracked`). They take storage-less boards
  from `no_board()`. A copy of such a board would fault, so `ChampionBelief`'s copy operations are deleted.
- `ally_engaged` builds a group's threat board only when a visible ally is within `CampGroup::threat_radius()` of its
  centre (each member's distance from the centre plus its reach; by the triangle inequality no threat tile is farther).
- `init_beliefs` writes the first ranks as each champion's index instead of calling `rank_turns`: with every
  priority 0 and each order by index, the insertion sort moves nothing.
- Wide bench, test drafts, 100M, against `astraeus-m160`: 52/52 replays identical. Round 1 mean 516.8k -> 513.8k
  (-0.6%, p90 -0.4%); play turns 49,184 -> 49,169 (total -0.04%). Profiled mandatory round-1 work 193.4k -> 188.5k
  (champion beliefs 10.3k -> 6.8k). At the real budget, round-1 turns that ran out fell from 28 to 21 of 241, and
  round-1 decides that finished rose from 215 to 222.

## 162: comms post the most urgent sighting and can replace a less urgent one (astraeus, 2026-10-26)

`comms.cpp` only; CHANGES 141's layout is untouched ([ward-sight.md](draft-compute/ward-sight.md)).
- Urgency of an enemy in sight: the distance to the nearest other live ally that may not see it, less the rounds since
  we last saw that ally, capped at `Strike::max_reach + 1`. An ally we see within 8 sees an enemy in the open (walls
  ignored), one in a bush only from inside its cluster (grown on demand). Past the cap the old order holds: bush
  first, then the rotation.
- `send()` posts the most urgent first. A teammate's sighting from this round (either slot, never a capture) is
  replaced only by a strictly more urgent one of another enemy: the teammates between it and us have read it.
- `receive()` works the urgencies out at the turn start (send at the turn end had ~1.5k to spare and ran out); allies
  are listed only when an urgency is needed, so the first turn does no extra work. No shadow cast, no fuel read.
- A/B, own drafts, against `astraeus-m160`: 49.4% of 1164 (46.5-52.3; ladder 47.1, gen 49.0, gen-s1 50.4); out-of-fuel
  turns 4558 vs 5716. Victims who knew their killer at their last turn 36% -> 41%, within noise. Kept as level.
- Why small: ward sight already reaches every decision; the gap was which enemy comms posts (in 113 of 173 teammate
  turns that saw a later killer both slots were taken). The ceiling is ~2% of deaths.
- Merged onto CHANGES 161 (`bots/variants/astraeus-wardcomms4` is the A/B'd code): wide bench, test drafts, 100M, 52/52
  replays identical to it; round 1 mean 516.9k -> 513.9k (161's cuts), play turns -0.1%.

## 163: round 1's farm loop takes the draft's leads first, with exact rated prunes; plan v7 (astraeus, 2026-10-26)

Fuel only ([round1-farm.md](draft-compute/round1-farm.md)).
- Prunes valid in any visiting order. A group's value is `rate(worth, cycle)`, which falls as the cycle grows, and no
  clear is quicker than the fastest (`fastest_clear`: alone, kiting and with a partner, `min_camp_damage` rounds up
  and `output` is at least basic plus spells). So `rate(gems + gold, trip + capture + fastest)` from the Chebyshev
  distance bounds it; a clear shared with the unclaimed partner is bounded by `rate(worth x part, trip + capture +
  fastest x part)`. A 1e-4 slack covers float rounding. The prunes skip only groups strictly below the best so far,
  never claimed groups, last turn's choice or a group we may help. Not for Ren (reflection clears faster) or in a
  pocket (a recall out beats the distance). Every turn, the bound applies before the steps when no centre field gives
  them; a crystal hop's steps can be under the distance, but group hops exist only once every centre field does.
- First turn only (`farm_turn<true>`; the caches it shares with later turns are in `FarmMemo`): the bound before the
  group's facts and after its steps, and `beyond_spare`, which skips a live group no spell kites whose attackers
  each strike until their own kill (alone and with the partner) for more than we spare, with no ally on its threat
  tiles. Such a group could only be risky, and a best exists.
- Leads: the draft guesses each body's two likeliest first choices. On the first turn farm visits them first, then
  the usual order. Ties go to the group earlier in the usual order (`earlier`, for best, risky, shared and help), so
  the choice is the usual one.
- Plan v7, 80-bit header: `schedule_at` is now `leads_at`, plus a `dash_steps` flag. After the attack tiles come the
  leads (6 bodies x 2 x `bit_width(groups)` bits, rewritten at every draft write), then per body a dasher's steps from
  its spawn tile (2-bit kind, 4-bit tile, 3-bit Rice parameter, 13-bit length, a Rice code per group), then the wards.
  The dash steps replace a field from the spawn tile on maps with crossable tiles.
- Merge review fixes: leads and dash steps are placed only if the whole ward section still fits after them (a ward
  site cut from the plan changes play); no leads past 256 groups (the order is bytes, as `nearest_groups`'s).
- Wide bench, test drafts, 100M, against `astraeus-merge162` (CHANGES 162): 52/52 replays identical; round 1 mean
  513.9k -> 500.2k (-2.7%, p50 -4.6%); play turns +0.01%. On 12 unbenched gen-s1 maps (most groups, most holes,
  dash and crystal gems; 24 games): 24/24 identical, round 1 -1.5% (p50 -4.6%), play turns level. A stress copy
  that visits every group in reverse order on round 1: 52/52 identical. Profiled on ca1139bd: mandatory round-1
  work 188.5k -> 173.6k, farm loop 46.2k -> 28.1k; at the real budget, round-1 run-outs in `decide` 21 -> 18 of 241.
- Draft: round 0 +117k mean (max 3.23M of 10M); later draft turns 1.7k -> 7.0k (max 9.0k with own drafts). Remaking
  every lead on every later turn (forced, gen-dense-camps-120105502, 98 groups) still picked with 52k left: type facts
  cost 300-420 a group and ranking 140-250, inside the 600 and 400 that their fuel checks budget.

## 164: the enemy spawn field is the ally field mirrored (astraeus, 2026-10-26)

Fuel only.
- `blocked_for_us` and `blocked_for_them` are mirror images (terrain, altars and spawns are symmetric, and each blocks
  the other side's spawn), so the steps from the enemy spawn to p are our spawn field's at `StaticMap::mirror(p)`
  (moved from draft.cpp). `enemy_spawn_steps(p)` replaces the second flood in the draft's field 1, `enemy_steps`
  without a plan, and `own_ground`; `warm_up` no longer builds it.
- Wide bench, test drafts, 100M, against 93d16695: 52/52 replays identical. Round 1 mean 500.2k -> 493.3k (-1.4%,
  p50 -1.2%, p90 -1.9%); draft turns -0.3%. Play turns after round 1 49,427 -> 49,458 (+0.06%, over 100k 3662 ->
  3693), not from `mirror`'s switch (a branch-free mirror changed nothing); likely codegen. Total over the games
  +0.05%.

## 165: farm weighs groups by home_ground from the first turn (astraeus, 2026-10-26)

Groups weighed 1 until the warm-up's centre fields were ready, which finishes on spare fuel (19-54 rounds on
100x100), so early camp choice depended on fuel and the 100M bench played a different opening from a real game.
`home_ground` reads only the drafted spawn steps, so it is now used from the first turn (FUEL-GATES).
- Against 93d16695, own drafts: 50.4% of 1164 (47.6-53.3; ladder 45.7 of 140, gen 50.4, gen-s1 51.8), out-of-fuel
  turns 4539 vs 4468. Level; kept as the logical rule.

## 166: readers of the warm-up's caches make what they need (astraeus, 2026-10-26)

The end-of-turn warm-up (centre, spawn and altar fields, group hops, bush clusters) ran on spare fuel, and readers
took a different path while its caches were cold, so play depended on how much fuel earlier turns had left
(FUEL-GATES rule 3). Each reader now makes what it needs, or reads a source that agrees with the cache:
- `note_upkeep` counts spawn steps from the second turn (on spawn 0, else the spawn field on demand);
  `kite_productive_action` no longer waits for the spawn field.
- Farm's heal trip reads `Pathing::centre_to_spawn` (centre field, the drafted spawn steps, else a field from the
  spawn's centre) in place of the Chebyshev distance when no centre field was warm; the first turn keeps Chebyshev.
- `approach_steps` makes the group's centre field (or the spawn field) when missing, so an approach search's cap no
  longer depends on the warm-up; estimates read only what is there. A farm walk whose search found no way descends
  the centre field, made if missing (one skipped for fuel goes crow-flies as before). Farm drops `centres_ready()`
  from its memo and context: its step sources already agree with the centre fields.
- Group hops are made on first ask, from the second turn. With the draft's steps only a group no spawn walks to can
  have one, so most maps need no flood, and the enemy's flood is skipped. Farm's Chebyshev prunes skip groups with a
  hop and pockets, whose steps can be shorter.
- The turn-start ward grows the bush clusters it needs from the second turn, and `ward_bushes` grows our ward's
  cluster: the warm-up's `find_all_bush_clusters` decided these before (the largest dependence).

Identical at 100M, where the warm-up finished in round 1, but at the real budget early turns now build the real
values instead of taking cold paths, so real-budget play changes. No real-budget A/B has been run yet.
- Wide bench, test drafts, 100M, against main f9d2e26b: 52/52 identical; play turns +0.1% (p99 +0.2%), round 1 -1.8%
  (group hops left out of the first turn's warm-up).
- Warm-off check (a copy skipping `prepare_next_turn`, `warm_reach`, the warm-up and the table queue): 2/52 identical
  before, 52/52 after. Without them play turns are -6.6% (p99 +4.0%: cold turns build fields), round 1 -63%.

## 167: one end-of-turn queue for every spare-fuel cache (astraeus, 2026-10-26)

`TurnEndQueue` (main.cpp, was CHANGES 109's `TableQueue`) runs all spare-fuel work in one order under its spent-fuel
bound: the fight tables around visible enemies, next turn's walk (`prepare_next_turn`), the map warm-up (spawn
field, group hops), the tables around us, then centre, altar and hop fields, attack tiles and bush clusters. Above
the real budget its floor rises by the excess, so it fills the same at 100M as at 100k. `warm_reach` is gone (a
subset of the tables around enemies). The walk to the farm choice is searched at the turn's start without
`walk_first_floor` (deleted); the queue has usually made it. `prepare_approach`'s gate counts a centre field it would
make (166's prepare made one past its gate and ran out 55 times).
- Wide bench, test drafts, 100M, against main 5027ec61: 52/52 identical. Round 1 is now bounded like a real turn
  (mean 490.6k -> 203.1k); play turns +0.8%, the warm-up spread over turns. Queue off vs on: 52/52 identical.
- Against 5027ec61, own drafts: 50.1% of 1164 (47.2-53.0; ladder 53.6, gen 49.6, gen-s1 49.6), out-of-fuel turns
  4776 vs 4810.

## 168: CHANGES 166's second-turn fuel spikes (astraeus, 2026-10-26)

166 made at the start of rounds 2-3 what the warm-up used to make on spare fuel: the spawn field (~31k on
01big-world), every group hop (50-78k on 01big-world, 124-156k on 01islands) and the turn-start ward's bush clusters
(35-95k for a giant cluster on gen-city). Against f9d2e26b its out-of-fuel turns in rounds 2-10 were 793 vs 278.
- Upkeep's spawn steps are folded in, in turn order, only when a reader multiplies their mean by damage taken
  (`upkeep_cost` with damage on record, `heal_rounds` when hurt). Exact: wide bench 52/52 identical.
- Group hops on a timetable: our walk on the second turn, then one more tried group a turn, in group order. The
  warm-up may make them sooner, but they are read only on schedule. `bankable_bag` checks for an altar's hop rather
  than any hop.
- The turn-start ward is only the draft's planned one; bush wards wait for the turn end, which grows clusters within
  its fuel check (our ward's cluster included). A copy growing them at the turn start: 49.7% of 1164 against this
  (ladder 55.7), out-of-fuel turns 4958 vs 4671.
- Wide bench, 100M: 14/52 identical to 167 (the start ward); warm-off copy 52/52 identical.
- 167-168 against 5027ec61 (166): 48.5% of 1164 (45.7-51.4; ladder 45.0, gen 48.0, gen-s1 50.0), out-of-fuel turns
  4816 vs 4905; in rounds 2-10 502 vs 795.
- 166-168 against f9d2e26b (before 166): 49.3% of 1164 (46.4-52.2; ladder 48.6, gen 50.6, gen-s1 48.2), out-of-fuel
  turns 4807 vs 4368 (+10%): rounds 2-10 513 vs 281, rounds 61+ 3241 vs 3076. Level; kept by the keep rule. The
  remaining early cost is the cold reads now made in the turn (centre fields for a new walk, the ward's growth at the
  turn end), which the queue fills only from spare fuel.

## 169: the end-of-turn queue builds centre fields before the tables around us (astraeus, 2026-10-26)

167's queue filled the tables within 8 of us (20 while dead) before the centre fields, and a walk exposes a new edge
every step, so the ring rarely completed: centre fields waited (first "WARM centres" median round 41, 1% by round 10;
4 and 74% before 167) and decisions built them (~26k each on 100x100). The queue now runs, after the fight tables
around visible enemies, next turn's walk and the map warm-up: centre fields, `Pathing::warm_up` and bush clusters
(the old warm-up's order), and only then the ring around us. No small ring around us before the centres: a step
exposes 5-9 new tiles at radius 2, comparable to a centre field.
- Wide bench, test drafts, 100M, against main 2fc174c5: 52/52 identical; play turns -0.7% (p99 -0.7%, over 100k
  3844 -> 3670), round 1 -0.3%.
- Against 2fc174c5, own drafts: 51.5% of 1164 (48.6-54.3; ladder 52.1, gen 51.6, gen-s1 51.2), out-of-fuel turns
  4688 vs 4698. First "WARM centres" median round 6 vs 41 (66% vs 1% by round 10), yet out-of-fuel turns in rounds
  2-10 are 507 vs 505: cold centre fields were not what ran those turns out.

## 170: first-turn fuel cuts, pass 5 (astraeus, 2026-10-26)

Seven fuel-only cuts, mostly to a champion's round 1 ([first-turn.md](draft-compute/first-turn.md), Pass 5):
- Round 1's `ally_engaged` checks go through the bounding box of the allies it reads first: a group whose centre is
  at least `members.size() + reach` from the box can't reach any of them (`threat_radius()` is at most that).
- Round 1's pre-facts rated bound hoists its turn constants and tests each `rate` alone (rounding is monotone, so
  `fl(max(b1, b2) c) < best` is both products below `best`).
- `home_ground` reads only the asked group's mirrored enemy steps on the first turn; the turn-end queue decodes every
  group first thing on round 1 (eager on play turns: lazy reads there cost round 2 +3.6k).
- `operator new` takes 16-aligned blocks from a 2 MiB static arena that is never freed, then malloc/aligned_alloc as
  before. Round 1 made ~300 allocations (every bitboard is an aligned new) at ~130 each plus frees. Nothing orders or
  hashes by address. The arena fills by rounds 100-500; a 100x100 game peaked at 4.6 MiB against 3.3 MiB (local cap
  256 MiB). Arena blocks start zeroed where recycled malloc blocks don't; an audit found no heap read before a full
  write (every `cambc::uninitialized` board is first written whole or read only behind a flag), assuming host ops
  write an `out` board's padding words too.
- `ward_bushes` tests `any_within(bushes, here, ward_range())` until the turn-end queue builds `near_bushes`, which it
  now does at the queue's start (built in the warm-up, rounds 2-5 paid +90-170 a turn).
- The attack-tile index counts each member's bush square with fixed masks (`count_in_small_square<R>`, R <= 4).
- The turn order skips escape threats when no enemy can be in strike reach (`out_of_reach`: Safety unbuilt, no enemy
  in sight, not a healer, no tracked `possible` board within `Strike::max_reach`).
- Wide bench, test drafts, 100M, against main 9ab21632: 52/52 replays identical; round 1 mean 202.1k -> 194.0k (p90
  -11%), play turns 50,002 -> 49,923 (total -0.17%). 24/24 identical on 12 gen-s1 maps. Profiled mandatory round-1
  work 184.8k -> 160.7k (over 200k 82 -> 40 of 241; arena -12.8k). At the real budget, round-1 turns that ran out
  16 -> 2 of 241; out-of-fuel turns overall 690 vs 702 (games diverge).

## 171: a carrier's retreat from an altar is retreat() (astraeus, 2026-10-26)

`carry_bag`, hit at an altar with nothing in reach to hit back, ran its own retreat: a dash and a `retreat_step`. It
predated `flee_camps` (aca2bd51), so it walked along an awake camp's reach, read no Heart of Ruin landing stun, and
took no safe kill on the way out. Carriers sent home by `want_home` already took `retreat()`; this one now does too
(the guard `guard_steps` placed is cleared first). It gains `flee_camps`, `step_to_kill` (only where nothing but the
victim reaches us), `cast_at_enemies` priced against the escape step, the tribute re-check after a kill, and the hits
after the step.
- Against 1cdca488, own drafts: 50.1% of 1164 (47.2-53.0; ladder 50.0, gen 50.2, gen-s1 50.0), out-of-fuel turns
  4202 vs 4156. It is rare: 11 of 326 maps' two games end on different rounds (the rest are mirror-identical); 10 of
  the 11 still go one game each, gen-hedges-120102905 went to it from both sides.

## 172: crystal hops judge the channel's start and landing; a refused bank hop waits (astraeus, 2026-10-26)

A crystal's channel cannot be cancelled by us (3 turn ends that damage does not stop; a death there hands over the
bag). Bank hops checked nothing; farm hops checked only the landing.
- `take_hop` starts a hop only where a tribute of as many turns could start (`tribute_safe`), and lands every hop,
  not only a farm hop, out of the strike of each visible enemy that could close in during the channel. A bag's last
  chance (`any_risk` over the rounds to its tribute) skips both. A source with no free landing is a refusal too.
- A refused bank hop waits on its source as `carry_bag` waits at a watched altar, with the same memory (`wait_altar`,
  decision `W`): as many rounds as the next way to an altar takes (a walk, or another altar's hop), then that way,
  the hop's altar avoided meanwhile (`hop_route` already skips `avoid_altar`). With no other way it waits; the
  turn-end recall may take the bag home (`recall_to_bank`). Farm hops keep their 16-round set-aside.
- `bank_gems` stopped avoiding an altar whenever no other was walkable, though its comment said "and no hop leads
  elsewhere": it now keeps avoiding it while a carried crystal's hop leads to another.
- Against 1cdca488, own drafts: 50.1% of 1164 (47.2-53.0; ladder 50.0, gen 50.0, gen-s1 50.2), out-of-fuel turns
  4164 vs 4167. 7 of 326 maps' games differ, all crystal maps (five atolls, gen-vaults-120201706,
  mut-pilgrimage-120201804); 6 still go one game each, gen-vaults went to it from both sides.

## 173: a clear's camp fire counts only the strikers that reach where we stand (astraeus, 2026-10-26)

`min_camp_damage` priced a clear as if every living member hit us every round until it died. Now, while we kill a
member, only the strikers still alive that reach its stand tile hit us: `range` from it on the side away from the
group's middle (its bounding box), inside the map, walls ignored. A wolf line's end is hit with only that wolf in
reach; adjacent elks and golems all still reach (an elk's 4 covers range 3 plus a tile). The order stays deadliest
first, ties to the least fire with every member alive, so a line's ends go before its middle. With every striker
reaching, the price is the old one exactly.
- `stand_reach`, per group and range (melee, ranged), built once: per member, the strikers (bits, the first 32) that
  reach its stand tile. A reprice sums the living bits' strength. The struggling-ally check prices at the ally's range.
- Against 00a638e, own drafts: 50.5% of 1164 (47.6-53.4; ladder 53.6, gen 50.0, gen-s1 50.2), out-of-fuel turns
  4413 vs 4173; fresh suite 41026: 50.4% of 512 (46.1-54.7), 2022 vs 1877. A first version walking every member pair
  read 51.3% with +34% out-of-fuel turns (gen-huge-shared maps, 02the-pack); at 100M the table version plays
  identically to it (three maps). Real budget on its 8 worst maps: 393 out-of-fuel play turns, main 368, it 1373.
- Standing by the same reach lost and is not in (EXPERIMENTS, "Camp fire by reach").

## 174: the turn-end queue finds ward_bushes' clusters around us first (astraeus, 2026-10-26)

`ward_bushes` gave up (`ward-no-bushes-clusters`) mostly in rounds 2-10, before the warm-up had labelled the bush
clusters. The queue now finds the clusters within ward range + 1 of us, and our ward's if it is on a bush, before
`prepare_next_turn` and the map-wide fills, until the warm-up is done (every turn after it: +750 a turn).
- Wide bench, test drafts, 100M: 52/52 identical, +20 a turn. Real budget: the gate 137 -> 116 (rounds 2-10 111 ->
  102). The rest is `grow_cluster`'s run labelling, which takes a batch only with 2 word costs (~16k) above its
  floor, rarely left early; a smaller batch needs a minimum step (one word can make no progress).

## 175: the farm loop stops once no group left in the nearest order can beat the best (astraeus, 2026-10-26)

In `nearest_groups(first)` order (last turn's choice first, then by Chebyshev distance from its centre), every group
from position k on is at least r_k - D from here (D: ours to first's centre). A table per `first` (O(n), on first
use) holds r_k and suffix maxima of gems and gold (and with Prospector extras). Position k is beyond once the most
any remaining group holds, at r_k - D plus the capture rounds and cleared at once, rates below the best (slack
1.0001), and r_k - D exceeds `help_radius`. Beyond is monotone along the order, so the first such position is binary
searched, again only when the best rises; from there only claimed groups (a crew share's cycle has no capture) and
groups with a possible crystal hop (`StaticMap::may_hop`) are weighed. Not in the opening (drafted lead order), while
banking a bag (the trip subtracts `bank_now`), or in a pocket.
- Exact: weight <= 1 off our last choice (position 0), no toll off hops, trip >= steps >= Chebyshev with no bag to
  bank, `rate` falls with rounds, ties need `earlier()` (opening only).
- Wide bench, test drafts, 100M: 52/52 identical, mean +0.34% (a fixed cost a farm call: table and searches; p99
  107519 -> 107832). Heavy set (8 maps of 28-100 groups, 16 games): 16/16 identical, mean -1.54%, turns over 100k
  9137 -> 8691 (dense-camps -3.9k a turn). Real budget, heavy: out-of-fuel play turns 1579 -> 365 (dense-camps 1313
  -> 81), `farm-partial-evaluation` 25682 -> 20242. Enabling it only from 24 groups changed nothing worth keeping.
- Left: banking turns (~40% of loops on dense-camps), whose trip is bounded by here-group-altar, not a ring.

## 176: step-guard and prey-cut-short narrowed (astraeus, 2026-10-26; reverted but for the step-guard tags)

Reverted after the full A/B (EXPERIMENTS, "Gate firings and CHANGES 174-177"): out-of-fuel turns +16% with it,
-4.5% without; only the tags `step-guard-entry`, `-sim`, `-look` stay.

`step_guard` kept the costliest placing lately in a static that decayed only on calls that placed or had no foe in
reach: once a placing cost tens of thousands, the entry gate (fights' estimate + `act_reserve` + it) fired on every
later call and the estimate never came down, so the guard stayed off for the rest of an engagement.
- Gates tagged apart: `step-guard-bound`, `-entry`, `-sim`, `-look`. Every gated return decays the estimate (the
  sim and look gates record the partial placing).
- The entry gate moved after the bounding pass: with no tile worse than ours the result is null anyway. The pass
  itself (threats, a lost foe's Reach, ~200 a tile) has its own smaller gate, and the estimate now measures only the
  fights and exact looks after it.
- `prey`: `fight_key` and `late` get a floor of their own (`prey-key`, the query estimate + reserve), and a candidate
  whose fight is already lost is skipped before the margin is checked. Gating only new simulations (memo hits free)
  raised out-of-fuel turns on the wide bench 985 -> 1368, all on the two gen-chambers maps, with either half alone
  ~770-800 against 688: a memoised win starts a chase ~10k lower. So every other candidate keeps the old margin.
- Wide bench, test drafts, 100M: 52/52 identical. Real budget against 9beb148: step-guard 4126 -> 2415 on wide
  (entry 1634, bound 445, look 315, sim 21), 2310 -> 1099 on the heavy set; prey (cut-short + key) 3628 -> 3357, 2044
  -> 1506; out-of-fuel play turns 985 -> 953, 1579 -> 1623.

## 177: the turn-end observe needs only the end reserve (astraeus, 2026-10-26)

`comms-stale-vision` re-read vision after a move only with `observe_cost_estimate()` (1000 a champion) plus
`end_reserve` (10k) left. Measured (100M, wide bench): observe + send mean 1.9k, p99 3.8k, max 6.3k, so the reserve
alone covers it; the estimate is gone. A fuel check only: identical at 100M.

## 178: play-identical cleanups and a stale tail out of the farm loop (astraeus, 2026-10-27)

- The support pair by role: the healer is `facts().heals()`, the protected mate `passive == gem_focus` (comms
  endpoints, mailbox indices `healer`/`protected_mate`); `support_turns` for the formation's 4. The draft's
  `DraftCounter` table (a placeholder that never matched) is gone. Rule literals named: the SDK's
  `camp_group_capture_type`, local enums for the camp and group state codes, `grid_r`, `dash_range`, `ability_range`,
  `ground_radius`, `max_camp_range` (with a debug check against the map's), and a `static_assert` that
  `Strike::max_reach` is one past the longest one-turn reach in the champion table.
- The farm loop reads fuel once a pass; fuel above the last read means the engine resumed a stale turn, and it throws
  `StaleTurn` instead of weighing groups on the next round's budget. The turn-end queue warms centre fields in
  `nearest_groups(farm_group)` order, so the groups the farm loop weighs before its stop get theirs first.
- Wide bench, test drafts, 100M: 52/52 identical (heavy set 16/16 for each part), +0.1%; over-100k turns on the
  heavy set 8946 -> 8533. A/B w1-fuel-13 50.3% of 1164 (47.4-53.1), out-of-fuel turns 4523 vs 4531 (rounds 1-10 825
  vs 837). The rest of the fuel plan lost or was level (EXPERIMENTS, "Phase 1").

## 179: Durability and camp phases by the rules in the threat model (astraeus, 2026-10-27)

- Durability: `worst_damage`, `damage_bound`, `damage_ceiling` and `bound` take a `blow_scale` on champion blows
  only, our `taken` from the self callers (`lethal`, `flee_camps`, `retreat_step`, `recovered_for_work`,
  `exposure_at`, the shield value), never for an ally's tile. `may_escape`/`offer_escape` scale the blow sum by our
  taken, `pack_boxes` divides health by taken on both sides, unseen hits are raw x the target's taken, and Ren's
  retaliation is scaled by ours.
- Camp phases: `camp_trapped`'s exit costs dps x r (the coming phase if we stay, then r - 1 on the walk out; was
  1.5r + 1); the fight sim's camp hits land on us, not our weakest (`play_shielded` hands camp turns to act()); the
  strike-search wake counts reach - d + 1 hits (the Monolith ban stays); `breach` takes Heart of Ruin's scale.
- A/B w2-dur 50.4% of 1164 (47.6-53.3), out-of-fuel turns 4720 vs 4673; with camp phases w2-camp 49.7% (46.9-52.6),
  4802 vs 4630.

## 180: allies in the fight sim join once a walk brings an enemy within their strike (astraeus, 2026-10-27)

`new_fight`, `stand` and `chase_trade` let every ally within 4 hit from turn 0; enemies already waited for their
approach. Each ally (not us) now arrives after the Chebyshev walk until its strike reaches the nearest enemy of the
fight, 0 if any enemy is unseen. Positions only, so the fight memo stays valid. Fires ~40 times a game.
- A/B w2-arrive (on 179) 50.3% of 1164 (47.4-53.1), out-of-fuel turns 5106 vs 4562: +8% over w2-camp, as delayed
  allies leave the plain fast path.
- A one-turn walk joins at once (only walks of 2+ turns delay), keeping more sims plain: merged A/B p1-narrow 50.7%
  (47.8-53.6) against p1-merged's 51.0%, out-of-fuel turns x1.103 against x1.116 of the REF's.

## 181: camp estimates count Monster and Collectors, not Skirmish (astraeus, 2026-10-27)

Farm and clear estimates used `output()`, raw x `damage_scale()`: Heart of Ruin's passive and the champion-damage
emblems (Skirmish, Collectors), never Monster's camp bonus, though Prism opens Monster-Focus in most games and
Vendetta buys Monster. `camp_output`/`camp_scale` = raw x HoR's scale x `camp_dealt` (Monster, plus Collectors per
family), allies' `camp_dealt` read in the same `emblems()` call. Used for the farm's strength, spell and basic
outputs, `struggling`, crew and partner outputs, `finishing_camp`, `team_power`, `recovered_for_work`, kite and the
siege's staged sum.
- `ally_scores_` backfills skipped rounds with the previous score, not the current one.
- A/B w3-monster 50.1% of 1164 (47.2-53.0; ladder 49.3, gen 48.4, gen-s1 52.0), out-of-fuel turns 5012 vs 4889; with
  the backfill w3-b6 49.2% (46.4-52.1), 4990 vs 4869. Skipping an enemy hold that pays before we arrive lost
  (EXPERIMENTS, "Phase 1").

## 182: capture state with any camp tile in view; recalls land on the first free spawn tile (astraeus, 2026-10-27)

Two rules settled by probes (cambc-rules.yaml `camps.state`, `recall.landing`; `probe-capture-vision`,
`probe-recall-land`).
- A cleared group with a camp tile out of view took its holder from the occupants seen, though an unseen tile may
  hold champions. `engine::capturer` now reads the holder and timer from the capture state, readable with any one camp
  tile in view; `occupants` stays as last fully seen.
- `StaticMap::landing_tiles`: our spawn tiles in the engine's order. A recall lands on the first with no visible ally
  (`recall_landing`), used by `home_trip`, `closing`, the pocket recall and the draft's `type_facts`. The home trip's
  heal turn is free when a spawn tile beside the landing is a step closer to an altar.
- A/B w4-probefix 50.3% of 1164 (47.4-53.1; ladder 48.6, gen 50.4, gen-s1 50.6), out-of-fuel turns 4747 vs 4811.

All of 178-182 together, against 0c13a93 (`bots/variants/astraeus-0c13a93`), own drafts: p1-narrow 50.7% of 1164
(47.8-53.6; ladder 52.9, gen 50.8, gen-s1 50.0), out-of-fuel turns 4982 vs 4516 (rounds 1-10 877 vs 846, 61+ 3525 vs
3138); fresh suite 1301 (`maps/fresh-1301`, p1-confirm-1301): 52.5% of 512 (48.2-56.8), 1810 vs 1666.

## 183: emblems chosen from measured income, no forced first emblem (astraeus, 2026-10-27)

Treasure was forced first for every champion but Prism (101, priced at 1.x's +20%; 2.0.0 made it +10%). With
nothing forced the model's own pick was level with Treasure first (emb-td-none 51.1%), and forced Prospector first
(54.4%) and Capture first (53.3%) both beat it, most on maps with many captures per gem (EXPERIMENTS "Phase 2").
`best_emblem` now prices five passive emblems in its own unit, the share of a farming turn saved:
- `Income` counts our gems collected, capture payouts taken part in, what a Prospector emblem would have added to
  them (sharers read from our share), base capture and kill gold (before bonuses) and Tribute's cut turn ends. A
  payout is read at turn start from the last turn's end tile, since a capture recall can take us home before our
  turn. `income_prior` (the map's groups each captured alone, plus measured ladder rates: 4.5 rounds alive a gem,
  0.005 kills and 0.015 Tribute turns a gem) counts as 30 gems until our own income outweighs it.
- `passive_saved`: Capture saves 2 hold rounds per payout, Tribute its cut turns, Prospector its extra gems as
  farming saved plus their gold; Treasure 10% of base gold (with Marcella's tribute gold), Hunter 50 a kill. Gold
  is priced at the best stat emblem's saving per gold (not a passive's), earned evenly until our share of the
  gems left is farmed or the game ends, so spent halfway there on average.
- A candidate is five shards in the main stat or Health plus its passive; a begun passive is finished first,
  with its term.
- Buys (W1 alone): first emblem Prospector 51%, Treasure 19%, Prism's Monster 13%; second Capture 22%, Jungle 20%,
  Treasure 16%. Capture per champion-game 0.46 on low-capture maps, 0.74 on high ones.
- A/Bs own drafts against d0244de: p2w1-a (before the best-stat gold price) 59.5% of 1164, p2w1-b 61.1% (ladder
  47.9), against Prospector first 56.9%.

## 184: Prism prices the passive emblems under the same model (astraeus, 2026-10-27)

Prism's branch (gem_focus) offered only stat and camp emblems and opened Monster-Focus in ~60% of games. It now
also offers Capture, Prospector, Tribute and Hunter in Health or Focus by `passive_saved`, its gold at its own best
stat emblem's saving. (W2's first version used static map rates and a fixed Prism kill rate: 49.6% against Prospector
first, ladder 54.3.)
- Prism's first emblem: Prospector-Focus 44%, Prospector-Health 23%, Monster-Focus 15%, Capture-Focus 6%; per game
  Bruiser-Focus 1.93 (was 2.83), Capture 0.77, Prospector 0.86, Hunter 0.09, Tribute 0.03. Prism's side won 51.1%
  (48.9% before).
- p2-merged-vs-w1 50.8% of 1164 (47.9-53.6; ladder 56.4, gen 48.0, gen-s1 52.0), out-of-fuel turns 4661 vs 4613.

183 and 184 together against d0244de (`bots/variants/astraeus-d0244de`), own drafts: p2-merged-vs-d0244de 62.4% of
1164 (59.6-65.1; ladder 57.1, gen 61.5, gen-s1 64.6), out-of-fuel turns 4789 vs 4773 (rounds 1-10 951 vs 865, 61+
3326 vs 3476); fresh suite 1302 (`maps/fresh-1302`, p2-merged-fresh1302) 64.3% of 512 (60.0-68.3), 2288 vs 1877.
By the map's captures per gem (terciles): 48.2 / 65.5 / 73.5.

## 185: Durability on Ren's retaliation everywhere; live_self's emblem factors; siege upkeep with allies' Monster (astraeus, 2026-10-27)

Gaps left by CHANGES 179 and 181.
- Ren's retaliation compared with our health unscaled by our `taken` (Durability) in the dash landing
  (`landing_suicidal`, visible and unseen), `skip_rens`, `sure_kill`, `best_hit` and the plan search's units: all
  scaled now, as `enemy_cast` and `unseen_suicidal` already were.
- `live_self` (turn_order.cpp) copies `taken`, `dealt` and `camp_dealt`: `read_strike`'s scale left out our
  Skirmish and Collectors; the escape checks read the live self's `taken` (same value as `world.me()`).
- `siege_upkeep`'s `others` sums the allies' `camp_output` (Monster, Collectors), not `floored_output` (removed).
- A/B todo-b1 50.3% of 1164 (47.4-53.1; ladder 50.0, gen 50.4, gen-s1 50.2), out-of-fuel turns 4806 vs 4811,
  against 929b142 (`bots/variants/astraeus-929b142`), own drafts.

## 186: a shopping trip counts the passives it completes; Prism offered Treasure (astraeus, 2026-10-27)

- `affordable_prefix` (used by `wants_shop` and the Prism bank detour) priced the shards a trip buys by their stats
  only. `Emblem::passive` carries `best_emblem`'s `passive_saved` term, and each emblem the prefix completes adds
  it, so a trip is worth what `best_emblem` already said it was.
- Prism's passive candidates include Treasure, under the same model as the others'.
- A/B todo-b2 (with 185) 49.6% of 1164 (46.7-52.4; ladder 49.3, gen 46.5, gen-s1 52.7), out-of-fuel turns 4962 vs
  4737 (gen 1967 vs 1738), against 929b142, own drafts.

## 187: the farm's rated bound on every turn; the first turn's setup trimmed (astraeus, 2026-10-27)

Fuel audit 2 (farm) P1 and P4. Fuel-only: replays identical at 100M (release builds, the turn-end queue on).
- `farm_turn<false>` tests CHANGES 163's rated bound from the Chebyshev distance before a group's facts, its fastest
  clear and its steps, on every group (the opening already did). The same
  exclusions: banking, a winning group, a claim, `best < 0`, our last choice, a group hop, `may_help`, Ren, a pocket.
  Worth is the facts' weighted worth while they hold, else the unweighed worth from per-group gem and gold arrays
  (`FarmMemo::worth_gems`/`worth_gold`, by Prospector); the fastest clear it reads is the one the facts keep. A
  verification copy that ran each pruned group's full path found none that would have become best, help or shared
  (791k prunes on the heavy set; only `risky`, unused with `best >= 0`).
- The first turn's leads order is filled by index (no `push_back`/`std::find`), and `group_hop(g)` (a host call a
  group) is asked only when `any_group_hop()`.
- Heavy set (16 maps, own drafts): turns over 100k in rounds 2-10 536 -> 402, rounds 11-60 809 -> 508; round 1 mean
  -2.1%, round 2 -16%. Wide set: rounds 61+ +0.15% mean (rounds 300+ +0.25%: the check on groups it rarely prunes;
  skipping it for groups whose steps are read was dearer, +0.43%).

## 188: plan v8, an index at the end of the draft memory (astraeus, 2026-10-27)

Fuel audit 2 P2 and P3. Fuel-only, identical at 100M.
- Once the draft's analysis is done, `write_index` fills the room left after the ward section (none if the ward
  section was cut) from the end of the stream: where the steps end, fixed-width steps (each kind's codes at the width
  of its largest; spawn offsets as two masks and a list) and a checkpoint every 8 attack groups (where that block's
  bush bits start). Checkpoints alone if the steps do not fit (gen-dense-camps-120105502). It checks what it wrote
  decodes to the Rice section's values. `PlanHeader::indexed` (1 bit); the other sections follow as in v7, a bit later.
- Champions decode the ally steps at build in one pass (round 2's group hops read every group's), and the enemy and
  altar steps one group at a time on first ask (`StaticMap::fixed_step`), the rest by the turn-end queue
  (`warm_drafted_steps`, a kind a check). `index_attack_tiles` counts bush bits only in the asked group's block.
- Heavy set round 1 mean 278.9k -> 269.6k on top of 187 (p99 433.5k -> 410.9k), round 2 -2.8k. Decoding every step
  lazily cost round 2 +2.4k (group hops), hence the ally steps at build.

## 189: the strike search's step guard worked out only when it can count (astraeus, 2026-10-27)

Fuel audit 1 (fight) F1. Fuel-only, identical at 100M.
- `guard_steps` defers `step_guard` with a cover, `step_guard_cover`: the tiles within the radius that step_guard's
  first test (distance-bound exposure against our exact exposure) does not clear, sharing its foes (`GuardFoes`). The
  search offers those tiles, and works the guard out (unchanged, same memo and gates) only when the price loop pops
  one, before the capped fallback prices one, or when fewer than 2 tiles off the cover decide the goal-field test. A
  guarded tile is skipped before it costs a query.
- `debug_lazy_guard` (off) works the guard out after every search and checks no priced or chosen tile was guarded and
  the guard lay inside the cover: 0 of 23k searches on the fight set; the leaf table never filled.
- Fight set (12 maps): rounds 2+ mean -0.14%, turns over 110k 2984 -> 2881. Smaller than the audit's 3.5-7k a heavy
  turn: the popped tiles are often in the cover.

187-189 together against dfaf546 (`bots/variants/astraeus-dfaf546`), own drafts: fuel2-tip2 50.9% of 1164 (48.0-53.7;
ladder 47.9, gen 51.2, gen-s1 51.4), out-of-fuel turns 3836 vs 4822 (-20%): round 1 277 vs 448, rounds 2-10 325 vs
483, 11-60 385 vs 431, 61+ 2849 vs 3460.

## 190: unity build (astraeus, 2026-10-27)

The arch audit's A1. The ladder builds `src/*.cpp` with fixed flags and no LTO, so calls between files were never
inlined. The units are now `.cc` files that `src/unity.cpp` includes, one translation unit; colliding
anonymous-namespace names renamed (abilities' `walked`, `camp_stunned` and one-argument `kept_recall`, plan's
`Tables`/`tables`). A new collision fails to compile. `tools/fuel/cap_variant.py` patches `main.cc`. A release build
takes ~45 s locally; the ladder has no compile timeout.
- Fuel-only: replays identical on the wide, heavy and fight sets (release, 100M). On top of 187-189, rounds 2+ mean
  -0.28% wide, -0.27% heavy, -0.25% fight; turns over 100k 5577 -> 5523, 4330 -> 4290, 4586 -> 4501.

## 191: our basic attacks count Skirmish and Collectors; reset_may_kill reads our live attack (astraeus, 2026-10-27)

From the assumption audit (2026-10-27).
- `champion_dealt_factor()` (bot.cc, beside `camp_dealt_factor`, read live from our items): Skirmish x1.05 times
  Collectors' +1% a family, as `emblems()` reads them for others. Our basic attacks at champions use it: the Board,
  the strike search (camp targets divide it back out), `attack_target`, the reset kill check, `dash_to_attack` and
  `sure_kill`. Spells already had it (`my_damage_to`), and so did `prey()` (`world.me().damage_scale()`).
- `reset_may_kill` tested `2 x` the belief's raw Strength: now our live Strength x Heart of Ruin's scale x
  `champion_dealt_factor()`.
- Replays identical on the wide bench (52/52 each): we never own Skirmish or Collectors (their passives price at 0),
  and Heart of Ruin has no reset.

## 192: a respawned enemy grows from the turn after its respawn turn (astraeus, 2026-10-27)

- `update_champion` fixed a respawned enemy to its spawn at `{round - 1, -1}`, so its respawn turn counted as a walk.
  It is fixed at `{respawned_round, slot(respawned_round)}` (rules death.respawn_turn: no walking that turn); when the
  round is ambiguous it still takes the earlier one, at most one turn too many. 9 of 52 wide replays differ.
- Comments only: a stun wakes a camp group too (rules camps.wake), in `CampBelief` and `access_fire`. In view the
  engine's awake reads already catch it.

## 193: Ren's retaliation lands on each attacker (astraeus, 2026-10-27)

- Trade (safety.cc) hurt the attacking side's weakest by every hit x the retaliation (`act()`, and `play_quiet` /
  `play_shielded` through `onto_them`/`onto_us`). Rules champions.ren.passive: each hit returns 0.2 x Focus to its
  attacker. `act()` picks its target first, and when it is a Ren records each fighter's hits (1 a basic attack, a
  cast's own count) and calls `Side::hurt_one` per attacker: its Durability and shield, no spill (`take()`, shared
  with `spill`). The quiet paths hand any half-turn with a Ren as either weakest to `act()`. `their_cap` and
  `overwhelmed` keep the pooled total, still a valid bound. Spill onto a second Ren stays unmodelled.
- Own drafts have no Ren: the wide bench (hecate on test drafts) differs in 9 of 52. No test-draft A/B finished.

## 194: shields and Durability by one helper (astraeus, 2026-10-27)

- `effective_hp` (world.h) = (health + shield) / taken: prey's kill turns, and `pack_boxes` on both sides.
- `camp_trapped`, `breach` and `finishing_camp` weigh camp fire against health plus our live shield.
- `attack_target`'s Ren check (and the reset's through it) and `landing_suicidal`: retaliation x our taken against
  health and shield.
- `enemy_cast` never took a Ren's retaliation off a cast's value (only a suicidal Ren was skipped): unit, ground and
  landing casts now subtract it, as the plan search does.
- A self-shield (Varg, Heart of Ruin) earns shield income on camp clears (`shielded_clear`: R / cooldown casts of
  min(amount, duration x fire a round)) in farm's `affordable`, the alone clear, `beyond_spare`'s bound and
  `recovered_for_work`; `beyond_spare` stays a lower bound.

## 195: can_act_before with our own rank (astraeus, 2026-10-27)

- `can_act_before` assumed we would be our team's first next round (always true when we start). It now ranks us at
  the packed priority each offer would set (`offer_kills` passes its band value) against the allies' next priorities
  as last read, and compares with the enemy's earliest rank by `World::slot`'s formula: we act first iff k <= j when
  we start, k < j when they do. Dead allies keep their slots, as in `slot()`. `side_damage` counts only the allies
  that act before the target.
- Prism, Vesper Vale, Ryth, Vendetta, Marcella and Heart of Ruin never bid for the bands: own drafts change only
  through Willow.

## 196: teleports onto dead camp tiles (astraeus, 2026-10-27)

`probe-teleport-dead-camp` (rules `teleport_crystal.target`, `capture.respawn`): a dead camp's tile is a legal
landing, and a teleport headed to a camp tile delays its group's return.
- `Pathing::teleport_targets` adds the camp tiles in range of groups believed cleared or respawning where vision shows
  no camp (an unseen respawning tile only until it is due back).
- `StaticMap::add_hop` keeps its static landings and adds `camp_landings` (the pocket's camp tiles within 3 of our
  walk), which `take_hop` uses only through `teleport_targets`' dead ones, preferring a landing off our farm choice's
  tiles while it respawns. No new hops.

191-196 against c6cb8e7 (`bots/variants/astraeus-c6cb8e7`), own drafts, ladder only (140 games, 24 threads):
191-193 46.4% (38.4-54.7), out-of-fuel turns 736 vs 737; 191-196 53.6% (45.3-61.6), 802 vs 727. Not A/B'd on gen
or gen-s1 as merged; 191-193 with the reverted recall check read 48.6% of 1164 (EXPERIMENTS "Assumption audit").
Kept as rules fixes under the keep rule.

## 197: v61's retreat rework and draft (astraeus, 2026-10-28)

From v61 (`bots/baselines/v61`; patch `research/hyperion/v61-split/retreat.patch`):
- Prism on a lethal tile with a step that takes no modeled damage or stun before our next turn takes it
  (`prism_retreat_walk`), nearest our spawn, retrying up to 8 refused moves and looking again after each. A
  walk-excluding cast replaces it only if it kills the sole visible threat (engine damage) or stuns it before it acts
  (`cast_at_enemies_for_escape`, `enemy_cast`'s `escape_enemy`).
- Heart of Ruin below the recall line with its dash ready keeps the dash to escape (`hor_retreat_casts`): only a
  landing that kills a visible enemy goes first (`enemy_cast`'s `lethal_landings_only`), then the quoted escape dash
  (`quote_escape_dash`/`cast_escape_dash`, dash_away's ranking), then any other cast.
- Drafts: Vendetta in Vesper Vale's slot on 4 and 5 picks and in `draft_preference` (Cassi and Issac third), and Vesper
  is never drafted (`pick_first_available`, not under `test_draft`).

Against deb288a, own drafts, six mixed batches (ladder + gen + gen-s1, both sides): 52.9% of 1164 (50.0-55.8); ladder
57.1% of 140, gen 51.6% of 512, gen-s1 53.1% of 512; 3/4/5 picks (gen suites) 50.7/53.4/52.7. Batches 57.1, 56.1,
52.6, 54.6, 47.9, 48.9. Out-of-fuel turns 4224 against 3619 (Prism's re-reads after each refused move are a suspect). The rest of the v61 port (emblem rules, 3-pick roles,
`turn_rank_valid`) is not in: EXPERIMENTS "v61's features ported into astraeus".

## 198: drafts from the draft lab's model of the map (astraeus, 2026-10-28)

- The draft measures the map's 19 features in C++ (`map_features.cc`, a step-for-step port of
  `tools/draftlab/features.mjs` and mapgen's `metrics`, rounding included) and drafts the best team of the map's pick
  count under the draft lab's model (`draft_model.h`, generated by `node tools/draftlab/model.mjs cpp`), on the first
  draft turn. Fuel 1.6M median, 5.6M at most (10M first turn).
- No counter terms (cross-validation fitted them to ~1e-4): teams are scored on champion values and synergy only and
  picked in champion id order; `model.mjs cpp` refuses a model with counters above 1e-3.
- `params::map_model_draft` (on) switches it; off, and on other pick counts, test drafts, spawns joined only by dash or
  crystal, or a failure, the old table draft (with v61's 3-pick Tavi switch). Vesper may be drafted on the model path.
- The model: night1, 88308 self-play games (tools/draftlab/README.md; EXPERIMENTS "Draft lab").

Against astraeus bb73f75 (`bots/variants/astraeus-e7a5b29`), own drafts, on the build before the counter terms were
removed, which drafts the same team on all but 4 of the 2798 pool maps, in a different pick order (by their ~0
counter sensitivity); not rerun: maps never played by the lab 56.8% of 868
(fall-holdout 55.3% of 356, 50.1-60.4; fresh suite seed 52826 57.8% of 512, 53.5-62.0); the standard suites, which the
model trained on, 57.9% of 1164 (55.0-60.7; ladder 62.1% of 140, gen 57.6, gen-s1 57.0). 3/4/5 picks on the unseen
maps 56.2/57.2/56.9. Out-of-fuel turns lower (holdout 557 against 937). In-game parity with the JS model: 0
differences on 248 maps.

## 199: settled camp groups skip the member reads (astraeus, 2026-10-28)

River's `camp_settled` (EXPERIMENTS "river: fuel"), ported. A group in view that reads as last round did skips
`update_camp`: respawning before the round it returns (`read_respawn`, the round + timer last read), or alive and
asleep with `witness`, a member read asleep last time, still asleep (damage or a stun wakes every asleep member, and
none sleeps again within a round). `CampBelief` gains both fields.
Behaviour-identical (wide bench, 52/52 at 100M fuel). Fuel a play turn 51,633 -> 50,770 mean (-1.7%), p90 86,155 ->
86,035, p99 101,782 -> 100,241, turns over 100k 2,534 -> 2,302; `update_camps` alone 2,815 -> 2,098 mean, p90 5,549
-> 3,886 (8 maps, metered copies). At the real budget out-of-fuel turns 1,099 -> 832, but only 23/52 games stay
identical there, so that is indicative only. No A/B.

## 200: bot.cc split into files and folders (astraeus, 2026-10-28)

Text moved only. `bot.cc` (6707 lines) keeps the turn: `play_turn`, `act`, `decide`, wards and re-observes. Its
branches are in `economy/` (shop, camps, bank, capture, farm, siege) and `combat/` (fight, guard, support), beside the
existing files now in `model/` (world, pathing, safety, comms, turn order), `combat/` (plan, abilities) and `draft/`.
- `bot_parts.h` holds what they share: the turn's state, the types it needs, and a declaration of each function used
  across files, still in the unnamed namespace (one translation unit), so linkage and inlining are unchanged.
  Default arguments moved from the definitions to these declarations.
- Includes are relative (`../model/world.h`): the ladder adds no include path for `src/`. `cambc bundle` keeps
  subfolders.
- Tools: draftlab's `model.mjs cpp`, `native.mjs` and `native_main.cc` read `src/draft/`; `vehicle.py` patches
  `src/draft/draft.cc`, or `src/draft.cc` in older frozen sources.
- Fuel-only: identical replays and fuel on the wide set at 100M and the real budget; the release object has the same
  functions and instructions (EXPERIMENTS Fuel). Draftlab native parity: 0 mismatches on the 70 ladder maps.

## 201: shared-gem kites cast only where spells out-damage basic attacks (astraeus, 2026-10-28)

- `kites_with_spells` (economy/siege.cc): on shared-gem maps a melee champion takes kite ground stations, and
  `main_stat`'s forced Focus, only if its damage spells a turn beat its basic attacks (with the reset's). Ryth now
  melees there instead of standing off to cast his stun every 8 turns, and buys by the normal rule; Marcella keeps her
  unit stations but loses the forced Focus. Ranged champions, Ren (retaliation) and champions without damage spells
  are unchanged.

Forced drafts on both bots (Ryth Vesper Marcella / + HoR / Ryth Vesper Prism Marcella HoR), against astraeus 3938c0f
with the same drafts: 59.2% of 120 (50.2-67.5) on 60 freshly generated shared-gem maps; on the standard suites'
10 shared-gem maps 13 of 20. Not confirmed on a second shared-gem set and no full-suite regression check. The logic
is gated by the static `StaticMap::shared_gems` (`kite` runs only there, bot.cc; `main_stat`'s check short-circuits
on it), but games elsewhere are not identical: the unity build's codegen shifts fuel costs, so fuel-bounded choices can
change. The two forced-Ryth A/Bs that differed only by this change disagreed on 41 of 1164 games, at least 21 of them
off shared-gem maps (fuel-side noise, not strategy). Ported from worktree commit 15d094bc onto the split layout
(CHANGES 200). Open: TODO "Next, ranked" 11.

## 202: code audit cleanup (astraeus, 2026-10-28)

Thirty file-by-file audits ([audit-2026-10-28](audit-2026-10-28/README.md)): comments made current and concise
(experiment tags and stale references dropped, wrong ones fixed), shared helpers for duplicated code, dead fields and
parameters removed (`MapEconomy::gem_groups`, `route()`'s `through`, unused `Board` fields), cached host reads, and
farm's six experiment traces (FPARTIAL, FCDELAY, FCWINDOW, FCPARTNER, FSEED, DASH-FOLLOW) removed. Fuel-only: the
wide set at 100M with test drafts is 52/52 identical, fuel -0.96% (debug build, so the traces count). The audits'
behaviour fixes are on branch `audit/fixes-2026-10-28`, not yet A/B tested.

## 203: audit fixes (astraeus, 2026-10-28)

Ten behaviour fixes from the code audit (CHANGES 202), each narrow:
- turn_order: raw priority 0 packs like any other (`(7 - index)` above the payload), so its payload is sent. CHANGES
  141 kept it at 0 to match an unseen champion's reading; that dropped the claim and support intents of an idle
  gemless Prism at 80-90% health. Unseen allies now misjudge a raw-0 champion's rank slightly.
- farm: a turn cut short before weighing walks on to last turn's group as its crew if it was one (`memory.crew` was
  reset, so a helper took over its ally's claim).
- safety, guard: a visible enemy with a pending teleport acts from its destination everywhere (`acts_from`).
- abilities: `camp_cast` values every camp spell with the Monster/Collectors factor, not only the finishing test.
- siege: `siege_load`'s strongest member is the strongest live one.
- capture: no contest of an enemy hold that cannot pay by round 2000.
- shop: `affordable_prefix`'s cache key includes the main stat.
- world: respawns and unseen recall arrivals keep the enemy's damage factor and drop its shield; an unseen payout
  clears `held_since`.
- map_features: crystal `travel` leaps from every tile within 2 of something unwalkable, as the JS (draftlab parity
  only; the bot runs it without crystals).

With an eleventh (spawn damage, dropped): 49.7% of 1164 against 55a8c79, own drafts (EXPERIMENTS "Audit fixes").

## 204: DIRECTIONS cleanups, no behaviour change (astraeus, 2026-10-28)

The mechanical items from [DIRECTIONS.md](DIRECTIONS.md), now removed from it:
- Renames: `may_shop` -> `shops_at_home`, `prism_capture_holder` -> `sole_capture_holder`, crew_work's `kill_resets`
  -> `dash_maybe_ready`.
- Moves: the emblem factors' declarations and one `has_family` (world.cc's `owns` now calls it) to a new `emblems.h`;
  `economy_pick_count`, `economy_three` and `support_protected(world, c)` from draft/map_economy.h to world.h;
  `raw_output` onto `ChampionFacts` (with `ability_cooldown`, now in champions.h); `CampLeft` into camps.cc.
- Shared: `banks_bag` (bank.cc) at its three spelled-out copies, `cycle_horizon(map)` for camps.cc's and farm.cc's
  horizon, `square_dilate` (util.h) in place of bank.cc's `dilate_into`, `support_pair(world)` (world.h) for comms
  and support. Dropped: `SupportExposure::damage` (never read), `MapEconomy::reachable_gems` (`gems > 0` is the
  same test), the support mailbox's respawn check and `Endpoint::present` (a death shows at a read in between).
- Asserts and comments: priority roles stay within a health bucket and below dead; ground spells exclude walking
  (the plan search's assumption); no healer dashes (Willow's guard); `positions_within`'s r <= 8 in a debug_block;
  `params::pick_up_radius`; turn_order.h's priority-0 note and `support_turns`' count made current.
- Fuel-only: `holding_capture` kept per turn (round, observations, tile, gems, gold); our emblem factors kept until a
  purchase (`items_bought`); one buff read for plan's foe shield and stun (`buff_state`); `enemy_lock_live` reads the
  locks raw; the capped `make_field` returns `optional<Field>` (no heap `Field`) and clamps its cap at `unreachable`.
- Latent: the draft resets its dash entries with the leads, clears the steps header's flags when the steps don't
  fit, and keeps `mirrored_enemy_steps`' cursor in `DraftSteps`; map_features rejects a spawn off the map.

Fuel bench, wide set, test drafts, 100M, against main eb66fdd2: 52/52 replays identical, total fuel -0.02%
(round 1 +0.1%). Left out: `respawn_earliest`/`respawn_latest` stay (`tools/replay/audit_beliefs.py` checks them);
`affordable_prefix`'s second cache entry is not fuel-only (DIRECTIONS shop 3).

## 205: two rules fixes from the audit's probes (astraeus, 2026-10-28)

- capture: a Prospector emblem's extra is 25% of our share with the remainder when we are the lowest-id holder
  (`our_share`; probe-prospector-remainder). It took the floor share only. The other multi-holder uses (farm's
  `gold_in`, `note_income_start`) are estimates that floor every share, and stay so.
- pathing: `teleport_targets` admits a dead member's tile in a live group once seen empty
  (probe-teleport-dead-member); it skipped live groups whole. Unseen, such a tile stays out.

Not A/B tested: both follow the engine. Smoke games on 00interlock and gen-archipelago ran clean.

## 206: stopping a game-winning tribute (astraeus, 2026-10-28)

DIRECTIONS fight 1, 4, 5, 11 and champions 1, one commit each after a debug-counter commit (ENDER-WALK, STOP-RANGE).

- fight 1: `game_ender` no longer skips a walking enemy carrier whenever our bag wins. It counts it when its walk
  to the nearest altar and channel (`carrier_tribute`, as `intercept_steps` times it) land before `win_lands`.
- fight 4: `intercept_steps` no longer takes reaching attack range as stopping a tribute or teleport, since damage
  interrupts neither. A kill counts by `kill_turn` (basic-attack hits to its effective health after the walk into
  range; on its spawn, where it heals every turn end, a one-hit kill only), as do a stun and a lock.
- champions 1: `ChampionFacts::stun_reach_with_walk` adds a tile for a stun that allows a walk first (Cassi 5, Heart
  of Ruin 4, Marcella 2). `ready_stun_reach(round, walk)` uses it for `intercept_steps`, `ally_stops`, and
  `stoppable_winning_tribute` while we can still walk (cancelling our tribute frees the walk). `stop_game_ender`
  steps before `dash_to_attack` when such a stun is a walk away: Heart of Ruin's dash landed out of stun reach.
- fight 5: an altar lock is placed after the last step (`intercept_steps`; `ally_stops` counts an ally a step beyond
  lock range). The melee hit after the last step is `kill_turn`'s, the walk-compatible stun the item above.
- fight 11: a walking Cassi or Issac channels its own bag: its own channel when its bag wins alone, else the longer
  of the two bodies'.

A/B against `bots/variants/astraeus-7884d8d`: 49.9% of 1164, level (EXPERIMENTS "Tribute stops"). The counters
fired rarely: STOP-RANGE in 7% of games, ENDER-WALK in under 1%.


## 207: a kill's worth, and Prism's sight of Willow (astraeus, 2026-10-28)

- abilities, plan: a kill is worth the tribute it cancels (`kill_stops`: `tribute_value`, and every gem of a
  game-winning one), which only a stun's worth carried, so a stun that left a winning tributer alive outscored
  killing it. The cast menu prices a killing blow with it and no stun. The strike search's `lose()` settles a death:
  it adds `kill_stops` and takes back a stun credited on the target this turn, so a stun counts only on a survivor;
  `hit_centre` sets its stun bits where `centre_value` credited them, before any death.
- self_abilities, plan: `attack_target` and `best_hit` (strike_enemy) value hits by the strike search's `hit_worth`
  (kill_distance, the bag, Cassi and Issac's weaker body) plus `kill_stops` on a kill. `attack_target` scored a kill as
  health + life, with no bag. `hit_worth` is shared from abilities.cc; the cast menu's form, which adds a cancelled
  recall, is `hit_worth_of`.
- support, safety: Prism's recovery window is the tiles Willow sees (`seen_from`, a cast from her tile with bushes
  opaque), not the tiles that see her: a heal needs its target in her sight, and a bush tile beside her counted. In a
  bush, `attack_viewers` stays.

A/B against `bots/variants/astraeus-509d9fb`: 51.3% of 1164, level (EXPERIMENTS "Kill worth, Prism's sight"). A
fourth fix, `main_stat` counting heals, is on branch `exp/main-stat-heals`, not kept.

## 208: escapes and the mend turn (astraeus, 2026-10-28)

- abilities: an escape's walk-excluding stun certifies on an enemy yet to act this round whose only turn before ours
  that is (`e.acted` was required): the stun takes that turn.
- fight: Prism's escape-walk rule (`escape_walk`, was `prism_retreat_walk`) covers every champion with a walk-excluding
  cast at enemies: on a lethal tile with a safe step, only a unit cast that kills or stuns in time the sole threat
  takes the walk. No ground cast is certified, so Ryth always walks (DIRECTIONS fight 8). After the walk, a cast that
  allows walking may follow (Cassi's stun).
- fight: Ren keeps its escape dash below the recall line as Heart of Ruin does (`dash_retreat_casts`, was
  `hor_retreat_casts`): a dasher whose other slot hits enemies. Before a dash that clears, only a killing cast (a unit
  cast or a landing; `cast_at_enemies`' `lethal_only`, was `lethal_landings_only`); otherwise the escape-walk rule,
  then any cast. The dash quote is dropped once the walk rule reads vision again.
- turn_order: `offer_escape` bids only when what lands whatever the order (the camps' expected damage, this round's
  strikes of visible enemies yet to act, not teleporting) leaves us alive.
- bot: the mend turn steps on spawn towards the next goal (an altar with a bag, else the farm group) when no more
  exposed (`mend_step`), as `home_trip` prices the heal; under camp fire it mends while it misses more than the camps
  take a round, where it never mended before (CHANGES 139).
- support: Prism's recovery window adds the tiles Willow's ward sees, while Prism sees the ward: a heal may target an
  ally seen only through the healer's ward (`probe-willow-heal-ward`, rules `abilities.unit_target`).
- Probes: `probe-willow-heal-ward`, and `probe-field-cap` (`compute_with_expansion_count` returns `min(cap, D + 1)`;
  DIRECTIONS util 1 stays open).

A/B against `bots/variants/astraeus-f61af92`: 55.1% of 1164 (52.2-57.9), ladder 50.7%, gen 53.5%, gen-s1 57.8%;
out-of-fuel turns +5.5% (EXPERIMENTS "Escapes and the mend turn"). Kept without a fresh-suite confirmation.

## 209: walk-only leaves, camp fire from champions yet to act, Ryth's escape stun, Willow's heal-step camps (astraeus, 2026-10-28)

DIRECTIONS plan 1, safety 3, fight 8 and support 2, as one bundle:
- plan: the strike search offers "walk, nothing else" as a terminal leaf, priced at its end tile, to every ranged
  champion that can walk, not only Prism and Stellar. Vesper, Willow, Cassi and Tavi weighed a strike from here only
  against staying put, both at the start tile's danger, since a ranged walk is kept only once a strike follows it.
  Willow's walk leaf can also heal from its end tile.
- safety: in `find_members` a visible champion yet to act this round, and not losing its turn to a stun, draws a
  monster's hit only from where it could move to first: its distance counts 1 more for the walk and 2 more with a dash
  ready (rules `rounds.sequence`: the camp phase comes before next round's turns).
- abilities: an escape certifies a ground stun (Ryth) as it does a unit cast, when the sole threat is visible,
  stunnable and has one turn before ours; only centres within 1 of it are tried, which hit it wherever they are.
- support: Willow's independent heal step counts only the camps its turn goes on to hit if it stays, those farm
  hits (`strength <= 0`, or its farm group), in both the attacks it gives up and the finish that keeps it in place.
  An asleep wounded wolf of another group no longer holds the step back.

A/B against `bots/variants/astraeus-085f676`: 50.2% of 1164 (47.3-53.0), ladder 52.1%, gen 48.0%, gen-s1 51.8%;
out-of-fuel turns +3.4% (EXPERIMENTS "Walk-only leaves, camp fire, escape stun, heal-step camps"). Level; kept (logic
fixes), except the safety part: reverted after the A/B, untested alone, because allies run our bot and a tank beside
the monster usually stays, so the move bound overstates the danger behind it. Back in DIRECTIONS safety 3 with
fixes that treat allies by their claim. What main keeps (plan, abilities, support) was not A/B'd without it.

## 210: cheap exact fixes (astraeus, 2026-10-28)

Eight small DIRECTIONS fixes, as one bundle:
- fight: `sure_kill`'s test against Ren's retaliation counts our live shield, as `attack_target` does.
- camps: `camp_attack_targets` ranks members as it scans, so a full list keeps the best 16 rather than the first 16
  in scan order.
- camps: `breach` charges the group's fire for one camp phase per hit, the last without the killed member: we stand
  there until our turn after the kill (rules `rounds.sequence`). It charged the killed member's fire in that phase too.
- turn order: our own cooldowns enter the priority a tick lower, as of our next turn, since our turn end ticks them
  first (rules `rounds.turn_end`); a slot at 1 counts as ready, as `read_strike` already has it.
- bank: `bankable_bag`'s pocket test reads the altar field at the recall landing, as `closing` does.
- abilities: `cast_at_enemies` always checks for a stale turn after choosing, not only for some callers.
- siege: kite's damage sim models the reset on any spent attack, including one spent before the turn's sim.
- world: an unseen champion's shield expires at its owner's turn start (`shield_end_round`), as an unseen channel
  completes; it never expired out of sight.

A/B against `bots/variants/astraeus-b34f219`, with a ninth fix: 49.7% of 1164 (46.9-52.6), ladder 48.6%, gen 50.4%,
gen-s1 49.4%; out-of-fuel turns +3.6% (EXPERIMENTS "Cheap exact fixes"). Level; kept (logic fixes). The ninth, Varg
holding its reset by `shield_if_needed`'s test, was dropped after the run (DIRECTIONS self_abilities 1), so what main
keeps was not A/B'd without it.

## 211: DIRECTIONS refactors, no behaviour change (astraeus, 2026-10-28)

Five refactors from [DIRECTIONS.md](DIRECTIONS.md), now removed from it:
- bot_parts 1: the turn's branch is an `enum class Branch` whose values are the old trace letters; `act()` and farm
  compare names (`Branch::wait_altar`, `Branch::chase`, `Branch::farm`), traces print the letter.
- combat_priority 6: `teacher_priority::Type` and turn_order.cc's 13 static_asserts are gone; `role()` switches on
  `cambc::champion_type`.
- camps 6: one `dealt_with(owned, added)` in emblems.h gives both damage factors (Skirmish/Monster, then Collectors in
  a branch, as world.cc had it); world.cc's `emblems()`, our own factors and shop.cc call it.
- shop 6: `begun_emblem(world, owned)` is the one list of begun emblems, in `best_emblem`'s finishing order;
  `best_emblem` finishes what it returns, and `wants_shop` tests it in place of `emblem_begun`, which also counted
  shards `best_emblem` never buys or finishes.
- util 2: `checked_round()` is gone; its callers use `round_now()` (a failed read only on an ABI mismatch).

Fuel bench, wide set, 100M, against main 9c19fd3d: test drafts 52/52 replays identical, total fuel +0.004%; own
drafts 52/52 identical, +0.001%. The first camps 6 version always multiplied by the Collectors scale: +0.13%.

## 212: one turn-order model for every champion (astraeus, 2026-10-28)

The "teacher" split from CHANGES 82 is gone (DIRECTIONS combat_priority 1-5, turn_order 1 and 3, idle_priority 1-3):
- Every champion bids for the kill and protect bands. Prism, Vesper Vale, Ryth, Vendetta, Marcella and Heart of Ruin
  had skipped `bid()`.
- `offer_channel` bids only when acting earlier can deny a cancel: not against this round's turn of a visible enemy
  yet to act, not against an enemy we cannot act before even with the bid, and not for a recall that a camp hit would
  cancel anyway (the bid would rank us first in its ties too). A recall or teleport is worth `recall_value` without
  the bag, as an enemy's in `offer_kills`: a cancel keeps the gems carried.
- `offer_heal` counts the ally's shield and damage taken, prices an enemy yet to act as its strike this round and a
  basic attack next round (as `threat_strike`), takes as landing before the heal this round's turns and next round's
  of enemies acting first even with the bid, and caps the heal at what health is left after those, shield first.
- The plain scale's danger comes from Safety's `strike()` and live reads at our turn's end: current health and
  shields, stuns cast this turn, Durability and our dealt factors, the next camp phase first, full health on our
  spawn. `combat_priority.h` (its own strike table) and World's turn-start enemy snapshot are deleted.
- The idle order decides who absorbs a camp's tie hit (rules camps.attack): first those the strongest tie hit leaves
  alive, by further such hits in hand, gemless before carriers; then those it would kill, fewest gems first (rules
  combat.camp_kill). The hit is `Safety::tie_hit`, the strongest member that would pick us had we acted first in every
  tie (`CampHit::tie_reach`, plus members that pick us only so), independent of the order it sets. No role table.
- `set_turn_order` keeps the last rank if working out the new one throws.

A/B against `bots/variants/astraeus-3f3aaac`, own drafts: 50.8% of 1164 on ladder and two fresh suites (ladder 54.3%,
fresh-82801 53.5%, fresh-82802 47.1%), and 52.0% of 512 on a third (fresh-82803); 51.1% of 1676 (48.7-53.5) in all.
Out-of-fuel turns 13141 against 14439 (EXPERIMENTS "One turn-order model for every champion"). Level; kept. A
read-only audit before the run found nine fixes, included.

## 213: the goal after the strike search (astraeus, 2026-10-29)

Batch 1's parts (2)-(3), without its goal-field fix (DIRECTIONS bot 1; EXPERIMENTS "The goal after the strike
search"):
- After a strike search that saw every enemy (`searched`: none of its own moves revealed one), chase only walks. Its
  dash, attacks and casts were priced and passed on by the search; `strike_after` hits from where the walk ends.
  With no walk left, chase gives way to the other branches.
- The ranged return after an attack is gone: with the walk spent, the goal keeps what the search cannot price (camp
  work, travel dashes). `wants_shop` is tried only with a walk, and siege skips its walking section without one.
- "Did we walk" tests compare with `World::turn_start`, our tile at `update()`, not `me().pos`, which `observe()`
  moves with us.
- `dash_across` takes its dash from `travel_dash_ready`: no dash across a wall with an enemy within
  `travel_dash_clearance` (the batch 1 auditor's Vesper finding; it covers every dasher and the bag's walk too).
- `Pathing::same_labels` keeps a cached approach field when at most 8 camp tiles changed and none of them can change
  a label (none within range of the group's members, no new camp on a labelled tile, no dead one on or next to one).
  A verification build checked 17,939 keeps against fresh searches with 0 differences.

The goal-field fix (`walk_target` ignoring our own recall) is not in: alone it read 47.3% at the real budget and
49.8% at 100M, its cost going to the fuel gates. A/B against `bots/variants/astraeus-be29e4b`, own drafts: 50.4% of
1676 (48.0-52.8) on ladder and fresh-82801/2/3; out-of-fuel turns 17282 against 16041. Level; kept. Not audited, and
`same_labels` not bench-checked byte-identical.

## 214: fuel round 1: fights end at our fall, shared tracking, unrewritten fixes (astraeus, 2026-10-29)

Three fuel-only changes (fuel campaign round 1), each byte-identical at 100M:
- `want_home`'s stand and `prey`'s chase read only `lost || (falls && self_falls)`: with `falls`, `Safety::stand`,
  `chase_trade` and the `fight_of` they fall back on pass `settle`, and the fight sim stops once our fighter falls,
  leaving `lost` unknown (`Trade::lost_known`). The fight memo hands such a trade only to callers that settle on the
  fall; step_guard's `known_fight_of` and every other caller replay it in the same slot.
- `World::track` shares a lineage's growth with enemies whatever their `at`: growth reads only the turns counted, not
  when they are dated, so enemies of a lineage on different slots now share one grow.
- `World::fix` skips clearing and rewriting `possible` (and a dasher's `undashed`) when they still hold just that
  tile from the last fix (`ChampionBelief::fixed_tile`; every other writer of the boards clears it). A visible enemy
  is fixed at every update.

Fuel bench at 100M against frozen 8ec2c4d: wide set (test drafts) 52/52 identical replays, total fuel -0.06%, p99
106866 -> 106316, turns over 100k 3615 -> 3551, rounds 2-10 p90 99365 -> 94461; OOF set (own drafts) 32/32 identical,
-0.23%, p99 147280 -> 145736, over 100k 11851 -> 11109, rounds 2-10 p90 104026 -> 95318 (EXPERIMENTS "Fuel round 1").
A/B against `bots/variants/astraeus-8ec2c4d`, own drafts, real budget: 49.8% of 1676 (47.4-52.2) on ladder and
fresh-82801/2/3, as fuel-only changes should read. Out-of-fuel turns 15809 against 19568; without the bimodal
gen-shared-gems-8280101604/8280201605 pair, 8342 against 8760 (-4.8%). Kept. Frozen as `bots/variants/astraeus-m1`.

## 215: routes leave the step guard deferred when it cannot change them (astraeus, 2026-10-29)

Fuel campaign round 1, third change, fuel only:
- `Pathing::route` searches without the deferred step guard first (`route_around`), while step_guard's costliest
  placing lately (`step_guard_costliest()`, now in util.h) is at least 15k and the guard has a cover. Walls only
  lengthen routes and the guard lies within its cover, so: a null cover means no guard (one search); a bare failure is
  the guarded failure, whose labels and `route_exhausted_` are worked out with the guard (`know_failure`) only when
  make_way or the wider search in `step_towards(Field)` could read them (`labelled_ally_beside`); a bare success that
  the route around the cover matches in steps and first steps (or in its first step, on a tile seen this turn) is the
  guarded route, and its steps skip the guard test (`Route::unguarded`, `move_to`).
- A guard left deferred so is worked out before what it reads changes (`settle_guard()` in `see_again`, `see_kills`
  and before decide's stun refresh). `closer_neighbours` tests the field before `steppable`, which may work out the
  guard. The 15k threshold picks only between exact computations of the same route.

Fuel bench at 100M, with CHANGES 214, against frozen 8ec2c4d: wide set 52/52 identical, total -0.11% (-0.06% over 214),
p99 106866 -> 106166, turns over 100k 3615 -> 3531; OOF set 32/32 identical, -0.62% (-0.39% over 214), p99 147280 ->
135669, max 430932 -> 394080, over 100k 11851 -> 10646. A/B against `bots/variants/astraeus-m1` (CHANGES 214), own
drafts, real budget: 50.6% of 1676 (48.2-53.0); out-of-fuel turns 18590 against 18754, and 8104 against 7970 without
the gen-shared-gems-8280101604/8280201605 pair: no real-budget OOF gain shown. Kept as exact. Frozen as
`bots/variants/astraeus-m1b`.

## 216: fuel round 2: end-of-turn exact cuts, step_guard's first union without per-tile keys (astraeus, 2026-10-29)

Fuel campaign round 2, fuel only, byte-identical at 100M:
- `may_escape` asks `camp_damage` (~10k on many-group maps) only once a seen or tracked enemy hits; the blows are
  summed after the camps in enemy order, so the float total is unchanged.
- Comms: `receive` keeps the sighting slots' codes and lists the mates (`list_mates`); `send` works out a slot's
  urgency only when `replaces` compares it. `urgency` stops at 0, its floor.
- `ward_bushes` tests for bushes near before its fuel check (both return false; only the shortcut note differs).
- `step_guard`, all foes listed: the first union takes the visible bits from the bounds, the allies from
  `Safety::fight_allies` and the unseen and stunned enemies from one `Safety::fight_enemies_any` over all the tiles
  (each enemy's bit from the first tile it hits); a tile's own key (`fight_key_with`) is worked out only past the
  exact exposure test. About 1.5k saved per forced guard.

Fuel bench at 100M against frozen 8ec2c4d: wide set 52/52 identical, total -0.43% (-0.31% over m1b), mean 50923 ->
50705, p99 106866 -> 106020, over 100k 3615 -> 3481; OOF set 32/32 identical, total -1.09% (-0.47% over m1b), mean
62520 -> 61839, p99 147280 -> 135655, over 100k 11851 -> 10492. Frozen as `bots/variants/astraeus-m2a`.

## 217: a turn after one that ran out finishes its decision late (astraeus, 2026-10-29)

Fuel campaign round 2, a livelock fix (behaviour change at the real budget only; identical at 100M):
- A turn whose decision costs more than the budget (the shared-gem livelocks: `want_home` ~38k plus the strike search
  ~30k before pricing, world ~14k) ran out, its stale tail was abandoned, the next round replayed the same turn from
  scratch and ran out again: one champion ran out 1745 rounds in a row and never acted.
- Now once a turn has not finished in its own round (main.cc's `late`), the next turn's decision is not abandoned if it
  runs out (`aph::finish_late()`: `throw_if_stale` and `World::is_stale` hold off): it finishes in the round it resumes
  in, as that round's turn, then `end_turn`. The first out-of-fuel turn of a streak still replays on fresh beliefs, so
  a streak acts every other round on beliefs a round old. No round gets two decisions: the late turn ends the round it
  finishes in. Actions on stale beliefs that the engine refuses spend nothing (caught in `act`).
- Comms `send` writes nothing from a turn finishing late (`World::resumed()`); the priority payload published then
  carries the decision's round, which teammates accept for one round as usual (support_mailbox).
- Known costs: the out-of-fuel line of a late turn names the last phase it reached (mostly "queue"), not where it ran
  out; a late tail can run out again and lose one more round (78 of 7815 out-of-fuel turns in the A/B, 10 before).

Fuel bench, with CHANGES 216: 100M 52/52 and 32/32 identical (+0.05% fuel: `finish_late` reads). Real budget against
m2a (216 alone): OOF set out-of-fuel turns 13784 -> 2423 (shared-gems maps 12611 -> 1245, the rest 1173 -> 1178); wide
970 -> 666. A/B of m2 (216 and 217) against `bots/variants/astraeus-m1b`, own drafts, real budget: 49.6% of 1676
(47.3-52.0) on ladder and fresh-82801/2/3; out-of-fuel turns 7815 against 9192 (6777 against 7609 without the gen-shared-gems maps); turns
in champion-games of 50 or more run-outs 587 against 1434. Kept. Frozen as `bots/variants/astraeus-m2`.

## 218: fuel round 3: exact cuts in camp members, Reach builds, the pack zone and the step guard (astraeus, 2026-10-29)

Fuel campaign round 3, fuel only, byte-identical at 100M:
- `find_members`: each group's member box is worked out on first use (all at once cost ~6k on many-group maps), and
  the wake check skips an other whose distance to the group's box exceeds `Strike::max_reach` or its strike's reach
  (no member lies nearer it than the box).
- `Reach::build` reads live camp members only within the radius the tile sets read (one per walk or dash step; the
  whole window for Varg's splash, which reads every member), straight from the cached camp tiles: no per-origin spot
  pool. A way's bound is worked out per query, not per build (`set_reach` gone; a build is queried at ~3 tiles), and
  `at()` drops its whole-reach test, which the per-way bounds already make.
- `camp_exit_rounds` drops its per-tile `camp_damage` test: `camp_area` is exactly where it is positive (every listed
  member has a reach and a Strength above 0; clusters have no range and are never listed).
- `in_pack_zone` sums the members within `pack_radius` of the tile instead of enumerating the pack boxes: a tile is in
  a box exactly when those members outmatch us, as outmatching only grows with members, in floats too (non-negative
  terms added in the boxes' order). The boxes are worked out only when `pack_zone` or `pack_covers` asks.
- `step_guard` and `step_guard_cover`: the bound pass reads per-foe cell masks over the step square (radius <= 2, 25
  cells), skips cells no foe reaches, and sums damage only when the mask alone does not decide.
- `Pathing::route` keeps the step guard's cover for the round while the guard stays deferred (each route asked again,
  ~9k on shared-gem kite turns, 2-3 a turn): every route that reads the cover leaves the guard skipped or works it
  out, and `settle_guard()` works it out before what the cover reads changes. `set_guard`, `defer_guard` and
  `restore_guard` drop the kept cover.

Fuel bench at 100M against frozen 8ec2c4d (against m2 in brackets): wide set 52/52 identical, total -0.64% (-0.27%),
mean 50923 -> 50594, p99 106866 -> 104910 (106049), over 100k 3615 -> 3300 (3484); OOF set 32/32 identical, total
-2.31% (-1.28%), mean 62520 -> 61071 (61866), p99 147280 -> 133461 (135680), over 100k 11851 -> 9061 (10500).
Real budget: OOF set out-of-fuel turns 2423 -> 1948 (m2; base 8339), shortcuts 35376 -> 31944; wide 666 -> 751
(base 1247), shortcuts 12688 -> 14324 (small samples, games diverge). A/B against `bots/variants/astraeus-m2`, own
drafts, real budget: 50.3% of 1676 (47.9-52.7) on ladder and fresh-82801/2/3; out-of-fuel turns 6775 against 7511
(5945 against 6597 without the gen-shared-gems maps). Kept. Frozen as `bots/variants/astraeus-m3`.

## 219: fuel round 4: round-1 world construction (astraeus, 2026-10-29)

Fuel campaign round 4, fuel only, byte-identical at 100M. `StaticMap::build` and `init_beliefs`, round 1's mandatory
work (~325k -> ~306k on many-group maps):
- Camp members are copied from the camp layout's words whole (`CampMember` reordered to the layout's order: handle,
  type, pos; offsets `static_assert`ed), with each camp type's stats and group-sum terms read once into a table.
- The groups are made in one `resize`; their monolith/shared-gems flags and centres are kept in locals while building.
- `StaticMap::camp_members` holds every group's members in group order, so `init_beliefs` fills the camp healths in
  one pass over all of them; the beliefs' slices are set through raw pointers.
- `find_crossings` shares its shifts (a shift of a union is the union of the shifts), and the striking camp tiles
  start from `camp_tiles` less the groups that never strike. `square_dilate`'s first shift writes its board whole.

## 220: fuel round 4: the plain fight path takes arrivals and Ren, the early-end cap sums casts lazily (astraeus, 2026-10-29)

Fuel only, byte-identical at 100M; `safety.cc`'s fight sim:
- A quiet turn against a Ren (`back > 0`) takes the quiet path: each living member in reach lands its basic attack
  alone, one hit each.
- The plain path takes arrivals: `Side::plain` now means only that every kit is plain (Strength and cast damage
  sixteenths below 4096, no shield, so sums are exact in any order), and the path counts only members in reach,
  recomputing its sum at the next arrival (`Side::arrival`). The `plain = false` lines in `walk_allies_in`,
  `join_late`, `chase_trade`, `stand` and `turns_to_kill_idle` are gone.
- `their_cap`'s casts and Ren term (`their_rest`) are summed only when the basic attacks alone fall short: the rest
  is at least 0 and `rounded_up` is monotone, so adding it cannot turn a miss into a hit.

Fuel bench at 100M, 219-220 against frozen m3 (against 8ec2c4d in brackets): wide set 52/52 identical, total -0.13%
(-0.77%), mean 50594 -> 50530, p99 104910 -> 104450 (106866), over 100k 3300 -> 3220 (3615), round 1 mean 197227 ->
195763, p90 210961 -> 203033; OOF set 32/32 identical, total -0.16% (-2.47%), p99 133461 -> 132459 (147280), over
100k 9061 -> 8827 (11851), round 1 mean 212700 -> 209980; OOF set on test drafts 32/32 identical, -0.14%; many-group
set 12/12 identical, round 1 mean 330501 -> 311088. Real budget: OOF set out-of-fuel turns 1948 -> 1732 (base 8339),
shortcuts 31944 -> 30430; wide 751 -> 710 (base 1247). A/B against `bots/variants/astraeus-m3`, own drafts, real
budget: 50.7% of 1676 (48.3-53.1) on ladder and fresh-82801/2/3; out-of-fuel turns 6703 against 6805 (5597 against
5859 without the gen-shared-gems maps). Kept. Frozen as `bots/variants/astraeus-m4`.

## 221: fuel round 5: `rank_turns` re-ranks only a team whose order may change (astraeus, 2026-10-29)

Fuel only, byte-identical at 100M. `World` keeps `ranks_stale_` and `ranked_round_` per team, and `rank_turns` sorts
only a stale team. Allies' priorities are compared shifted by `priority_payload_bits`: `packed_priority`'s rank bits
(the code times 8 plus 7 - index) differ for each ally and are never 0, and an unset priority is 0, so the order by
the whole priority is the order by its rank bits and a payload-only change cannot move it. An enemy's unread-priority
test reads the enemies' own `ranked_round_`, never newer than the shared one was, so enemies re-rank at least as
often as before, and a re-rank with unchanged keys gives the same order. `rank_turns` was stale on 95% of turns.

## 222: fuel round 5: an idle strike search skips read, grow and price (astraeus, 2026-10-29; reverted)

Reverted the same day (exact at 100M, but more out-of-fuel turns at the real budget; below). Fuel only,
byte-identical at 100M. `plan_strikes` reads our own state first (`Search::read_self`); when `idle()`
holds, no visible enemy within reach of a basic attack (range + walk + dash), a landing (dash + walk + radius) or a
ready damage/stun unit cast (its reach, +1 unless it excludes walking), and nothing else could be offered (no ready
shield or heal, no splash or Vendetta, no reset with the attack spent, no ranged walk, no excludes-walking ground
cast), the full search's only leaf is the start tile's root with no actions: never guarded, priced first, never
capped, so chosen exact. `searched` is then whether `read()` takes any enemy (`any_foe`, the same per-enemy test).
About 35% of searches, ~11.2k each.

Fuel bench at 100M, 221-222 against frozen m4 (against 8ec2c4d in brackets): wide set 52/52 identical, total -0.90%
(-1.67%), mean 50530 -> 50073, p99 104450 -> 102412 (106866), over 100k 3220 -> 2959 (3615); OOF set 32/32
identical, total -1.25% (-3.69%), mean 60973 -> 60209, p99 132459 -> 130872 (147280), over 100k 8827 -> 8261
(11851); OOF set on test drafts 32/32 identical, -1.11%, over 100k 4920 -> 4606. Real budget: OOF set out-of-fuel
turns 1732 -> 1700 (shared-gems maps 802 -> 785, the rest 930 -> 915; base 8339), shortcuts 30430 -> 31253; wide
710 -> 744 (base 1247), shortcuts 14239 -> 12545 (small samples, games diverge). A/B 221-222 (`astraeus-m5`)
against `bots/variants/astraeus-m4`, own drafts, real budget: 50.0% of 1676 (47.6-52.4) on ladder and
fresh-82801/2/3; out-of-fuel turns 7053 against 6657 (+5.9%; 5881 against 5726 without the gen-shared-gems maps),
rounds 300+ 3934 against 3523, champion-games of 50+ run-outs 832 against 527. 222 reverted, 221 kept. A/B 221 alone (`astraeus-m5a`) against m4,
the same way: 50.4% of 1676 (48.0-52.7); out-of-fuel turns 6453 against 6658 (5543 against 5718 without the
gen-shared-gems maps), rounds 300+ 3432 against 3569, champion-games of 50+ run-outs 486 against 427.
Frozen: `bots/variants/astraeus-m5` (221-222), `bots/variants/astraeus-m5a` (221 alone, = main).

## 223: fuel round 6: `make_centre` runs one uncapped field search (astraeus, 2026-10-29)

Fuel only, byte-identical at 100M. `make_centre` doubled a capped field search until one finished, with no fuel
check between tries, so the failed tries were waste: one uncapped `make_field` gives the same field and
`max_field_layers`, and the cap is doubled afterwards to where the tries would have left it. Labyrinth first-approach
turns -20k to -25k.

## 224: fuel round 6: a failed route search asked again reuses its labels (astraeus, 2026-10-29)

Fuel only, byte-identical at 100M. A blocked walk asks `know_failure` for the same goals several ways (the guarded
search after the bare one when the guard walls nothing new, the field route after the attack tiles). `Pathing`
keeps the last failed search (`failed_`: goals, walls, tile, cap, layers); the same goals, walls and tile at a cap no
higher, or any cap once it ran dry below its own, label the same tiles, so its labels are reused. A lower cap reads
them through `route_label`, which hides labels past the current cap. Maze turns over 100k -2.4%.

## 225: fuel round 6: strike-search reads skipped where unused (astraeus, 2026-10-29)

Fuel only, byte-identical at 100M. `read_geometry` builds the dash-path blockers (`pass_`) only on a turn that can
dash (grow's dash nodes are the only reader). `strike_possible`'s unseen-threat pass asks `threats_at` with
`unseen_only`, which skips the visible enemies whose blows built a Reach only to be discarded. Turns over 100k
-1..-1.3%.

## 226: fuel round 6: the farm loop's stop while banking (astraeus, 2026-10-29)

Fuel only, byte-identical at 100M. CHANGES 175's nearest-order stop now also holds while banking a bag (TODO item 1):
the trip is at least the steps less `bank_now`, and a skipped group must also stay below the larger of the best and
`from_altar_value` through its cycle from the altar (altar walk + capture), as both only rise. Built inline it cost
+0.18% on the wide set (`farm_turn`'s flattened codegen), so later turns' banking calls go to an out-of-line
`farm_turn<false, true>` past `pick_up`, and the usual instance compiles with `banks_bag` false. `dash_kind`'s static
moved to `farm_dash_kind<opening>`, shared by both instances. Many-group set turns over 100k -4.7%; wide and OOF set
total +0.01-0.02%.

Fuel bench at 100M, 223-226 against frozen m5a (against 8ec2c4d in brackets): wide set 52/52 identical, total -0.04%
(-1.38%), mean 50238 -> 50220 (50923), p99 104276 -> 103911 (106866), over 100k 3198 -> 3145 (3615); OOF set 32/32
identical, total -0.07% (-3.24%), mean 60533 -> 60491 (62520), p99 132391 -> 131618 (147280), over 100k 8811 ->
8687 (11851). A/B 223-226 (`astraeus-m6`) against `bots/variants/astraeus-m5a`, own drafts, real budget: 50.3% of 1676
(47.9-52.7) on ladder and fresh-82801/2/3; out-of-fuel turns 6069 against 6366 (-4.7%; 5393 against 5693 without
the gen-shared-gems maps). Kept. Frozen as `bots/variants/astraeus-m6` (= main).

## 227: fuel round 7: `rank_turns` copies this round's order into next round's when the keys agree (astraeus, 2026-10-29)

Fuel only, byte-identical at 100M. Passes 0 and 1 (this round's keys) note whether every member's key equals its
`next_priority` (allies compared above `priority_payload_bits`, as CHANGES 221 argues: the rank bits alone set their
order). Passes 2 and 3 then copy `turn_order_` and set `next_rank` to `rank`: the comparator (key, then index) is a
strict total order, so the sort's result never depends on the order it starts from.

## 228: fuel round 7: a settled camp reuses last round's in-view members (astraeus, 2026-10-29)

Fuel only, byte-identical at 100M. `update_camps` counts changes of its camp-tile view (`camp_view_`).
`camp_settled` keeps its last settling's round, version, view count and in-view member mask; settled in round - 1
with the same view and version, the same members are in view, each with `health_round` set to round - 1 then (only
`restore`, which bumps the version, or `update_camp` in that same round, which writes round - 1, write it since).
`CampBelief` gets an empty constructor so `camps.resize` no longer zeroes it first; every older field has a default
member initialiser and the three new ones are read only once `settled_round` (initialised -1) is.

Fuel bench at 100M, 227-228 against frozen m6: wide set 52/52 identical, total -0.35%, mean 50220 -> 50043, p99
103911 -> 103647, over 100k 3145 -> 3121; OOF set 32/32 identical, total -0.47%, mean 60491 -> 60209, p99 131618 ->
131315, over 100k 8687 -> 8557. A/B 227-228 (`astraeus-m7`) against `bots/variants/astraeus-m6`, own drafts, real
budget: 50.1% of 1676 (47.7-52.5) on ladder and fresh-82801/2/3; out-of-fuel turns 6098 against 6157 (-1.0%; 5224
against 5254 without the gen-shared-gems maps). Kept. Frozen as `bots/variants/astraeus-m7` (= main).

## 229: fuel phase 2: `warm_centres` one capped search a try, emblem families from the item counts (astraeus, 2026-10-29)

Fuel only, byte-identical at 100M. `grow_centre` takes the queue's fuel floor and doubles its cap as far as
`fuel_ok(floor + search_cost_estimate(2 * cap))` allows, then runs one capped field: a field that completes within a
cap is the same at any larger cap and sets `max_field_layers` the same, so the end state is the doubling loop's, without
its thrown-away tries (each search stays gated on its own estimate). `World::update` reads the passive families plus
Skirmish and Monster straight from `counts.ptr()` instead of eight checked `has_family` lookups (~110 a visible champion
update); Collectors owners still go through `dealt_with`, so the floats are unchanged. `owns()` is gone.

Fuel bench at 100M against m7: wide 52/52 identical, total -0.12%, mean 50043 -> 49985, p99 103647 -> 103559, over
100k 3121 -> 3105; OOF set 32/32 identical, total -0.17%, mean 60209 -> 60107, p99 131315 -> 131171, over 100k 8557
-> 8502. Real-budget OOF set (32 games, indicative): out-of-fuel turns 1939 -> 1767, shortcuts 32033 -> 30911. Not
A/B'd. Also `tools/fuel/simprof` (a per-turn fight-simulation profiler).

## 230: a first decision that runs out finishes in round 2 (astraeus, 2026-10-29)

Behaviour change at the real budget only; identical at 100M (+15 fuel in round 1). CHANGES 217's late finish now
covers round 1: `late` starts true in main.cc, so a round-1 decision that runs out finishes in round 2 on beliefs a
round old instead of being abandoned and replayed. On ~100-group maps round 1's mandatory work is ~265-320k against
200k, so it always ran out, and the round-2 replay (a normal second turn costs 157-175k there) usually ran out too;
the abandoned tail itself cost 67-77k for non-dashers (no stale check after the farm loop). Real budget, many-group set
(6 maps, own drafts, both sides, against 8ec2c4d): out-of-fuel turns 222 -> 177, rounds 1-10 113 -> 73, round 2 53 ->
0; every round-1 run-out now acts by round 3 (25 in round 2). OOF set 1977 -> 1954. Not yet A/B'd: run
`py tools/ab.py astraeus variants/astraeus-m7 --suites ladder,maps/fresh-82801,maps/fresh-82802,maps/fresh-82803
--no-test-draft` (m7 = before 229-230) before relying on it. Designs weighed for making round 1 fit are in
`draft-compute/first-turn.md`.

## 231: no forced emblems (astraeus, 2026-10-29)

`best_emblem` drops every hard-coded emblem bb73f75 brought back from v61 (never A/B'd on this base): Prism's
Prospector on cluster maps; off 3 picks Hunter for Vendetta and Heart of Ruin and Prospector for Marcella where
clusters lie on our walk; on 3 picks Prospector on cluster maps and Tavi's Prospector then Hunter. Every champion
chooses by the model; Monster stays a `best_stat` candidate for everyone on 3 picks. Against c6423d3, own drafts:
52.8% of 1164 (50.0-55.7; ladder 52.1, gen 53.7, gen-s1 52.1) and 53.3% of 512 on the fresh suite
`maps/fresh-102901` (49.0-57.6), out-of-fuel turns level.

## 232: learned emblems from the emblem lab; gold priced 1.5x (astraeus, 2026-10-29)

`best_emblem` is the old chooser (`current_emblem`) except at a new emblem `buy_shards` starts: there
`economy/emblem_table.h` (`tools/emblab/policy.py`, from the lab's 172k-game fit) names an arm per pick count,
champion type and count of emblems owned, where its gain over the old choice has a bootstrap 10th percentile above 0
(62 of 156 cells; none for a first emblem but 5-pick Prism and Willow, Jungle-Health). A learned emblem is priced by
pinning it in `begun_emblem`, which now finishes any begun emblem; one whose passive is already owned falls back.
`params::gold_price_scale` 1.5 scales `prices().per_gold`, as in every lab game. Against 1c0d627 (own drafts), each
~2,544 games over ladder, gen, gen-s1 and the held-out fall-holdout, fresh-2918, fresh-2934: table + 1.5x 52.0%
(53.0 / 51.2); table against 1.5x alone 52.0% (51.2 / 52.7); table + 1.0x 50.8%; 1.5x alone 49.6%. Out-of-fuel turns
level.

## 233: emblem table from the round-2 lab, selected on held-out outcomes (astraeus, 2026-10-30)

`economy/emblem_table.h` is now `learned_arm[picks - 3][type][ordinal < 12]` (`tools/emblab/candidate.py --flat`
from `replays/emblab/r2/dmodel-dr.policy2.json`, class 0, z 2); `shop.cc` is unchanged. Round 2 (800k games from
8fad72c, arms drawn in the game with logged propensities) scored every reached decision doubly robustly; per (pick
count, type, ordinal) the arm (or the current logic) that beat the base by 2 standard errors on the other four folds
replaced it: 222 cells, ~42% of decisions. Cross-fitted gain +0.08 +- 0.03 win points per decision. Against 8fad72c,
own drafts, on fresh suites no lab or selection used: 53.0% of 10,240 (fresh-5021..5040; the same decisions with the
lookup keyed by the current logic's pick) and 52.3% of 10,240 (fresh-5041..5060, this table). Out-of-fuel turns ~5%
more (28,410 against 26,950), from the different emblems rather than the lookup. Against the old chooser (1c0d627):
55.0% of 10,240 (fresh-5061..5080; 54.0-55.9), out-of-fuel turns 28,836 against 26,550.

## 234: drafts from the draft2 lab's model (astraeus, 2026-10-30)

`draft/draft_model.h` is now `model.mjs cpp --lab replays/draftlab/draft2-noctr`: the draft2 lab (590,711 self-play
games from 26d273e on ~50k regenerated maps, explore-heavy, Stellar out of random drafts; `tools/draftlab/README.md`)
refitted without counter terms. Per pick count, champion x 19 map features + pair synergy, penalised toward a pooled
fit; cv log loss 0.6217 (night1 0.6326). Against 26d273e, own drafts, on fresh-6177..6196 (held out of the lab):
51.9% of 10,240 (50.9-52.9); out-of-fuel turns ~10% more (26,129 against 23,664). `model_team` also takes our picks
and the opponent's revealed ones for counter-aware drafting (`model.mjs cpp --counters`: re-ranked each draft turn
from team scores cached in round 0), off in this header: with draft2's counters it scored 48.4% of 10,240 against
this and 50.0% against 26d273e. Its first version re-ranked every team on the later draft turns (60-90k fuel) and
missed picks on 5-pick maps, which made the rest of the draft random (40.7% against this). `write_leads` writes leads
only for bodies finished for the current expected team (no change without counters).

## 235-240: the macro-4 changes (astraeus, 2026-10-30)

Against ef8f0b8 (`bots/variants/astraeus-ef8f0b8`), own drafts, unlimited fuel, on ladder + gen + gen-s1 +
fresh-6051..6066 (9,356 games) unless noted; each number is the cumulative bot. Notes and the analysis behind them:
[MACRO-NOTES.md](MACRO-NOTES.md); EXPERIMENTS "Macro overhaul, macro-4".

235. **Threat-aware recall line** (`recall_line`, combat/fight.cc): the line is 0.18 of max health
   (`safe_recall_health_fraction`) while no visible enemy is within 12 and Safety sees no credible hit within
   `threat_radius` 6, else 0.35. `want_home`'s low test, farm's spare health and Willow-Prism's recovery use it; the
   draft keeps 0.35 (`draft_recall_health_fraction`). 53.3%.
236. **Comms without enemy sightings; a claim field per ally** (model/comms.cc): sightings made teammates give way
   to enemies they could not see (Safety's pack zone counts sightings dated this round); every ally's claim is in
   its own field, the capture record in its own slot. 55.0% (no sightings alone: 55.3%).
237. **Walking out of camp fire** (combat/fight.cc `camp_exit_field`, `flee_camps`, `camp_trapped`,
   `Memory::camp_fled`): the walk out of camp reach by walking distance, not Chebyshev (it oscillated in reach by
   holes and walls); leave while health covers the hits along it plus one; home until health recovers. Camp deaths
   halved. 55.9%.
238. **Recall out to farm** (hermes's prototype, ported): empty-handed, farm prices reaching a group by way of
   spawn (recall, the walk out) with the stop's heal and emblem credited as HomeTrip does, and `continue_recall`
   keeps the recall while it still lands sooner. 56.3%.
239. **Giving way to packs less**: pack zone radius 5 (was max reach + 1 = 7), home and hurt retreat ratios 3.0 and
   3.5 (were 2.0 and 2.5). 58.3%.
240. **Giving way less, continued**: `pursuit_steps` 2 (was 3), `hurt_health_fraction` 0.35 (was 0.5), `brake_bag`
   25 (was 11). 59.4% (58.4-60.4).

## 241: max_wait 3; macro-4 shipped (astraeus, 2026-10-30)

astraeus is macro-4's bot (235-240, branch `macro-4`, frozen `bots/variants/astraeus-67cad24`) with one change.
At normal fuel, own drafts, 10,240 games each, macro-4 read 59.9% against ef8f0b8 (fresh-7021..7040), 83.3% against
hyperion and 66.4% against 54254fb (fresh-7001..7020). The macro-1 to macro-5 results are in EXPERIMENTS "Macro
overhaul, macro-4" and "Macro merge, macro-5".

241. **`max_wait` 3** (was 5): farm walks to a group still respawning on arrival only if it is back within 3
   rounds; the same bound for a recall out to farm. The merge (macro-5) read 0 at 52.3% of 9,356 dev games
   against 5, but 50.0% of 4,096 held-out; 3 was not A/B'd.
