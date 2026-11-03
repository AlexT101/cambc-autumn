# hyperion change log

What is in hyperion and astraeus and why, oldest first. Entry numbers are stable because commits and research notes
cite them. Missing numbers are fuel-only work, bug fixes, cleanups, superseded and reverted changes, dropped in the
2026-10-22 and 2026-11-02 trims: the untrimmed logs are `git show 1d5ddf0:research/hyperion/CHANGES.md` (to 81) and
`git show a8b0b5c6:research/hyperion/CHANGES.md` (to 274).

- hyperion was named hecate until 2026-10-21. `bots/hecate` was items 1-31 and `bots/baselines/hyperion-v1` was
  items 1-81; both were deleted 2026-11-02 (`./copybot -r cde47ec6 hecate variants/hecate` restores one).
  `bots/baselines/v37` is ladder submission v37, the teammate's Khaos line after v36.
- Results are win rates against the bot before the change, all maps from both sides at the real fuel budget, unless
  noted. 1094-1164 games is ladder + `maps/gen` + `maps/gen-s1`; earlier entries used smaller suites, later ones
  10,240-game fresh suites. "Own drafts" means each bot on its own draft.

## 1-31: the reference bot (hecate, 2026-10-17..21)

hecate began as nemesis 2dba924; results up to 6 are against nemesis.

1. Monolith sieges: a ranged caster with no melee ally next to the Monolith casts from range 4, out of reach. Camp
   stuns are worth the member's Strength when a visible ally is in its reach, on Monolith groups only (elsewhere they
   cost ~2.5%). Monolith-only maps 70.7%.
2. Shared-gem maps (every gem source a big group or a Monolith): `kite()` replaces siege (stand within 4 of the
   block's hitting monsters but out of their reach, casters cast on cooldown, nearest 3 capture, contest an enemy
   hold), and spell users build Focus and skip Jungle. Shared-gem maps 77.3%.
3. A capture holder hits other harmless or already-awake groups in reach; a melee champion whose hit clears a group
   steps onto it the same turn. 55.6%.
5. Death avoidance: `step_guard()` keeps pathing off tiles where want_home would make us leave at once (fight lost,
   lethal, a Cassi/Issac body falls); `threat_strike()` gives an enemy with two turns before our next one more step of
   reach or a second attack; a lost pursuit sends us home (now `Safety::stand`, 66). Deaths ~-29%; 60.0%.
6. `contest_capture()`: step onto a cleared group of contest_gems 40+ in sight that the enemy holds, if reachable
   before it pays. 60.3% vs 59.0%.
10. Cassi and Issac: basic attacks pick the pair with the weakest body, and damage counts only once it takes a body
    below its partner (`useful_damage`; changed by 271); Cassi farms gold (gold_farmer_weight 4). Level.
11. `tribute_safe()` judges the next tribute_window (6) turns, not the whole channel; siege() and kite() walk with
    `step_towards_funded`. 52.3%.
14. Farm clears with spells from outside the camps' reach (`spell_clear`) and first picks up a cleared group in sight
    (`pick_up`, one taker per group). 51.0%.
15. The 2026-10-19 overnight session (58.0% vs hecate-v2): carriers chased when the bag can be intercepted
    (`intercept_steps`), `stop_game_ender`, contesting any gem capture; `Reach` (enemy movement over open tiles and
    dashes, attacks needing sight); emblems by measured value; banking by our measured tribute rate (`closing()`);
    passing hits only on harmless groups, ones an ally clears or (melee) awake ones; the lighter bag yields in an ally
    corridor deadlock. Its strike planner was replaced by 37.
18. A stunned turn runs the whole decision path (only the refused recall attempt is skipped). Skipping it was
    byte-identical locally but went 26-49 against 30-45 in ladder scrims vs the top 5.
21. From koi: a farm cycle is worth `worth / (cycle (1 + cycle / H))`, H = 100 x max(1, longer side / 50), on every
    farm value including bank-then-farm (discounting one side only made carriers bank early); `step_towards` searches
    to here + 6 x max_detour round live camps when the funded search and descent fail; an enemy on a cleared group
    counts its gems as its bag in `prey()`. 51.9%.
23. Camp reach from the camp designs (wolf 3, elk and golem 4, Monolith 5) everywhere a monster's reach is used. 54.3%.
24. Gem limits for the week 2 rewards: big_gems 55, chain_bag_limit 30, brake_bag 11. 52.8%. Since 26, big_gems only
    picks the maps that are kited.
25. Heart of Ruin played and modelled: its dash landing priced in the planner, enemy casts and camp casts; the
    missing-health passive in our damage and kill checks; enemy landings in Strike, Reach and the fight kit; active
    shields counted as health. 70.8% in the HoR-draft mirror, level in the normal-draft mirror.
26. Big non-Monolith groups are not sieged off shared-gem maps (corridors' lane groups pulled the whole team), and
    `holders()` splits a capture only until each share's tribute fits tribute_window turns. 54.7%.
28. Teleport crystals to altars no walk reaches (`StaticMap::hops`); a crystal is bought only once a hop would have
    won. 52.2%.
29. Dashers cross one-tile hole and altar lines (`StaticMap::crossable`, `dash_across`); walks from spawn shorten
    51-60% on fracture, concentrated-wealth and gold-rush. 52.0%.
30. Week 2 draft ([DRAFT.md](DRAFT.md)): Heart of Ruin, Marcella, Vesper, Ryth, Stellar; 69.3% vs the previous draft on
    a fresh suite. Superseded by 82's draft.
31. Monsters sleep one by one: a group is awake while any striker is, and strikers read asleep stay asleep inside an
    awake group until hit; danger counts them only while another champion is within 4. Level.

## 33-59: 2026-10-21/22

33. The periodic off-bush ward and the rally deleted; `World::track` counts an unseen enemy's turn this round
    whatever its modelled order. 50.3%.
35. Sealed altars: `AltarAccess` (tribute tiles a walk from spawn reaches with live camps as walls) and `altar_usable`
    (believed-awake fire over tribute_turns(bag) below the carrier's health). `bankable_bag` farms a bag no altar is
    usable for as if empty, and while the team's largest bag has none, the groups sealing the altars are siege
    candidates. 49.0%.
36. Farm always evaluates; `heal_rounds` prices every heal trip; Safety's camp hits carry our Jungle and Durability;
    plus fixes. 54.5%, fresh seed 59.4%.
37. Strike search ([STRIKE-SEARCH.md](STRIKE-SEARCH.md)): `plan.cpp` searches every legal order of moves, dashes and
    strikes, camps as targets; a move only when a strike follows it, no landing that wakes a sleeping striker. 52.6%
    (582), 55.2% at 100M.
38. An enemy Varg's splash in Reach and Strike. 51.0%.
40. Farming stage 1: one heal price (`heal_rounds`), one `HomeTrip` price for every trip home, `prices()` for the next
    emblem's gain and gold in gems, `holders()` for cleared groups. 50.0%.
42. The strike search takes heal and shield as options; decide and act() skip their own heal and shield on turns the
    search priced exactly. 50.0%.
43. Killed and (one-turn) stunned enemies leave the strike search's end-tile danger. 48.9%, 51.0% at 100M.
44. Main stat by counted use: Focus when the counted casts' Focus gain beats the counted attacks' Strength gain; a begun
    emblem is finished first. 56.4%.
46. Turn-start ward, placed right after continue_recall cancels our recall (ward and recall share one channel), from
    bush clusters already found. 50.7%.
47. The ward moves only to a cluster with strictly more tiles within ability_range of here plus of the work tile. 50.6%.
48. Fights simulate 17 own turns (2 x cooldown + 1) instead of 24, with exact early ends. 49.8%.
49. Camp flight prices each step by the camp hits still to come before leaving every awake camp's reach (priced by
    one step's damage, steps tied and champions circled Elks and Golems). 49.9%; camp deaths 1 vs 7 on 4 games.
50. A carrier's step is the farm step (`farm_step_value`), so walk-blocking casts fire while carrying (Stellar's nuke
    never did); `cast_at_enemies` takes the walk's worth. 52.1%.
56. After the goal, `strike_after` runs the strike search again from where the goal left us while a hit is possible
    (Marcella's armed stun, Vendetta's refresh, Varg's splash count after the goal).
58. The strike search's moves may pass guarded tiles: step_guard drops end tiles only. 48.9%, kept as logical.
59. A turn that ran out of fuel and resumed next round is abandoned (`StaleTurn`) and the round replayed (see 217 and
    230 for when it finishes late instead). Not A/B'd.

## 66-81: 2026-10-22

66. want_home asks one fight: `Safety::stand()` replaces pursuit and visible_threat (enemies who can strike first,
    visible walkers joining, camps). 52.2%.
76. The strike search grows at most 24 nodes (binds on 0.45% of searches). 49.7%.
81. On turns the strike search ran, farm skips its evaluation and walks on to last turn's choice (or banks). 53.7%.

## 82: Khaos's changes (2026-10-22)

A teammate's bots/khaos_v26 (hyperion plus ~1.2k lines) merged with hyperion's 40 later commits. 61.5%, each on its
own draft; draft and play were not separated. Several parts copy a "teacher" bot's observed behaviour, with fitted
constants.

- Draft: on 4-5 pick maps Prism, Vesper Vale, Marcella, Vendetta or Ryth, Heart of Ruin (Vendetta when camps average
  over 10/3 members a group); `draft_preference` starts Prism, Vesper Vale, Heart of Ruin, Marcella (3-pick maps).
- Turn order: Prism, Vesper Vale, Ryth, Vendetta, Marcella and Heart of Ruin skip the priority bands: 14 + floor(10 x
  danger) when danger > 0 (the larger of our best strike over an enemy's health + shield and theirs over ours), else
  an idle value by role and health. Other champions keep the bands (until 88); the split ends with 212.
- Prism keeps its gems (`retaining_gems`) and takes captures (`prism_capture_holder`; allies `yield_capture`). It
  shops the affordable shards of the next emblem when they plus the heal outweigh the trip home; emblem choice for
  gem_focus prices Monster and Home too, and the shared upkeep model now prices them for everyone.
- Vesper Vale dashes onto a gold group a higher-id Heart of Ruin holds alone the round its claim clears
  (`take_capture_handoff`).
- Camp casts: Prism casts on the approach to an awake group (`cast_at_camp_on_approach`); after the basic attack, a
  cast that finishes a group's last visible member needs no minimum value.
- Farm: `prefer_partial` (a ranged farmer whose hit would wake a sleeping group hits a damaged harmless cluster
  instead); crew work counts a claimed ally's damage only from its earliest arrival (`work_arrival`).
- Movement: equally short first steps go nearest the target group's centre; after a travel dash farm walks on down that
  dash's field.
- Kiting with ground casters: stations are tiles from which a cast reaches a striking member;
  `kite_productive_action` steps or fires from inside a monster's reach when two turns' damage outweighs the heal time.
- Chase: `prey` asks `Safety::chase_trade` (allies that cannot hit next turn arrive a turn late).
- Strike search: Prism gets the walk alone as a terminal leaf (every ranged champion since 209).

## 84-86: the 2026-10-22 audit

84. Enemies' Durability emblems (`ChampionBelief::taken`, 0.9 with one) count in every basic-attack kill test.
86. Judgment calls (54.9%):
    - `game_ender` contests a winning tribute next to the enemy spawn too (a stun or a lock cancels it whatever
      healing).
    - `closing()` prices a bag with no walk to an altar as `recall_turns` plus the walk from our spawn (was 0).
    - Camp ground casts and Heart of Ruin landings stay off tracked unseen Rens whose retaliation would kill us.

## 88: one turn-order scale for every champion (2026-10-22)

Champions outside the teacher six take idle, dead and danger priorities from `teacher_priority::priority` (idle up
to 12, dead 13, danger 14..23); before, any of them with an enemy within 8 outranked a teacher in top danger. Protect
(10000+) and kill (20000+) bids stay above, for non-teacher champions only. 51.3%, level; only test drafts change
(our own draft is all teacher champions).

## 89: enemies revealed by our own move (2026-10-22)

The strike search after moving, farm's post-walk `strike_enemy` and Safety read only the enemies seen at turn start, so
a walk revealing one (1.6% of turns) fell through to the camp hit. Vision is now re-read and Safety rebuilt
(`see_revealed`) after farm's walk, after the strike plan in `decide()`, and in `act()` before `strike_after`. 51.4%.

## 90: enemy ward sight per owner, bushes included (2026-10-22)

`Reach` credits an enemy only with its own ward's sight (vision.personal), from the engine's mask (`sdk_ward_vision`).
Before, every visible enemy ward's walls-only shadowcast counted for every enemy. 50.8%.

## 91: Prism's camp stun on another harmless group (2026-10-22)

From v37. After its basic attack at a harmless group, Prism's stun that would deal less than its full damage to what
is left goes to a visible member of another live harmless group within range, if that takes more. 50.7%.

## 92: long winning-bag tributes wait for a safe window (2026-10-23)

From the v38 ladder replays (26 deaths and ~25k gems handed over in 19 games, mostly 01boss_battle). Level locally:
self-play rarely builds bags that big.

- `any_risk` takes a winning bag's tribute at any risk only when its channel is `tribute_window` (6) turns or fewer;
  a longer one goes through `tribute_safe` like any bag.
- `tribute_ok` never starts or keeps a channel that cannot finish by round 2000.

## 95: an enemy's second turn counts what comes ready by then (2026-10-23)

From v38's ladder deaths (203, mostly one-cast Marcella kills). An enemy acting twice before our turn checks
readiness at `turn_round + 1` for its walk-then-act moves, and has dash tiles if its dash is ready on either turn
(`Reach::build`, `threat_strike`): one cast across both turns, no two-slot chaining. 50.1%; deaths -2%, to Marcella -6%.

## 97: a sure kill before retreating (2026-10-23)

From v38's ladder replays (119 retreat turns in 90 games walked away from a one-hit kill). 50.4%.

- `retreat()` first attacks a visible enemy in range that one basic attack kills (Ren's retaliation guarded). A
  ranged champion, whose attack spends the walk, takes it only where nothing else can hit its tile next turn or a
  ready dash still lands out of every reach.
- Melee: a kill one step off waits for the step, and an attack still unspent after the step is used on an enemy.

## 98: an unseen bush is not cover from an enemy whose ward we do not see (2026-10-23)

From v38's ladder replays (196 deaths on bush tiles whose cluster held an enemy ward we had not seen). When we do not
see an enemy's ward, a bush tile we cannot see counts as seen by that enemy from anywhere, since a ward hidden in the
cluster sees all of it. 50.3%; deaths on stepping into a bush 63 vs 81.

Cumulative (2026-10-23): 92-99 against `bots/baselines/v37`, own drafts, 57.2% of 1104, where v38 read 54.8%.

## 101: Treasure emblem first (2026-10-23)

From v38's ladder games: the opponents' extra gold was almost all Treasure (+16.2% on base capture gold against our
+1.6%); 16 of 18 top teams used it and we never bought it. Until a champion owns a Treasure emblem it builds
Treasure, in the stat the emblem model would pick; Prism's Focus build is unchanged. 52.5%, fresh suite 52.7%;
against v37 59.1%. (Forcing ended with 183.)

## 102: 4-pick maps draft Heart of Ruin over Ryth/Vendetta (2026-10-23)

On the ladder we won 63% of 3-pick and 60% of 5-pick games but 43% of 4-pick games, the only count whose draft had no
Heart of Ruin. With 4 picks the fourth pick is now Heart of Ruin, swapped with the Ryth/Vendetta role. Own drafts:
53.0%, 4-pick maps 60.0% of 330; fresh suite 54.1%.

## 103: Bruiser emblems in the emblem model (2026-10-23)

From v38's ladder games: the opponents' extra health was Bruiser (7 shards' stats for 5), which `best_emblem` never
priced. It now prices Bruiser in the main stat and in Health (Prism: Health and Focus); a begun Bruiser is finished
first, and a completed emblem gets its extra stats in the model. 56.2%, fresh suite 54.5%. With 101-103, against v37
on own drafts: ~65% of 1616.

## 104: farm values gold as paid to us, with our bonuses (2026-10-23)

Farm priced a group's base gold, though our share is paid with our bonuses (Treasure, Vesper Vale's +33%). `pick_up`
and the gold that completes an emblem on the way home now count them. 51.3%; against v37 67.3%. Weighting gold more
lost (3x 46.9%): the value model already prices gold by what the next emblem saves, and gems are the score.

Cumulative (2026-10-23): 92-104 against v38, test drafts (so without 102's draft): 61.1% of 1104.

## 106: enemy teleports land at their destination (2026-10-23)

A seen enemy teleport lands at its turn start in `channel_end_round` and acts that turn; a stun or kill by us leaves
it in place. Before, only tracking widened its `possible` to tiles within 3. Not A/B'd on its own (rare locally).

- Safety: it threatens nothing if it lands after our next turn, otherwise strikes from the landing tile.
- The fight search leaves it out until it lands; `prey` skips one we can't reach before it lands, and
  `intercept_steps` stops it by stun or hit in time or races its walk from the landing.
- A stun values cancelling a teleport like cancelling a recall; turn order offers to act first to stun one about to
  land.

## 108: audit judgment calls (2026-10-23)

Each A/B'd alone (all level), then together (50.6%):
- Unseen threats measure range by Chebyshev distance from `possible`, as Strike does: ground casts and ranged attacks
  across a wall line count.
- A carrier drops a hold only when waiting for the payout would leave too little time to bank the bag and its share
  before the round limit, while banking now still fits (`holding_capture`).
- kite() stations for a unit-spell caster without a ground spell (Marcella) are tiles that see the monster within unit
  range.
- The strike search treats a target our own ward sees as attackable from any tile in range (`Search::ward_sees`).
- `can_act_before` trusts only enemy priorities that can no longer change this round.
- An ally hold on a group unseen last round is dated this round, the later possibility.

## 112: a retreat step out of every reach (2026-10-23)

When no step that keeps or shortens the walk home leaves every reach (camps included), `retreat_step` also takes one
that lengthens it and does. A step that only lowers the exposure stays excluded: a pursuer takes it back. 49.7%.

## 115: captures left to allies free to take them (astraeus, 2026-10-24)

`capture_taken` (siege and kite captures of a cleared big group) counts an ally not on its tiles as a holder only if
it is not bound elsewhere: tributing, on a kept recall, or claiming another group. 50.1%.

## 117: a hold yields to the damage it takes; respawning tiles left free (astraeus, 2026-10-24)

`want_home`'s low-health exemption for a capture hold lasts only while last round's health loss, repeated to the
payout (+1), stays below our health: camps hitting from out of sight and bush attackers never showed in the fight
sim. The approach to a respawning group drops the group's own tiles from its goals, since a group returns only once
its tiles are empty. 50.8%.

## 118: a retreat steps or dashes to a sure kill (astraeus, 2026-10-24)

`retreat` took a sure kill only from where we stood. It now also takes one from a tile a step away (melee only) or a
ready dash away, when nothing but the victim reaches that tile; the dash lands nearest our spawn. 50.2%.

## 119: a carrier on our own ground checks for pursuers (astraeus, 2026-10-24)

`want_home` skipped the pursuit steps for a healthy champion on our own ground. A kill takes the whole bag, so a carrier
of `brake_bag` or more now runs `stand(here, pursuit_steps)` there too. 51.4%; with 118, gems lost on death -5.4%.

## 120: joining an enemy Monolith siege (astraeus, 2026-10-24)

Off Monolith-only maps a live Monolith was a siege candidate only when it sealed the altars. An awake Monolith with a
visible enemy in its reach is now one too (`enemy_in_reach`), judged by its current health without the health-pool
check, since the nearest champion takes its hits. Against a proxy that sieges Monoliths everywhere, on mixed-Monolith
maps: 58.6% vs 55.2%; our Monolith captures 11 -> 33. Full suites 49.9%.

## 121: Willow takes no chase (astraeus, 2026-10-24)

`prey()` returns null for Willow: `want_home` sends it home whenever an enemy is likely to hit it, so a chase walked it
into reach only to leave the next turn (85% of its chases never landed a hit). Five-pick maps 49.5%, level.

## 122: enemies who walk into a fight join its verdict (astraeus, 2026-10-24)

When more enemies arrived than the fight sim counted, 9.3% of "won" verdicts died (1.4% otherwise).
`Safety::late(p, key)` lists the visible enemies outside a fight's key who walk into reach of p within
`pursuit_steps`, joining at their arrival.
- `want_home`: `stand()` takes them once a visible enemy hits us, even where pursuit is skipped: a fight already on
  draws them.
- `prey`: `chase_trade` at the target's tile takes them.
- 50.9%; fresh suite 52.1%.

## 123: a shop trip is priced by everything the gold buys (astraeus, 2026-10-24)

A trip was priced by the next emblem only, so a healthy champion that never died never went home: on the ladder our
Prism held 300+ gold for 100+ rounds in 138 of 299 games. `affordable_prefix` now prices the whole purchase as
`buy_shards` makes it. Non-Prism champions still need the next emblem affordable before going. 52.4%; fresh suite
50.6%. Prism's mean gold held 146 -> 95.

## 126: our winning bag no longer blocks interception (astraeus, 2026-10-24)

While our bag would win, `game_ender` and `continue_tribute` ignored the enemy's winning tribute. Now our tribute
waits for a stun or a lock only if theirs lands before our win (`win_lands`), unless a visible ally acting in time can
stop it alone (`ally_stops`); `game_ender` pursues only a tribute that lands first. 49.4%, level (rare locally).

## 127: a visible enemy's stun takes its next turn in Safety (astraeus, 2026-10-24)

A visible enemy's pending stun takes one turn from `turns_before_ours`; with none left before ours its threat strike is
empty, so per-tile damage, lethal, recall and tribute safety and the step guard ignore it. It still fights, arriving a
turn late as a stunned ally does. 51.1%.

## 128: a stun we cast is read mid-turn (astraeus, 2026-10-24)

`World::read_stuns` re-reads the stun after our own stunning cast, for visible enemies near us; if one changed, Safety
starts again. 50.5%.

## 133: a small bag chains past distant enemies, up to 45 gems (astraeus, 2026-10-24)

`may_chain` sent a bag home whenever any credible enemy was anywhere on the map (44% of our ladder bank trips; our
non-Prism tribute bags were about half the top teams'). It now refuses only for a credible enemy within `pursuit_steps`
of our reach, and `chain_bag_limit` is 45 (was 30). Kept on the ladder argument: locally fewer, bigger tributes but more
gems lost on death. 51.4%; fresh suite 49.2%.

## 134: 3-pick maps draft Marcella, Vendetta, Heart of Ruin (astraeus, 2026-10-24)

The draft is one table per pick count (`params::draft_three/four/five`). 3 picks: Marcella, Vendetta, HoR replaces
Prism, Vesper, HoR ([DRAFT.md](DRAFT.md#astraeus-draft-search-2026-10-24)). Against proxies of 8 top-10 teams on every
3-pick map: 63.7% vs 47.3% for the old draft; head to head on 3-pick maps 61.5%.

## 136: Marcella's tribute gold in farm worth (astraeus, 2026-10-24)

Marcella's farm worth counts her 2 gold per tributed gem. Since 140 (folded in here) it takes our gold bonus too, which
`probe-marcella-gold` showed the engine applies.

## 137: Vendetta's Treasure in Health (astraeus, 2026-10-24)

Vendetta's first emblem, Treasure, goes in Health instead of the model's stat (always Strength for Vendetta), as 74%
of ladder Vendettas build it. 3-pick maps 53.8%, fresh 54.1%.

## 138: Vendetta's Monster emblem (astraeus, 2026-10-24)

`best_emblem` offers Vendetta a Monster emblem in Strength, priced by the model like the others; camp kill tests count
the bonus. 3-pick maps 54.3% of 676.

## 139: crystal-only altars (astraeus, 2026-10-24)

With every altar behind a hole moat (repro map `crystalaltar`, [repro-maps/](repro-maps/)), every champion stood still
from about round 150, 0-0 at round 2000. Now `recall_to_bank` keeps the recall when walking reaches no altar, a hop is
wanted and we can buy a crystal; a bag only a crystal could bank counts as unbankable while we hold none and cannot buy
one, so we farm the gold first (only on maps with hops); and the crystal is bought before shards. That map now ends in a
1000-gem win at round 1506. Full suites 49.2%.

## 141: claims in the priority payload (astraeus, 2026-10-25)

The 8 shared bytes hold each record as one mixed-radix number sized from the map. Priorities carry an
order-preserving rank code and a 16-bit payload with the claim and the Prism/Willow support intents, so an ally in
sight always reads our current claim. 49.9%, kept as the base for vision changes.

## 142: special cases generalised (astraeus, 2026-10-25)

From an audit for literals standing in for rules and per-champion exceptions. All together 49.9% of 1616, level:
- A capture is finished while it pays before any enemy seen this round or last could walk into reach (was: none
  within 3 and payout within 2); camp casts and the camp reset are held while a visible enemy is within a step of our
  reach or of its own strike (`engagement_near`).
- A camp stun credits sparing any ally in the monster's reach (was Monolith only), and the Monolith-only floor for a
  damage-free stun is gone; any unit cast overkilling a
  harmless group retargets (was Prism's); approach casts for any ranged champion whose casts outreach its attack (was
  Prism); every champion's basic attack target takes the most value, kills first (was Varg only).
- A stun is worth the target's damage a turn (was 80), a stopped game-winning tribute the game's gems (was 5000), and
  the camp-cast floor is the cast's cooldown cost (`cast_cost`; was 50).
- A Monolith splits by the tribute window like any group (3 holders, was 2); any dasher paid more gold takes a
  one-holder gold capture from a higher-id ally paid less (was Vesper from Heart of Ruin).
- The pack zone's healthy ratio is gone: only hurt (2.5) or at home (2.0) does a pack send us back early.

## 143: hits short of a kill priced by kill progress (astraeus, 2026-10-25)

On the 2026-10-24 ladder we hit the lowest-hp enemy in range 64-65% of the time (top teams 78-91%). A hit short of a
kill was worth its damage whatever the target's health; now every hit is worth the fall in `kill_distance`: 0.4 x
health + (0.6 x full + life + bag) x sqrt(health / full) (`params::chip_value` 0.4). A kill from full health is worth
the same as before; chip damage counts ~0.8x at full health and ~1.3x at 20%. 52.4%, fresh suite 49.0%; deaths a game
4.77 vs 5.29.

## 144: a low Monolith burst on mixed maps; no siege heal trip once the group is cleared (astraeus, 2026-10-25)

On Monolith maps the top teams captured one in 53-55% of ladder games, we in 17%. A live Monolith whose known health
the team clears within `params::burst_rounds` (20) is now sieged too. `siege_heal_trip` no longer keeps a recall once
the group is cleared (in a smoke game all three recalled and the enemy took the winning capture). 50.5%, Monolith maps
53.0%; Monolith captures 208 vs 121. 143 and 144 were each A/B'd alone; together only smoke-tested.

## 145: camps in the way are breached (astraeus, 2026-10-25)

Static fields count camps as cleared, so a walk could end beside a live camp holding a 1-wide corridor and stand
there. `step_safely` now hits the weakest such member in reach (`breach`) when every step down the field is onto a live
camp, if we outlast the fire of its members that reach us for as many turns as the kill takes. With other stall
fixes: 50.5%; stalls of 300+ rounds 26 vs 35.

## 146: a contest needs only a hold's holders (astraeus, 2026-10-25)

`contesting()` held every ally on a contested group's tiles, anchored, so with both teams on a shared group nothing paid
(gen-shared-gems: 0-0 at round 2000). Allies that make `holders(G)` now man the contest and the rest farm and fight;
while contested, a contester's strike search may walk or dash to any of the group's tiles. 49.8%; shared-gem maps no
longer reach round 2000.

## 147: farm hops into crystal-only regions (astraeus, 2026-10-25)

Farm skipped any group no walk reaches, so walkers never left their region. `StaticMap::hops()` now also holds a hop
per walk region with a farmed group off our walk, within crystal range of it and not the enemy's region.
- Farm prices such a group by the walk to a source, the channel, the walk from the landing and a recall out when the
  region has no altar; from our spawn when a crystal must be bought.
- A farm hop lands only out of the strike of every visible enemy that could close in during the channel, else it is
  set aside for 16 rounds.
- 51.3%; teleport-access maps 54.4%, dash 62.5%.

145-147 together: 50.7%; against v44 58.2% (was 56.3%).

## 148: patch 2.0.0 rules (astraeus, 2026-10-25)

`champion_table` takes 2.0.0's stats; Monster is 1.15, Treasure 0.1. An enemy's Skirmish and Collectors emblems
multiply its `scale` in every fight estimate. A visible cleared group's `capture_state()` dates its hold. Not A/B'd.

## 149: owned 2.0.0 emblems in the model (astraeus, 2026-10-25)

Our Tribute counts in `tribute_turns`, our Capture in `capture_rounds`, Collectors in camp damage, Prospector in
capture shares and farm values, and an enemy's Tribute in interception timing. Nothing new bought yet.

## 157: the farm loop visits groups nearest last turn's choice first (astraeus, 2026-10-26)

`pick_up`'s farm loop visits last turn's choice, then the other groups by Chebyshev distance between centres, in place
of index order. A loop cut short has weighed the likeliest groups. 51.6%; 58-62% on maps of 40+ groups, though a fresh
many-group suite read 49.4% of 180. Ordering by
walking distance from the draft added nothing.

## 159: a ward plan in the draft (astraeus, 2026-10-26)

The draft picks one ward tile per work site (each camp group, then each altar) within placement range, scored by
enemy-standable tiles a champion at the site's centre cannot see. `place_ward` places the planned tile for our work
once within 2, keeps it while that work lasts, and otherwise falls back to the greedy bush ward (since 168, at the
turn end). 52.1%, fresh suite 52.5%; wards a champion a game 18 -> 28, surprise deaths -25%.

## 165: farm weighs groups by home_ground from the first turn (astraeus, 2026-10-26)

Groups weighed 1 until the warm-up's centre fields were ready, so early camp choice depended on fuel. `home_ground`
reads only the drafted spawn steps, so it is used from the first turn. 50.4%, kept as the logical rule.

## 172: crystal hops judge the channel's start and landing (astraeus, 2026-10-26)

A crystal's channel cannot be cancelled (a death there hands over the bag). `take_hop` starts a hop only where a tribute
of as many turns could start, and lands every hop out of the strike of each visible enemy that could close in during the
channel; a bag's last chance skips both. A refused bank hop waits on its source as at a watched altar, as many rounds as
the next way to an altar takes, then takes that way. 50.1%.

## 173: a clear's camp fire counts only the strikers that reach where we stand (astraeus, 2026-10-26)

`min_camp_damage` priced a clear as if every living member hit us every round. Now, while we kill a member, only the
living strikers that reach its stand tile hit us; the order stays deadliest first, so a wolf line's ends go before
its middle. 50.5%, fresh suite 50.4%.

## 180: allies in the fight sim join once a walk brings an enemy within their strike (astraeus, 2026-10-27)

`new_fight`, `stand` and `chase_trade` let every ally within 4 hit from turn 0. Each ally now arrives after the walk
until its strike reaches the nearest enemy (at once if any enemy is unseen, or the walk is one turn). 50.3%.

## 183: emblems chosen from measured income, no forced first emblem (astraeus, 2026-10-27)

Treasure was forced first (101). Unforced, the model was level with it, while forced Prospector first (54.4%) and
Capture first (53.3%) beat it. `best_emblem` now prices five passive emblems as the share of a farming turn saved:
- `Income` counts our gems, capture payouts, what Prospector would have added, base capture and kill gold and
  Tribute's cut turn ends; a prior from the map and ladder rates counts as 30 gems until our income outweighs it.
- `passive_saved`: Capture saves 2 hold rounds per payout, Tribute its cut turns, Prospector its extra gems plus their
  gold, Treasure 10% of base gold, Hunter 50 a kill. Gold is priced at the best stat emblem's saving per gold.
- A candidate is five shards in the main stat or Health plus its passive; a begun passive is finished first.
- First emblems: Prospector 51%, Treasure 19%. 61.1% against the old bot, 56.9% against Prospector first.

## 184: Prism prices the passive emblems under the same model (astraeus, 2026-10-27)

Prism opened Monster-Focus in ~60% of games; it now also weighs Capture, Prospector, Tribute and Hunter in Health or
Focus. Its first emblem became Prospector in 67% of games. 50.8%.

183 and 184 together: 62.4%, fresh suite 64.3%; 48 / 66 / 74% by the map's captures per gem (terciles).

## 186: a shopping trip counts the passives it completes; Prism offered Treasure (astraeus, 2026-10-27)

`affordable_prefix` priced the shards a trip buys by their stats only; each emblem it completes now adds its
`passive_saved`, so a trip is worth what `best_emblem` says. Prism's candidates include Treasure. 49.6%.

## 196: teleports onto dead camp tiles (astraeus, 2026-10-27)

A dead camp's tile is a legal landing (`probe-teleport-dead-camp`). `teleport_targets` adds the camp tiles in range of
groups believed cleared or respawning where vision shows no camp; `take_hop` prefers a landing off our farm choice's
tiles while it respawns. No new hops.

## 197: v61's retreat rework and draft (astraeus, 2026-10-28)

From v61 (`bots/baselines/v61`):
- Prism on a lethal tile with a step that takes no modelled damage or stun before our next turn takes it, nearest our
  spawn. A walk-excluding cast replaces it only if it kills the sole visible threat or stuns it before it acts.
  (Every champion since 208.)
- Heart of Ruin below the recall line with its dash ready keeps the dash to escape: only a landing that kills a
  visible enemy goes first, then the escape dash, then any other cast.
- Drafts: Vendetta in Vesper Vale's slot on 4 and 5 picks and in `draft_preference` (Cassi and Issac third); Vesper is
  never drafted on the table path.

52.9% (ladder 57.1%); out-of-fuel turns +17%.

## 198: drafts from the draft lab's model of the map (astraeus, 2026-10-28)

The draft measures the map's 19 features in C++ (`map_features.cc`, a port of `tools/draftlab/features.mjs`) and drafts
the best team for the map's pick count under the draft lab's model (`draft_model.h`, from `node tools/draftlab/model.mjs
cpp`), with no counter terms. `params::map_model_draft` switches it; off, and on test drafts, split maps (until 244) or
a failure, the old table draft. Vesper may be drafted on the model path. Maps the lab never played: 56.8% of 868;
standard suites, which it trained on, 57.9%.

## 201: shared-gem kites cast only where spells out-damage basic attacks (astraeus, 2026-10-28)

On shared-gem maps a melee champion takes kite ground stations, and `main_stat`'s forced Focus, only if its damage
spells a turn beat its basic attacks. Ryth now melees there instead of standing off to cast every 8 turns; Marcella
keeps her unit stations but loses the forced Focus. On forced drafts, 60 fresh shared-gem maps: 59.2% of 120. Not
confirmed on a second set, and no full-suite regression check.

## 206: stopping a game-winning tribute (astraeus, 2026-10-28)

- `game_ender` counts a walking enemy carrier when its walk to the nearest altar and channel land before our win.
- `intercept_steps` no longer takes reaching attack range as stopping a tribute or teleport (damage interrupts
  neither): a kill counts by the hits it takes after the walk into range, as do a stun and a lock.
- A stun that allows a walk first reaches a tile farther (Cassi 5, Heart of Ruin 4, Marcella 2) for interception; an
  altar lock is placed after the last step.
- A walking Cassi or Issac channels its own bag when it wins alone, else the longer of the two bodies'.

49.9%, level (its debug counters fired in 7% of games or fewer).

## 207: a kill's worth (astraeus, 2026-10-28)

A kill is worth the tribute it cancels (`kill_stops`; every gem of a game-winning one), which only a stun's worth
carried, so a stun that left a winning tributer alive outscored killing it. A stun counts only on a survivor.
`attack_target` and `best_hit` value hits by the strike search's `hit_worth` (kill distance, the bag) plus
`kill_stops`. 51.3%.

## 208: escapes and the mend turn (astraeus, 2026-10-28)

- 197's escape-walk rule (`escape_walk`) covers every champion with a walk-excluding cast at enemies: on a lethal tile
  with a safe step, only a unit cast that kills or stuns the sole threat in time takes the walk's place. After the
  walk, a cast that allows walking may follow (Cassi's stun).
- An escape's stun certifies on an enemy yet to act this round whose only turn before ours that is.
- Ren keeps its escape dash below the recall line as Heart of Ruin does: before a dash that clears, only a killing
  cast; otherwise the escape-walk rule, then any cast.
- `offer_escape` bids only when what lands whatever the order leaves us alive.
- The mend turn steps on spawn towards the next goal when no more exposed (`mend_step`); under camp fire it mends while
  it misses more than the camps take a round (before, it never mended under camp fire).
- A heal may target an ally seen only through the healer's ward (`probe-willow-heal-ward`).

55.1% (ladder 50.7%); out-of-fuel turns +5.5%. Kept without a fresh-suite confirmation.

## 209: walk-only leaves, Ryth's escape stun (astraeus, 2026-10-28)

- The strike search offers "walk, nothing else" as a terminal leaf to every ranged champion that can walk, not only
  Prism and Stellar: the others weighed a strike from here only against staying put. Willow's walk leaf can also heal.
- An escape certifies a ground stun (Ryth) as it does a unit cast, when the sole threat is visible, stunnable and has
  one turn before ours.

50.2% with a safety change since reverted; what is kept was not A/B'd without it.

## 212: one turn-order model for every champion (astraeus, 2026-10-28)

The "teacher" split from 82 is gone:
- Every champion bids for the kill and protect bands.
- `offer_channel` bids only when acting earlier can deny a cancel. A recall or teleport is worth `recall_value`
  without the bag: a cancel keeps the gems carried.
- `offer_heal` counts the ally's shield and the damage landing before the heal, and caps the heal at what health is
  left after those.
- Danger comes from Safety's `strike()` and live reads at our turn's end (current health and shields, stuns cast this
  turn, the next camp phase first, full health on our spawn).
- The idle order decides who absorbs a camp's tie hit: first those it leaves alive, gemless before carriers; then
  those it would kill, fewest gems first. No role table.

51.1% of 1676, level.

## 213: the goal after the strike search (astraeus, 2026-10-29)

- After a strike search that saw every enemy, chase only walks: the search already priced its dash, attacks and
  casts; `strike_after` hits from where the walk ends. With no walk left, chase gives way to the other branches.
- The ranged return after an attack is gone: with the walk spent, the goal keeps what the search cannot price (camp
  work, travel dashes).
- No travel dash across a wall with an enemy within `travel_dash_clearance` (until 274).

50.4% of 1676, level.

## 217: a turn after one that ran out finishes its decision late (astraeus, 2026-10-29)

A turn whose decision costs more than the budget (shared-gem livelocks) ran out, was abandoned, and the next round
replayed it and ran out again: one champion ran out 1745 rounds in a row and never acted. Now once a turn has not
finished in its own round, the next turn's decision is not abandoned if it runs out: it finishes in the round it
resumes in, as that round's turn. The first out-of-fuel turn of a streak still replays on fresh beliefs, so a streak
acts every other round on beliefs a round old. Comms writes nothing from a late turn. With a fuel change: 49.6% of
1676, out-of-fuel turns -15%.

## 230: a first decision that runs out finishes in round 2 (astraeus, 2026-10-29)

217's late finish covers round 1: on ~100-group maps round 1's mandatory work always ran out, and the round-2 replay
usually did too. Not A/B'd.

## 231: no forced emblems (astraeus, 2026-10-29)

`best_emblem` drops every hard-coded emblem brought back from v61 (Prospector on cluster maps for Prism and on 3
picks, Hunter for Vendetta and Heart of Ruin, Marcella's Prospector, Tavi's Prospector then Hunter): every champion
chooses by the model. Monster stays a candidate for everyone on 3 picks. 52.8%, fresh suite
53.3%.

## 232: learned emblems from the emblem lab; gold priced 1.5x (astraeus, 2026-10-29)

At a new emblem, `economy/emblem_table.h` (from `tools/emblab/policy.py`, the lab's 172k-game fit) names an arm per pick
count, champion type and emblems owned, where its gain over the old choice was reliably positive (62 of 156 cells).
`params::gold_price_scale` 1.5 scales `prices().per_gold`. Table + 1.5x 52.0% of ~2,544; table + 1.0x 50.8%; 1.5x alone
49.6%.

## 233: emblem table from the round-2 lab (astraeus, 2026-10-30)

`emblem_table.h` is now per (pick count, type, ordinal), from round 2 of the lab (800k games): per cell, the arm (or the
current logic) that beat the base by 2 standard errors on held-out folds; 222 cells, ~42% of decisions. 52.3% of 10,240
on an unused fresh suite (53.0% on another, with the lookup keyed by the current logic's pick); against the old chooser
55.0%. Out-of-fuel turns ~5% more.

## 234: drafts from the draft2 lab's model (astraeus, 2026-10-30)

`draft_model.h` is refitted on the draft2 lab (590k self-play games on ~50k maps), without counter terms. 51.9% of
10,240 on held-out suites; out-of-fuel turns ~10% more. Counter-aware drafting is built but off: with draft2's counters
it read 48.4% against this.

## 235-240: the macro-4 changes (astraeus, 2026-10-30)

Cumulative, at unlimited fuel, 9,356 games ([macro/macro-4.md](macro/macro-4.md)):

235. **Threat-aware recall line** (`recall_line`): 0.18 of max health while no visible enemy is within 12 and Safety
   sees no credible hit within 6, else 0.35. 53.3%.
236. **Comms without enemy sightings; a claim field per ally**: sightings made teammates give way to enemies they
   could not see. 55.0%.
237. **Walking out of camp fire** by walking distance, not Chebyshev (it oscillated in reach by holes and walls);
   leave while health covers the hits along it plus one; home until health recovers. Camp deaths halved. 55.9%.
238. **Recall out to farm**: empty-handed, farm prices reaching a group by way of spawn (recall, the walk out), with
   the stop's heal and emblem credited; `continue_recall` keeps the recall while it still lands sooner. 56.3%.
239. **Giving way to packs less**: pack zone radius 5 (was 7), home and hurt retreat ratios 3.0 and 3.5 (were 2.0 and
   2.5). 58.3%.
240. **Giving way less, continued**: `pursuit_steps` 2 (was 3), `hurt_health_fraction` 0.35 (was 0.5), `brake_bag`
   25 (was 11). 59.4%.

## 241: max_wait 3; macro-4 shipped (astraeus, 2026-10-30)

astraeus is macro-4's bot (235-240) with one change. At normal fuel macro-4 read 59.9% against the bot before it and
83.3% against hyperion.

241. **`max_wait` 3** (was 5): farm walks to a group still respawning on arrival only if it is back within 3 rounds;
   the same bound for a recall out to farm. 51.2% of 10,240.

## 243: kite needs a caster (astraeus, 2026-10-30)

On shared-gem maps kite() took every big group, but its stations only cast, so a team with no damage spell worth
kiting with stood guard forever (0 gems both sides). Without such an ally, live big groups go to farm; cleared ones
are still kite's to capture. With a pathing fix: 50.8%, level.

## 252: value-holder captures and takeovers, siege cover, ally recall feints (astraeus, 2026-10-31)

From the farming-macro branches (EXPERIMENTS "Farming macro, round 2"):
- **Value holder**: of the allies on or beside a cleared group, the one whose hold multiplies its reward holds it
  (Marcella's tribute gold on its gems, or a gold bonus on its gold), at one shared gold price so every ally names
  the same holder. The others step off only once it stands on a
  tile, so the hold never lapses. Prism's lone hold still comes first.
- **Takeover**: a free Marcella or gold-bonus champion walks onto an ally's counting hold when it arrives before the
  payout and the hold is worth more than its best farm cycle.
- **Siege cover**: the leave test counts only the members that would target us (an ally strictly nearer covers us).
  It counted every member in reach, so at a Monolith four of five full-health champions read too hurt to stay.
- **Ally recall feints**: every champion starts a recall at its turn end and cancels it next turn unless wanted, so
  allies count as recalling only on a recall kept through a turn start.

52.3% of 20,108.

## 256: crew economics (astraeus, 2026-10-31)

quill's farming refactor ([macro/quill.md](macro/quill.md)):
- **Trip-aware job cost**: a job's cycle adds the trips home its camp damage forces, against the health we spare
  (`crew_trip_risk` 0.6). Replaces the hard health filter: a strong group too costly alone is a team job.
- **Shared crew damage**: each camp hits the nearest champion in its reach, so a crew's damage goes to its tanks.
- **Operations** (`plan_crew`): a champion proposes a strong group valued with the crew it expects (claimers plus free
  allies within `crew_near_radius`, the whole team on round 1); allies join through farm's crew branch. A proposer
  alone after `crew_wait_rounds` bails out and bans the group for `crew_ban_rounds`. A crew we are in holds us at
  `crew_stickiness` over a single pull.
- **Monolith crews** on maps with other camps: crew-only operations for the whole team; members wait just out of
  reach until `mono_gather_share` of the crew's output has come (at most `mono_max_wait`). siege() keeps Monolith-only
  maps and seals.
- Shared-gem maps: kite()'s big group keeps the old pricing.

At the real budget, own drafts, with two small fixes, 20,480 games each on unused suites:

| Against | Win % | 95% CI | Out-of-fuel turns (cand / ref) |
|---|---|---|---|
| astraeus f33d8e6 (before 247) | 61.4 | 60.8-62.1 | 118.6k / 84.7k |
| astraeus 3938c0f | 74.9 | 74.3-75.5 | 124.1k / 120.0k |
| hyperion | 87.4 | 87.0-87.9 | 114.4k / 46.6k |

## 261: drafts from the draft3 lab's model, 23 features (astraeus, 2026-10-31)

`draft_model.h` is refitted on the draft3 lab (477k games on a 46k-map pool), no counters, with 23 map features
(draft2's 19 plus `dash_gain`, `spawn_ring`, `max_group`, `camp_altar`). 51.3% and 52.0% of 10,240 on unused suites.
Vendetta, Marcella, Prism and Heart of Ruin lead; 3 picks most often Vend Marc HoR, 4 picks Vend Cass Marc HoR.

## 264: middle-band pricing with smooth edges (astraeus, 2026-10-31)

(263 is a held fix on `fix/necks-gap`.) Farm weighs a group by its side of the map, `home_side`: d_enemy / (d_ally +
d_enemy) over the walks from the two spawns. A group between `mid_low_share` 0.35 and `own_ground_share` 0.6 is worth
up to `mid_exposure` 1.2 of itself, easing in by smoothstep over `mid_edge` 0.05 either side of each bound, on top of
`home_ground`. 51.4% of 20,480 (hard edges read the same within noise).

## 269: holds that outlast stay; the work's steps keep off tiles want_home would leave (astraeus, 2026-11-01)

In v66's ladder replays 73% of our capture resets were a healthy holder walking off on want_home (a lost `stand` or the
pack zone, even a round before payout).
- **Hold rule**: `hold_outlasts(p, rounds)` keeps a hold whose payout is `rounds` away when nothing can kill us there
  before our next turn, last round's loss repeated over rounds + 1 leaves us alive, and the enemies in sight and the
  camps cannot kill us idle within rounds + 1. It exempts `low`, `outmatched` and the stand; camps still send us home.
- **Work guard** (`guard_work`): bank, shop, contest, siege and farm steps also keep off the tiles beside us that
  want_home would send us back from (the pack zone, or where the recall line rises above our health), except our own
  spawn tiles. A chase keeps the plain step guard.

51.5% of 15,360; out-of-fuel turns +17%. Hold walk-offs 1.17 a game vs 2.40; holds under pressure paid 81% vs 71%.

## 270: Willow's heal cast by its value over the cooldown (astraeus, 2026-11-01)

With the heal ready next to an ally missing under half a heal, our Willow healed 2% of turns, the top teams' 13-14%.
A heal is cast when gain >= amount x (1 - min(T, cooldown) / cooldown), T the rounds until the ally misses a full heal
at its loss rate (camps that would hit it plus enemy blows): the share of the heal a partial cast wastes is at most the
share of the cooldown waiting would spend. Out of fights any gain casts; an ally that could die before our next turn
is healed at once. Stepping to heal keeps the old gate. 50.5% of 10,240; 52.8% in games with Willow. Heal casts a game
38 -> 52.

## 271: Cassi and Issac: damage counts along the body we can reach (astraeus, 2026-11-01)

Damage on the healthier body counted only once it went below the other (10), so a hit on Issac was worth 0 wherever
Cassi stood. Now the partner's health caps a body's damage only while the partner is visible, off its spawn, and within
one turn's basic-attack reach of us or a visible ally that can act (`partner_bound`); damage short of the cap counts
its chip. The fight simulator still links both bodies. 49.7% and 49.8% of 10,240, level; kept as the rule. A lone Issac
in our reach, with a lower Cassi beyond every reach of ours, is hit on 86% of melee turns (was 72%).

## 273: our champion falling before any of theirs loses the fight (astraeus, 2026-11-01)

The fight play-out judged a fight lost only once all of ours fell. In v66's ladder verdicts, 22% of not-lost stands had
our champion falling in the play-out, and those died within 10 rounds 20.5% of the time against 5.2%. Now our fighter
falling while every enemy in the fight still stands ends the play-out as lost (a champion lost for nothing); want_home's
stand, the step guard and the chase read it. 51.0% of 10,238; deaths 4.93 vs 5.41 a game, kills 4.92 vs 4.46.

## 274: dash-aware travel in Pathing (astraeus, 2026-11-02)

A dasher travels by the turn: each step_towards, descend and step_towards_funded weighs a walk, a walk round a hole or
altar line, a wait for the cooldown beside one, a dash, a dash then a walk, or a walk then a dash, by turns to the goals
(`model/dash_turns.h`). Of equally quick options it dashes, keeping a ranged champion's walk if it can. Replaces
dash_across, both dash_towards and travel_dash, so travel dashes also go in sieges, captures and walks home.
- No travel dash with a visible enemy within vision + 2. It waits only while the dash cools; a crossing it cannot take
  with the dash ready is walked round.
- Heart of Ruin keeps its landing veto (sleeping groups, killing retaliation).

52.2% of 10,240 against the bot before 269-273. Out-of-fuel turns +26-28%, a tail on hole-heavy maps not yet
attributed (TODO).

## 275: enemy dash paths cross neither our spawn nor our champions they see and that stay put (astraeus, 2026-11-02)

Reach's enemy dash paths crossed anything but walls and live camps. By the rules a dash path crosses neither the
enemy spawn (ours, to them) nor a visible enemy champion: a path's middle tile is next to the dasher, so it always sees
a champion of ours there unless it stands in a bush. Now `pass` leaves out our spawn (`Terrain::uncrossable`) and our
visible champions off bushes whose next turn comes after the enemy's last chance to dash (its turn, or its second
with two turns before ours): one that acts first may step aside. First version (every visible ally barred paths):
49.8% (48.8-50.7) of 10,240 on fresh-70101..70120, out-of-fuel turns +1.2%; narrowed at the session merge
(EXPERIMENTS "Session merge").

## 276: a retreat step a stun reaches is not clear (astraeus, 2026-11-02)

`retreat_step` read only damage, so a step in reach of a stun with no damage (Cassi's) counted as clear and could
justify a step away from home. Now a step is clear only with no damage and no blow reaching it (escape_walk's
`untouched()` rule), and at equal damage a stun-free step comes first. Merged A/B (276-278) below 278.

## 277: prey delays us by our own strike this turn (astraeus, 2026-11-02)

`prey`'s fight read delayed us only when ranged, out of range and with no walk-friendly cast ready, so a melee
champion far off counted as striking this turn. Now we are delayed as allies are: when our strike this turn, walking
first, from the slots ready by live cooldowns (`strike_with`), cannot reach the target, unless a heal or shield is
ready. Unchanged when we cannot walk or are channelling.

## 278: kill bids count allies yet to act this round (astraeus, 2026-11-02)

`side_damage` (offer_kills) counted only allies acting before the enemy next round, though an ally yet to act this
round strikes before the enemy's next turn whatever the order. Its turn now counts; with both turns, a spell cast in
the first is not counted again in the second (`two_turns`). 276-278 together: 49.9% (48.9-50.9) of 10,240 on
fresh-71301..71320 against astraeus 702704b, out-of-fuel turns +0.3%; kept as the rules.

## 279: the walk home counts the spawn's heal (astraeus, 2026-11-02)

A turn ended on our spawn heals to full before any enemy acts. `Safety::lethal` now reads full health on our spawn.
With no clear retreat step, `retreat_step` puts first the homeward steps whose walk down the home field onto the spawn
survives, each enemy yet to act counted twice, and leaves us healthier on the spawn than now (`HomeWalk`); among them
276's order holds (damage, then stun-free). Only walks no recall beats are looked at (`recall_turns() + 1` steps).
Against idle on 60 L00-family maps (touching spawns), with a recall kept when no walk home survives (removed at the
session merge: an enemy in reach cancels it anyway, EXPERIMENTS "Session merge"): 1000 gems 5.2% sooner [2.6, 8.1],
gems by 600 +32.5 [+11, +53]; elsewhere level. Merged A/B (279-281) below 281.

## 281: no range-0 approach from off the group's centre field (astraeus, 2026-11-02)

(280, sealed crystal pockets in farm pricing, was dropped at the session merge: EXPERIMENTS "Session merge".)
`search_approach` at range 0 returns no approach at once when the group's whole centre field (same static walls)
leaves our tile unreachable, instead of a walk-cap search that also doubled `walk_cap_`. 279-281 together (280 and 279's recall keep included): 50.2%
(49.3-51.2) of 10,240 on fresh-71201..71220 against astraeus 103c9ba, out-of-fuel turns +0.9%; kept.

## 282: our stun ends the target's channel (astraeus, 2026-11-02)

A stun cancels a recall, tribute or teleport. `World::read_stuns`, which reads the stuns we just cast, now also clears
a newly stunned enemy's channel and teleport destination: until the next full update the belief kept it channelling
for the rest of our turn. Fired ~33 times a game (1,050 in 32 self-play games).

## 284: several landed tributes empty their bags (astraeus, 2026-11-02)

(283, visible tributes that win together, was dropped at the session merge: EXPERIMENTS "Session merge".)
When several believed enemy tributes end in one update, `update_scores` empties the unseen bags of the only subset of
them (bags as before the update) summing to the score delta; with no unique subset, the old single-bag rule. Several
ended at once 30 times in 32 games, a unique match each time.

## 285: the respawn window starts at the previous update (astraeus, 2026-11-02)

A death found at a full update dates from that update's predecessor (`previous_update_`), not round - 1: the two
differ only after an out-of-fuel turn resumed.

## 286: Ryth's Power Health is an emblem candidate (astraeus, 2026-11-02)

`best_stat` offers `value(power, health_stat)` to `health_strength` (Ryth), whose Health adds Strength; for the others
Durability-Health always beats a sixth Health shard. Rare (4 in 202 Ryth champion-games).

## 287: count_use counts casts and walks as made (astraeus, 2026-11-02)

The shop's ability-use record counted casts from cooldowns at the turn's end and a walk from a changed position, so
it missed Vendetta's kill-readied casts and counted Vesper's walk + dash + reset + attack as 2 attacks. The cast
wrappers and `Pathing::move_to` now record each cast and the walk (`turn_acts`). 286-287 alone (b5/shop):
50.2% (49.2-51.2) of 10,240 against astraeus 103c9ba; 282-285 alone (b5/channel-beliefs, unseen tributes counted in
283): 49.9% (48.9-50.8). 282-287 merged (283 included): 50.2% (49.2-51.1) of 10,240 on fresh-71501..71520 against astraeus ad74b7b, out-of-fuel
turns -1.4%; kept as the rules.

## 288: farm's wait cutoff counts the trip in travel turns (astraeus, 2026-11-02)

`farm_turn` dropped a group whose respawn wait passed `max_wait`, with the wait measured against our walk in steps;
a dasher (`step_towards` dashes whenever ready) covers 3 steps in a dash turn, so as it neared a group the measured
wait jumped by 2 and the group left the candidates: 10.1% of farm re-pricing flips. On a plain walk the test now
measures the wait from `Pathing::travel_turns(steps)` (`dash_turns::open` with the travel dash's readiness and
enemy clearance, as `travel()`); the trip price stays in steps. Unworked farm flips -11.6% (512 traced games).
Alone (b6/farm-flips): 52.1% (51.1-53.0) of 10,240 on fresh-70701..70720 against astraeus ad74b7b, out-of-fuel turns
+0.8%; against idle tributed +5.1 and gold +28 at round 600. Merged with fuel-only work, replays byte-identical at
100M (b5/sim-fuel: fight sims -2.6%, 50.1%; b6/guard-fuel: the step guard's window scan and keys, 50.3%). Merged: 52.9% (51.9-53.8) of 10,240 on fresh-71601..71620 against
astraeus cd600d7, out-of-fuel turns +6.4%; kept.

## 289: chases outlast a step out of sight, and the search's walk follows the chase (astraeus, 2026-11-02)

A chase stopped whenever its target left sight (25% of chase stops on the ladder and in self-play), and on turns the
strike search ran first, its walk went toward the farm, leaving chase no walk (8-13%). Now an enemy we chased or
struck on our previous turn (`engaged_before`, from attacks, champion unit casts and chases) stays prey once out of
sight while every tile it could be on lies within our sight square (`lost_prey`); chase walks onto those tiles, and a
hidden one reveals it. While such an enemy is still visible and prey's cheap tests (`preyable`, prey's filters moved
out) take it, the strike search ranks its walk tiles by crow-flies distance to it (`Intent::aim`, `chase_aim`)
instead of the goal field. Chasing past prey's own-ground filter instead lost (48.8%): healthy targets on their half
almost never die. Out-of-sight chase stops in committed chases 225 -> 134 (40 traced games); kill share at equal
numbers .510. Held-out fresh-81081..81100, 10,240 games against astraeus f9074463: 52.2% (51.2-53.1), out-of-fuel turns
+1.2%; against v66, paired with the base on the same games, +2.13 points (+1.07 to +3.19, z 3.95). The branch
(0c45902e) recorded a unit cast on a camp as engaging the champion with that handle number, and champion casts not
at all; fixed here (level with the branch, -0.2).

## 290: a fight we press stays our chase (astraeus, 2026-11-02)

`prey` takes the fight we press (`pressed`: a visible enemy we struck or chased on our previous turn, off its spawn's
edge, with a smaller share of its health left than ours) whenever prey's cheap tests pass, without the chase
play-out's verdict. want_home already kept us in that fight, so a lost play-out only handed the turn to the farm,
which walked off mid-fight from a hurter enemy. On v66's ladder games our healthy pursuers dropped hurt targets twice
as often as the top teams' (EXPERIMENTS "Chases and leaves on the ladder"). 10,240 games against astraeus 5713135 on
fresh-82001..82020: 50.6% (49.7-51.6); held out on fresh-82021..82040: 50.4% (49.4-51.3), out-of-fuel turns level.
Against v66, paired with the base on the same games: +0.99 (+0.00..+1.97) and held out +1.39 (+0.41..+2.36).

## 291: a teammate's pressed fight is ours too (astraeus, 2026-11-02)

`team_pressed`: a visible enemy, off its spawn's edge, in a visible ally's attack range with a smaller share of its
health left than that ally (vision is personal, so contact stands in for 290's "struck last turn"). With no pressed
fight of our own, prey takes it as 290 takes ours (prey's cheap tests, no play-out), and with no engagement last turn
the strike search's walk aims at it. On v66's ladder games each nearby ally of ours joined a chase about as often as
theirs (0.28-0.31 against 0.31-0.40 helpers per ally within 8); the rest of the helper gap is cohesion. Against
astraeus 290 (`bots/variants/astraeus-290`): 50.0% (49.0-51.0) of 10,240 on fresh-82001..82020 and 50.0%
(49.0-50.9) held out on fresh-82021..82040, out-of-fuel turns level; against v66, paired with 290: +0.51
(-0.27..+1.29) and +0.64 (-0.13..+1.42). Changes 46% of games; kills 5.42 / 5.26, deaths 6.67 / 6.79 a game (2,048).
Kept as 290's rule for the team.

## 292: equally short steps lean toward the team (astraeus, 2026-11-02)

`Pathing::pull(p)`: the summed distance (beyond 2 tiles) from p to each ally within 30, visible allies off our spawn
at their tiles, unseen ones at their claim's centre. It ranks ties only, so no walk gets longer and no choice
changes: `route_around`'s equally short first steps (farm walks, banking, shops, plain retreats; now ranked even with
no aim), `closer_neighbours`, `step_closer`, and `retreat_step` after damage, stuns, steps and gap. Against astraeus
291: 51.9% (51.0-52.9) of 10,240 on fresh-83041..83060, 51.3% (50.4-52.3) held out on fresh-83001..83020; against
v66, paired with 291, +0.85 (-0.44..+2.13) and +0.73 (-0.57..+2.03); solo farming level. Allies within 8 at first
contact 1.56 -> 1.67 against v66 (ladder teams 2.12), deaths a game 5.44 -> 5.08, gems level. Out-of-fuel turns
+17% head to head and +24% solo: pull itself is ~1% of a turn's fuel; walking near allies makes farm and carry turns
dearer (farm ~+600 a turn, carry_bag ~+8% a call), already paid in the numbers above. (Cohesion agent C, variant
`coh-c-p4`.)

## 293: idle allies nearer an enemy act later (astraeus, 2026-11-02)

`idle_priority`: with no camp tie hit to order, an idle champion ranks by the nearest enemy last placed (visible, or
tracked within 3 rounds), in steps of 2 tiles, nearer acting later; it used to rank by health. Acting before a near
enemy only hands it the reply: when deadlast moved idle allies near enemies 1.4 enemy turns earlier, they took 38% more
damage and died 35% more, dealing no more (EXPERIMENTS "Turn order and ally coordination"). Against astraeus e9c37971
(`bots/variants/astraeus-e9c3797`): 51.5% (50.5-52.5) of 10,240 on fresh-85200..85219, 52.3% (51.1-53.4) of 6,828 on
fresh-85228..85239 + ladder + gen, 52.3% (51.4-53.3) of 10,240 on fresh-85300..85319: ~52.0% of 27,308; out-of-fuel
turns level. The reverse order (nearer acts earlier) lost 44.4%. (Measurement agent, variant `ast-idle-nearlate`.)

## 294: demeter's pair-yield (astraeus, 2026-11-02)

Ported from `bots/demeter` (astraeus e9c37971 + pair-yield, EXPERIMENTS "demeter reset"): the draft takes only teams
with Cassi & Issac (two bodies for one pick); the pair's hold is worth `pair_hold_share` (0.5) of its value in the
holder choice (`hold_shy`: a death of either takes both bodies and both bags), so it hands captures to any other ally on
the tiles or in pick-up reach (`holder_value`, `outvalues_holders`, farm's pick-up); Cassi farms with the crew instead
of gold-only groups (Tavi on gold maps keeps that role). Against astraeus 293 (`bots/variants/astraeus-293`): 54.3%
(53.7-54.8) of 30,208 on fresh-85400..85458, 56 of 59 suites above 50%; out-of-fuel turns +5.5% (251,870 / 238,804).

## 295: kill bids are kept, made only where a plan reaches, and not while channelling (astraeus, 2026-11-03)

- On a turn our kill bid holds a seat for, the leave branch (`want_home` -> `retreat()`, which tries only one basic
  attack) first runs the strike search behind the step guard, offering only plans that kill the bid's target
  (`follow::binding`, `Search` `bound`); elsewhere a plan that breaks the bid ranks below every one that keeps it.
- No kill bid while a tribute or teleport channel runs past our next turn: that turn is the channel's (Prism's long
  tributes).
- A winning kill offer is re-read at the real distance (`real_distance`: tiles from which a basic attack reaches and
  sees the target, walkable or one dash away), not Strike's straight-line one.

Traced (2,048 games): a bid's target dies at our next turn 84.8% of the time (77.2% before); bids with no legal plan
2.7% -> 1.2% of bound turns. Against astraeus 294 (`bots/variants/astraeus-294`, variant `ast-kill2`): 50.4%
(49.9-50.8) of 40,448 on fresh-86100..86178, after 50.5% and 50.5% of 10,240 each on fresh-86000..86039; out-of-fuel
turns +0.6%. Kept as rule-derived and cheap (EXPERIMENTS "Turn order and ally coordination"; notes in
`research/turn-order-2026-11-02/follow-through.md`, `kill-value.md`).

## 296: the team lock: always Cassi & Issac, never Stellar (astraeus, 2026-11-03)

A user decision. `draft_model.h` carries the lock (`required`, `banned`, from `model.mjs TEAM_LOCK`); `model_team`
ranks only teams that hold Cassi & Issac and no Stellar (294 required Cassi & Issac there already), and `draft.cc`
applies it to the table drafts and every fallback pick (`locked`, `lock_forbids`: banned picks skipped, the last pick
forced to Cassi & Issac if still missing). Off on test drafts and in draft lab vehicles. No A/B: on draft3-cheap's
model no team changes on any of 46,404 pool maps (Stellar never joins a Cassi & Issac team there), so only drafts
that fall back off the model change; native parity 0 differences on 442 maps.
