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

## 297: draft4's model (astraeus, 2026-11-03)

`draft_model.h` from `draft4-cheap`: draft4's 1,347,324 self-play games (fresh pool fresh-77000..77195; opponents the
top 10 teams' ranked drafts since 2026-10-31; our teams under 296's lock) refitted on the 23 features 261 ships, at
draft4's penalties. The best team changes on about half the pool maps (3/4/5 picks 44 / 52 / 55%). A/B against
b65b0d8 (draft3-cheap's header), own drafts: 51.6% of 20,480 (fresh-9320..9339 and fresh-93000..93019, 50.9-52.3);
no confirm run (a user decision). All 25 features against these 23: 50.0% of 20,480 (49.3-50.7), and their header still
takes the fresh-9136 dash-lattice to 9.16M on the first draft turn, over the 8.5M bar. Native parity 0 differences on
854 maps; first-turn fuel as 261's (the same features). EXPERIMENTS "Draft lab draft4".

## 298: the farm loop's fuel reserve covers dash travel (astraeus, 2026-11-03)

The farm loop evaluates groups until fuel falls to a reserve (walk_reserve plus the route search), and that reserve
left out `Pathing::travel`: with the dash ready the walk after the loop is a travel plan (~7.8k) and its crossing
trace (~2.7k), so dashers ran out after the loop (the census: p.plan was the innermost scope of 16% of first
out-of-fuel turns). The reserve and its `ample` threshold now add `travel_cost_estimate` (12k) when we have a dash,
may cast and its cooldown is 0. An existing gate's reserve corrected, no new gate; replays identical at 100M on all
eight bench sets. Real budget against astraeus-fc4b (fc99b847), own drafts: 49.3% (48.4-50.3) of 10,240 on
fresh-11000..11019, out-of-fuel turns 66,944 against 95,767 (-30.1%); 50.0% (49.0-50.9) on fresh-10100..10119, 64,929
against 93,828. farm-partial-evaluation fires +17% (the loop stops earlier); comms-stale-vision and turn-order fall.
Merged with a fuel-only cut, replays identical at 100M: `Pathing::plan` ORs its window's boards word by word before
one row extraction (~450 a plan). Round 1 of fuel campaign 4 with 299-301: EXPERIMENTS "Fuel campaign 4, round 1".

## 299: comms re-reads vision after moving down to 5k fuel left (astraeus, 2026-11-03)

`refresh_floor` (main.cc) 5k, was `end_reserve` (10k). `World::observe` after a move costs 1.2k median, 4.3k p99.9,
5.2k p99.99 and 7.2k at most (506k refreshes). comms-stale-vision fires -82% (494k -> 88k a bot), out-of-fuel level
(97,495 against 97,376 in 10,240 games), 50.1%; at 3.5k out-of-fuel rose 1.1%. Identical at 100M.

## 300: the step guard's costliest-placing estimate also decays on an entry cut (astraeus, 2026-11-03)

`costliest` decayed by 1/8 only after a completed placing or when nothing reached us, so one dear placing kept the
guard off while enemies stayed near (FUEL-AUDIT finding C); it now decays on each step-guard-entry cut too. Guard
tags -4.4% (entry 471k -> 432k, look and sim up), out-of-fuel level (96,938 against 96,979), 50.4%. Identical at 100M.

## 301: ward_bushes grows bush clusters down to 5k fuel left (astraeus, 2026-11-03)

The growth floor was `small_cost_estimate + end_reserve` (15k), now `end_reserve / 2` (5k): what follows a ward (turn
order, comms) has its own checks. ward-no-bushes-clusters -32% on top of 299-300; 299-301 together against fc4b:
out-of-fuel 96,244 against 97,543, 50.6% of 10,240; 50.5% of 5,120 on fresh-11100..11109 (out-of-fuel -1.2%).
Identical at 100M. With 298 (merge round 1, `astraeus-fc4-m1`): 49.6% (48.7-50.6) of 10,240 against fc4b,
out-of-fuel 66,239 against 95,128 (-30.4%), comms-stale-vision -89%.

## 302: the farm loop reads allies' crew facts once a call, and skips plan_crew with no crew to form (astraeus, 2026-11-03)

Fuel only. A crewable group whose crew bound finds no claimer seen lately and no available ally no longer calls
`plan_crew`: its crew would be us alone (output == strength), which the `plan.output > strength` test never takes
(1.64 such calls a cut turn, ~2.6k each). `CrewAllies`, a table filled on first need in each farm call, holds each
ally's claim and "seen" test, and lazily its camp_output, crew_available's group-independent part and share_damage's
pool entry; the crew bounds, plan_crew, share_damage and crew_available read it in ally order, so sums and the
pool's sort are unchanged. Replays identical at 100M on all eight bench sets; total fuel q -3.90%, big -1.91%, wide
-1.85%, oof -1.09%, mg -0.99%, tgt -0.64%, fight -0.03%, fs +0.03%; p99 -3.6% to -9.6% on wide, oof, mg, q, big.
Real budget against `astraeus-fc4-m1` (CHANGES 298-301), 10,240 games on fresh-11000..11019: 50.5% (49.5-51.4),
out-of-fuel 64,368 against 69,041 (-6.8%), farm-partial-evaluation 2.03M against 2.69M (-24.6%), shortcuts -19.6%.
Round 2 of fuel campaign 4: EXPERIMENTS "Fuel campaign 4, round 2".

## 303: an ally one walk-turn out of striking reach joins the fight sim a turn late (astraeus, 2026-11-03)

`walk_allies_in` (model/safety.cc) delayed an ally's first hit only for walks of 2 or more turns; one a single step
short of striking reach (its one-turn reach, the walk included) joined at once, a simplification kept so sims stayed
on the fast path. By turn.walk it strikes a turn later, so `arrives_at` is now 1 there too. A behaviour lift, not
exact. Against `astraeus-fc4-m1`: 50.2% of 10,240 on fresh-11000..11019 (out-of-fuel +1.1%), 49.9% on
fresh-10120..10139 (-1.6%). Merged with 302 (`astraeus-fc4-m2`): 50.1% (49.1-51.1) against m1, out-of-fuel 65,003
against 68,685; against 302 alone (`astraeus-fc4-m2f`) 49.7% (48.7-50.7), out-of-fuel 64,195 against 64,396.

## 304: make_way and label_through skip label walks that cannot find a label (astraeus, 2026-11-03)

Fuel only. `make_way` returns false at once when `goals` is empty (farm's attack tiles all held by allies), and
`label_through` returns unreachable after a walk-parted search (`route_label_cap_ == -1`, so `route_label` is
unreachable everywhere). Neither could find a label: a fresh search with no goals labels nothing, and labels reused
through `within_failed` were already found beside no ally. Before, each call walked the crowd of allies at ~5k an
ally; in m2's A/B against fc4b that ran every decide out on gen-fortress-1101902231 (941 OOF turns) and
gen-dash-lattice-1100707609 (1,915), which then showed as `OOF <r> queue` on alternate rounds (a late turn ends its
decide in the next round). Replays identical at 100M on all eight bench sets and the five census runaway maps; total
fuel -0.06% (fs) to -0.43% (fight). Against `astraeus-fc4-m2`: 50.2% of 10,240 on fresh-11000..11019, out-of-fuel
62,263 against 64,097. Round 3 of fuel campaign 4: EXPERIMENTS "Fuel campaign 4, round 3".

## 305: the opening farm loop reserves the walk's attack-tile decode (astraeus, 2026-11-03)

On the first turn no turn end has decoded the chosen group's attack tiles, so the walk after the farm loop paid
~16.5k for them (drafted block index ~8k, ~2k a member) on top of a reserve that left them out, and the turn ran out.
On the opening turn only, the loop's reserve now adds `attack_tiles_cost` (0 once cleared, kept or undrafted;
otherwise 9,000 unless indexed plus 2,500 a live member not yet ready) and its `ample` test adds the map's
largest-group bound. `farm_attack_tiles`' kept union is now one cache shared by the farm_turn instances (the same
group, range and live members give the same union). Behaviour only at the real budget: identical at 100M on all
eight sets. Against `astraeus-fc4-m2` with 304: 49.5% (48.5-50.5) of 10,240 on fresh-11000..11019, out-of-fuel
59,553 against 64,634 (-7.9%), round 1 4,038 against 7,139; 50.4% (49.4-51.3) on fresh-11240..11259, out-of-fuel
-6.6%. The same reserve on every turn cost farm-partial-evaluation +16% and was dropped.

## 306: walk_down skips a repeated failed descent, and camp_cast reads out-of-reach members only for sole_finish (astraeus, 2026-11-03)

Fuel only. Farm's walk and the siege seal walk ran `descend(field) || step_towards(field)`. After its search failed,
step_towards repeated the same descent, including its ~4.3k dash plan. `Pathing::walk_down` now gives step_towards
a token of the first failure: `acts_`, which `invalidate()` bumps on every move, dash, hidden-blocker bump and outside
dash, plus the guard state. While the token still matches, the repeat is skipped. The skip still stamps the trace that
the repeat's `ahead()` would have read, so `traces_` keeps the same replacement order. `camp_cast` no longer fully reads
members beyond every ready slot's hit (unit: range; ground: min(range, 4)+1, as `best_ground` clamps; landing:
dash range + radius). Those members are no target, and they are read only while `sole_finish` (all visible, one
alive) is still open. Replays identical at 100M on all eight bench sets; total fuel +0.00% (big, fs) to -0.09% (tgt),
turns over 100k down on every set. Round 3 of fuel campaign 4: EXPERIMENTS "Fuel campaign 4, round 3b".

## 307: on a quiet turn the turn-order gate keeps a 6k reserve instead of 10k (astraeus, 2026-11-03)

A quiet turn has no enemy in sight, isn't a healer's, has no channel of ours ending, and isn't the first round. On
one, `set_turn_order` runs its bid down to 6k left instead of `end_reserve`'s 10k. Its cost there is linear in camp
members and tracked enemies: 0.6k median, p99.99 6.7k, over 6k on 0.020% of 3.2M calls. The check (`enemy_seen`, the
facts, one `my_record()`) is read only on turns under the old reserve. At 6k, the comms refresh keeps most of its 5k:
at 5k, comms-stale-vision rose by a third. Behaviour only at the real budget: identical at 100M on all eight sets.
Against `astraeus-fc4-m3`, with 306: 50.3% (49.4-51.3) of 10,240 on fresh-11000..11019, out-of-fuel 58,042 against
59,882; 50.0% (49.1-51.0) on fresh-10000..10019, 60,742 against 62,640. turn-order firings -41% and -42%,
comms-stale-vision +20% / +20%. Round 3 of fuel campaign 4: EXPERIMENTS "Fuel campaign 4, round 3b".

## 308: a crew share's value floors the farm loop's own-group prunes (astraeus, 2026-11-03)

Fuel only. Once the loop has set a share (`shared_value`), an own group whose value stays below it changes no pick:
the share wins unless the best beats it. So farm_turn's prunes (pre_upper, the pre-facts prunes, `beaten_near`, the
clearing estimate, the alone-clear test, the stop and the crew bound) test own groups against max(best_value, the
share's value) instead of best_value alone. `bar_lt` is used for `<` tests and `bar_le` (the next float below the
share) for `<=` tests, so a group equal to the share is never pruned: a tie goes to the best. shared_value only rises,
and a later share needs a value at least the current one, so a lower best never lets in a share the old loop
refused. The floor is off where best_value is read past the pick: banking (against from_altar_value), maps with a
kited group (the risky pick replaces a missing best; `kited` is static per map) and a takeover in reach (its work
rate is best_value; the test is the takeover loop's own). Replays identical at 100M on all eight bench sets. With
309: total fuel -1.07% (mg) to -2.18% (big), +0.59% on fs (codegen in the flattened `farm_turn`). Alone against
`astraeus-fc5b`: 50.5% (49.5-51.4) of 10,240 on fresh-11000..11019, out-of-fuel 59,690 against 59,616,
farm-partial-evaluation -17.6%. Round 1 of fuel campaign 5: EXPERIMENTS "Fuel campaign 5, round 1".

## 309: once the farm loop has a help call, it skips groups that cannot be a nearer help (astraeus, 2026-11-03)

Fuel only. A help call overrides the best and the share. Only a farm Monolith best that we claim keeps it off. So on
maps with no farm Monolith (`farm_monolith` false for every group, static per map), once `help_group` is set, a group
that `may_help` rules out changes no pick: too far by Chebyshev distance, past help_steps or help_radius, not alive,
no strength, or banking. Help candidacy reads no best: every prune before it exempts `may_help` groups, and the final
help group always passes `may_help` at its turn. Replays identical at 100M on all eight sets, -0.01% to -0.35% total
on top of 308. With 308 against `astraeus-fc5b`: 50.5% (49.5-51.5) of 10,240, out-of-fuel 59,359 against 59,441,
farm-partial-evaluation 1,655,578 against 2,065,448 (-19.8%), all shortcuts -13.8%, fuel a play turn mean -1.5%.

## 310: the strike search's step guard reuses its cover's first pass (astraeus, 2026-11-03)

Fuel only. From the strike search's read until its plan is carried out (`GuardInputsHeld`), step_guard_cover keeps
its `GuardFoes` (foes, Strikes, Reach pointers, the exposure here) and the tiles past `no_worse_at` with their nears.
A `step_guard` from the same tile and radius in that window skips the constructor, `expose_here` and the window pass.
It runs the same per-tile body over the kept tiles in the same order. Nothing it reads changes in that window. The
search acts only after `release()`. Safety's beliefs, Strikes and Reaches are fixed until `refresh()`/`invalidate()`,
which run only after acting. The map is static. A second search starts with nothing kept, and a turn resumed after
running out throws at step_guard's `throw_if_stale` before reading. Replays identical at 100M on all eight sets.
fight p99 -0.8%, max -1.5%. Against `astraeus-fc5b`: 49.8% (48.8-50.7) of 10,240, out-of-fuel 59,268 against 58,954
(noise), step-guard-sim -16%, step-guard-look -4%.

308-310 together (`astraeus-fc5-m1`) against `astraeus-fc5b`: 50.1% (49.1-51.0) of 10,240 on fresh-11000..11019,
out-of-fuel 60,117 against 60,007 (level), shortcuts without out-of-fuel 2.60M against 3.05M (-14.8%), fuel a play turn mean 49,179
against 49,921 (-1.5%), p90 86,050 against 86,150, p99 92,250 against 92,450.

## 311: the strike search finds its landing classes by one partition (astraeus, 2026-11-03)

Fuel only. A landing that hits (Heart of Ruin and other landing dashes) is priced once per class of cells alike in
the foes within the landing radius and the camp groups touched. Those classes were found cell by cell on first need,
from per-cell `land_foes` / `land_touch` memos. `find_classes` now partitions `land_hits` once a search: it splits by
each foe's landing square, then by each local camp group's member squares. Two cells share a class iff they agree on
every split, which was the old key. `group_landings` adds a class's hit cells to their group as one mask. Groups
still come in the order of their lowest cell. `class_foes_all` now covers classes not hit yet. That only turns on a
merge when every foe of the hit classes is alive, and then a merge joins nothing. Replays identical at 100M on all
eight sets and on a forced Heart of Ruin firing set (62 replays). wide max -1.4%, tgt max -0.9%. Against
`astraeus-fc5-m1`: 50.1% (49.1-51.1) of 10,240, out-of-fuel 56,103 against 57,961, rounds 300+ 24,277 against
25,732. Round 2 of fuel campaign 5: EXPERIMENTS "Fuel campaign 5, round 2".

## 312: make_way's walk through a line of allies first checks for a labelled tile in its reach (astraeus, 2026-11-03)

Fuel only. When no tile beside an ally next to us holds a label from the failed search, `label_through` walks the
line of allies behind it. That costs a host test and a field read per tile, ~5.5k a call, and a standoff's make_way
runs it up to eight times a turn. The search's `visited` board (`route_labelled_`) now moves with `route_field_`
wherever the field does. Once the line holds 4 allies, one Chebyshev square of radius min(8, ally count) around the
first ally, intersected with that board, shows whether any labelled tile is in the walk's reach. Every tile the walk
reads lies within that radius. If the square holds none, the call returns unreachable at once. The walk also skips the
first ally's neighbours, already read, and stops once no deeper ally can beat the best label. Replays identical at
100M on all eight sets. gen-rivers-1100302130's runaway: 5.2k a call down to 2.05k.

## 313: route searches keep three earlier failed searches (astraeus, 2026-11-03)

Fuel only. `failed_` held only the latest failed search, so a standoff that alternates two or three failing searches
a turn (gen-topo-shortcut-1101506904: a 16k attack-tile search and a 20k wide one) ran them all every turn. Before a
fresh search, a live `failed_` moves into the least recently used of three spare slots. A slot keeps its field,
labelled board, goals, walls, origin, cap and layers. A search matching a slot by failed_'s own rule swaps it back
and reuses it as failed_ would: same origin, goals and walls, and a cap no higher or a search that ran dry. Its
result is a function of exactly that key. Campaign 4 dropped a similar 3-slot cache as level. This one is LRU and
carries 312's labelled board. Replays identical at 100M on all eight sets, total fuel +0.05-0.1% (the lookups).
topo-shortcut-1101506904 side b: 1,516 out-of-fuel turns down to 329. With 312 against `astraeus-fc5-m1`: 49.7% of
10,240, out-of-fuel 57,669 against 58,940, runs of 50+ 2,395 against 4,318.

311-313 with 308-310 (`astraeus-fc5-m2`) against `astraeus-fc5b`: 50.7% (49.8-51.7) of 10,240 on
fresh-11000..11019. Out-of-fuel 57,920 against 59,731 (-3.0%), rounds 300+ 25,331 against 26,721 (-5.2%). Shortcuts
without out-of-fuel 2.60M against 3.04M (-14.5%). Fuel a play turn: mean 49,229 against 49,918, p90 86,050 against
86,150, p99 92,250 against 92,450.

## 314: retreat's untouched tests stop at the first blow (astraeus, 2026-11-03)

Fuel only. `quote_escape_walk`, `dash_retreat_casts`' quote tile and retreat_step's longer steps read only whether a
tile is touched: `bound(p)` with no damage, hit or stun. `Safety::touched` walks the same terms in each_threat's order
(camp damage first) and returns at the first blow that hits or has damage. Every term bound sums is at least 0, so a
sum is above 0 exactly when some term is, and a stun implies a hit. The blows skipped are Reach builds and `asked`
memos, caches of the turn's state. `untouched()` is gone. Replays identical at 100M on all eight sets; fight total
-0.23%. Against `astraeus-fc5-m1`: 49.8% of 10,240, out-of-fuel 54,809 against 57,749 (-5.1%), rounds 300+ -6.5%;
on fresh-10000..10019 50.1%, 56,684 against 59,434 (-4.6%). Retreat turns are the heaviest near turns. Round 3 of
fuel campaign 5: EXPERIMENTS "Fuel campaign 5, round 3 and summary".

## 315: retreat_step prices its homeward and sideways steps only as far as their rank needs (astraeus, 2026-11-03)

Fuel only. Each step's `Safety::tally` sums bound()'s damage, hits and stuns in each_threat's order and stops after
the first term that makes damage positive; `finish` resumes from the enemies left. Homeward walks (priced in full)
and complete steps with no damage and no stun rank before every other step, so they are tried first in the full
sort order. The rest are finished, sorted and tried only if all of those are refused. The sort is stable and every
lead step ranks strictly before every other, so the two halves joined are the old order. A refused move changes no
Safety input: Safety reads World, not Pathing. The unread `doubled` and `threat` terms are dropped. Replays
identical at 100M on all eight sets (fight -0.11%, oof -0.06%).

## 316: Willow's want_home threat test stops once the threat holds (astraeus, 2026-11-03)

Fuel only. Willow read only `bound(here).threat`. `Safety::threat_at` walks bound's order: a visible hitter settles
it, and unseen hitters multiply the same miss chance until it reaches `recall_risk`. Once true it never turns false
again, so it returns there. Replays identical at 100M on all eight sets.

## 317: only_threat stops at the first other hitter and never prices the victim (astraeus, 2026-11-03)

Fuel only. retreat's sure-kill test asks, per adjacent tile and per dash landing, whether anyone but the victim may
hit there. It built every entry of `threats_at`, the victim's blow included. `Safety::other_hits` walks threats_at's
entries in its order and under its 16-entry cap, skips the victim and returns at the first hit. The unseen bisection
is shared as `unseen_blow`. Replays identical at 100M on all eight sets. 315-317 against m2 with 314: 50.1%, out-of-fuel
53,758 against 54,074 (-0.6%); on fresh-10000..10019 50.2%, -0.7%.

## 318: the spare failed-search lookup runs only from a spare's origin (astraeus, 2026-11-03)

Fuel only. 313's lookup was inlined in flattened route_around and paid on every fresh search, and its three spares
were allocated on the first turn. The lookup and the eviction are now out of line, called only when our tile equals
one of the spares' origins, mirrored in `spare_me_` (set in swap_spare, the only place a spare changes). A spare's
key includes its origin, so no other search can match. Spares are made on first use, empty slots first, as the old
LRU order took them. Replays identical at 100M on all eight sets: totals -0.01% to -0.03%, round-1 means -0.1%.

## 319: label_through keeps its line walks under the same labels (astraeus, 2026-11-03)

Fuel only. make_way's callers walk the same line of allies again under the same labels (step_safely with and
without avoid, labelled_ally_beside then make_way). A 4-entry ring memo keeps the walk's result, keyed by
`route_gen_`, the label cap, a, me, and the allies, avoid and guard boards by content. `route_gen_` is bumped at the
four places route_field_ changes. A pending guard bypasses the memo, since the walk would work it out. Replays
identical at 100M on all eight sets; q -0.83%, turns over 100k on q 16,493 to 15,714. Storing up to 3 boards costs
~280 a walk where nothing repeats, raising oof and mg p99 by 0.7% and 1.0% (+70 and +67 turns over 100k). m3 without
it read 50,874 against 59,181 out-of-fuel turns, level with m3's 50,627 against 58,754.

## 320: farm's takeover pass asks its walk-independent tests before building a group's walk field (astraeus, 2026-11-03)

Fuel only. After the farm loop, each cleared group near us with an ally on it got `pathing.to_group(g)`, a static
field of ~15k built once per group, before `takeover_worth`. That test rejects at once anyone who is not a
Marcella and lacks Vesper Vale's gold bonus, and any group another holds alone, an enemy stands on, or our hold
would not outvalue. `takes_over` (once a turn) and `may_take_over` now run first. `takeover_gain` runs next: the
holder loop, the gain and the payout timer. Its `timer < steps_to + 1` rejects only what `timer < walk + 1` would,
since a walk to the members' tiles is never shorter than their Chebyshev distance. All are pure reads, and a field
built later is the same (static walls, kept forever). Fewer builds can leave the fuel estimates
`max_field_layers()` / `costliest_field()` lower on some turns. Reserves read them, so at the real budget play may
differ there; at 100M it cannot. Replays identical at 100M on all eight sets; totals -0.08% to -0.39%. Against m2:
50.2% of 10,240, out-of-fuel 52,130 against 56,111 (-7.1%), rounds 11-60 -17%; on fresh-10000..10019 -6.6%. The
builds fell on early-mid turns, where allies first hold captures.

314-320 with 308-313 (`astraeus-fc5-m3`) against `astraeus-fc5b`: 50.4% (49.4-51.4) of 10,240 on
fresh-11000..11019. Out-of-fuel 50,627 against 58,754 (-13.8%), rounds 11-60 -23.6%, rounds 300+ -13.8%. Shortcuts
without out-of-fuel 2.56M against 3.04M (-15.7%). Fuel a play turn: mean 49,139 against 49,907, p90 86,050 against
86,150, p99 91,850 against 92,450. Confirmed on fresh-52000..52019: 50.2% (49.2-51.2), 51,067 against 57,039 (-10.5%).

## 321: the ostrich, and diana's SPSA-tuned constants (astraeus, 2026-11-03)

From diana (astraeus fc99b84 + the ostrich, tunified). Turn order (`turn_order.cc` `engaged`): an enemy in reach
takes us to the danger band's early seats only once we or a visible enemy within reach lost health within
`ostrich_rounds` (2); before the fight begins we keep the late seat. `world.h` keeps each enemy's `hurt_round`. The 51
constants of SPSA run `replays/tune/d1`'s final iteration (1312) replace the defaults in `params.h`, still
`constexpr`. Against pre-tune main: 54.6% (53.9-55.3) of 20,480 on fresh-53000..53039, out-of-fuel +3.2%. Against
a ladder test drafter: 69.7% against pre-tune's 66.5%. Evidence and per-composition table: EXPERIMENTS "The ostrich
and SPSA-tuned constants".

## 322: test drafts from the current ladder (astraeus, 2026-11-03)

`test_compositions` (used only with `params::test_draft`) is rebuilt from the top 10 other teams' ranked games of
2026-10-31..11-03 (21,425 games): the 10 most common compositions per pick count, each in its most common pick
order. No Stellar any more; Vesper, Marcella, Heart of Ruin, Vendetta and Cassi & Issac dominate. Own drafts are
unchanged (52/52 replays identical at 100M on the wide set).

## 323: static fields priced by the costliest measured flood (astraeus, 2026-11-03)

`static_field_cost_estimate(layers)` (util.h): a field over the static walls cut off at `layers` costs no more than
the whole flood, so its estimate is the layer bound (`search_cost_estimate`) capped at a quarter over
`costliest_field()`, the margin `full_field_cost_estimate` already uses; with nothing measured yet it is the layer
bound. On winding 100x100 maps the layer bound read 68k against a measured whole flood of 26k, above what any turn
had left: the warm-up never built the spawn field, `prepare_approach` priced the centre at ~128k and skipped every
approach, and `walk_on`'s crow-flies fallback walked into a wall (a Heart of Ruin stood 1072-1302 rounds on gen-s1
`gen-topo-shortcut-600206905`, ~900 on `gen-topo-backdoor-600206700`). Used by `field_cost_estimate()`,
`grow_centre`'s doubling, `warm_centres` and the centre cost in `prepare_approach`; approach searches keep the layer
bound (capping them too was +4.1% out-of-fuel turns). Evidence: EXPERIMENTS "Last-minute bug fixes".

## 324: a respawning group's camp tiles kept clear (astraeus, 2026-11-03)

A group returns only at a round start that finds all its camp tiles empty (rules `capture.respawn`).
`Pathing::attack_tiles` drops the camp tiles while the group is respawning (beliefs out of view can still count
members alive, and seen-dead members free their tiles), farm's kept attack tiles are keyed on it too, and `walk_on`'s
`walk_down` / `descend` / `step_closer` toward a respawning target avoid its camp tiles, as `search_approach` already
did. A cleared group awaiting capture is unaffected. In a dead end on `gen/gen-topo-necks-600107006` one champion on
a camp tile with four queued behind held a respawn back 328 rounds.

## 325: a siege's out-of-reach tiles keep out of every stirring group's reach (astraeus, 2026-11-03)

`siege()` staged, stepped out when low, cast out of reach without a tank, and fell back on the stage square by
dropping only the target group's `threat()`. Those tiles now also drop the `threat()` of every other group in
`each_stirring` (alive and awake or maybe awake: rules `camps.attack`, an awake monster hits the nearest champion in
its reach). A Prism with 404 gems staged 3 tiles from a Golem it had woken farming and stood there 13 rounds until it
died (gen-s1 `gen-topo-backdoor-600206713` as A against v67): camp-death gems 696 -> 86, a loss -> a win.

## 326: off a respawning camp tile when farm has nothing to farm (astraeus, 2026-11-03)

A group returns only at a round start that finds its camp tiles empty (rules `capture.respawn`). With no group worth
farming, `farm_turn` returned with the champion standing where it was, often on the camp tile of the group it had
just captured. Now a champion on a respawning group's camp tile steps to the nearest standable tile (camp tiles are
not standable), keeping out of the pack zone as farm does; a cleared group awaiting capture is unaffected. On
`02the-pack` and gen `mut-the-pack-600101820` three or four champions holding 160-460 gems held their groups back
600-800 rounds (3,956 blocked group-rounds -> 0). Against astraeus f22811d1: 50.2% of 10,240 on fresh-98401..98420,
out-of-fuel turns flat in games that played the same.

## 327: an emptied bag drops an enemy Prism's gem Focus (astraeus, 2026-11-03)

Prism gains 1.5 Focus per carried gem (rules `champions.prism`). An enemy's believed bag was emptied at death,
respawn, a tribute the score shows landed, or an inferred tributer, but its Focus, last read with that bag, kept the
gems' Focus: an unseen Prism read as strong as its last sighting with a full bag. `drop_bag` empties the bag and takes
its Focus with it at all four places (overestimated-Focus belief rows 28k -> 0.9k over 172 traced games). With a
capture-credit change since dropped: 50.0% of 10,240 on fresh-98801..98820 against f22811d1, out-of-fuel turns flat.

## 328: healing on our own spawn, in farm, siege, heal trips and exits (astraeus, 2026-11-03)

A turn ended on our spawn heals to full (rules `rounds.turn_end`), and no enemy can enter it (`map.spawn`). So camp fire
taken there costs one camp phase of health, not health carried away, and near the spawn a heal is a short walk rather
than a recall. One model now covers this (`economy/home.cc`), shared by pricing and execution:
- **Spawn stands.** `StandReach` (camps.cc) keeps, per group, the members a clear can hit from a spawn tile in range
  and sight, the strikers reaching that tile, and which spawn tiles they are. `min_camp_damage` prices a member hit
  from its spawn stand as free when that fire is within `home_survivable` (max health above the safe recall line).
  Crews price it at the least sturdy member's line.
- **Heal trips.** `heal_trip` is the walk home and back from the group's nearest stand that takes fire off spawn
  (`home_gap`), or the recall and the walk out, whichever is sooner. It is used by farm's `heal` and trip prices, the
  shop's `upkeep_cost`, Prism support and the siege. `note_upkeep` no longer counts camp damage taken on spawn.
- **The spawn board.** `home_board` (once a turn) holds the spawn tiles where the next phase's fire, as Safety reads
  it, stays within `home_room`. `home_room` is max health above the recall line at the spawn's centre: with an enemy
  near, the higher line, since enemies attack into spawn between the heal and the phase. A group's sleepers, which
  our hit wakes, are added per tile (`phase_fire`). The board is:
  - an exit from camp fire (`camp_exit_field`);
  - the target of the walk home (`home_exit_steps`);
  - the farm and siege stands (`home_stands`).
- **Farm.** Farm walks to a free spawn stand of its group first. In range off one, it steps onto an adjacent stand
  before the attack (a ranged attack costs the step). Melee hits and then walks on. A spawn tile whose fire has
  outgrown `home_room` is left for one that fits. The post-fight walk (`struck`) holds or seeks a spawn stand
  (`home_stands_near`) instead of walking off it.
- **Siege.** On spawn, a sieger is low only when `phase_fire` passes `home_room`, and then moves to a spawn tile that
  fits. Off spawn, it leaves when its health no longer covers the hits on its walk out of reach or home. It walks
  home when that is no slower than a recall (`walk_home_beats`: steps ≤ turn ends left + 1), keeping on until healed
  or home (`camp_fled`). `siege_ready` takes off the fire of members hit free from spawn (`home_free`, from live
  strikers). Past the pool test it accepts a siege the team keeps up in heal trips: usable health above where
  `siege()` sends a body home, slowing the clear. This replaces a first pass's spawn-distance test (ba56caa0 and 35825723, reverted for this).
- **Recall.** A recall for health is kept only while the walk home is longer (`walk_beats_recall`), in
  `continue_recall` and `siege_heal_trip`. A mend turn on spawn still hits the fully awake group we work (`mend_hit`).

Against astraeus 15a050a1 (round 2 with those first passes), own drafts, 33,412 games: 51.1% (50.5-51.6). That is 51.0% on 40 unused
fresh suites, 51.3% on 6,380 maps whose nearest striking camp is within 5 of our spawn, and 54.8 / 51.1 / 50.6% at
distance 1 / 2 / 3. Out-of-fuel turns +8.5%. Evidence: EXPERIMENTS "Healing on our own spawn".

## 329: altars sealed inside a camp ring: camp hops, the entry gate, and waking the ring on an enemy (astraeus, 2026-11-03)

On 02the-pack the only altar sits inside one 48-wolf ring; v68 never bought a crystal and went 0-10 on the ladder while
opponents teleported in to tribute. Design, rules and measurements: [sealed-altars.md](sealed-altars.md).
- **Camp hops** (`StaticMap::make_hops`, `Hop::camps`): an altar on foot but off the walk with every camp standing gets
  a crystal hop into its pocket. The draft flags such maps (`PlanHeader::camp_sealed`, plan version 9); everything
  is inert on other maps (`any_camp_hop()`).
- **Access and banking:** the hop keeps the pocket's tribute tiles open while `access_fire` still prices an awake
  ring; walks to an altar count only through its open tribute tiles; without a crystal, `bank_gems` heads home for
  one. An altar only a hop reaches stays sealed for the siege, which decides whether clearing the way pays.
- **Entry gate** (`ring_quiet`): no hop while a seen enemy could wake the ring before the tribute ends; a refused hop
  farms for the window instead of standing on the source.
- **Leaving:** sealed in a camp pocket, the turn ends once the bag is in so the turn-end recall goes out
  (`sealed_in`); a woken ring keeps the tribute channel.
- **Waking the ring on an enemy** (`wake_ring`): a visible enemy bag inside a sleeping ring that would die before its
  channel ends, with no ally in reach, is woken by a hit from a tile the members that could pick us fire on least.
- **Siege stall:** a siege still gathering that finds no step towards its gathering tiles gives the turn to farm.

Before the rebase onto 328: level on broad suites (50.1% of 20,652; 49.8% of 30,720 on fresh-97101..97160) with
out-of-fuel turns +1.7-3.0%, sealed map families 63.3% against main. With 328, against astraeus 4d2040c (both
CHANGES 328 and 329): ladder maps 54.7% (47.2-61.9) of 172, winning 02the-pack and 03homonoliths from both sides.

## 330: no walk home leaves a sealed camp pocket (astraeus, 2026-11-03)

From the merge audit of 328-329: `home_exit_steps` read the static walk to spawn, which crosses camps, so from a camp
hop's pocket (`sealed_in`) it gave a short walk home and a hurt champion banking there could drop its recall for a walk
no route makes. It now returns unreachable there; `sealed_in` takes the tile. Against astraeus 4d2040c, normal fuel,
fresh-97401..97480 (40,960 games): 50.5% (50.0-51.0), out-of-fuel turns 236,691 against 212,582; against v68 the same
suites: 50.5% (50.0-51.0), 236,236 against 207,826. Same suites with main before this fix (1b4430e3) not run; on
fresh-97301..97380 that version read 50.4% against 4d2040c, and 50.7% with unlimited fuel.

## 331: wake_ring's tile safety reads each member's reach once and skips a ring too weak to kill (astraeus, 2026-11-03)

Fuel only. `wake_ring`'s live members keep `min(reach, distance to the prey)`, the test stops once the fire reaches our
health, and when the whole ring's fire is under it no tile is tested (positive strengths, so no tile's sum exceeds the
ring's). Replays identical at 100M with 332-333 (wide 52/52, heavy 78/78).

## 332: nearest_groups by SIMD distances, its prefix sums stopping at the farthest group (astraeus, 2026-11-03)

Fuel only. The group centres are kept as bytes (coordinates under 100) and sixteen groups' Chebyshev distances are
taken a vector; the counting sort's prefix sums stop at the farthest distance. ~90 fuel a group read one by one:
16.8k a call on 126 groups, now ~11k. Same order (stable by group within a distance).

## 333: warm_centres prices its nearest-first order and resumes where it stopped (astraeus, 2026-11-03)

The turn-end queue's `warm_centres` made `nearest_groups` unchecked, which ran turns out on its own; it now asks
prepare_next_turn's price (100 a group + 3000) first and otherwise leaves the work to a later queue. Not a fuel gate:
only the warm-up is deferred, and a decision missing a centre field still builds it. It also resumes its order where
the last call stopped (fields stay made and `farmed` is static; a new `near` restarts it), ~70 fuel a group less a
queue. Replays identical at 100M with 331 (wide 52/52, heavy 78/78); the worker read gen-donut's real-budget
out-of-fuel turns 18 to 6.

## 334: four rare cases from the audit of 325-330 (astraeus, 2026-11-03)

Found by reading the code; each was confirmed there before it was changed.
- **The siege stall exit keeps the wait** (siege.cc). A siege still gathering that finds no step towards its gathering
  tiles gives the turn to farm (329), but it went through `stop_siege`, which restarted `staged_since`. The step
  also fails when fuel is short or the out-of-reach tiles (325) leave none. So a champion at the stage could alternate
  siege and farm, and `siege_max_wait` never ran out. Now the exit clears only `memory.siege`. In 12 instrumented games
  (6 ladder maps, both sides, against v69) it fired 22 times with the wait already started, all on 02guardians.
- **The walk home goes round live camps, to free spawn tiles** (`home_exit_steps`, home.cc). It read the static walk,
  which crosses camps: a hurt champion behind a respawned camp read a short walk home, so it cancelled its recall each
  turn for a walk that could not get through. The static walk is now only a lower bound. From there, floods
  (`reachable_tiles`) over `blocked_for_us` and `live_camps()` run one step deeper each time, up to a `longest` the
  caller passes: the longest walk that beats a recall (`walk_home_limit`), the siege's `max(steps_out, ...)`, or
  `mono_trapped`'s steps out. Past it the walk reads unreachable, since no caller takes a longer one. That also covers
  330's sealed pocket, so `sealed_in` is no longer called here. Usually it is one flood (~100 fuel).
- **The siege's walk home and its target read the same tiles.** `home_exit_steps` counted spawn tiles that allies stood
  on, while `walk_home` walks to `home_tiles`, which drops them. With every fitting tile taken, `low` used a walk home
  that did not exist, and the walk fell back on the stage square. Both now use `home_tiles`.
- **A ranged farmer leaves a burning spawn tile only for a stand it fires from** (farm.cc). Its refuge was any spawn
  tile that fits `home_room`. With no stand among its attack tiles, it stepped off, walked back, and never attacked. Now
  ranged leaves only for `home` (its group's stands, the sleepers it wakes counted). With none, it attacks from where it
  stands, as before 328. Melee, which hits before it walks, keeps any fitting tile.

Against v69 (3d4d9c52), own drafts, fresh-96101..96140 plus the 86 ladder maps (20,650 games): 50.0% (49.3-50.7);
ladder 48.3% (40.9-55.7) of 172; out-of-fuel turns 121,102 against 121,293; no failed matches.

## 335: a way found past the search cap stays walked (astraeus, 2026-11-03)

`Pathing::step_field` searched up to the static field's steps plus `max_detour`. When that failed it took the static
descent, and it ran the wider search (`here + 6 * max_detour`) only when no descent step was free. The static field
counts live camps as cleared. So where a live camp held the static way, the wider search found the long way round and
took its first step, which was seldom down the field. Next turn the capped search failed again, and the descent stepped
straight back. The two-turn cycle never ended. On 02guardians, v69's Marcella held 110 gems east of the sleeping Monolith
from round 809 to 963 (v68 did the same). It also hit bank, retreat and siege walks on shared-gems, hole-maze and
labyrinth maps.

The first search's cap is now at least our steps on the kept route (`kept_routes_`), when that route is to the same
goals, bounded by the wide cap. If its walls have not changed, `kept_steps` reads the steps with no search. If they
have, the search runs to those steps (at most the wide cap) rather than `max_detour` past the static ones. The deeper
cap also prices the existing fuel shortcut to the static descent, so under fuel pressure the cycle can still occur.

In 512 instrumented games (fresh-43001, against v68), wide steps undone by the descent the next turn fell from 752 to
67. Against astraeus 0c332d65, own drafts, fresh-43001..43040 plus the ladder (20,652 games): 49.6% (48.9-50.3);
ladder 54.1% of 172; out-of-fuel turns 124,749 against 126,340. Level, so kept as a logic fix.

## 336: no walk stalls on a respawning group's camp tile (astraeus, 2026-11-03)

A captured group returns only once its camp tiles are empty (rules `capture.respawn`). Farm stepped off them (farm.cc,
`best < 0`), but a walk that `step_safely` could not advance stood wherever its descent ended. On mut-fan-4300101836,
Prism captured a Wolf at round 430 and stood on its tile from round 481, holding 411 gems (a winning bag from about
round 600). Meanwhile Cassi waited on the altar's only reachable tribute tile for that Wolf to return. Three allies
stood still for some 1,100 rounds, and the Wolf came back only at round 1972.

Now, when `step_safely` neither moves nor breaches, and we stand off the field's goals on a respawning group's tile,
we step to the nearest standable tile (`Pathing::leave_respawning`, which farm's step-off now uses too). The same
game ends at round 844 instead of 1985.

Against 335 (4347ec62), own drafts, fresh-43001..43020 and 43041..43060 plus the ladder (20,652 games): 50.0%
(49.3-50.7); ladder 49.4% of 172. Level, so kept.

## 337: oscillation, stuck and target-switching fixes, four streams (astraeus, 2026-11-04)

Phase 1 traced ~7,700 games (astraeus against v61, v65-v69) with a per-turn `D` line (`bots/variants/astraeus-trace`,
`research/oscillation-2026-11-04/trace.patch`) and `tools/replay/osc_detect.py`; three investigators traced the
episodes to their mechanisms (`research/oscillation-2026-11-04/{A,B,C}-findings.md`). Four fixers then each took
one cause (notes in `research/oscillation-2026-11-04/<stream>-fix.md`):

- **1, terrain-aware enemy reach** (`model/enemy_reach.{h,cc}`): the turns an enemy needs to strike a tile, over
  walls, holes and dash crossings, replace straight-line reach in the pursuit horizon (`approach`/`stand`),
  `recall_outruns`, `may_chain`, `recall_line`, `paying_soon`, `engagement_near` and the travel-dash clearance
  (`Pathing::fight_near`). A champion with no walk home keeps its recall; a travel dash held for a fight still
  travels when no walk reaches the goals. Dashers no longer freeze on dash-only islands near enemies.
- **2, one verdict for stepping and leaving**: `leaves_at(p)` is want_home's verdict at p (recall line, pack zone,
  the stand with `pursued` read at p), and want_home is built from it. A lazy veto (`Pathing::set_veto`, armed by
  guard_work) asks it of the tile a work step or dash lands on, so work never steps where it would leave from next
  turn. Enemies seen last round count from their last tile.
- **3, farm pricing by the walk**: approach searches keep their result, failed ones included, and farm prices groups
  by them, so an unreachable target is skipped rather than re-picked; every champion falls back to `walk_on`; farm
  skips groups the enemy holds and prices an ally's long tribute as pending until it is near landing;
  `step_towards_funded` makes way; champions leave and unblock a due respawn's camp tiles.
- **4, kite and siege**: one team kite plan per big group (stations out of every monster's reach, casters by type,
  stations shared by comms claims; no station: farm), read by kite, farm and siege; an engaged siege that neither
  steps nor hits yields; siege judges "low" at the stands it walks to and walks only to stands it can hold.

Detector, 1,024 traced games against v69 on gen and gen-s1, episode turns before → after: stuck_fail -65%,
stuck_idle -55%, pingpong -44%, jitter -42%, retreatchurn -34%, branchflip -25%, wander -21%, goalflip -14%,
claimflip +3%; all kinds -22%. On shared-gems maps the old bot drew 0-0 on some; the kite plan won 60% of 448
games against 088bf3f4.

Against 088bf3f4, own drafts, fresh-88001..88040 (20,480 games): 50.6% (49.9-51.3). Out-of-fuel turns 458,675
against 111,325 (in 19,014 games against 12,528), mostly stream 2's stand simulation at vetoed landings (~16k a
time) and stream 1's reach: a fuel pass follows.

## 338: leaves_at works out the recall line and the hold only when its verdict reads them (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, veto). The work veto's `leaves_at` (combat/guard.cc) computed the hold (`hold_rounds`,
`hold_outlasts`), lethal, the recall line and the pursuit terms before its 8-entry `StandsRead` lookup, whatever the
verdict: a memo hit still cost 5-6.6k. `HoldAt` now works out its rounds on first read and keeps them, and the recall
line is read only by verdicts that use it. `drawn_home` tests the cheap health bound first: both recall lines are at
most `recall_health_fraction`. Notes: hyperion/fuel-campaign-6/NOTES.md `## veto`.

## 339: stand_lost_at reads lethal and pursuit only where its roster does (astraeus, 2026-11-04)

Fuel only. `Safety::stand_roster` is split into `stand_reach` (the seen and believed walks) and
`stand_roster(p, reach, ...)`; with a hit, the roster reads neither `pursued` nor `unseen`, so neither is computed, and
lethal is computed lazily, at most once. One trap: `own_ground` (inside `pursued`) builds the ally spawn field on first
need, and farm and camps price by a bound until that field exists, so `pursued` stays computed while
`!from_ally_spawn_ready()`. Without that guard 6 of 322 bench replays differed.

## 340: Safety::lethal skips the enemies' strikes when none is within any strike's reach (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, econ). With no enemy in sight, not every enemy known, the camps' damage at p under our
health, and no unseen enemy's possible tiles within `Strike::max_reach` of p (`unseen_beyond`), `lethal` returns false
without building the enemies' strikes: every blow at p is none, so `damage_bound` equals the camp damage and the old
path answers false too. Most of round 1's rise from 337 was this build at the first work step's veto (~12.5k a body).
A first version also ran with enemies in sight and cost +0.1% mean. At 100M some ~2k of round 1's work moves to round
2 (the caches it skipped are built there); round-2 out-of-fuel turns stay level.

## 341: label_through's memo keeps 16 walks (astraeus, 2026-11-04)

Fuel only: same key, more entries (4 before). A standoff's `make_way` asks ~9 walks a turn under 2-3 caps, so 4
entries thrashed. On the worker's q+osc census (real budget), out-of-fuel turns ending in make_way fell 808 -> 131 and
make_way's cost a call 11.0k -> 3.2k.

## 342: farm's loop keeps back what the work veto's next ask may cost (astraeus, 2026-11-04)

`Pathing::vetoed` measures each `veto_fn_` ask; `veto_reserve()` is the dearest recent ask, decaying by a quarter an
ask, while a veto is set. Farm's loop reserve and its `ample` bound add it, since the walk's landing is asked of the
work's veto (`guard_work`). It extends the loop's existing reserve (as 298 and 305 did), so it is not a new gate;
replays are identical at 100M (+0.02-0.04% total fuel for the measuring), and it changes play only at the real budget.
It measures the veto after 338-339, so the reserve shrinks with the cheaper asks. Round-1 out-of-fuel turns -23% in
the worker's A/B; farm-partial-evaluation +11-13% (the loop stops earlier to keep the reserve).

338-342 together against d6e74b6f (own drafts, real budget, fast runner): 49.1% (48.2-50.1) on fresh-66201..66220 and
49.7% (48.7-50.6) on 20 unused suites (seeds 66701..66720), 49.4% (48.7-50.1) of 20,480 games; out-of-fuel turns
196,967 / 237,559 and 202,235 / 246,397 (-17.1%, -17.9%). At 100M all 322 bench replays and the 16-game default bench
are identical. Evidence: EXPERIMENTS "Fuel campaign 6, round 1".

## 343: label_through's walks survive a failed search taken back from the spares, and serve lower caps (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, runaway). `route_gen_` was bumped on every field swap, so label_through's memo (341) missed
whenever a search came back from the spares. Each computed field now carries an id that moves with it (spares, kept
routes, the walk round), so an entry stays valid while its field is current. The walk at cap c is min{s+1+d : s <= c},
so an entry also answers a lower cap c' when the label it used is <= c' (unreachable stays unreachable). In a one-wide
dead-end jam (topo-shortcut-6621506918, six allies queued ~700 rounds) label_through per out-of-fuel turn fell
13.2k -> 7.3k and 9.8k -> 3.8k (its two sides). Notes: hyperion/fuel-campaign-6/NOTES.md `## runaway`.

## 344: a wider failed search drops its spares under lower caps first (astraeus, 2026-11-04)

Fuel only. A spare with the same start, goals and walls under a lower cap (or any cap, once `failed_` ran dry) answers
nothing the wider failed search doesn't, so its slot is freed before the LRU evicts a useful one, and a standoff's
distinct searches stay in the spares. In the same jam route per out-of-fuel turn 38k -> 33.6k and 36k -> 27.9k (on top of 343).

## 345: farm's loop keeps back the work veto's unmeasured first ask (astraeus, 2026-11-04)

342's `veto_reserve()` is 0 until the veto's first ask is measured, so the first turns' loops reserved nothing for it
(round-1 census: first ask median 3.7k, p90 4.9k, plus `ally_spawn_field` for `own_ground`, median 4.6k, max 40.8k).
While a veto is set and nothing is measured, farm reserves 5k plus `full_field_cost_estimate()` while the ally spawn
field is missing. It extends the loop's existing reserve, so it is not a new gate; replays are identical at 100M and it
changes play only at the real budget. Worker's bench: out-of-fuel turns in rounds 1-5 1,627 -> 1,360 (round 1 633 ->
490).

343-345 together against fc6-m1 (338-342; own drafts, real budget, fast runner, fresh-66301..66320, 10,240 games):
49.9% (49.0-50.9); out-of-fuel turns 200,640 / 203,481 (-1.4%), round 1 7,479 / 11,798 (-37%, rounds 2-10 12,714 /
11,716). At 100M all 322 bench replays and the 16-game default bench are identical (+0.00 to +0.03% total fuel, q
-0.19%, osc -0.04%). Evidence: EXPERIMENTS "Fuel campaign 6, round 2".

## 346: enemy_reach's walk lookup checks the slot last found for its key first (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, share). `walk_from` (model/enemy_reach.cc) scanned all 24 walks for its (from, dasher)
key, ~470 of `distance`'s ~680 a call. A 64-entry direct-mapped hint keeps the slot last found or made for a key
hashing there and is checked first. A slot matches only once made and no two made slots share a key, so the hint
returns what the scan would, with the same `used` update; `within` shares it. On the worker's census, distance on
out-of-fuel-first turns fell 2,725 -> 1,721 a turn. A/B against fc6-m2 (fresh-67201..67220, 10,240 games): 50.2%
(49.2-51.2), out-of-fuel turns 182,662 / 192,005 (-4.9%). Notes: hyperion/fuel-campaign-6/NOTES.md `## share`.

## 347: the work veto reads our own tile's leave only for a tile it would veto (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, tail). `work_veto` (combat/guard.cc) is `!leaves(here) && leaves(tile)` and worked out
`leaves(here)` first; about nine asks in ten clear their tile, so it now asks `leaves_at(tile)` first and our tile
only when that holds. Until the ally spawn field exists the old order stays: `own_ground` builds it on first need
and farm prices by it (the trap 339 also met). Dearer only where our tile leaves too (both stands run): fight's
dearest turn 368,355 -> 382,179. Notes: hyperion/fuel-campaign-6/NOTES.md `## tail`.

## 348: the walk's searches keep back the work veto's ask of their step (astraeus, 2026-11-04)

walk_on's `prepare_approach`, farm's two walk searches (`funded`, `search`) and static-descend kept back only
`end_reserve` after their search, but the step that follows is asked of the work veto (`guard_work`, 337): on
out-of-fuel turns whose last passed check was one of these, the veto took 64-70% of the fuel left there (~1.5-2
asks), and about half ran out inside it. Each adds `Pathing::veto_reserve()` (342; 0 while no veto is set). Their
fallbacks still step, but skip the search. It extends existing reserves, so it is not a new gate; replays are
identical at 100M and it changes play only at the real budget. A/B against 347 alone (fresh-67101..67120, 10,240
games): 50.3% (49.3-51.2), out-of-fuel turns -6.8%; static-descend 74k -> 134k, farm-no-route 53k -> 88k. (fc5's flat
14k near-enemy reserve at these sites lost; this is the veto's measured ask, only while a veto is set.)

## 349: prey keeps back the work veto's ask for the walk after it (astraeus, 2026-11-04)

prey's sims (combat/fight.cc) kept back a search and the turn's end. With no prey the farm walks next, its step asked
of the work veto; on out-of-fuel turns whose last passed check was prey's (10%), the veto ran after it on 89%. The
reserve adds the veto's measured ask (`Pathing::veto_cost()`, set or not: the chase itself walks under the strike
guard, unvetoed). Not a new gate; identical at 100M, real budget only. A/B against 347-348 (fresh-67101..67120): 50.0%
(49.0-50.9), out-of-fuel turns -8.2%; prey-cut-short 160k -> 253k.

347-349 together against fc6-m2 (fresh-67101..67120, 10,240 games): 50.4% (49.4-51.3), out-of-fuel turns 174,323 /
201,647 (-13.6%). 346-349 (fc6-m3) against d6e74b6f (own drafts, real budget, fast runner, 40 unused suites
fresh-67301..67340, 20,480 games): 49.9% (49.2-50.6); out-of-fuel turns 329,711 / 484,858 (-32.0%: the campaign's
338-349 at scale), round 1 -58%, games with 50+ out-of-fuel turns -42%. At 100M all 322 bench replays and the
16-game default bench are identical to fc6-m2's (total -0.06% fs to -0.47% fight; turns over 100k 133,953 ->
132,016). Evidence: EXPERIMENTS "Fuel campaign 6, round 3".

## 350: hops share an earlier hop's pocket, remember barren pockets, and list a ring by stamp (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, big). `make_hops` (model/world.cc) flooded the same pocket again for every altar and
camp source in it, and listed the ring with a `std::find` per rim tile. A flood from any tile of a pocket under the
same walls is that pocket, so a source inside an earlier hop's pocket copies that hop with its own altar, and a
pocket with no landings is kept in a barren board and never flooded again; the ring is listed by stamp. Round 1's
hops per body: gen-topo-shortcut 644k -> 95k, backdoor 245k -> 144k, odd-spawn 90k -> 73k. Notes:
hyperion/fuel-campaign-6/NOTES.md `## big`.

## 351: a whole flood searches a distance field when the map's layers would cost more (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, big). `reachable_tiles_into` costs the map's chunk count a layer with no cap; a
distance field's search costs at most 40k. `flood_into` (util.h) takes the field once the deepest field so far
puts the layers past that (~220 layers on 100x100): the hops' pocket and walk floods, `dash_flood` before the foot
exists and `add_group_hop`'s enemy walk. Not bank.cc's altar walk: it is flattened into farm_turn, where the call
cost ~23 fuel a turn in codegen.

350-351 together (fc6-m4b): at 100M all 322 bench replays, the 16-game default bench and 32 games on 16 topology maps
are identical to fc6-m3's; q round-1 mean 316,405 -> 285,754 (-9.7%), its dearest turn 1.15M -> 598k; other sets'
round 1 within 0.05%, round 2 level. Against fc6-m3 (fresh-67501..67520, 10,240 games): 49.9% (48.9-50.9),
out-of-fuel turns level (topology maps are ~2% of those suites). Against d6e74b6f (own drafts, real budget, fast
runner, 40 unused suites fresh-67601..67640, 20,480 games): 49.5% (48.8-50.2); out-of-fuel turns 311,551 / 462,889
(-32.7%: the campaign's 338-351 at scale). Evidence: EXPERIMENTS "Fuel campaign 6, round 4".

## 352: the strike search reads and grows only the stay and walk leaves when no strike reaches a foe (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, exact). Ranged walkers with no strike were 35% of strike searches and 31% of their fuel
(18.6k mean): a stay leaf and walk-alone leaves only, but read and grow ran in full. `strike_free` code 4
(combat/plan.cc) now answers for a ranged walker with no foe within any strike's reach of any end tile: read() takes
only the foes' health, Heart of Ruin and kill bits, and the root settles without growing. A ranged attack's bound is
max(range, range + walk with a reset, range + dash with an attack): a ranged walk spends the attack and a dash takes the
one cast. Against fc6-m4b on the same 20,480 games (fresh-67921..67940, fresh-66001..66020): +0.21 points paired (-0.22
to +0.63), out-of-fuel turns -1.4%. Notes: hyperion/fuel-campaign-6/NOTES.md `## exact`.

## 353: farm keeps back the veto's unmeasured first ask only for a group to walk to (astraeus, 2026-11-04)

Fixes 345 (fuel campaign 6, audit; real budget only). 345 kept back 5k plus a full field while no veto ask was measured.
With no group yet, weighing the first one may need a field from here, and with both fields kept back it never fit: no
group was chosen, nothing walked, the veto was never asked or measured, every turn. All four champions sat on spawn all
game on gen-gem-drought-6770405800 and gen-topo-shortcut-6770806907 (4 of 10,240 games against v69, all lost). The first
ask is now added only to a group's loop reserve (`g >= 0`), so later passes still keep it. It is added inside the
per-group reserve, not at the reserve's return: the worker's form shifted farm_turn's flattened codegen (fs +0.45% total
fuel at 100M, every set dearer); the merged form is +0.00%. Identical at 100M. Against fc6-m4b on the same 20,480 games:
-0.07 points paired (-0.33 to +0.19), out-of-fuel turns level (round 1 up: the opening's first group is weighed without
the reserve). Wasted turns against v69 (bridged osc_detect, all+oof, 10,240 games): -0.63% (-1.14 to -0.11). Notes:
hyperion/fuel-campaign-6/NOTES.md `## audit`.

352-353 (fc6-m5b) against d6e74b6f (own drafts, real budget, fast runner, 40 unused suites fresh-67921..67940 and
fresh-66001..66020, 20,480 games): 49.9% (49.2-50.6); out-of-fuel turns 322,838 / 487,656 (-33.8%: the campaign's
338-353 at scale; fc6-m4b on the same games 49.7%, -32.7%). At 100M all 322 bench replays and the 16-game default bench
are identical to fc6-m3's (total -0.21% fight and osc, others within 0.13%; turns over 100k 132,016 -> 131,239). Not
shipped: the exact worker's lazy stand walkers (fuel only; -0.73 points paired, -1.42 to -0.04, OOF +1.4%) and round 4's
post-strike veto refusal (a28721f3; -0.58 points, 49.1% against d6e74b6f). Evidence: EXPERIMENTS "Fuel campaign 6, round
5".

## 354: decode_steps keeps the plan reader in locals (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, init). decode_bounded and the offsets loop read the reader, the Rice parameter, the boxes
and the data pointers through `this`, which clang reloaded after every store to the steps (~110 fuel a group a kind).
Copied into locals: on fuel-stress maps (fs) the ally steps 25.2k -> 23.7k a body, altar 14.0k -> 12.8k, offsets
13.8k -> 11.7k. Notes: hyperion/fuel-campaign-6/NOTES.md `## init`.

## 355: build() takes the group count from the engine (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, init). The camp layout was walked to count groups and members (~30 fuel a group).
`sdk_map_num_camp_groups` gives the groups and the layout's length the members; a layout that does not add up is walked
as before. fs -6.6k a body in round 1.

## 356: find_crossings tests only the camp tiles near a crossing (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, init). landing_dash_walls reads striking members' tiles only within 2 of a crossable tile.
With 24+ groups, the crossable tiles are dilated (squares of radius 2 when few, else square_dilate), ANDed with
camp_tiles, and only those (up to 128) are tested for striking groups, instead of copying camp_tiles, clearing every
non-striker's members (~60 a group) and dilating. Fewer groups keep the old form, which is cheaper there. fs crossings
~25k -> 13-15k a dasher.

## 357: camp groups and beliefs are written whole, not constructed then written (astraeus, 2026-11-04)

Fuel only (fuel campaign 6, init). `map.groups` and `World::camps` use `UnwrittenAllocator`, whose resize writes
nothing: build() placement-news each group as it fills it, and init_beliefs stores one prototype CampBelief held in
v128 locals over each (constructing each was ~110 a group; a memcpy compiles to memory.copy at a fuel a byte).
init_beliefs camps 24.5k -> 19.8k on fs.

354-357 (fc6-m6): at 100M all 322 bench replays and the 16-game default bench are identical to fc6-m5b's; round-1
mean fs 607,449 -> 578,852 (-4.7%), q 285,759 -> 283,534, oof 251,258 -> 248,480, others -0.2 to -1.4%; round 2 and
later level (total -0.00% to -0.09%). A fs body still cannot finish round 1 inside 200k (its world init is ~201k).
Against fc6-m5b (fresh-68101..68120, 10,240 games): 49.5% (48.6-50.5); out-of-fuel turns 160,548 / 157,701 (+1.8%, all
from one 2000-round game on gen-leaky-diagonals-6811007814 that m5b's code also reaches; +0.5% without it), round 1
-6%. Evidence: EXPERIMENTS "Fuel campaign 6, round 6".

## 358: every advance that is not a hit asks the work veto; short-fuel walks search less (astraeus, 2026-11-04)

Round 2 of the oscillation hunt (`research/oscillation-2026-11-04/round2-findings.md`, `r2-2-fix.md`). The work veto
(337) saw only work steps: the strike search's executed move and chase's step ran before it was armed, and stepped
where want_home sent us back from. Now:
- a strike-search plan that hits nothing has its end tile asked once; a refused best plan gives way to the best plan
  that hits or stays (a hit is never refused; a dash counts as a hit only where it lands on someone);
- chase's step is asked unless a hit follows it; a refused chase hands the turn to the work;
- the search, chase and work share one verdict memo for the turn;
- `step_field` searches as deep as the fuel left pays for, instead of skipping the search for the static descent;
- a bag refused short of its altar waits there as carry_bag waits at an altar it stands on, then avoids that altar
  (`Pathing::hold_refusals`, bank.cc `walk_to_altar`/`wait_for_altar`): the leaky-diagonals bank runaway (873 turns
  between two tiles) is gone.

Detector against main on the same 1,708 games vs v69 (osc_compare, `--bridge-oof`): all episodes -4.3% (-7.2 to
-1.5), pingpong -12%, jitter -18%, retreat churn -9%, stuck_fail +12% (refusals on capture and siege walks, which
have no fallback). Against 8c0f3d49, own drafts, fresh-91021..91040 and 99101..99120 (20,480 games): 50.0%
(49.4-50.7); out-of-fuel turns 336,326 against 311,179 (+8.1%), mostly chase's asks (up to 8 first steps at 2-16k
each): bounding them is open.

## 359: the work veto and the stand's believed enemies removed (astraeus, 2026-11-04)

The work veto (337, its asks 358) cost 2.2x the out-of-fuel turns for no win rate: `Pathing::set_veto` and all that
served it (`vetoed`, `refuses`, `hold_refusals`, the merged guard, the veto reserves of 342, 345, 348, 349 and 353,
347's own-tile read, guard.cc `work_veto`, bot.cc's arming before the strike search, plan.cc's no-hit refusals,
chase's ask, bank.cc's altar hold) is gone, and with it `leaves_at`, `stays_here`, the stand memo `StandsRead`,
`Safety::no_worse`, `Safety::stand` and the 4-argument `stand_roster`. want_home keeps 337's parts (`HoldAt`,
`drawn_home`, `stand_lost_at`) and 338-340's laziness. At 100M every replay is byte-identical to 19f22154 with the
veto never armed. The stand and want_home's early return read only visible enemies again (337's believed enemies:
`stand_reach`'s second loop, `enemy_believed`); recall_outruns, paying_soon and fight_near still count those seen
last round. Kept from 358: `step_field`'s fuel-bounded search. Also: fight_near's memo keys on the observations
too (a ward's reveal mid-turn), siege's camp fire is one `fire_at` over a cover built once.

Fresh-99318..99357, own drafts, 20,480 games each: against 19f22154 49.8% (49.1-50.5), out-of-fuel turns 142,066
against 336,151 (-58%); against 088bf3f4 50.0% (49.3-50.7), 142,241 against 115,653 (+23%); against the veto removal
alone (believed enemies kept) 49.6% (48.9-50.3), 144,335 against 147,138. Evidence: EXPERIMENTS "Oscillation work,
final check and the veto ablation".

## 360: one safety model for keeps and the work guard; unseen enemies struck once per turn (astraeus, 2026-11-04)

`paying_soon` and `recall_outruns` ask `Safety::may_reach_within`, which reads an unseen enemy from `possible`
rather than from its last tile with its turns since uncounted (`Safety::walk_in` removed), and counts a stunned
enemy's walk a turn later, as `approach()` does. Willow's leave test in want_home is `exposure_here().enemy`, the
test its stations' guard keeps it off tiles by. The work guard's `keep_out` asks want_home's own `drawn_home` at each
tile beside us (`drawn_home_at`) instead of its copy of the recall line and pack zone. `threat_strike` no longer
counts twice the turn an unseen enemy takes after ours this round: World::track has grown `possible` through it
already, so the strike from `possible` (`moved_strike`) drops that turn's walk, dash travel and walk-then-stun,
a second turn before ours still full.

Against e73fe3ca on fresh-99401..99420, 10,240 games: 49.8% (48.8-50.8), out-of-fuel turns 72.1k against 70.9k;
the double count on top, fresh-99421..99440, 10,240 games: 50.1% (49.1-51.1), 71.1k against 71.3k. Level and free;
shipped for the single model. The unseen stand and step guard and the own-ground stand in `keep_out` were left out
(+70% and more out-of-fuel turns, level). Evidence: EXPERIMENTS "One safety model".

## 361: unseen enemies read where they may be, not at their last tile (astraeus, 2026-11-04)

Every test that read an out-of-sight enemy at its last tile (`e.pos`, `age(round) <= 1`) reads its `possible` tiles,
counted while Safety counts it (`Safety::credible_unseen`): the pack zone (an unseen member's box around its possible
tiles, off its spawn), `may_draw_home`, `pack_covers`, `preyable`, `chase_aim`, bank's `ring_quiet`, capture's
`enemy_may_see`, `Pathing::fight_near` (`Safety::unseen_within`, through `Pathing::use_safety`), the turn order's
`enemy_dist`, and the stand: `stand_reach`, `late` and `turns_to_kill_idle` by `Safety::unseen_approach`, and
stand_lost_at's early return by `unseen_may_hit_within(p, pursuit_steps)`. Left on the last sighting: prey and chase
aim, the sealed-pocket prey, `walk_allies_in`, the retreat tie-break and the in-sight tests. `unseen_approach` reads a
per-enemy capped Chebyshev field once an enemy is asked about near a second tile.

Against 7b4f4ad on fresh-99561..99580, 10,240 games: 49.7% (48.7-50.6), out-of-fuel turns 85.2k against 72.3k
(+18%). Level; shipped for the single model. Evidence: EXPERIMENTS "Unseen enemies where they may be".

> **362-384 are in `bots/astraeus_wip`, not astraeus** (2026-11-04). Together they lost 46.0% to 57194754 on 40k
> games at the real fuel budget (out-of-fuel turns 1.03M vs 351k) but were 50.6% at 10M fuel a turn: the loss is fuel.
> `bots/astraeus` was restored to 57194754 (CHANGES 361) until their cost is cut; see EXPERIMENTS "Phase 1-2 fuel".

## 362: walking distances for capture races, claims and sides (astraeus, 2026-11-04)

Straight lines replaced by walks where the code compares who gets somewhere first: `capture_taken` ranks allies by
the walk onto the group's camp tiles (`walk_to`: `Pathing::to_group`, the straight line where no walk reaches);
contest_capture's race against an enemy hold and kite's `too_late` read `to_group` (the vision prefilter stays);
kite ranks groups by `walk_to`; the takeover that keeps farm's floor prune off needs a walk under capture_time;
kite's guard wait and farm's opening heal and home trips read the drafted `ally_steps` instead of the line from our
spawn centre; Willow's homeward tie-break reads `to_ally_spawn`; place_lock's "our side" compares the walks from both
spawns to the altar's tribute tiles (`our_side`, kept per altar, +2 margin kept). The lower bounds (`steps_to`,
`via_bound`, `reach`, `least`) stay.

Against 57194754 on fresh-147001..147020, 10,240 games: 49.9% (49.0-50.9), out-of-fuel turns 89.7k against 88.7k.
Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1a".

## 363: the tribute race by walks and locks (astraeus, 2026-11-04)

`win_lands`, when our winning bag is not yet channelling, prices the walk to an altar's tribute tiles
(`Pathing::to_altar`) plus breaking its enemy lock (`lock_turns`, now in bot_parts.h), not the straight line less the
tribute range; `stoppable_winning_tribute` and `game_ender` take Pathing for it. `carrier_tribute` picks the enemy
carrier's altar by its walk over the enemy's static walls (a dasher's across what its dash jumps:
`enemy_altar_field`, kept per altar) plus breaking our lock there (5 hits), not the nearest altar as the crow flies.
Both fall back to the straight line where no walk reaches an altar.

Against CHANGES 362 on fresh-147021..147040, 10,240 games: 50.1% (49.1-51.1), out-of-fuel turns 100.4k against
94.5k. Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1a".

## 364: camp-hit ties by turn order; a priority heal only where it can land (astraeus, 2026-11-04)

`ally_camp_fire` (HealGate's camp damage on an ally) gives a monster's hit at equal distance to whichever champion
acts first in next round's order (`World::slot`, rules camps.attack), not to nobody nearer. `offer_heal` bids for a
priority heal only if a tile we may heal from next turn has the ally within heal range and in sight
(`heal_reaches`): our tile, else a free standable step that `attack_viewers` lists, or any once our ward sees it.

Against CHANGES 363 on fresh-147041..147060, 10,238 games: 50.3% (49.3-51.2), out-of-fuel turns 97.5k against 96.5k.
Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1a".

## 365: capture holders by the remainder share; siege capacity in effective health (astraeus, 2026-11-04)

`holders` splits until the biggest share, the lowest id's floor plus remainder, fits the tribute window (10 gems over
4: 4, not 3); it stays a function of the group alone, so every ally names the same count. `siege_ready`'s pool counts
each body's health over its own `camp_taken` (current health for us and allies in sight off our spawn, full health
for the unseen and those on spawn), so our `camp_hit_factor` no longer scales the whole team's fire; `leave` and
`usable` are in the same units.

Against CHANGES 364 on fresh-147061..147080, 10,240 games: 50.1% (49.2-51.1), out-of-fuel turns 100.0k against
99.8k. Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1a".

## 366: shield absorption while clearing by whole casts (astraeus, 2026-11-04)

`shielded_clear` counts the casts a clear holds instead of a fractional rounds / cooldown: casts start `ready_in`
rounds in and then every cooldown, each absorbing at most its amount or the fire over its window (the duration, or
what is left of the clear for the last), so a short clear gets a whole cast's worth. Still constant time and rising
with the damage. farm's alone-clear price passes our live shield cooldown for the group we are clearing (`farm_group`,
awake); every other clear starts with the shield ready.

Against CHANGES 365 on fresh-147081..147100, 10,240 games: 50.5% (49.6-51.5), out-of-fuel turns 93.2k against 91.5k.
Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1a".

## 367: the draft's camp-heal cost by the drafted walk (astraeus, 2026-11-04)

`type_facts` (the draft's leads, which choose between a body's kite and a plain clear) prices a heal trip from the
drafted walk between the recall's landing tile and the group (`landing_steps`: its spawn tile's steps, else the
ally-spawn field's), taking the quicker of walking there and back or recalling and walking back, as the runtime's
`heal_trip` does, not a recall plus the straight line. Unreachable groups keep the straight line. It changes the leads
written into the plan; picks come from draft_model.h.

Against CHANGES 366 on fresh-147101..147120, 10,240 games: 50.0% (49.0-51.0), out-of-fuel turns 91.6k against 91.7k.
Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1a".

## 368: capture races on one walk for the team; a shield already up while clearing (astraeus, 2026-11-04)

Fixes to CHANGES 362, 366 and 363. `capture_taken` ranks our walk and allies' by `team_walk_to`
(`Pathing::to_group_walking`: walking only over `blocked_for_us`, kept per group), not `walk_to`, whose field follows
the asking body's dash kind: Issac's dash crossed what Cassi's walk could not, so the two could each count the other
ahead, or neither. Every ally now runs the same race; kite, the contest race and the takeover, which decide only for
us, keep `walk_to`. farm's alone-clear price for the group we are clearing also subtracts the shield already up
(`min(shield, fire a round x its turn ends left)`, a window before the next cast's), which `shielded_clear` from its
cooldown left out. `intercept_steps`' comment names `carrier_tribute`'s altar, not the nearest.

Against CHANGES 367 on fresh-148121..148140, 10,240 games: 50.3% (49.3-51.3), out-of-fuel turns 95.6k against 95.1k.
Level; shipped as the fix. Evidence: EXPERIMENTS "Phase 1a".

## 369: crews and pick-ups by the walk to the group (astraeus, 2026-11-04)

`crew_arrival` (share_damage's 2-round arrival cutoff) reads the walk onto the group's camp tiles less the attack
range, not the straight line, still kept per group and body by tile; plan_crew ranks its free helpers by that
arrival, not the straight line to the group's centre, and a helper that saves no trip is skipped, not the end of
recruitment. pick_up decides who takes a cleared group by the walk for us and each claimer, after the straight-line
`pick_up_radius` filter, and its step's search cap is our walk plus `max_detour`. All compare our walk with allies',
so they read `team_walk_to` (CHANGES 368). Pathing passed into `crew_arrival`, `share_damage` and `plan_crew`.

Against CHANGES 368 on fresh-148001..148020, 10,240 games: 49.6% (48.7-50.6), out-of-fuel turns 106.5k against
97.4k. Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1b".

## 370: combat values from the strike that is ready (astraeus, 2026-11-04)

`stun_worth` values an enemy in sight (cooldowns known) by the damage of the turn it loses: `strike` at its next turn
(cooldowns then) at the distance to our nearest body, us included, not its stats-only `output`; unseen, `output`
stays. `Safety::tie_hit` sums the tied, unstunned camp hits at a tile instead of taking the strongest: acting first
draws every one of them in that phase (idle_priority's hits in hand are then phases in hand). The escape dash ranks
landings by expected damage, not depth in straight-line reach: a visible enemy's `threat_strike` blow at that
distance (at least 1 where it reaches, so a stun counts), and an awake monster's hit on us (`camp_hit_factor`) only
where we would be its target, the nearest champion with ties to who acts first next round (`ally_camp_fire`'s rule);
0 still means nothing reaches us. `offer_heal` prices an enemy's two turns before our heal like `two_turns`: the pair
over first-turn slots that deals the most (`two_blows`), split by turn, not a strike and then a basic attack.

Against CHANGES 369 on fresh-148021..148040, 10,240 games: 49.7% (48.8-50.7), out-of-fuel turns 107.0k against
103.5k. Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1b".

## 371: camp targets, breaches, ambushes and sieges by the hits that land (astraeus, 2026-11-04)

Varg's camp-target score adds each member its splash reaches in the main score's units, Strength per health times
the share of our hit it takes (`min(1, hp / hit)`), not +1 a member; another group's members count only once it is
fully awake, since the splash wakes a sleeping one. `breach` counts the turns its hits take with the reset (two hits
a turn whenever it is ready: from its cooldown, a turn later if the cast is spent, then every cooldown), not one hit
a turn. The sealed-pocket ambush adds a visible prey's shield, up to the fire over its turns left, to the health the
ring must burn through; an unseen prey's is not trusted. `siege_ready` no longer skips its health checks whenever a
visible enemy stands in the group's reach: a member whose nearest champion is a visible enemy, nearer it than our
nearest stand (our shortest attack range, ties to us), has its Strength taken off the fire the checks price.

Against CHANGES 370 on fresh-148041..148060, 10,240 games: 50.0% (49.1-51.0), out-of-fuel turns 101.9k against
102.0k. Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1b".

## 372: the tribute deadline by our share; Capture's value by the rounds it would have saved (astraeus, 2026-11-04)

farm's `too_late` prices the tribute of our share, not the whole reward: the lowest id's over `holders(G)` (the crew,
if smaller, for a crew's clear), remainder and Prospector's extra included, as `known.gems` adds it. A recorded
capture payout credits the Capture emblem with the rounds our own emblem would have cut off it (rules
capture.timing: R + 4 held from R, J + 3 joined at J, never later than it paid, so an ally owner's speed-up counts),
from the hold's start (`held_since`) and our join round, both tracked at our turn ends, not the full 2 rounds for
every hold; the prior's form is kept. With Collectors owned, `or_passive` prices each passive family's shards by
their own `value`, whose +1% damage holds only for a new family; otherwise one shared value, as before.

Against CHANGES 371 on fresh-148061..148080, 10,240 games: 49.9% (48.9-50.9), out-of-fuel turns 117.8k against
112.8k. Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1b".

## 373: paths forget the camps we kill; Willow walks to her heal's tiles (astraeus, 2026-11-04)

`World::observe` mid-turn refreshes vision and champions but not camps, so Pathing's live board and `blocked()` held
a member we had just killed until next turn. Every basic attack or cast at camps bumps `camp_strikes()` (beside
`camp_hits()`, plus the fight plan's camp attacks and ground casts, which `camp_hits` leaves out); Pathing then reads
the engine's liveness of the believed-live members within a ground cast's reach of us, drops the dead from its live
board (and its per-group bits, so next turn's rebuild stays right), and invalidates. World's camp beliefs are left
alone: capture and cleared-group logic read them. Willow's formation step, outside heal range, measures progress and
`gap` by a capped walk (16) round walls and units to the tiles her heal works from (`formation_view`), not the
straight line to the mate, so she can step round an obstacle; past the cap, the cap plus the line.

Against CHANGES 372 on fresh-148081..148100, 10,240 games: 49.4% (48.5-50.4), out-of-fuel turns 131.4k against
120.8k. Level (the CI's top is above 50%); shipped as the calculation. Evidence: EXPERIMENTS "Phase 1b".

## 374: sight for a sole holder's unseen watchers, unseen enemies' approach, heals in the fight sim (astraeus, 2026-11-04)

`enemy_may_see` (only `sole_capture_holder` asks, once no enemy is in sight) counts an unseen tracked enemy only if a
tile it may be on can see p: the tiles that see p by the symmetric shadowcast over walls and bushes, from a bush
over walls alone (as `sight()` reads it), a bush tile only from bushes; kept for the last tile asked. Enemy wards
are unknown, so a sole holder is a little bolder. `walk_allies_in` no longer makes every ally arrive at once when
the fight has an unseen enemy: an ally's delay is its turns until a tile the enemy may be on is within its strike
(`Safety::unseen_walk`, by bisection as `unseen_approach`, at most 16, kept per ally and enemy for the Safety's life),
0 if it could be anywhere. In the fight sim a healer heals the weakest hurt member its heal reaches: within its range
and a step, seen from its tile (the shadowcast) or, for ours, by its ward; each healer in sight's champions are
worked out once per Safety (`heal_masks`), an unseen healer reaching all as before. `ward_sight` and
`own_ward_sees` move from support.cc to safety.cc for it.

Against CHANGES 373 on fresh-148101..148120, 10,240 games: 50.1% (49.1-51.0), out-of-fuel turns 132.7k against
122.5k. Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1b".

## 375: heal_reaches on support's heal helpers (astraeus, 2026-11-04)

Fuel only. support.cc's `heal_viewers` and `support_view` move to safety.cc beside `ward_sight` (declared in
safety.h), and turn_order.cc's `own_ward_sees_tile`, a copy of `own_ward_sees` that cast the ward's vision again on
every call, is gone: `heal_reaches` reads `heal_viewers` (every tile in range while our ward sees the ally, else
`attack_viewers`; its own-tile bit is past the early return) and tests each step with `support_view`. Bench replays
identical, 16/16 at 100M and 52/52 on `--set wide`; total fuel -0.00%.

## 376: heal positions on dead camp tiles (astraeus, 2026-11-04)

`map().standable` rules out every monster spawn tile, even a dead monster's, which is walkable. Support's step loop
tests `open_for_us` instead and leaves live monsters to `pathing.blocked()` (which holds `live_camps()`, less our
kills this turn since CHANGES 373); `heal_reaches` tests `open_for_us` and no member believed alive on the tile
(`live_camp_on`, the beliefs as `live_camps` reads them). Willow's skip of a cleared group's tiles, never reached
under the old test (both came in with the v40 import), now applies: she stands on a dead member of a live group or
a respawning group's tile, not on a capture waiting for holders.

Against CHANGES 375 on fresh-148141..148160, 10,240 games: 50.0% (49.0-51.0), out-of-fuel turns 144.2k against
144.5k. Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1b".

## 377: a carrier's way through our lock by the hits left on it (astraeus, 2026-11-04)

`World::update_altars` keeps our visible locks' `hits_remaining` (`AltarBelief::ally_lock_hits`) as it does the
enemy's, and `carrier_tribute` adds those hits for an altar we lock, not a flat 5, so hits the enemy already landed
count; 0 or unread falls back to `altar_lock_hits`, as `lock_turns` does.

Against CHANGES 376 on fresh-148161..148180, 10,240 games: 50.2% (49.3-51.2), out-of-fuel turns 140.1k against
140.2k. Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 1b".

## 378: an enemy's two blows by the larger first on a tie; no Capture credit with an ally owner on the hold (astraeus, 2026-11-04)

Fixes to CHANGES 370 and 372 from the phase 1b audit. `two_blows` tried first-turn slots 3, 2, 1, 0 and kept the
first strictly larger sum, so two damage spells (Stellar, Prism), whose sums tie in either order, put the weaker one
first: `offer_heal` then undercounted `before` when the enemy's second turn falls after our heal. A tie now keeps the
larger first blow. The Capture credit read the hold's start from the engine's countdown (`held_since`, round + timer
- 6), which an ally Capture owner on the hold shortens, so R came out early and a hold we joined from its start was
credited as joined late (J + 3, not R + 4): a hold on which a visible ally with `fast_capture` stood at one of our
turn ends is credited nothing (`Income::hold_fast`). Comments: `enemy_may_see`'s back above it, not `viewers_of`;
`enemy_in_reach` no longer says the enemy takes the nearest-champion hits.

Against CHANGES 377 on fresh-149121..149140, 10,240 games: 50.0% (49.0-51.0), out-of-fuel turns 141.4k against
141.5k. Level; shipped as the fix. Evidence: EXPERIMENTS "Phase 1b".

## 379: unseen enemies and allies walk round walls to where they strike (astraeus, 2026-11-04)

An unseen enemy's approach read Chebyshev distance from `possible` over an empty board, as if its walk to an attack
tile ignored walls. It now reads enemy_reach's D from all of `possible` (`UnseenLayers`, per enemy, made per Safety
as asked): the tiles within k king steps of `possible` over its static walls (a dasher's across what its dash
jumps), widened by its act range, so D <= act + k is one bit test; within act, still the straight line; past 16
steps, the straight line. `unseen_approach`, `unseen_may_hit_within`, `may_reach_within`'s unseen branch, the unseen
Threat (its area and `at()` past its act range) and `unseen_blow` read it; `credible_unseen`, `unseen_weight` and
`unseen_radius` are unchanged, and each_threat's bound stays the straight line. `walk_allies_in` delays an ally
behind a visible enemy by D from the ally over our side's walls by its own dash kind (`StaticMap::our_walls`;
without a dash of our own, an ally's dash walls are made on first ask), less its reach (`Safety::ally_walk`, kept
per ally and enemy for the Safety's life), not the straight line; the unseen half (CHANGES 374) stays. enemy_reach's
walks are keyed by wall kind (32 slots, from 24).

Against CHANGES 378 on fresh-149001..149020, 10,240 games: 49.2% (48.2-50.2), out-of-fuel turns 176.8k against
138.9k (+27%). Level (the CI's top is above 50%); shipped as the calculation. Evidence: EXPERIMENTS "Phase 2".

## 380: the fight sim's Heart of Ruin by its health; camps after our fall by who they would hit (astraeus, 2026-11-04)

Heart of Ruin's passive in the fight sim read its damage at its last-read health for the whole fight. Each fighter
now keeps its damage scale at the health it entered with (`Fighter::ruin`) and rescales its Strength and cast damage
(the dash landing's included, its shield not) by its simulated health whenever it deals them. A change in its health
ends its side's quiet stretch (`Side::touched`), and `play_quiet` / `play_shielded` leave a Heart of Ruin taking the
hits (or the camps') to `act()`. The bounds read a Heart of Ruin's Strength and casts at their most (0 health:
`their_cap`, `their_rest`, `overwhelmed`'s own damage and a stun's Strength) or least (full health: `overwhelmed`'s
basic attacks). Once we fall, the camps no longer hit our side's weakest: each ally takes the hits the camps would
deal it with us gone (`Safety::camp_if_gone`: ally_camp_fire's nearest-champion and tie rule without us, kept per
ally for the Safety's life), in the stand fights the camps join (`stand_trade`); `their_cap`'s rate takes the larger
of our camp fire and theirs, and `overwhelmed` counts the camps only when nobody of ours outlasts us, since a hit
past an ally's health is lost. Enemies near camps are left as they were.

Stuns on the damage's target (Prism's, Tavi's and Ren's unit stuns and Marcella's stunning attack on the side's
weakest, not its strongest) were left out: with them, against CHANGES 379 on fresh-149021..149040, 10,240 games:
48.6% (47.6-49.6). Without, on fresh-149141..149160, 10,240 games: 49.9% (48.9-50.8), out-of-fuel turns 214.2k
against 190.3k (+13%). Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 2".

## 381: allies' strikes in a kill bid by their real distance (astraeus, 2026-11-04)

`side_damage` (offer_kills' kill bid) read each ally's strike at the straight line to the enemy. It now reads it at
`real_distance`, generalised from ours to any ally in sight for its turn's round: its own range, its ready damage
spell (which keeps the line) and ready dash, its own ward (`sdk_wards` by owner), its tile among the tiles that see
the enemy, and the tiles walls, camps, visible enemies, the enemy spawn and the other allies (us at our tile) leave
it; past max_reach when none. Kept per ally, enemy and round for the turn (`ally_distance`, reset when we move).
`side_damage` takes the enemy rather than its tile.

Against CHANGES 380 on fresh-149041..149060, 10,240 games: 50.5% (49.5-51.5), out-of-fuel turns 230.0k against
213.0k (+8%). Level; shipped as the calculation. Evidence: EXPERIMENTS "Phase 2".

## 382: a stun on a tributing enemy by the rounds it puts off the tribute (astraeus, 2026-11-04)

`stun_worth` priced a tributing enemy's stun at its whole bag (`gem_value * gems`), though it keeps the gems and can
start again. The bag is now priced by the delay: the lost turn, then the channel restarted whole
(`tribute_turns(gems, its Tribute emblem)`) against what was left of it, `gem_value * gems * delay /
stun_tribute_horizon` (10 rounds: untuned, a policy weight). `kill_stops` (the flat tribute value and a winning
tribute's urgency) is unchanged.

50.1% (CI 49.1-51.0) of 10,240 games against bundle 3; out-of-fuel turns unchanged (218.5k / 218.4k).

## 383: the shop's quotes refresh when income or the horizon move (astraeus, 2026-11-04)

`prices()` and `affordable_prefix()` kept their quotes under share, stats, main stat and gold, though they also read
upkeep, the income rates and `bag_rounds_left`. Both keys add `Income::version` (bumped on a capture payout, a kill's
gems or gold, and a Tribute emblem's cut) and `income_rates`' horizon in 5% steps (`horizon_bucket`), so a quote is
worked out again when those move, not every round.

49.8% (CI 48.8-50.8) of 10,240 games against bundle 4; out-of-fuel turns 259.5k against 235.2k (+10%).

## 384: camp stands on tiles that see the member (astraeus, 2026-11-04)

`stand_reach`'s table (which strikers reach the tile a clear stands on to hit each member) placed every stand
`range` from the member away from the group's middle, which could be a wall, hole or camp tile or out of the
member's sight. It now takes, of the standable tiles within `range` that see the member (`sight_off_bushes`, as the
spawn stands read it; sight is symmetric), the nearest the old tile; the old tile only where none does. Still built
once per group and range, on first ask (`sight_off_bushes_into` writes a kept board). Picking the tile with the
least fire instead (the brief's version) lost: 48.5% (CI 47.5-49.4) of 10,240 games against bundle 5, out-of-fuel
turns 319.3k against 254.7k; the best-case stand makes a camp look cheaper to clear than a clear coming from our
side finds it.

50.3% (CI 49.3-51.3) of 10,240 games against bundle 5; out-of-fuel turns 300.3k against 263.9k (+14%).

## 385: locks broken with the reset and the arrival hit; endgame walks and handoffs by the lock-aware walk; a pair's tribute by each body's own (astraeus_wip, 2026-11-05)

`break_lock` (bank_gems' lock path) only attacked. After a hit that leaves the lock standing it now casts a
ready attack reset and hits again (attack_reset restores a spent attack; five hits fit inside one cooldown,
so one reset at most). A melee champion that steps beside a locked altar hits it in the same turn
(walk and attack are independent), where it used to wait for the next turn's hit; a ranged champion whose
hit broke the lock from a tribute tile starts its tribute in that turn. `lock_turns` now counts what that
does: a hit a turn, less the melee arrival hit, less a second hit when the champion's reset is ready by the
turn before the last. It takes the champion, its walk and the round, and serves bank_gems' altar choice,
`hop_route`, `win_lands` and `carrier_tribute`'s break of our lock (the enemy body's facts and cooldowns).

`altar_turns` is the walk to a tribute tile plus the break of that altar's believed enemy lock, least over
the altars, with per-altar fields only while some lock is believed (as bank_gems chooses). `closing` and
`holding_capture_now`'s late-hold test read it instead of `to_any_altar`, so a near altar we hold a lock
against no longer makes a late bag look bankable. The four capture handoffs near the round limit
(`sole_capture_holder`'s Marcella and Prism branches, `join_marcella_capture`, `take_capture_handoff`) priced
the trip as the map's width plus height. `handoff_banks` now takes the hold's rounds to payout (a whole
count if none is under way), the new holder's walk from the group's tiles to a tribute tile with the lock
broken (`group_altar_turns`: walking fields round static terrain, kept per altar, so every ally reads the
same walk) and the tribute of its bag with the group's gems, with `endgame_margin` to spare; width plus height
only where no walk reaches an altar. `carrier_tribute` took Cassi's or Issac's partner's longer channel at the
first body's walk; it now works out the partner's own completion (its walk from where it is or lands, its
altar and our lock there, its channel; a tribute under way at its end) and takes the later.

Against CHANGES 384 on maps/p3-b1 (fresh-150001..150020), 10,240 games: 49.6% (CI 48.6-50.5), out-of-fuel turns 296.5k
against 288.9k.

## 386: combat reach by the walk round walls; an ally's stop by the tiles it stands on; heals through the camp phase (astraeus_wip, 2026-11-05)

`kill_turn`, `intercept_steps` (the walk into attack range, the ready stun's reach, a lock's placement within 2 of
the altar, the race to the carrier's altar) and `preyable`'s teleport test read the straight line less the range.
They now read our walk round our static walls (`walk_within`: `enemy_reach::distance` with our dash kind's walls
and `act` set to the range in question), which reads the same on open ground; no walk is unreachable. `prey` ranks
by that walk and by our output with spells (`output`, whose damage scale already carries the champion-damage
emblems) rather than Strength; an enemy we lost sight of is ranked from the nearest tile it may be on.

`ally_stops` took an ally's ready stun reach with a walk from its tile. It now tries the ally's tile and, for a
stun that allows walking, each step onto a free open tile with no live camp, within the stun's own reach and, for
a unit-target stun or Marcella's attack, in sight of the enemy (a shadow cast off bushes; sight is symmetric).
Ryth's ground stun needs no sight; Heart of Ruin's landing keeps the old reach. A lock counts from the ally's tile
or a step, within 2 of the altar. `offer_heal` reads each enemy's blow on the ally at its distance round walls
(as CHANGES 381 does for allies), adds next round's camp phase (`ally_camp_fire` on the ally's tile), which lands
before every champion turn, and lets the ally's shield absorb next round's blows only while it lasts past that
round's start.

Against CHANGES 385 on maps/p3-b2 (fresh-150021..150040), 10,238 games: 50.3% (CI 49.3-51.3), out-of-fuel turns 303.1k
against 290.8k.

## 387: shield, reset, holders, Prospector sharers and heal trips from what is known (astraeus_wip, 2026-11-05)

The farm priced every clear not under way as if the shield were ready on arrival. `shielded_clear` now gets
the cooldown left less the trip: the walk or recall to the group (`reach`) for a group alone and a crew's share,
the straight line for a group in passing; `recovered_for_work`, at the group, the cooldown left. Willow's
`immediate_camp_finish` takes two basic attacks only with the reset ready, else one.

`capture_taken` counted every ally in sight on a camp tile as a holder; one teleporting away, or on a kept recall
that lands before the payout, is no longer counted (`held_back`). `bound_elsewhere` also counts an ally's teleport
whose landing is not on the group, unless its claim is the group (an ally's landing is not read). Without a
Prospector emblem, the extra it would have paid on a payout took the sharers as `lround(1/share)`; it now
averages over every count of sharers n whose split gives our share, the floor share or with the remainder as the
lowest id (the only case with no living ally of lower id), the old rule where none fits. `upkeep_cost`'s heal
trips came from the mean spawn steps over every turn, though `heal_trip` is not linear in them: each noted turn
keeps the damage taken there, and the trip is the damage-weighted mean of each damage's own trip (`hurt_trip`,
kept by recall length until more damage is noted).

Uncached, `hurt_trip`'s loop ran in every `upkeep_cost` of a `best_emblem` call: 48.9% (CI 47.9-49.9) against
CHANGES 386 on maps/p3-b3 (fresh-150041..150060), out-of-fuel turns 403.9k against 316.8k.

Against CHANGES 386 on maps/p3-b6 (fresh-150101..150120), 10,240 games: 50.7% (CI 49.7-51.6), out-of-fuel turns 311.2k
against 304.8k.

## 388: an ally's walk to an unseen enemy and a crew's arrival round walls (astraeus_wip, 2026-11-05)

`Safety::unseen_walk`, an ally's walk until an unseen enemy's possible tiles are within its reach, was the
straight line (CHANGES 379 walked the other half). It now walks round our walls by the ally's dash kind, as
`ally_walk` does: `enemy_reach::steps_to` grows the ally's kept walk from its tile a step at a time until it meets
the possible tiles widened by the reach, capped at `unseen_walk_cap`.

`crew_arrival` took the walk onto a camp tile less the attack range. It now takes the walk to the standable tiles
within attack range of a member that see it (`crew_stand_field`: off bushes, as `stand_reach` reads stands; one
walking field round static terrain per group and range class, kept), so every ally ranks alike as CHANGES 368
needs; the old walk only where no such tile is reached.

Against CHANGES 387 on maps/p3-b5 (fresh-150081..150100), 10,240 games: 50.6% (CI 49.6-51.6), out-of-fuel turns 355.6k
against 309.6k (+15%).

## 389: patch 4.0.0 rules (astraeus, astraeus_wip, 2026-11-05)

cambc 5.0.0 ships balance patch 4.0.0. `champion_table` takes its stats: Vendetta health 900 and Strength 65,
Vesper Strength 35, Stellar Focus 85, Prism Focus 90, Marcella Strength [40, 3.5] and Focus growth 10, Varg
Strength 50, Heart of Ruin Focus [80, 9]. `skirmish_dealt` is 1.1, `greed_stats` 40. The same edits went into
demeter, proteus, diana and hyperion. probe-facts finds no mismatch against the 5.0.0 engine (seven against
4.0.0's).

Against astraeus 5b41a02 (the 2.0.0 tables), both on stock cambc 5.0.0 with own drafts, 1280 games: 49.2%
(CI 46.5-52.0; ladder 46.9% of 256, gen 51.2%, gen-s1 48.4%), out-of-fuel turns 12.1k against 12.4k. Kept as the rules.

## 390: phase 3 audit fixes: a pair's wait, emblem double counts, exact walks, lock turns, team-alike handoffs, lock-aware bank timings, forgotten locks (astraeus_wip, 2026-11-05)

`carrier_tribute` waited for Cassi's or Issac's partner whenever the body's bag alone fell short, a partner with
no gems or a pair that cannot win included; it now takes the later landing only when the pair wins and the body
alone does not. `prey` and `kill_turn` counted the champion-damage emblems twice (`output()` and the self
belief's `damage_scale()` already carry them; `kill_turn` now reads our live health and emblems). `walk_within`
read a walk past enemy_reach's kept steps as their count, a lower bound races could pass on; past them
`enemy_reach::steps_within` reads one field (four kept), so every walk is exact and unreachable means no walk.

`lock_turns` (CHANGES 385) counted a melee champion's reset only from three hits, and a champion already at the
altar as hitting a turn later than `bank_gems` does. It now counts the first hit in the walk's last turn for a
melee champion or one already there and the turn after for a ranged walk, and the reset's turn from two hits.
The team's holder choice (`handoff_banks`, `group_altar_turns`) read beliefs allies hold differently; it reads
the engine's countdown of our hold (else a whole count), no Capture or Tribute emblem, no reset, a fresh lock
wherever the walk ends and no camp hop's altar from outside its pocket, so every ally names the same holder.
The reset in `holding_capture_now`, `closing`'s recall and `home_trip` is timed from the round the walk starts.

The bank timings that ignored enemy locks read `altar_turns`, which now also skips an altar a camp ring seals
(`altar_steps`): `home_trip`'s walk from the landing, `recall_to_bank`'s and `capture_recall`'s walk, and the farm's
`too_late` (from the centre, once per group, only while a lock is believed). A lock, ours or theirs, unseen for
20 rounds is forgotten (`lock_memory`): no ally shares sightings, and either side's can be broken out of sight.

`offer_heal` took the ally's shield from World, which reads only enemies' and ours (always 0); it reads the
buff and lets each blow land on it by turn order against the ally's turn start, prefiltered from a teleport's
landing. `ally_stops` sees from a bush (its own cluster transparent) and through the ally's ward. The farm's
shield trip is the walk to a stand in range of a member, not the straight line to the centre. Prospector's
sharer average counts each n once. `bound_elsewhere` reads an ally's teleport landing while its tile is in sight.

Against CHANGES 388 with the 4.0.0 tables (dbf3fea3) on maps/p3-b8 (fresh-150141..150160), 10,240 games on cambc
5.0.0's fast runner: 49.3% (CI 48.4-50.3), out-of-fuel turns 410.5k against 399.1k.

## 391: an awake group's fire before our first hit (astraeus_wip, 2026-11-05)

`min_camp_damage` takes no fire in the round of our first hit: right for a sleeping group, which never attacks
(standing in reach wakes nothing), and for a clear under way from our stand. An awake group strikes in every camp
phase we spend in a striker's reach first. `awake_arrival_fire` adds it: for each awake (or maybe awake) striker
that reaches the first target's stand (`StandReach` now keeps each member's stand tile), its Strength for the
approach steps inside its reach (at least reach less its distance to the stand, at most the walk less one) and,
ranged, the arrival turn, since the walk spends the attack. A striker with nobody else in its reach sleeps after
two empty camp phases (rules camps.sleep), so it counts only when we enter its reach within two. The farm adds it
to a clear's damage, our walk to the stands being `crew_stand_field`'s (by way of spawn, the recall's rounds), with
`ally_engaged` keeping the group awake; `plan_crew` adds it at our arrival while no ally engages the group.

The brief's second camp item, charging the walk between stands when the next target in clear order cannot be hit
from the current one, lost three ways and is left out: to each member's own stand 46.5% (with the arrival fire),
to the next target's nearest stand 48.3% alone and 48.8% with it, and only once no member left is hit from the
stand 47.5%, out-of-fuel turns up a fifth (EXPERIMENTS "Phase 4"). The attack takes whatever member is in reach,
so a fixed clear order overstates the walking.

Against CHANGES 390 on maps/p4-b7 (fresh-150321..150340), 10,240 games on cambc 5.0.0's fast runner: 50.0% (CI
49.0-51.0), out-of-fuel turns 426.1k against 418.5k.

## 392: a crew's helpers by when they can come (astraeus_wip, 2026-11-05)

`crew_available` read an ally as free for an operation by radii: within `crew_available_radius` (12) of the group's
centre and claiming nothing, or a harmless group or a cleared one within `crew_near_radius` (8) of it, or within 12
of us claiming nothing harmful. It now times the ally: its walk to the group's stands (`crew_stand_field`, by its
range) after the rest of its own work (`claim_rest`: a harmless claim's health left over its output, a cleared group
it stands on until the payout our hold reads, else a whole count) must come before the clear is done (`crew_needed_by`:
our walk there, or its respawn, then its health over our output and the claimers'). An ally claiming a strong group
stays unavailable unless it stands on a cleared group, which makes any ally available whatever its claim. No radius caps the walk: an ally we see is within our sight or our ward's, and the two radii are gone
from params.h. `plan_crew` tries the free allies by that time, the soonest first.

The brief's first crew item, counting each helper's output only from its arrival after ours (one rate over the
clear, (H + sum o_i d_i) / O, over the helpers that come before it ends), lost: with both 48.6% (CI 47.6-49.5)
against CHANGES 391 on maps/p4-b2, alone 48.9% (48.0-49.9), the timing alone 49.7% (48.8-50.7) (EXPERIMENTS
"Phase 4"). It is left out.

Against CHANGES 391 on maps/p4-b8 (fresh-150341..150360), 10,240 games on cambc 5.0.0's fast runner: 50.2% (CI
49.3-51.2), out-of-fuel turns 451.0k against 424.1k.

## 393: capture watchers by exact sight, a Capture owner's hold, a tribute's proof of no lock (astraeus_wip, 2026-11-05)

`viewers_of`, the tiles from which an enemy could see a sole holder, read a bush viewpoint over walls alone, so a
viewer counted through other bush clusters; it is now `StaticMap::viewers`, which casts each bush cluster near the
tile over walls and every other cluster (rules vision.occlusion). A visible enemy in `enemy_may_see` counts by that
sight from its tile rather than by distance alone, though `sole_capture_holder`, its only caller, asks only with no
enemy in sight. Enemy wards stay unknown.

The farm priced every hold at our own Capture emblem. `capture_rounds(world, pathing, g, here)` also counts a
Capture owner in sight standing on the group (not leaving) or claiming it: an owner joining in round J brings payout
to min(R+6, J+3) (rules capture.timing), J by its walk there (`team_walk_to`) and R by ours. The prunes take
`capture_floor`, the least over the owners in sight, so they stay bounds; `hold_rounds` (fight.cc) reads the group's.

An ally's tribute under way at an altar (the only altar in its range) proves no enemy lock there: placing one
cancels every tribute at it, and one blocks ours. `update_altars` clears that altar's `enemy_lock` before reading
the locks in sight.

`holders(G)` is left as it is. Its split assumes empty bags, no Tribute emblem and no Prospector bonus; bags and
emblems would raise it, but no ally shares its bag or items, and which allies each decider sees is not common
knowledge (an ally walking in from out of sight runs `capture_taken`'s race with the same count), so any input
past G's static facts can split the team's answer.

Against CHANGES 392 on maps/p4-b3 (fresh-150241..150260), 10,240 games on cambc 5.0.0's fast runner: 50.1% (CI
49.1-51.0), out-of-fuel turns 445.1k against 437.4k.

## 394: strikes split into spells and the basic attack; a second turn after the first's moves (astraeus_wip, 2026-11-05)

`real_distance` read the whole Strike at the straight line once any damage spell was ready, so a basic attack
blocked by walls or sight was credited too, and an ally's unit spell without its own sight of the target (rules
abilities.unit_target). It now reads the basic attack alone; `castable_spells` takes a ground spell within its reach
and a unit spell within range of a target the caster sees (its tile by `StaticMap::viewers`, its ward, ours by our
sight), and `blow_with` takes the larger of the basic part (`strike_with` without the damage slots, at the real
distance) and a castable spell where the caster stands, plus its basic attack when that hits from there (every
damage spell excludes walking). `side_damage` and `offer_kills` read it. `two_turns` and `two_blows` read the
second turn where the first's moves leave the champion (`after_moves`: a walk closes 1, a dash 2 more, an exclusive
spell none, never inside its attack range).

`reset_and_attack_enemy`'s kill test takes `damage_scale` like the other two; only Heart of Ruin scales and it
has no reset, so nothing changes.

The brief's fight-sim heal item lost and is left out: `Safety::heal_masks` from the healer's tile and each free
walkable step, by the symmetric cast with the bush rule (the old stand-in is within heal range + 1, in sight of its
tile), read 48.5% (CI 47.5-49.4) with the rest of the bundle against CHANGES 393 on maps/p4-b4 (out-of-fuel turns
573.6k against 462.2k), 48.6% alone, and 48.6% kept per observation across Safeties on maps/p4-b9 with the out-of-fuel
turns unchanged (570.8k against 457.3k): the loss is in what it changes, not its cost. Without it, 49.6% on maps/p4-b4.

Against CHANGES 393 on maps/p4-b10 (fresh-150381..150400, generated for this rerun), 10,240 games on cambc 5.0.0's
fast runner: 49.7% (CI 48.7-50.7), out-of-fuel turns 464.3k against 452.8k.

## 395: escape-dash landings by walks round walls and by unseen enemies (astraeus_wip, 2026-11-05)

`threats_near` priced each visible enemy's blow on a landing by Chebyshev distance, as on open ground, and left
out enemies out of sight. Each enemy's blow is now worked out once a call for every tile within a dash of us (the
landings `danger` scores, up to 25): a visible one at its distance round its walls from where it acts
(`enemy_reach::distance` from `enemy_reach::origin`, read by the Strike as offer_heal reads it), and, with the
Safety, a credible unseen one by its Threat (`Threat::at`: its walk from the tiles it may be on). `dash_away`,
`quote_escape_dash`, `dash_clears` and `dash_to_attack` take the Safety; `stop_game_ender`'s dash, which has none,
reads visible enemies only.

Against CHANGES 394 on maps/p4-b5 (fresh-150281..150300), 10,240 games on cambc 5.0.0's fast runner: 50.2% (CI
49.2-51.2), out-of-fuel turns 476.1k against 451.3k.

## 396: the shop's forecasts price the emblem buy_shards buys (astraeus_wip, 2026-11-05)

`best_emblem` took the learned table's emblem (`learned_arm`) only inside `buy_shards` (`shopping`); everywhere
else it returned `current_emblem`, so `prices()` and `affordable_prefix()` priced a different emblem than the one
bought. It now picks the learned emblem for every caller, keyed by the emblems of the inventory asked about: with a
hypothetical one (`items`, `affordable_prefix`'s purchases so far), its emblem count, begun shards and passives,
not `my_items()`. The pinned family is priced with that inventory and released after. The learned table was fit
while the forecasts priced the current logic's emblem (as gold_price_scale's comment in params.h notes, at 1.5), so
its arms were chosen under forecasts that no longer hold.

Against CHANGES 395 on maps/p4-b6 (fresh-150301..150320), 10,240 games on cambc 5.0.0's fast runner: 50.4% (CI
49.4-51.4), out-of-fuel turns 481.1k against 484.0k.

## 397: phase 4 audit fixes: second-turn sight, arrival fire by the landing's walk, nits (astraeus_wip, 2026-11-05)

`two_turns` read an ally's second turn at the distance its first turn's moves leave it (`after_moves`), but
`castable_spells` still tested a unit spell's sight from the ally's current tile: one 5 from a visible enemy closing
to 4 never had its second-turn spell credited (rules abilities.unit_target), and one already near could be credited
from a tile it had left. The second turn's sight is now any open tile within the first turn's king steps of the ally
(`first_moves`: a walk 1, a dash 2 more, an exclusive spell none) and within `d2` of the enemy that is among its
viewers (`StaticMap::viewers`, the bush rule included), or its ward's: open ground, as `after_moves` walks it.

`awake_arrival_fire` took one count for both the approach steps in a striker's reach and the rounds before we
stand there, and the farm fed it the recall's channel plus the walk from spawn to the group's centre, or a crystal
trip's whole length: an engaged group near spawn was priced at a reach's worth of hits (a golem 480 against 120). It
now takes the walk from where we last land (here, the recall's landing tile, or a crystal's landing, by the walk to
the centre) to the group's stands (`crew_stand_field`) for the steps in reach, and the rounds until we stand there,
the channel included, for the sleep skip, which a recall's empty phases still trigger.

Nits: `side_damage`'s unused `Strikes` parameter and `offer_kills`' dead `Strikes`; `enemy_may_see`'s visible-enemy
test, unreachable since its only caller asks with no enemy in sight; `dash_away` and `dash_clears` comments (they
count credible unseen enemies too); `best_emblem`'s pinned family is reset by a scope guard; CHANGES 392's text on
claims (any ally standing on a cleared group is available whatever its claim).

Against CHANGES 396 on maps/p5-a (fresh-150481..150520), 20,480 games on cambc 5.0.0's fast runner: 49.8% (CI
49.1-50.5), out-of-fuel turns 944.2k against 940.5k.

## 398: the fuel-neutral phase 1 changes back in astraeus: CHANGES 362, 364-368, 370, 371, 382 and 378's two-blow tie (astraeus, 2026-11-05)

astraeus_wip's phases 1-2 lose to astraeus only at the real budget, by out-of-fuel turns (EXPERIMENTS "Phase 1-2
fuel"). The commits whose drop-one result left those turns level (within ~1.5%) come back to astraeus on their own:
362 (walking capture races, claims and sides), 364 (camp-hit ties by turn order; priority heals where they land),
365 (capture holders by the remainder share; siege capacity), 366 (shield absorption by whole casts), 367 (the
draft's camp-heal cost by the drafted walk), 368 (the phase 1a audit fix: team-alike capture races, a shield
already up), 370 (combat values from the ready strike), 371 (camp targets, breaches, ambushes and sieges by the hits
that land) and 382 (a stun on a tributing enemy by the rounds it delays the tribute), with 378's fix to 370's
`two_blows` tie (the larger first blow). Bot code only, as in those commits. Left in astraeus_wip: the fuel-costly
(372 borderline, -3.5%) 363, 369, 372-374, 379-381, 383 and 384, the 1b audit fixes that build on them (375-377, the rest of 378), and
phases 3-4, which build on them.

Against astraeus at 6c8746a4 on maps/port-a (fresh-190001..190040), 20,480 games on cambc 5.0.0's fast runner:
49.9% (CI 49.2-50.6), out-of-fuel turns 204.0k against 195.5k (+4.4%: the commits' small costs add up on
astraeus's leaner budget). Level; shipped as principled fixes for the retune.

## 399: one camp-targeting rule (astraeus_wip, 2026-11-05)

Rules camps.attack (a monster hits the nearest champion in its reach, a tie to the first in that round's order) was
written out ten times, and the copies disagreed on who counted. `model/camp_target.h` holds it once: `CampField`
names the champions that may take the hit instead (the one asked about left out; us at our tile when an ally is
asked; the other allies; enemies in sight, only those held in place, or none; an enemy just killed), `camp_present`
who stands there in camp phase R (alive, in sight, and no recall or teleport completing at a turn start before R:
the phase comes before R's turns, so a channel ending at its owner's next turn start still stands there), and
`camp_rival` / `camp_picks` / `camp_takes` the nearest such champion and whether one d away at a given slot is hit.

Routed through it: `Safety::find_members`' others (whose reach thresholds and SIMD loop stay), `Safety::camp_if_gone`,
`ally_camp_fire`, `threats_near`'s camp hazards, siege's cover and `siege_ready`'s enemy tank, `find_wakers`/`wake`,
`wake_ring` and `camp_cast`'s stun value. What changes: siege's cover counted no teleporting ally and no ally whose
real recall ends by next round, and gave ties to the monster; it now takes the allies in place by the rule and ties by
turn order (enemies stay no cover there: a siege does not lean on one staying). `siege_ready` keeps ties to us, as
which of us stands nearest is unknown. `wake_ring` reads ties by the prey's slot for the hit it takes now, and keeps
ties against us for the tiles it walks to, which it stands on in a round whose order is unknown. `camp_cast`'s stun
counted any of us in reach; it now needs one of us to beat every enemy in sight to the monster. `camp_if_gone` now
leaves out an enemy killed this turn, as `find_members` did. Every copy now leaves out a champion whose recall or
teleport completes before the phase. `find_wakers` keeps counting enemies only while held in place.

Against CHANGES 397 on maps/p5-b (fresh-150521..150560), 20,480 games on cambc 5.0.0's fast runner: 50.2% (CI
49.5-50.8), out-of-fuel turns 967.4k against 958.8k.

## 400: altar locks unseen 20 rounds forgotten, an ally's tribute proves no enemy lock, kill_turn's emblem counted once (astraeus, 2026-11-05)

From astraeus_wip's CHANGES 390 and 393. An altar's lock belief, ours or theirs, was cleared only when one of us
saw the altar again (since the first aphelios, 9d06d67e), so a lock seen once could turn bags away from that altar
for the rest of the game, though either side's lock can be broken out of our sight. One unseen for 20 rounds
(`lock_memory`) is now forgotten. An ally seen channelling a tribute clears the enemy lock believed on the one
altar in its range: an enemy lock blocks our tributes and cancels those under way (rules altar_locks).
`kill_turn` multiplied our basic attack by the champion-damage emblems twice (`damage_scale()` of our belief
already carries them); it now reads our live health and emblems once.

Against CHANGES 398 on maps/port-b (fresh-190041..190080), 20,480 games: 49.7% (CI 49.1-50.4), out-of-fuel
turns 210.0k against 207.2k. Level; shipped as fixes.

## 401: refactors: share splits, move outcomes, recall_line's cache, recall predicates, turn outcomes (astraeus_wip, 2026-11-05)

No behaviour change, but for one error path: a `std::exception` thrown in `decide` after the support code took
the turn now loses that ownership, which the globals kept. `split_share(amount, n, lowest)` (world.h) is a sharer's part of a capture (the floor share, the
remainder too for the lowest id): `prospected`, `our_share`, `holders`, `held_gold`, the shop's income check and
the farm's too_late read it, and the farm's `gold_in` asks for the floor share alone explicitly. `held_gold` takes
the group's cluster gold and prices the Prospector bonus on it (`prospected`), not on the whole gold share, so its
caller's `cluster_gold == gold` test no longer carries it.

`Pathing::try_move` and `move_to` return `Pathing::Move` (`moved`, `hidden`: a hidden unit held the tile, now in
sight; `refused`: illegal or guarded) in place of a bool and a `refused` out-parameter. `recall_line_uncached`
works the recall line out without touching the Safety's one-tile cache, so `home_room` no longer saves and restores
its fields. `live_kept_recall` (a recall read live as kept, for a champion whose record we read now) and
`recall_ends_by` (a recall completing by a round's turn start; the turn-end feint never gets that near) name what
capture.cc wrote out five times.

The turn's ownership globals are gone. `search_strikes` returns a `StrikeSearch` (attacked, ran, priced every enemy
seen), whose `struck` goes to `farm` (via `carry_bag` too) and `searched` to `chase`. `local_support` and
`willow_independent_heal_step` return a `SupportTurn`: whether they took the turn, or handed it to retreat(), and,
apart, the `SupportIntent` (requested, offered) the turn end posts. `decide` returns a `TurnOutcome` (whether the
support code owns the turn, its intent), which `act`'s wrap-up and `play_turn`'s comms read.

`act` is kept out of line (`[[gnu::noinline]]`): inlined into `play_turn`, every call in it cost more, +0.23% fuel.
`tools/fuel/bench.py` against CHANGES 399 (default, wide and 120 p5-b games): 188/188 replays identical at 100M
fuel, +0.04% fuel. At the real budget the replays differ (fuel-gated choices), so an A/B: against CHANGES 399 on
maps/p5-c (fresh-150561..150600), 20,480 games: 49.9% (CI 49.2-50.5), out-of-fuel turns 946.5k against 944.2k.

## 402: the draft5 model, no team lock, and test drafts from the patch 4.0.0 ladder (ocean, 2026-11-05)

`bots/ocean` is astraeus 5b66bde0 with a new draft. `draft/draft_model.h` is `model.mjs cpp --lab
replays/draftlab/draft5`: 1.09M lab games on cambc 5.0.0 (balance patch 4.0.0), the 25-feature header, opponent prior
from the top 15 other teams' ranked drafts on the new engine (`tools/draftlab/ladder_prior.py`,
research/ladder-drafts-2026-11-05.md), and an empty team lock (`required = 0u, banned = 0u`): Cassi & Issac is no
longer forced and Stellar no longer banned (the lab puts Stellar 11 points below the average champion at every pick
count; deployed teams take it on 1-3% of maps). C++/JS parity 384/384 (`native.mjs --src`). `test_compositions`
(`params::test_draft` only, off) is `tools/draftlab/test_comps.py`'s: the 16 most common compositions per pick count
in pick order, chosen by map and side with their ladder frequency as weight. First draft turn (`firstturn.py`,
draft5's sample, 2,859 maps): none out of fuel, start-up plus model draft median 2.81M, max 7.29M; the dash-lattice
fresh-9136 913607608 alone is over the 8.5M bar, at 9.17M.

Own drafts, fast runner: against astraeus 53.0% (52.3-53.7) of 20,480 on maps/oc-d1 (fresh-505021..505060). Against
the new ladder test drafter (ocean with `test_draft` on) on maps/oc-t1 (fresh-505061..505080), 10,240 games each:
ocean 71.6% (70.7-72.5), astraeus 69.0% (68.1-69.9). Evidence: EXPERIMENTS "ocean".

## 403: a draft plan that fails its check resigns the game in local builds (astraeus, 2026-11-05)

`StaticMap::build` used to drop a draft plan whose `plan_check` mismatched and compute everything itself, so a broken
draft-to-champion handoff went unnoticed. In a `debug_block`, which runs only in non-`--release` builds (`cambc run`,
and the `cambc build` that `run_batched.py`, `ab.py` and `bench.py` use; the platform always builds release), a
champion now prints `PLAN-CHECK no plan: check 0, map's XXXX` when the draft never set a check (it crashed, failed or
ran out of fuel first; not past 255 groups, where it writes none on purpose) or `PLAN-CHECK mismatch: plan's XXXX,
map's XXXX` otherwise to team stdout and resigns (`cambc::resign`), so the game is lost in round 1: a local A/B shows
it as lost games, not in ab.py's failed column, which counts only engine match failures (a bot cannot cause one). A
resign that fails throws instead, leaving the map unbuilt. On the ladder nothing changes.
Release builds are the same code: every function body matches one of the unmodified source's (the toolchain itself
varies four functions' try_table layout from build to build, so whole modules seldom match byte for byte).
`tools/fuel/bench.py` (debug builds, 100M fuel): 16/16 replays identical; round-1 turns' mean fuel +95,
total fuel -0.00%.
A draft that writes a wrong check and one that never writes draft memory both threw from r1 on 00ambush; with the
resign, the wrong check's copy resigned in round 1 (`Team B wins: team A resigned in round 1`) and ocean against
astraeus on the same map played to the end.
No false alarms on the 128 ladder maps, both sides, against `bots/idle` (256 games).
`bots/ocean` has the same change.

## 404: farm recalls out while carrying, and re-weighs the pick during the channel (ocean, 2026-11-05)

From the farm-routes study's `bots/variants/oc-best` (knobs `params::route::r1` and `f1`; the other knobs and their
code are left out).
- **Recall out with a bag** (R1). Farm's recall to spawn and on to a group (FarmRecall) is priced while carrying too,
  since a recall keeps the gems: by group, only while the recall, the group and the healed trip on to an altar
  (`healed_home`/`healed_winning`, no second stop) beat the walk, the group and the trip home (farm.cc's loop and the
  banking pre-prune bound). `recall_to_farm` keeps such a recall under the same test, and `recall_farm` is set only for
  a group the loop routed by way of spawn (`routed`).
- **Re-weigh during the channel** (F1). Each turn of our recall to a farm group, empty-handed, `continue_recall` runs
  the farm pick again (`farm_reprice`: `farm_turn<false, false, true>`, which neither acts nor picks up) with the
  channel's turns left. It keeps the recall while some group still goes by way of spawn, and the group may switch;
  otherwise the recall is cancelled as before.

Against oc-r0 (ocean before it), own drafts: **51.37% (50.69-52.06)** of 20,480 on fresh ladder-mix seeds
506900-939, and 51.25% (50.28-52.22) of 10,240 on `--mix varied`. bench.py at 100M: `bots/ocean` replays identically
to oc-best (16/16 default set, 52/52 wide set with test drafts; total fuel +0.03%, from CHANGES 403's check in debug
builds). Real budget, wide set with test drafts: mean 54,375 (oc-r0 53,705), p99 95,580 (95,419), 831 out-of-fuel turns
(813); farm partial evaluations +16%. Frozen as `bots/variants/oc-base1`. Evidence: EXPERIMENTS "Farm routes via spawn
(2026-11-05, ocean)".

## 405: SPSA-retuned constants (ocean, 2026-11-05)

The 61 constants of SPSA run `replays/tune/oc2`'s final iteration (1288; `bots/ocean_tune` against astraeus, proteus
and pre-tune ocean on the ladder maps, 1.98M games) replace ocean's defaults in `params.h`, still `constexpr` and as
exact float32s. Unlike CHANGES 321's run it also tuned `crew_tank_line` and `max_exposure`, which are now their own
values (0.320 and 1.215; `recall_health_fraction` 0.356, `mid_exposure` 1.361), and the four turn values `life_value`
273, `gem_value` 16.0, `tribute_value` 83.2 and `recall_value` 66.3. turn_order.cc reads fixed copies `turn_life_value`
300, `turn_gem_value` 15, `turn_tribute_value` 100 and `turn_recall_value` 60, because its rank codes need those
values modulo 15. On ocean as it was before CHANGES 404, the same params.h replays identically to the tuned run's bot
at 100M (68/68 games). Own drafts, ladder-mix seeds 509100-509179, 20,480 games each: against oc-base1 (CHANGES 404)
**53.2% (52.5-53.8)**, with 12.5% fewer out-of-fuel turns; against astraeus 56.8% (56.1-57.5), where oc-base1 had
54.0%; against proteus 55.0% (54.3-55.7), where oc-base1 had 52.7%. Frozen as `bots/variants/oc-base2`. Evidence:
EXPERIMENTS "SPSA retune (ocean, 2026-11-05)".

## 406: exact fuel savings in the farm turn (ocean, 2026-11-05)

Idea programme track Z (`research/ideas-2026-11-05/fuel.md`), `bots/variants/oc-fuel-s5` as plain code. The allies'
parts of `gems_short`, `race_left`, `gems_share` and `World::ally_rate` are memoised by observation and round (our own
bag is read each call: a kill mid-turn changes it). In farm_turn's loop: `strong`/`kited`, `exposure` (fixed once
`home_side` reads a group), `may_expect`'s enemies in sight, the travel dash and the walk range are read once, and
`too_late` uses the chained tribute. The loop's last prune runs first at the static walk (with the via-spawn bound),
before the walk round live camps. bench.py at 100M: identical replays but for 1-2 of 312 games (default, wide, df-mono and 60 one-altar maps).
`early_prune` skips `live_steps`, and with it `Pathing::same_labels`' snapshot of the camps, so a later
`labels_hold` can fail where it held and re-search. Real budget: farm-loop cuts -24%. Against oc-base1: 50.5%
(49.8-51.2) of 20,480. Evidence: EXPERIMENTS "Farm turn fuel (ocean, 2026-11-05)" and "Idea integration (ocean,
2026-11-05)".

## 407: home Monolith sieges from our spawn (ocean, 2026-11-05)

Idea D (`research/ideas-2026-11-05/spawncamp.md`), `bots/variants/oc-spawncamp-L512m`. On Monolith-only maps, a
Monolith group whose live strikers all fire on spawn stands the sturdiest of us outlasts (`home_siege`, over
`home_free`) is sieged once the team, its power scaled to the stands' share of bodies, clears it within
`home_siege_rounds` (512). From the spawn it costs time, not health, and camps never regenerate. A static
per-group prefilter (a member within 3 of the spawn box) keeps far Monoliths free. 03homonoliths is won in ~660
rounds instead of ~1400; 80.6% on home-Monolith maps (df-mono); level on full suites (it acts on 0.2-0.8% of maps).
Evidence: EXPERIMENTS "spawncamp (ocean, 2026-11-05)".

## 408: altar control on one-altar maps (ocean, 2026-11-05)

Idea A's e3 (`research/ideas-2026-11-05/altar.md`), `bots/variants/oc-altar-e3`, as plain code in
`economy/altar_guard.cc`. On a one-altar map, guarding runs while the enemy has 600+ tributed and leads by 200+
(until the lead is under 100), and while a body of ours carries a winning bag. During it, the 3 strongest bodies by
base health x Strength (a linked pair last; at least one body keeps farming) hold stand tiles within 2 of the altar
(bushes first, out of camp reach) and chase enemies within 6 of it. `place_lock` keeps our lock on that altar. 51.1%
(50.4-51.8) of 20,500 on one-altar maps; identical on multi-altar maps at 100M. Evidence: EXPERIMENTS "Altar control
(ocean, 2026-11-05)".

406-408 together on oc-base2 (CHANGES 405), as `bots/variants/oc-combo2` (frozen; = `bots/ocean`). Own drafts, real
fuel: **51.3% (50.6-52.0)** of 20,480 against oc-base2 (fresh-516181..516220), with 4.4% fewer out-of-fuel turns;
51.5% (50.1-52.9) of 5,120 on `--mix varied`; 52.7% (51.7-53.7) of 10,240 against the same changes on oc-base1. The
panel passes, with a mean of +0.8 against oc-base2's rates. Evidence: EXPERIMENTS "Idea integration (ocean,
2026-11-05)".

## 409: ocean's CHANGES 402-404 in astraeus (astraeus, 2026-11-05)

9cb65c88, from `bots/variants/oc-base1` merged three-way onto a790c441: the draft5 draft with no team lock (Cassi &
Issac no longer forced, Stellar no longer banned) and the weighted ladder test compositions (402), the plan-check
resign in local builds (403), and farm's recall out while carrying and its re-pick during the channel (404). The
farm loop of 3076ffa9 assumed no recall out while banking, so three of its bounds now count it: PreLanes::block's
banking lanes and `claim_most` take the recall-out trip, and `beaten_near`'s banking bound prices that trip without
the walk's trip home (`bank`). The loop prices it on to an altar healed, which can undercut `bank`, so the bound
could skip a group the loop would choose. `beaten_near`'s was in ocean too, so there astraeus's choices differ from
ocean's. Own drafts, fast runner, real fuel: 55.0% (54.4-55.7) of 20,480 against a790c441 on fresh-518000..518039,
out-of-fuel turns 183.5k against 187.0k. Evidence: EXPERIMENTS "ocean's 402-404 in astraeus".

## 410: selected wip accuracy fixes without its new path searches (astraeus, 2026-11-05)

From astraeus_wip: support formation and priority-heal positions can use dead camp
tiles (376); Willow's camp-finish check respects reset readiness, shields are priced
from their cooldown after travel, and departing capture holders no longer count as
covering the hold (selected parts of 387). The passing-camp shield estimate uses
the minimum straight-line distance into attack range instead of wip's stand fields;
the main farm loop uses its existing travel estimate.

Banking uses a ready reset on a surviving lock, attacks after melee arrival, and
starts tribute after the final ranged hit; lock timing matches those actions
(385 with 390's timing corrections). Shop forecasts choose the learned emblem
shopping would buy, including hypothetical inventories (396), while retaining
astraeus's existing caches. The farm's tribute deadline uses the planned capture
share, including the lowest id's remainder and Prospector, capped by crew size for
a crew proposal (372's deadline only). No new fuel gates or path fields.

Against frozen astraeus 0f7830e1, both own drafts, real budget, native fastrunner:
49.88% (95% CI 49.19-50.56) over 20,480 games on 10,240 fresh ladder-mix maps
(seeds 247001-247040), zero failed matches. OOF 145,848 vs 146,230 (-0.26%); farm
partial evaluations 2,487,699 vs 2,457,358 (+1.23%). Level, with a small increase
in farm cuts, not strict fuel neutrality. Evidence: EXPERIMENTS "Initial wip
accuracy port on current astraeus" and `research/accuracy-port-2026-11-05/`.

## 411: withdraw lock resets and share-based tribute deadlines (astraeus, 2026-11-05)

At the user's request, remove two parts of 410. `break_lock` no longer casts an
attack reset, and lock-duration estimates no longer credit one. Keep the melee
arrival hit and immediate tribute after a final ranged hit. The farm's `too_late`
returns to the pre-410 whole-group tribute estimate, so an assumed split cannot
make a deadline look feasible when allies yield to a sole recipient.

The rest of 410 remains. Its 20,480-game A/B measured the original bundle, not this
reduced one; no new A/B for this requested rollback.
Validation: `cambc build bots/astraeus` and `git diff --check` passed.

## 412: share the draft's health reserve with recall (astraeus, 2026-11-05)

Draft farming estimates use `recall_health_fraction` (0.3250693) instead of the
separately tuned `draft_recall_health_fraction` (0.329403), which is removed.
This slightly increases the draft's usable-health estimate and makes its reserve
follow the threatened recall threshold.

Against frozen prior astraeus 29cd0921, own drafts, native fastrunner, real fuel:
50.02% (5,002-4,998; 95% Wilson CI 49.04-51.00) over 10,000 games on 5,000 fresh
ladder-mix maps, zero failed matches. Out-of-fuel turns 67,219 vs 67,224. Level;
kept as one fewer tuned parameter. Evidence: EXPERIMENTS "Shared draft recall
threshold" and `research/draft-recall-2026-11-05/`.

## 413: a fight value for emblem stats (ocean, 2026-11-05)

Gold pricing audit round 2, fix 5 (`research/ideas-2026-11-05/value.md`). An emblem's saving (`current_emblem`'s
value, so both the emblem bought and `prices()`' per_gold) adds `fight_saved`: `fight_weight` 0.5 x the share of the
damage we take that comes from champions (`upkeep.champ_taken` over all taken plus a prior of 500 camp damage) x the
fight power the build gains over now, 1 - (output x effective health now) / (with it). Skirmish is a passive
candidate at the same share x its +10% dealt. Bodies that fight start more emblems (5.16 per champion against
4.70), more Bruiser, Durability and Home Health. Alone, against oc-combo2 (CHANGES 406-408), own drafts, real fuel:
52.4% (51.7-53.1) of 20,480 on fresh-519100..519139, 53.5% of 5,120 on `--mix varied`, panel up 1.8-3.1 on every
member; out-of-fuel turns +6%. Counted in emblem choice only it reads 51.5, in pricing only 50.7.

## 414: funnel farm's gold to the richer body (ocean, 2026-11-05)

Farm's per_gold is multiplied by (300 + our wealth) / (300 + the team's mean), wealth being gold plus 30 a shard
owned (an ally's gold read directly, its items as last seen), once per turn and gold. The richer body takes the gold
groups and completes its emblems sooner. The user's spreading idea (fushia's capture rule, S / (S + wealth), on
holds or in farm) lost at every setting (46.5-49.8); its inverse gains 51.4% (50.7-52.1) of 19,968 alone.

413-414 together, `bots/variants/oc-value2` (frozen as `bots/variants/oc-base3`; = `bots/ocean`), against
oc-combo2, own drafts, real fuel: **53.8% (53.1-54.5)** of 20,480 on fresh-519140..519179; 53.0% (51.6-54.4) of
5,120 on `--mix varied`; 50.9% (50.2-51.6) of 20,480 against 413 alone. The panel passes with every member up,
mean +2.9. Out-of-fuel turns +11% over oc-combo2 (real-budget bench: 908 against 888), from the games it plays: the
per-turn factor costs nothing measurable. bench.py at 100M: identical to the knob version `oc-v2-f5sf300mc` (16/16
default, 52/52 wide, 128/128 pool). The audit's other fixes (the bought emblem priced, a split hold's share, fitted
holder and draft prices, an absent ally's rate, lumpy gold, passive gold scaling) were level or lost. Evidence:
EXPERIMENTS "Round 2: structural gaps and spreading (ocean = oc-combo2, 2026-11-05 evening)".

## 415: astraeus's exact farm-turn fuel savings in ocean (ocean, 2026-11-05)

astraeus's fuel campaign since 5b66bde0 (3076ffa9, 7950979e), ported three-way: live camps by dirty group and the
pack zone after the loop (with the loop reserve covering it), the pre-facts bounds (PreLanes in blocks of 4), the crew
pricing tables, the turn-end queue's clear warm-ups, the KeptArrival table and `claim_bound`, exact travel-plan
windows, altar access without floods, the unseen enemy's `possible_box` and the BagKey. Its logic changes are left out
(d737bcf6, 4a16bebf, 9dba3ed8, 1310d649 and the refit, CHANGES 409's beaten_near fix). Adapted to ocean: the banking
trip and `claim_most` take CHANGES 404's recall out; the bounds scale worth by `exposure_most` (CHANGES 405's
`max_exposure` is below `mid_exposure`), with ocean's own pre-facts prunes at `max_exposure` kept beside them; and
`pre_value` and `claim_most` run after `live_steps`, whose kept camp labels later turns read. bench.py at 100M:
identical to oc-base3 (16/16 default, 52/52 wide, 128/128 pool), total fuel -2.3 to -2.6%. Real budget, wide bench:
OOF turns 929 -> 693. Own drafts, 20,480 games each: against oc-base3 **50.7% (50.1-51.4)** on fresh-525100..525139
(50.8% on 525000..525039), out-of-fuel turns -21%; against astraeus-now-1105 55.8% (55.1-56.5), its OOF excess +8.5%
(oc-base3: +39%). Frozen as `bots/variants/oc-fuel4` (= `bots/ocean`). Evidence: EXPERIMENTS "Fuel round 4 (ocean, 2026-11-05)".

## 416: home Monolith sieges on mixed maps, out of the awake Monolith's reach (ocean, 2026-11-05)

Frozen as `bots/variants/oc-spawn2` (oc-fuel4 plus this); shipped in `bots/ocean` with CHANGES 422 as
`bots/variants/oc-base4` (see 422). Round 2 of idea D (`research/ideas-2026-11-05/spawncamp.md`). CHANGES 407's home siege now runs off Monolith-only maps too
(siege.cc `siege_candidate`). There, home sieging keeps the Monolith awake, and bodies walking out through its reach
died to it. So while a home Monolith one of us claims is awake, the work guard bars its reach off our spawn
(`home_reach_avoid` in `guard_work`, which bank, shop, siege and farm walks honour). The exception is a body
already standing in it off spawn. A static per-map test (`home_monolith_map`: a Monolith within ranged reach of
our spawn's box) keeps other maps' turns at one test (+0.04% fuel at 100M, replays identical). On the 122
home-Monolith maps (df2-mono) it reads 63.5% against oc-fuel4: 71.2% on the 78 with other gems, unchanged on the
Monolith-only ones. Deaths to camps fall from 1.20 to 0.28 a game against the siege alone, and those games end at
~r830 instead of ~r1300. On df2-mono the panel mean rises by +10.6. Full suites are level: 49.8% (49.2-50.5) and
50.0% (49.3-50.7) of 20,480 each, varied 50.4% of 5,120. Panel-check is within 0.6 of oc-fuel4 for every member
(mean -0.46). The change acts on ~0.2% of maps. Evidence: EXPERIMENTS "spawncamp round 2 (ocean, 2026-11-05)",
which also records the losers: a home-stand coefficient in farm's value (no gain at k 0.001-0.25, its loss was fuel)
and spells from spawn (level).

## 417: ocean's SPSA constants, emblem fight value and gold funnel (CHANGES 405, 413, 414) in astraeus (astraeus, 2026-11-06)

Ported from committed `bots/ocean` (ad32d648) onto 4f17957d.
- 405: every constant astraeus shares with ocean takes ocean's exact float32, 50 values in all (`track_horizon` 9 -> 4,
  `chain_bag_limit` 45 -> 34, `big_gems` 55 -> 70, `chip_value` .334 -> .217, `gold_price_scale` 1.41 -> 1.64, ...).
  `crew_tank_line` (0.320) and `max_exposure` (1.215) are their own values, no longer aliases. `life_value`,
  `gem_value`, `tribute_value` and `recall_value` are tuned, and turn_order.cc reads the fixed copies `turn_*`
  (300/15/100/60), because its rank codes need those values modulo 15. oc2's `draft_recall_health_fraction` is
  dropped, since CHANGES 412 removed it: the draft reads the tuned `recall_health_fraction`, 0.356.
- 413: `fight_saved` in an emblem's value, and Skirmish as a passive candidate (shop.cc), as in ocean.
- 414: farm's per_gold x (300 + our wealth) / (300 + the team's mean) (`champion_wealth` in capture.cc), as in ocean.
- Adapted: `max_exposure` now lies below `mid_exposure`, so it no longer bounds `exposure()`. The prunes ocean also has
  (`rated_below`, `beyond`, `altar_below`, PreLanes' non-banking `out`) stay at `max_exposure`. The exact bounds from
  astraeus's fuel campaign (PreLanes' `value` and banking lanes, `claim_most`) use `exposure_most` =
  max(1, mid_exposure, max_exposure). Ocean's own banking pre-facts prune, at `max_exposure`, is kept beside them as
  the lanes `old`/`old_alt`.

Own drafts, fast runner, real fuel, against committed ocean (`bots/variants/ocean-ad32d64` = oc-base3): **50.9%
(50.4-51.5)** of 30,720 games on fresh ladder-mix suites 532000-532059 (`maps/suites/merged/ast-port1`), with 0 failed
matches. Out-of-fuel turns were 211.3k against ocean's 298.8k. Before the port, oc-base3 beat astraeus 55.6%. Frozen as
`bots/variants/astraeus-port1`. Evidence: EXPERIMENTS "ocean's 405, 413-414 in astraeus".

## 418: SPSA retune for the fight value and the funnel (ocean, 2026-11-05)

Shipped (2026-11-06) as `bots/variants/oc-tuned4` (= `bots/ocean`): `bots/variants/oc-base4` with SPSA run oc4's 23
constants (`tools/tune`, 750 iterations, 1.54M games, half of them against oc-base3, the rest against
astraeus-now-1105 and panel-proteus). The set was chosen from oc2/oc3's gradients: 413/414's constants, two new knobs,
and the farm, shop and retreat/engage constants with measured signal; the rest stay. As exact float32 `constexpr`
values: `fight_weight` 0.5 -> 0.611, `fight_camp_prior` 500 -> 518, `funnel_wealth` 300 -> 292, `gold_price_scale`
1.641 -> 1.365, `chain_bag_limit` 34 -> 26, `track_horizon` 4 -> 3, `pick_up_radius` 5 -> 6, `recall_health_fraction`
.356 -> .298, `hurt_health_fraction` .441 -> .488, plus small moves in `heal_trip_fraction`, `pair_hold_share`,
`life_value`, `gem_value`, `chip_value`, `hurt_retreat_ratio` and `home_retreat_ratio`. New constants:
- `funnel_power` -1.161 (414's exponent, was -1).
- `shop_gain_scale` 0.822: wants_shop weighs a purchase's saving at this share against the trip, so shopping trips
  wait for more.
- `hit_given_reach` .236 and `recall_risk` .194: safety_params, which now read params.h.

Own drafts, real fuel, against oc-base4: SPRT 0.50/0.51 H1 at 9,591 games (51.5%), **51.0% (50.4-51.7)** of
20,480 on fresh-526500..526539, and 52.4% (51.1-53.8) of 5,120 on `--mix varied`. The panel passes against oc-base4
with astraeus-now-1105, with no member down and a mean of +1.46 (astraeus +1.2, proteus 0.0, demeter +2.3,
ocean-td +1.9, v67 +1.9). Out-of-fuel turns are -5%. The same diff on oc-base3 replays identically to the tuned run's
bot at 100M (52/52 wide, 92/92 one-altar and df-mono), and `bots/ocean` replays identically to oc-tuned4 (bench.py
default set, 16/16). Evidence: EXPERIMENTS "SPSA retune round oc4".

## 419: holder choice by gold efficiency (ocean, 2026-11-06)

Shipped (2026-11-06) with 420 and 421 as `bots/variants/oc-retest-clean` (= `bots/ocean`): `bots/variants/oc-retest`
with the three settings as plain code and its unused `params::retest::` knobs removed. bench.py at 100M replays
identically to oc-retest (16/16 default, 52/52 wide, 128/128 pool) at -0.24% total fuel, and `bots/ocean` to
oc-retest-clean (16/16 default). Value round 3's h1any
(`research/ideas-2026-11-05/value.md`).
- In capture.cc `holder_value`, a hold's gold part is multiplied by the holder's gold efficiency over the team's
  mean. Efficiency is the fight power (output x max health) that an emblem's 5 shards in its best stat add, times
  its gold rate.
- Holds with gold are compared whatever the bonuses (`multiplies`).
- Alone, on oc-tuned4, own drafts, real fuel:
  - 51.2% (50.5-51.8) and 51.3% (50.6-52.0) on two unused 20,480-game sets (fresh-532100..532139 and
    532200..532239);
  - 50.7% of 5,120 on `--mix varied`;
  - panel mean +0.98;
  - out-of-fuel turns +0.5-0.9%.

## 420: farm's gold funnelled by gold efficiency, not wealth (ocean, 2026-11-06)

Shipped (see 419). Value round 3's e1p1 without the wealth funnel.
- Farm's per_gold is multiplied by (our gold efficiency / the team's mean) instead of 414's wealth factor
  (`champion_wealth`, `funnel_wealth` and `funnel_power` are removed).
- Each ally's efficiency is kept until its max health, Strength or Focus change, or its being in sight; ours, until
  our gold rate changes (`kept_efficiency`). Read afresh, it cost ~2.4k fuel a farm turn (+2.3% total, +15%
  out-of-fuel turns at no decision change). Kept, it is exact: 16/16, 52/52, 128/128 at 100M, at -1.3% fuel.
- Alone it reads 50.6% on unused seeds; its gain shows with 419 and 421.

## 421: a reveal ward into the bush that likely hides an attacker (ocean, 2026-11-06)

Shipped (see 419). Idea C's reveal ward, mode 3 (`research/ideas-2026-11-05/bush.md`; bot.cc `reveal_ward`).
- When to try: at turn start, after a fight last turn or a health loss since our last turn, while our ward is ready.
- Where: the unseen bush cluster within ward range that holds at least 25% of an unseen enemy's credible tiles near
  us (`reveal_mass`), weighted twice (`reveal_prior`) when the enemy was last seen beside it.
- The ward goes on the cluster tile that sees most of those tiles, so this turn's strikes see what it reveals.
- Alone it reads 50.6% on unused seeds, out-of-fuel turns +2.6%.

419-421 together (`bots/variants/oc-retest`), against oc-tuned4 (CHANGES 418), own drafts, real fuel:
- **51.9% (51.2-52.6)** of 20,480 on unused fresh-532200..532239. Without 420's cache: 51.7%, and 50.9% against 419
  alone.
- 51.9% (50.5-53.2) of 5,120 on `--mix varied`.
- Panel (panel-check-514510): astraeus-now-1105 59.7 (57.7), proteus 63.0 (61.5), demeter 67.7 (65.0), ocean-td 82.3
  (81.1), v67 77.0 (77.2). Mean +1.44, no member down. Second set: astraeus 60.4 (58.1), proteus 63.2 (60.2).
- Out-of-fuel turns +6.1% in the A/B and +2.1% on varied.
- The knobs-off dev copy `bots/variants/oc-retest4-dev` (`params::retest::`) replays identically to oc-tuned4 at
  100M.

Retested and level or losing on this base: gemfight's carrier-weighted chase, 420 with the wealth funnel kept, a
harder wealth funnel (-1.6 to -2.4 against the tuned -1.161), SPSA's per-type weights, 12/6 search caps (OOF -9%),
and spells from spawn. Evidence: EXPERIMENTS "Near-miss retest on oc-base4 (ocean, 2026-11-06)".

## 422: a ranged walker with no strike to follow stays and leaves the walk to the goal (ocean, 2026-11-05)

Frozen as `bots/variants/oc-fuel6` (oc-fuel4 plus this). In `plan_strikes`, a ranged champion from whose every end tile no strike is possible (`strike_free` 4) no longer runs the walk-only search, whose chosen
step spent its attack; it stays, and the goal does the walking under its step guard. A decision change, not a fuel
one: OOF turns -1.0%, prey-cut-short shortcuts -12%. Own drafts against oc-fuel4: **51.3% (50.6-52.0)** of 20,480 on
528100-528139 (50.9% of 15,524 on the dev suite, SPRT H1), varied 51.1% of 5,120; panel-check mean +0.72 with no
member failing (astraeus-now-1105 +1.2, proteus +2.2), and on oc4-panel2 astraeus +2.2, proteus +1.7. Evidence:
EXPERIMENTS "Fuel round 6 (ocean, 2026-11-05)", which also records the losers (shorter fight and stand horizons,
smaller search caps, no walk leaf in full searches, a rotating farm window).

**Shipped with 416** (2026-11-06) as `bots/variants/oc-base4` (= `bots/ocean`): oc-fuel6 plus 416's diff, which
touches other files (bot.cc, bot_parts.h, guard.cc, siege.cc and a params.h comment; 422 is plan.cc alone) and applied
cleanly. bench.py at 100M against oc-fuel4: identical to oc-fuel6 on the default (16/16) and wide (52/52) sets, which
hold no map where 416 acts (total fuel +0.04-0.05%, its static map test). On df2-mono against hyperion, 416 changes
the same 154 games on oc-fuel6 as on oc-fuel4 (154 of the 156 mixed-map games, none of the 88 Monolith-only ones)
and shortens them alike (play turns -34% / -33%). Own drafts, real fuel: against oc-fuel4 **51.1% (50.4-51.7)** of
20,480 on fresh 531000-531039 (`oc-base4-conf`), out-of-fuel turns 157.1k / 158.5k; against oc-fuel6 on df2-mono
60.2% (54.0-66.2) of 244, 66.0% (103/156) on the mixed maps and 50.0% (44/88) on the Monolith-only ones.
Evidence: EXPERIMENTS "oc-base4: CHANGES 416 and 422 merged (ocean, 2026-11-06)".

## 423: ocean's second SPSA retune, ranged walker, holder and funnel by gold efficiency, and reveal ward in astraeus (astraeus, 2026-11-06)

Ported from `bots/ocean` (ocean's CHANGES 418-422) onto 37e1eb64 (CHANGES 417), as ocean's own diffs, which applied
with line offsets only.
- 418: SPSA run oc4's constants: `fight_weight` 0.5 -> 0.611, `fight_camp_prior` 500 -> 518, `gold_price_scale`
  1.641 -> 1.365, `chain_bag_limit` 34 -> 26, `track_horizon` 4 -> 3, `pick_up_radius` 5 -> 6,
  `recall_health_fraction` .356 -> .298, `hurt_health_fraction` .441 -> .488, and small moves in `pair_hold_share`,
  `hurt_retreat_ratio`, `home_retreat_ratio`, `heal_trip_fraction`, `life_value`, `gem_value` and `chip_value`.
  New: `shop_gain_scale` 0.822 (wants_shop weighs a purchase's saving at this share against the trip), and
  `hit_given_reach` .236 and `recall_risk` .194, which safety.h now reads from params.h (were 0.25 and 0.2).
  astraeus's values before were ocean's before the retune, so the port is exact.
- 419: capture.cc's `holder_value` multiplies a hold's gold part by the holder's gold efficiency over the team's mean
  (the fight power its best stat's 5 shards add, times its gold rate); `multiplies` counts any hold with gold.
- 420: farm's per_gold is multiplied by our relative gold efficiency instead of CHANGES 414's wealth funnel
  (`champion_wealth`, `funnel_wealth` and 418's `funnel_power` are removed). Each ally's efficiency is kept until
  its stats or its being in sight change.
- 421: the reveal ward (bot.cc `reveal_ward`): after a fight last turn or a health loss since our last turn, with
  the ward ready, a ward into the unseen bush cluster within ward range that holds at least `reveal_mass` (0.25) of
  an unseen enemy's credible tiles near us, weighted `reveal_prior` (2) when it was last seen beside it.
- 422: in `plan_strikes`, a ranged champion from whose every end tile no strike is possible (`strike_free` 4)
  returns without the walk-only search, leaving the step to the goal under its step guard.

Own drafts, fast runner, real fuel, on `maps/suites/merged/ast-ocean-40k` (fresh ladder-mix 550000-550156, 80,384
games each): 418 alone against 37e1eb64 **51.3% (50.9-51.6)**, out-of-fuel turns -4%; ocean against 37e1eb64 53.8%,
against 418 alone 53.0%, and against all of it **49.5% (49.2-49.9)**. Frozen as `bots/variants/astraeus-418port`
(418 alone) and `bots/variants/astraeus-p421` (= `bots/astraeus`). Evidence: EXPERIMENTS "ocean and ocean_tune3
against astraeus on 40k fresh maps".

## 424: fuel campaign 7, merge 1: stand check reads, farm's centre fields (astraeus, 2026-11-06)

Fuel only, byte-identical at 100M on all six fc7 bench sets (def, wide, pool, big, heavy, td).
- `stand_lost_at` reads walks and pursuit only when its roster reads them. `stand_reach` tests only the hits. The seen
  walkers' walks wait for `stand_walks`, which runs only with a hit or a pursuit (without either, the roster drops
  every walker). `pursued` is read only when some walker could be kept by it, and a stand with no roster returns
  before `lethal()` is asked for `falls`.
- The farm loop's first two groups without a centre field make theirs (`pathing.centre_field`, kept for good: the
  same steps by walking symmetry over the same static walls) in place of the throwaway flood from here. A third group
  floods as before. Groups that read the flood are marked `want_centre` and go first in the next `warm_centres`.
  Not on the opening turn. Each field is behind the base's one-flood fuel check.

100M against 5166d1c: total fuel -0.19% to -0.70%, p99 -0.0% to -1.7%, turns over 100k 23,980 to 22,655 (-5.5%),
round 1 level. Max per turn rose on pool, big and heavy (early turns making two or three fields). A/B on
`fc7-m` (10,240 games, own drafts, real budget): **49.9% (48.9-50.9)**, out-of-fuel turns 69,970 against 71,830
(-2.6%; rounds 2-10 -21%). Frozen as `bots/variants/fc7-m1`. Evidence: EXPERIMENTS "Fuel campaign 7, merge 1",
`research/hyperion/fuel-campaign-7/NOTES.md`.

## 425: fuel campaign 7, merge 2: routes to no goals, altar lock beliefs, place_lock's reach (astraeus, 2026-11-06)

Fuel only, byte-identical at 100M on all six fc7 bench sets (def, wide, pool, big, heavy, td).
- A route to an empty goal board (farm's goals off its zone) returns exhausted with no labels, before building its
  walls or searching, as a walk-parted one does (`route_label_cap_ = -1`). No search labels a tile from no roots.
- `update_altars` skips the lock-forgetting loop and the allies' tribute proof while no altar holds a lock belief
  (`World::lock_beliefs_`, set by the lock read, the only writer of a belief).
- `place_lock` lists the altars in its reach once, in altar order (every altar past 8), and returns when none is.

100M against 5166d1c: total fuel -0.80% to -1.47% (-0.49% to -0.85% on merge 1), p99 -0.3% to -1.9%, turns over
100k 23,980 to 22,236, round 1 level. A/B on `fc7-m` (10,240 games, own drafts, real budget): **50.3%
(49.4-51.3)**, out-of-fuel turns 68,314 against 71,023 (-3.8%; rounds 2-10 -22%). Frozen as `bots/variants/fc7-m2`.
Evidence: EXPERIMENTS "Fuel campaign 7, merge 2", `research/hyperion/fuel-campaign-7/NOTES.md`.

## 426: fuel campaign 7, merge 3: altar walk after returns, kite plan memo, siege's team power, round-1 start-up (astraeus, 2026-11-06)

Fuel only, byte-identical at 100M on all six fc7 bench sets (def, wide, pool, big, heavy, td) and on a set of
Monolith, Monolith-only, shared-gems and altar-rebuild maps where the goal changes fire.
- `rebuild_altar_access` drops returned camps from the altar walk without a flood from spawn when the walk's tiles
  beside them stay connected through the rest of the walk (`returns_go_round`: a flood within it from one such tile,
  reach 16 then 64, else the flood from spawn as before).
- `kite_plan` keeps each group's plan while the group's version and the team's station output hold, and sums the
  output from each reach once a round; `siege()` works `team_power` out once a call; `team_pressed` loops over the
  visible enemies only, its board test last.
- Round 1: no static destructor is registered (`[[clang::no_destroy]]` on every global), the instance is a
  `constinit` global instead of zeroed on main's stack, the drafted attack tiles decode a chunk word's bush bits at
  once, team B's landing tiles sort as packed keys, and Pathing's trace tiles are left unzeroed.

100M against 5166d1c: total fuel -1.11% to -1.84% (-0.27% to -0.39% on merge 2; -1.6% on the Monolith set), p99
-0.9% to -2.7%, turns over 100k 23,980 to 21,462 (merge 2 22,236), round 1 mean -2.3% to -2.8%. A/B on `fc7-m`
(10,240 games, own drafts, real budget): **50.3% (49.3-51.3)**, out-of-fuel turns 63,798 against 70,795 (-9.9%;
round 1 -21%, rounds 2-10 -31%). Frozen as `bots/variants/fc7-m3`.
Evidence: EXPERIMENTS "Fuel campaign 7, merge 3", `research/hyperion/fuel-campaign-7/NOTES.md`.

## 427: fuel campaign 7, merge 4: the SDK's start-up globals skipped, a reach bound before the foe build (astraeus, 2026-11-06)

Fuel only, byte-identical at 100M on all six fc7 bench sets (def, wide, pool, big, heavy, td).
- `src/sdk_skip.cpp` defines the guard variables of the SDK's `champion_designs` and `draft_memory` as 1, so start-up
  never builds either (~6.1k a body in round 1); neither the SDK nor the bot reads them. draft.cc reads its
  `DraftPlan` bytes once at the top of `main()` (`capture_draft_memory`) and writes through the raw import; a
  `static_assert` pins both globals' names and types, so an SDK change fails to compile.
- `Safety::may_reach_within` and `credible_enemy_may_hit_within` skip an enemy farther than `Strike::max_reach` +
  turns (visible: from where it acts; unseen: its possible box) before building its foe (~1.5k).

100M against 5166d1c: total fuel -1.13% to -1.86% (-0.02% to -0.04% on merge 3), turns over 100k 23,980 to 21,443
(merge 3 21,462), round 1 mean -5.0% to -5.2% (-2.3% to -2.8% on merge 3). A/B on `fc7-m` (10,240 games, own drafts,
real budget): **50.8% (49.9-51.8)**, out-of-fuel turns 62,822 against 70,569 (-11.0%; merge 3 -9.9%; round 1 -33%,
rounds 2-10 -46%). Frozen as `bots/variants/fc7-m4`.
Evidence: EXPERIMENTS "Fuel campaign 7, merge 4", `research/hyperion/fuel-campaign-7/NOTES.md`.

## 428: fuel campaign 7, merge 5: turn ranks by counting, the stale turn caught in play_turn, our slot kept from the update (astraeus, 2026-11-06)

Fuel only, byte-identical at 100M on all six fc7 bench sets (def, wide, pool, big, heavy, td).
- `World::rank_turns` gives each champion the count of its team ahead of it (higher priority, or equal at a lower
  index) with two i32x4 vectors, a scalar loop past 8, instead of an insertion sort (`turn_order_` removed): the
  same ranks as the sort under its strict order (~550 a pass for 6 champions).
- A `StaleTurn` thrown in act, see_stuns or set_turn_order is caught at that try block in `aph::play_turn`, which
  returns: the same unwinding and destructors, with one personality call and no second unwind to main's run()
  (2,085 -> 1,093 a throw).
- `World::my_slot_now/next` (our slot this round and next) are set once in `update()`, the only place ranks and the
  round change, and read by `next_turn_round`, `turns_before_ours`, a threat check, update_champion's shield and
  channel expiry, `hold_start` and `now()`.
- update_champion works out the damage scale again only inside the emblem read (the one place `dealt` changes) and
  compares the emblem key as bits.

100M against 5166d1c: total fuel -1.58% to -2.05% (-0.20% to -0.52% on merge 4), turns over 100k 23,980 to 20,482
(merge 4 21,443), round 1 mean -5.1% to -5.4%. A/B on `fc7-m` (10,240 games, own drafts, real budget): **50.9%
(49.9-51.8)**, out-of-fuel turns 57,360 against 71,382 (-19.6%; merge 4 -11.0%; round 1 -33%, rounds 2-10 -49%,
11-60 -13%, 61-300 -18%, 300+ -14%). Frozen as `bots/variants/fc7-m5`.
Evidence: EXPERIMENTS "Fuel campaign 7, merge 5", `research/hyperion/fuel-campaign-7/NOTES.md`.

## 429: the timed lock: late locks on long enemy channels, a 100-gem deny, the merged altar site (ocean, 2026-11-06)

`bots/ocean` is now `bots/variants/oc-iw8-clean`: oc-retest-clean plus `variants/oc-fixm-iw8`'s behaviour as plain
code, frozen as `variants/oc-base5`. Their bench replays are identical at 100M (16/16 default, 52/52 wide). Notes: research/ladder-scrims-2026-11-06/fix-macro.md
(round 2).

**The timed lock** (fight.cc `lock_plan`):
- A body holding a lock for an enemy tribute (stop_game_ender) does not lock at once. It stands 8-11 steps from
  the altar's lock tiles, out of every visible enemy's reach, and keeps the plan while the channel is out of sight.
- It walks in to lock one turn before our last turn before the channel lands. The enemy then loses the whole
  channel, not the turns it had run.

**The deny** (channel_to_deny): a visible enemy tribute of 100+ gems that does not end the game is stopped the same
way when we hold a lock or a stun for it, unless our death would hand over max(40, its bag / 3) or more.

**The route:** holding a hard stop, stop_game_ender walks to the lock or stun tiles before it acts, since a ranged
attack spends the walk. The travel dash is never withheld on that walk (`force_travel_dash`); withheld near the
enemy, it sent 03homonoliths-a's Vesper back and forth for 60 rounds.

**The site guard:** the guard treats altars within 3 of each other as one site (00quarry, 03homonoliths, 04plaza),
held at its altar nearest the enemy spawn, and keeps our lock on the site's other tiles.

Results against oc-retest-clean, own drafts:
- 2x fuel: 51.0% of 20,480 (538000-538039), SPRT H1.
- Real budget, 538000-538039: 50.8% (50.1-51.5) of 20,480.
- Real budget, unused ptw-c (543080-543119): 50.5% (49.9-51.2) of 20,480. Pooled with the above: 50.65% (50.2-51.1)
  of 40,960. Out-of-fuel turns +6-7%.
- `--mix varied` (538060-538069): 50.3% of 5,120.
- The panel: mean +0.72 over the base's 68.3, no member down.
  - astraeus-now-1106: 54.6 against 53.1;
  - proteus: 64.4 against 63.3;
  - demeter: 67.1 against 66.0;
  - ocean-td: 81.7 against 82.1 (fail below 80.6);
  - v67: 77.5 against 77.2.
- Paired against fixed opponents at 2x, held out: bots/fish +0.20 points; the hoarding puppet `variants/fixm-hoard`
  +0.44 (+0.04 to +0.84).
- Live gate (v80): net -1 of 160 paired games (15/16 flips), level. The lock fires live (53 late cuts), but Fish and
  Mite break it in a median of 13 rounds and bank again.

## 430: fuel campaign 7, merge 6: round-1 zero fills left out, the emblem price's terms once, the landing order from the spawn's box (astraeus, 2026-11-06)

Fuel only, byte-identical at 100M on all six fc7 bench sets (def, wide, pool, big, heavy, td), and with every arena
allocation filled with 0xA5.
- `current_emblem` computes the current build's `upkeep_cost` terms (`UpkeepBasis`) and `fight_saved`'s fight
  scale and power once a pricing, not once a candidate: the same sub-expressions in the same order.
- An enemy without a dash gets no `undashed` board (`ChampionBelief(Walker)`): every use is behind `has_dash()`.
- `StaticMap::build` reads the enemy spawn's and the altars' tiles into static 64-tile buffers (`positions()`
  past 64).
- A spawn filling its bounding box gets `landing_tiles` row by row from the box (for team B the mirrored box,
  mirrored back): the old sort's order. Other spawns sort as before.
- World and StaticMap are made with `new T` (default-initialised): the bump arena never reuses memory, each is
  made once, and every member has an initialiser, so make_unique's zero fill (~630 each) did nothing.
- ChampionBelief's default constructor is user-provided (no 256-byte zero fill before the initialisers); World's
  `tracked_` and StandReach's `exposed`, `exposed_box`, `kind_strength` are left unwritten, read only below their
  counts.

100M against 5166d1c: total fuel -1.67% to -2.11% (-0.06% to -0.11% on merge 5), turns over 100k 23,980 to 20,242
(merge 5 20,482), round 1 mean -6.9% to -8.1% (-1.7% to -2.9% on merge 5). A/B on `fc7-m` (10,240 games, own
drafts, real budget): **50.7% (49.7-51.6)**, out-of-fuel turns 55,547 against 70,513 (-21.2%; merge 5 -19.6%;
round 1 -47%, rounds 2-10 -54%, 11-60 -13%, 61-300 -17%, 300+ -14%). Frozen as `bots/variants/fc7-m6`.
Evidence: EXPERIMENTS "Fuel campaign 7, merge 6", `research/hyperion/fuel-campaign-7/NOTES.md`.

## 431: fuel campaign 7, merge 7: the strike search's guard cover read on first need, Route's and Neighbours' tiles and home_fires' table left unwritten (astraeus, 2026-11-06)

Fuel only, byte-identical at 100M on all six fc7 bench sets (def, wide, pool, big, heavy, td), and with every arena
allocation, Route's and Neighbours' tiles and home_fires' table filled with 0xA5.
- `plan_strikes` reads the deferred step guard's cover (`step_guard_cover`, ~3k) only when a tile it may cover would
  count (the `sure < 2` pre-check, a tile the price loop selects within 2 of us, the capped tail), not in every
  search's `read_geometry`: nothing the cover reads changes before the plan is carried out, and the guard is
  resolved at the same points.
- Route's `first_steps` and Neighbours' `tiles` are left unwritten (anonymous unions, user-provided constructors):
  read only below `count`.
- `home_fires` zeroes only the spawn's tiles of its 64-entry fire table, the only ones read.

100M against 5166d1c: total fuel -1.88% to -2.29% (-0.18% to -0.24% on merge 6), turns over 100k 23,980 to 19,965
(merge 6 20,242). A/B on `fc7-m` (10,240 games, own drafts, real budget): **50.3% (49.4-51.3)**, out-of-fuel turns
51,059 against 70,013 (-27.1%; merge 6 -21.2%; round 1 -47%, rounds 2-10 -54%, 11-60 -18%, 61-300 -23%, 300+ -22%).
Frozen as `bots/variants/fc7-m7`. Evidence: EXPERIMENTS "Fuel campaign 7, merge 7",
`research/hyperion/fuel-campaign-7/NOTES.md`.

## 432: fuel campaign 7, merge 8: the step guard's exposed tiles from rows of bits, its keys from the union read and its first pass kept per Safety generation; altar-access floods, kite pricing and siege stands cheaper (astraeus, 2026-11-06)

Fuel only, byte-identical at 100M on all six fc7 bench sets (def, wide, pool, big, heavy, td).
- The step guard and its cover find the tiles more exposed than ours from rows of bits (`GuardFoes::each_exposed`):
  the same predicate in the same cell order and float order.
- The step guard's exact keys reuse the union read: `fight_enemies_any` records each unseen or lost enemy's first hit
  spot, and `fight_enemies_at` skips the enemies that hit none or first hit a later spot.
- The cover's first pass is reused outside the strike search too, keyed on our tile, the radius and
  `Safety::generation()` (bumped by every Safety made, `refresh()` and `invalidate()`; beliefs change only with a new
  Safety).
- `walk_deaths` floods within 8 steps first (a region holding at most 8 tiles is whole), and floods uncapped only past that;
  `returns_go_round` searches past reach 16 with `compute_to`, stopping once it holds the tiles beside the returns.
- `kite_productive_action` lists the covering allies and the members that may hit once, skips casts that cannot
  happen, reads the engagement tests only where they decide, and ends an endpoint no hit lands from; siege's stand loop
  lists the members that may hit once.

100M against 5166d1c: total fuel -1.92% to -2.32% (-0.03% to -0.05% on merge 7; heavy turns cheaper, p99 -0.2% to
-0.4%), turns over 100k 23,980 to 19,574 (merge 7 19,965). On the altar/siege fires-set, 81/82 games are identical; the
other diverges through `Pathing::route`'s `cheap_guard` switch, which reads the step guard's measured cost (the base with
debug prints added to the guard diverges the same way). A/B on `fc7-m` (10,240 games, own drafts, real budget):
**50.4% (49.4-51.3)**, out-of-fuel turns 50,582 against 70,161 (-27.9%; merge 7 -27.1%; round 1 -47%, rounds 2-10
-54%, 11-60 -19%, 61-300 -25%, 300+ -23%). Frozen as `bots/variants/fc7-m8`. Evidence: EXPERIMENTS "Fuel campaign 7,
merge 8", `research/hyperion/fuel-campaign-7/NOTES.md`.

## 433: astraeus's fuel campaign 7 merges 1-5 (CHANGES 424-428) in ocean (ocean, 2026-11-06)

Fuel only, ported by hand into a copy of `variants/oc-base5` (patches from f9ff0caa and the merge 3-5 commits; ocean's
siege, bank and fight code differ, its model files hardly at all). Byte-identical to oc-base5 at 100M on 246 games
(16/16 default, 52/52 wide, 128/128 fc7 pool, 50/50 fc7 heavy).
- 424: `stand_lost_at`'s reads (walks and pursuit only when the roster reads them; `stand_walks`). **Left out:** the
  farm loop's first two centre fields in place of the flood from here. Fields that persist a turn sooner change a
  later approach (gen-monolith-heavy-102107600, round 9: a crew join instead of group 20), with or without
  `want_centre`.
- 425: all of it (routes to no goals, `lock_beliefs_`, place_lock's altars in reach).
- 426: the altar walk's `returns_go_round`, kite_plan's output sums and per-group memo, `team_pressed`, and the
  round-1 start-up (`no_destroy`, `constinit` instance, attack-tile words, team B's landing keys, Pathing's trace
  tiles). **Left out:** siege()'s `team_power` once a call, which diverged on the same game at the same decision
  (a pure fuel burn in siege() did not).
- 427, 428: all of it (`sdk_skip.cpp`, `may_reach_within`'s reach bound; `rank_turns` by counting, StaleTurn caught in
  play_turn, `my_slot_now/next`, the damage scale in the emblem read).

100M, mean fuel a play turn: -1.4% to -1.7% (424 -0.1%, 425 -0.6 to -0.9%, 426 -0.2 to -0.3%, 427 ~0, 428 -0.5%); p90
-0.1%; max -0.6 to -1.2%; round 1 -5.2 to -5.5% (426 -2.4 to -2.9%, 427 -2.7 to -2.9%). A/B on fresh-547000..547039
(`merged/fuel8-conf`, 20,480 games, own drafts, fast runner, real budget): **50.9% (50.3-51.6)**, out-of-fuel turns
141,506 against 169,924 (-16.7%; round 1 -35%, 2-10 -26%, 11-60 -11%, 61-300 -15%, 300+ -15%),
farm-partial-evaluation -5.7%, turn-order -16%, prey-cut-short -13%. Frozen as `bots/variants/oc-fuel8`; merged as `bots/ocean`
(`variants/oc-base6`, identical to oc-fuel8 at 100M). Evidence: EXPERIMENTS "Fuel round 8: astraeus's campaign 7 in ocean".

## 434: astraeus's fuel campaign 7 merges 6-8 (CHANGES 430-432) in ocean; the lock plan's wait tiles once an altar (ocean, 2026-11-06)

Fuel only, in a copy of `variants/oc-base6`. Byte-identical to oc-base6 at 100M on 246 games (16/16 default, 52/52
wide, 128/128 fc7 pool, 50/50 fc7 heavy), checked after 430, 431, 432's step guard, its floods and its kite and
siege pieces, and the lock plan.
- 430, 431, 432: all of them, from the campaign's commits (537d936a..b01c2230, b6390da2..9b454ca6). Only main.cc's
  `new aph::World` was placed by hand (ocean has no first-turn spawn-field line).
- `lock_plan_wait` (CHANGES 429) tested the up to 27 x 27 tiles round the altar one host call at a time, up to three
  passes a turn (~60k a pass): the open tiles within 11 steps of the lock tiles, and those 8 or more, are static, so
  each altar's two boards are made once, and a pass is the band less the enemies' reach mask.

100M, mean fuel a play turn (def / wide / pool / heavy): -0.5 / -1.1 / -1.5 / -2.9% (430 -0.2 to -0.3%, 431 -0.2%, 432
~-0.05%, the lock plan 0 / -0.5 / -1.0 / -2.4%); round 1 -1.6 to -3.0% (430); pool max -4.8% (432). A/B on
fresh-547100..547139 (`merged/fuel9-conf`, 20,480 games, own drafts, fast runner, real budget): **50.9% (50.2-51.6)**,
out-of-fuel turns 120,429 against 143,281 (-16.0%; round 1 -23%, 2-10 -11%, 11-60 -8%, 61-300 -11%, 300+ -20%),
turn-order -13%, comms-stale-vision -8%, farm-partial-evaluation -3%. Frozen as `bots/variants/oc-fuel9`; merged as `bots/ocean`
(`variants/oc-base7`, identical to oc-fuel9 at 100M). Evidence: EXPERIMENTS "Fuel round 9: campaign 7's merges 6-8 and the lock plan's wait in ocean".

## 435: fuel campaign 7, merge 9: Reach's way bounds once a build and no dash-only work without a dash, allies' next turns on first need; the fight sim's early end out of line and asked only as a member falls (astraeus, 2026-11-06)

Fuel only, byte-identical at 100M on def, wide, pool, big and heavy; td 63/64 (below).
- `Reach::build` works out each way's bound once (`bounds_`, after every `build_ways`), and a build whose enemy has
  no dash ready skips the dash-only work (the last dash slot, the allies' `fixed` and bush bits, the camps' solid
  bits: they feed only the dash path). An ally's next turn is worked out only when a dashing enemy's window holds it.
- The fight sim's early end (`decided`, out of line, returning its turns) runs at the start and after an act only
  when `us.alive + 16*them.alive` changed (members fall only in act and the camps' hits; play_quiet never kills), not
  on the last turn; non-plain act looks for stunned members only when some are; act's member loops unroll for one.

100M against 5166d1c: total fuel -2.01% to -2.37% (merge 8 -1.92% to -2.32%; p99 -0.2% to -0.6% on merge 8), turns
over 100k 23,980 to 19,163 (merge 8 19,574). The td game that differs diverges through `Pathing::route`'s `cheap_guard`
switch (the step guard's measured cost, 15,559 for merge 8 and 14,695 here in round 370, against 15,000), the first
difference in a debug trace. A/B on `fc7-m` (10,240 games, own drafts, real budget): **50.7% (49.8-51.7)**,
out-of-fuel turns 48,321 against 71,064 (-32.0%; merge 8 -27.9%; round 1 -47%, rounds 2-10 -54%, 11-60 -22%, 61-300
-28%, 300+ -29%). Frozen as `bots/variants/fc7-m9`. Evidence: EXPERIMENTS "Fuel campaign 7, merge 9",
`research/hyperion/fuel-campaign-7/NOTES.md`.

*Note (2026-11-06, from ocean's SPSA oc5; see CHANGES 436):* not behaviour-exact in every state. In ocean (436) with
oc5's tuned constants it diverges on 00gemfight b (round 430: a dash for a walk), through the same `cheap_guard`
switch as the td game above: the step guard's measured cost, which main.cc's real-budget tile warming feeds even at
100M. The safety.cc changes themselves are semantically equal; any fuel change can flip that switch.

## 436: astraeus's fuel campaign 7 merge 9 (CHANGES 435) in ocean (ocean, 2026-11-06)

Fuel only, in a copy of `variants/oc-base7`. All six of 435's commits (64acbeff..e015010a) apply unchanged: ocean's
`model/safety.{cc,h}` were astraeus's before them. Byte-identical to oc-base7 at 100M on 246 games (16/16 default,
52/52 wide, 128/128 fc7 pool, 50/50 fc7 heavy); mean fuel a play turn -0.1% on each set, p99 -0.2 to -0.4%, round 1
unchanged. Real-budget benches, out-of-fuel turns 1,979 -> 1,856 (heavy 602 -> 510). A/B on fresh-547200..547239
(`merged/fuel10-conf`, 20,480 games, own drafts, fast runner, real budget): **50.2% (49.5-50.9)**, level; out-of-fuel
turns 117,046 against 121,244 (-3.5%; round 1 and 2-10 level, 11-60 -4%, 61-300 -4%, 300+ -4%), turn-order -4%,
step-guard-entry -2%. Profiling found no exact lever in ocean's own code (EXPERIMENTS "Fuel round 10"). The A/B is level, not a win: it is merged as exact
with fewer out-of-fuel turns, and keeps ocean's safety.cc in step with astraeus's for later ports. Frozen as
`bots/variants/oc-fuel10`; merged as `bots/ocean` (`variants/oc-base8`, identical to oc-fuel10 at 100M).

*Note (2026-11-06, SPSA oc5):* exact on the bench sets at default constants, not in every state.
- With oc5's 26 tuned constants patched in, oc-base8 diverges from oc-base7 on 00gemfight side b in round 430:
  champion 8 dashes where it walked. oc-fuel8 and oc-base7 stay identical, and it reproduces at 1e9 fuel.
- The cause is the same as in 435's td game. The simulate() rework alone (`decided`, the alive-gated checks) is
  semantically equal to the old loop, but it shifts fuel. main.cc's tile-warming pass spends the leftover fuel as if
  the budget were real, even at 100M, so the shift changes how far the caches are warmed. That changes the step
  guard's measured cost (`step_guard_costliest`), which flips `Pathing::route`'s `cheap_guard` switch (15,000).
- With that switch disabled, or the warming pass off, the two replay identically.
- No exact fix in 436 exists: any fuel change can flip this switch. Making it exact means replacing the measured cost
  with a deterministic estimate, which is a behaviour change. Evidence: EXPERIMENTS "SPSA retune round oc5".

## 437: fuel campaign 7, merge 10: the strike search's members unzeroed and its grid boards read in place on big maps; the wakers' and camp threats' champion lists once a group or call, farm's clear priced last (astraeus, 2026-11-06)

Fuel only, byte-identical at 100M on def, wide, pool, big and heavy; td 63/64 (merge 9's game, below), and identical to
merge 9 on all seven sets.
- The strike search leaves its members' healths and death cells unzeroed (read() writes both below n, nothing reads
  past it), and on maps of 100+ 8x8 chunks reads its grid boards (blocked, and the pass board's three without
  `or_into`) from the board storage in place through pathing.cc's window; the box is drawn only where still needed.
- `Search::find_wakers` lists the champions within the group's widest reach of its members' box once per group, in the
  same order; `threats_near` lists the other champions and their turn order once a call, not per camp member; farm's
  `passing()` prices a clear (`affordable`) only after its cheap tests pass.

100M against 5166d1c: total fuel -2.07% to -2.43% (merge 9 -2.01% to -2.37%; -0.03% to -0.09% on merge 9), turns over
100k in the six sets 23,980 (base) -> 19,163 (m9) -> 19,064. The td game that differs is merge 9's, through
`Pathing::route`'s `cheap_guard` switch; on the camps-hot set (96 games) the one game merge 9 differs in from the base
(`mut-one-gem-77021217053` b) diverges the same way (15,348 for merge 8, 14,906 for merge 9 in round 126). A/B on
`fc7-m` (10,240 games, own drafts, real budget): **50.5% (49.6-51.5)**, out-of-fuel turns 48,710 against 71,315
(-31.7%; merge 9 -32.0%: level). Frozen as `bots/variants/fc7-m10`. Evidence: EXPERIMENTS "Fuel campaign 7, merge
10", `research/hyperion/fuel-campaign-7/NOTES.md`.

## 438: draft6: ocean drafts from a ladder-mix lab of its own play against mixed opponents, F92 model (ocean, 2026-11-06)

`draft/draft_model.h` and `draft/map_features.{h,cc}` from `variants/oc-draft6-f92` on `variants/oc-base8`; nothing else
changes. Lab `replays/draftlab/draft6`: 1,000,000 games, oc-base7 the player against ocean itself, astraeus-now-1106 and
panel-proteus (a third each), on the ladder plus fresh ladder-mix seeds 548000-548099. Draft5's sampling is kept.
The fit adds a per-opponent offset and per-opponent champion deviations. Deployed fit (`replays/draftlab/draft6-f92`):
draftfeat's 92 features, CV log loss 0.5658 against 0.5698 for the 25. Counters (-3.7 (1e-4)) stay off, as do an LCB team rule and extra shrinkage,
which were level in play. JS/C++ parity on the ladder and fresh-548200: 0 team mismatches. First draft turn max 9.23M (base 9.17M), none
of 1,348 out of fuel.

A/B against oc-base7, own drafts, fast runner (20,480 games a cell; d6-v 5,120):

| Draft | d6-e 2x fuel | d6-c 2x (held out) | df-c real | d6-v `--mix varied` real | panel mean |
|---|---|---|---|---|---|
| draft6 25 features (`oc-draft6`) | 51.8% | 51.9% | 52.1% | 49.5% | +1.42 |
| **draft6 F92 (this change)** | **52.9%** (52.3-53.6) | **53.4%** (52.7-54.1) | **52.9%** (52.2-53.6) | 51.0% (49.6-52.4) | **+2.10** |
| F92 against 25 features | 50.9% | 51.3% | 51.1% | | |

One-altar / multi-altar maps: 54.2 / 52.6% (d6-e), 52.6 / 53.6% (d6-c), 54.2 / 52.5% (df-c), 53.4 / 50.6% (d6-v).

Panel (real fuel, `panel-check-514510`, 5,120 games each, oc-base7 re-measured):

| Member | oc-base7 | this change |
|---|---|---|
| astraeus-now-1106 | 54.9 | 57.6 (+2.7) |
| panel-proteus | 63.6 | 66.3 (+2.7) |
| panel-demeter | 66.6 | 69.0 (+2.4) |
| panel-ocean-td | 82.3 | 83.5 (+1.2) |
| baselines/v67 | 78.1 | 79.6 (+1.5) |

Notes:
- No member is down. Demeter, ocean-td and v67 were not lab opponents.
- Out-of-fuel turns rise about 4% at the real budget (118.1k against 113.8k on df-c).
- **Stale data, not features:** the same F92 form fitted on draft5's games read 49.9% (draftfeat). Refitted on the
  current player's games against mixed opponents on a ladder-mix pool, it drafts ~3 points better.
- Ladder teams change on 101 of 126 maps. Vesper (44 to 60%), Willow (32 to 47%) and Tavi (2 to 13%) rise; Marcella (52 to 37%), Ryth (30 to 11%) and Prism (83 to 75%) fall.
- At 100M, bots/ocean is byte-identical to oc-draft6-f92 (which has oc-base7's safety files) on 68 of 68 bench games (def 16, wide 52).

Frozen as `bots/variants/oc-base9`. Evidence: EXPERIMENTS "Draft6 lab (ocean, 2026-11-06)",
`research/ideas-2026-11-05/draft6.md`.

## 439: our own turn-end recall is not a channel for the walk to our farm choice (astraeus, 2026-11-06)

`start_recall`'s turn-end recall, which the next turn cancels unless kept, counted as a channel in `walk_target`, so
off spawn neither act()'s turn-start approach nor `prepare_next_turn`'s searched the walk to our farm group: 35.9% of
the strike search's goal-field reads found none (ladder, 256 games).
- `recall_feint` (bank.cc) marks a recall start_recall began and no turn has kept (continue_recall clears it);
  `channel_held()` is `channelling()` but for it. `walk_target` (now farm.cc, by group) and the self branch of
  capture's `held_back` read it. Wards, locks, start_recall and `strike_after` keep `channelling()`: the engine
  refuses those during any channel.
- `prepare_next_turn` searches the walk on feint turns, unless farm means to keep the recall (`recall_farm`).
  act()'s turn-start approach still skips any channel; `goal_field` searches when the strike search reads it
  (`prepare_approach`, floor `act_reserve + 30000`). The goal gain is `max(0, steps here - steps there)`.
- Reads without a field 35.9% -> 6.7%.

A/B against `variants/astraeus-0305953` on `merged/gf2-741` (fresh 741001-741040), own drafts, real budget: 50.1% of
20,480 (49.5-50.8), out-of-fuel turns 90,295 against 92,095. Level; kept as the rules' reading of our own recall.
Frozen as `bots/variants/astraeus-gf2`. Evidence: EXPERIMENTS "The goal field off spawn, retried".

## 440: feinting enemies read by kept recalls: camp wakers, unseen heals, a new bag's bank keeps the feint (astraeus, 2026-11-06)

Every team starts a recall at its turn ends and cancels it next turn unless wanted (research/recall-detection-2026-11-06.md:
Fish and Mite too), so a recall seen at its start says nothing of intent.
- **Camp wakers** (`find_wakers`): an enemy counts as staying by the camp only if it has acted, has a stun pending,
  or is on a tribute, teleport or kept recall lasting past this round (`held_this_round`, world.h), not on any channel.
- **Unseen heals** (world.cc): `recall_kept` is computed for enemies too. Once the enemy team is seen feinting
  (`enemy_feints_`: an unhurt enemy, read after its turn, restarting a recall two rounds running), an unseen enemy's
  recall heals it only if kept; before that, as before. The spawn stays in its `possible` either way.
- **The bank keeps the feint** (`recall_to_bank`): a bag new this turn that carry_bag is sure to bank
  (`banks_bag && (closing || !may_chain)`) keeps the running recall instead of cancelling and restarting it a round later.

A/B against `variants/astraeus-9e1fad3` on `merged/ff24-746` (fresh 746001-746040), own drafts, real budget: 49.9% of
20,480 (49.2-50.5), out-of-fuel turns 96,517 against 94,402. Level; kept as the rules' reading of enemy recalls.
Frozen as `bots/variants/astraeus-ff24`. Evidence: EXPERIMENTS "Turn-end feint fixes, feintfix".

## 441: the pooled level changes plus tuned constants (ocean, 2026-11-06)

Eleven changes that each read 50.1-50.8% alone (none significant), pooled, with oc-tuned5's SPSA constants and
mapcond2-q's map conditioning, on `variants/oc-base9`. The tested arm is `variants/oc-pool1t`, where each member sat
behind a `params::pool` flag over its source's knobs; here every member is unconditional and the off knobs' code is gone
(the race model, the kill rule, the seat ledger, nuke zones, fight openings, the hunt, ambush and hop gambits, obese
bags, channel fixes C1-C4, Ryth's Marcella draft check, the ungated mirror pull).
- **cbdp** (comeback.cc, farm.cc, fight.cc): while cooked (enemy 400+ tributed and 150+ ahead, until under 100), farm's
  mirror pull and enemy-side camps x1.5, and lost chases taken against a 40+ carrier while we last 2 turns with the
  other allies (up to two) within 4.
- **ptw** (turn_window.{h,cc}, safety.cc, fight.cc, plan.cc, turn_order.cc): enemies' turn order as a window in threat
  and slot checks; this round's enemy turns after ours go to the unseen enemies nearest our turn's start.
- **b3w** (altar_guard.cc): winning-bag escorts clear enemies within 8 of the altar, walking at the nearest.
- **bt3** (fixc.cc, pathing.cc, fight.cc): first steps and retreat ties take a hidden bush; within a ready enemy
  strike's reach + 2, the bush rank comes first and a hidden bush step is let off 0.1 of our health of damage.
- **t1b** (shop.cc, bank.cc): the Tribute emblem priced from the bag we carry, from 100 gems; a restarted channel's
  cut counts once.
- **r1** (farm.cc): the banking farm loop's walk reserve at 60%.
- **b5** (guard.cc): a 100+ bag at stake makes the pack zone outmatch us at ratio 2 (hurt_retreat_ratio is 3.34).
- **b1** (bank.cc): a 150+ bag with a 10+ turn channel banks at the altar best on threat arrival, channel, walk and cover.
- **cm2** (fixc.cc, bot.cc): a lost retreat from one pursuer, hit lately, fights when our attacks kill it a turn first.
- **gf** (fight.cc, safety.cc): prey's chase against a carrier plays with our health x (1 + min(0.3, bag value / life)).
- **c1** (plan.cc): the strike search capped at 12 nodes and 6 exact queries (24 and 10).
- **tuned5** (params.h, capture.cc): oc5's 26 SPSA constants. **mapcond-q** (draft.cc `condition_on_map`, main.cc):
  recall_health_fraction and gold_price_scale shifted per map on each champion's first turn by a quarter of oc5's
  fitted feature slopes.

Evidence (own drafts, fast runner, against oc-base9): real budget **53.3% (52.6-54.0) of 20,480 on each of two unused
suites** (pool-held 570100-570139, pool-held2 570400-570439); 2x SPRT H1 at 2,593 games; `--mix varied` 52.2% of 5,120;
panel mean +2.0, no member down (astraeus-now-1106 +2.7, proteus +2.7, demeter +2.6, ocean-td +1.0, v67 +1.0).
Out-of-fuel turns +58% at the real budget (190.1k against 120.3k), mostly ptw's.

Leave-one-out at 2x (20,480 each; below 50 the member helps): t1b 49.2 (48.5-49.9, the one significant alone), tuned5
49.5, ptw 49.7 (50.1 at the real budget, where it costs ~30% of the out-of-fuel turns), cbdp 49.8, cm2 49.8, bt3 49.9,
mapcond-q 49.9, b1 / b3w / b5 / gf / r1 50.0, c1 50.3. Dropping ptw and c1 together (oc-pool3t) read 52.1% against
oc-base9 and 49.7% against oc-pool1t, so the pool is kept whole.

The cleanup is exact: byte-identical to oc-pool1t at 100M on 68 of 68 bench games (default 16, wide 52 with test
drafts), total fuel -0.3%. At the real budget the wide set diverges in 33 of 52 games, as any fuel shift does there;
out-of-fuel turns 741 against 722 (bench noise). Frozen as `bots/variants/oc-base10`. Evidence: EXPERIMENTS "Pooled level changes",
`research/ideas-2026-11-06/pool.md`.

## 442: initial unlimited-fuel teacher with wip accuracy fixes (astraeus_teacher, 2026-11-06)

`bots/astraeus_teacher` is a clone of current astraeus with astraeus_wip's
CHANGES 362–401 assumption fixes merged against their common source base.
It retains astraeus's draft5, tuned constants, gold efficiency, emblem fight
value, reveal wards and recall fixes. Fuel gates and end-turn warm-up are gone;
exact caches remain. Strike enumeration and exact pricing have no node/query
budget, leaves and camp wakers grow as needed, local masks cover the complete
search window, and long walking queries no longer fall back at the cache cap.
Neither astraeus nor astraeus_wip was edited.

`tools/teacher_ab.py` runs exactly 10k games by default with unlimited teacher
fuel and unchanged normal opponent fuel, using the native fast runner's
`FASTRUNNER_UNLIMITED_BOTS`. The default runner remains byte-identical to stock
in the dedicated regression check; asymmetric budgets were checked on both sides.

First benchmark against astraeus, fresh ladder-mix maps, own drafts:
**47.38% of 10,000 (46.40–48.36)**, no failed matches, out-of-fuel turns 0 vs
46,484. This is the requested starting teacher, not a strength improvement.
Evidence: EXPERIMENTS "Initial unlimited-fuel astraeus teacher" and
[the report](../astraeus-teacher-2026-11-06/README.md).


## 443: repair teacher crew bookkeeping; retire astraeus_wip (astraeus_teacher, 2026-11-06)

The wip crew reader did not fill the newer astraeus farm’s claiming index, so
crew_work ignored allied progress after the crew table was read and overvalued
joining camps that would be finished before arrival. Rebuild that index with the
records. Keep all exact-walk and wip model changes, unlimited searches and caches.
Also check current ally visibility before reading its shield for turn-order bids.

The crew-index fix raises the teacher from 47.38% to **52.48%** against normal-fuel
astraeus on the same 10,000 games. A new-seed 10,000-game confirmation gives
**52.62% (51.64–53.60)**, zero failed matches and zero teacher fuel exhaustion.
Three generated layouts repeat; the other 9,994 games give 52.61% (51.63–53.59).
A 10M-fuel unchanged-astraeus control scores 52.73%; restoring the teacher’s old
search caps, original combat planner, shop pricing or cache warm-up does not
recover the regression. Detailed ablations are in the teacher report.

Remove `bots/astraeus_wip` at the user’s request, with its port in
`bots/astraeus_teacher`. The original source remains in git history.
Evidence: EXPERIMENTS “Teacher regression: missing crew index” and
[the report](../astraeus-teacher-2026-11-06/README.md).


## 444: exact teacher terrain visibility (astraeus_teacher, 2026-11-06)

Combat and support use cluster-correct bush visibility, retaining terrain caches.
Reveal wards rank legal positions by actual shadowcast coverage of suspect tiles.
Strategic weights, cluster selection and uncertainty about enemy wards stay intact.

Unlimited teacher versus unchanged normal-fuel astraeus, own drafts, 20,000 games
per version: **53.265% versus 53.045%** (+0.220 points). Another 20,000 games each
on unseen unique layouts: **53.425% versus 53.340%** (+0.085 points). Neither
paired interval excludes zero; kept under the requested measured-WR rule with
positive results on both suites. No match errors or teacher fuel exhaustion.
Evidence: [teacher audit](../astraeus-teacher-2026-11-06/AUDIT.md).


## 445: preserve HoR retaliation states (astraeus_teacher, 2026-11-06)

Combat frontier dominance now requires no stronger surviving Heart of Ruin
retaliation as well as at least as much raw value and enemy removal. The same
multiplier serves dominance and final scoring. Growing frontiers and candidate
lists retain nondominated states without a fixed 64-entry limit; constructed
vector storage stays outside the raw table union.

Unlimited teacher against unchanged normal-fuel astraeus, 20,000 games each:
53.320% versus 53.265% (+0.055 points). Fresh confirmation: 53.025% versus 53.065%
(−0.040 points). Zero match errors or teacher fuel exhaustion. These tiny deltas
establish no WR gain. Kept under the user's explicit correctness exception:
the previous pruning could discard a better-scoring plan before applying its
existing HoR return-damage adjustment. Evidence: [teacher audit](../astraeus-teacher-2026-11-06/AUDIT.md).


## 446: exact retreat continuation (astraeus_teacher, 2026-11-06)

Exit damage now minimizes the cumulative camp damage along descending shortest
paths, sharing memoized results across candidate first steps. HomeWalk checks all
descending continuations ending at a spawn tile that meets its survival condition.
Strict survival tests, blockers, recall horizon and danger estimates stay intact.
ExitHits uses an explicit stack; HomeWalk recursion is bounded by the existing
six-step strategic horizon. Damage caches last only for the current decision.

Unlimited teacher against unchanged normal-fuel astraeus, 20,000 games: exactly
level at 53.320% (10,664 wins each; 153 gained, 153 lost), no match errors or teacher
fuel exhaustion. Kept as a pure calculation improvement under the user's exception.
The initial bundle also removed the exit-field depth cap and changed unreachable
handling; it lost 0.240 points, so those changes are excluded. Evidence:
[teacher audit](../astraeus-teacher-2026-11-06/AUDIT.md).


## 447: search complete camp exit fields (astraeus_teacher, 2026-11-06)

Camp exit fields now search fully and invalidate on Safety generation, camp
version and member discovery. Long routes use the existing exact continuation
pricing. Truly unreachable exits retain the original finite risk estimate;
removing the search cap does not require treating every no-exit state as trapped.

Unlimited teacher versus normal-fuel astraeus, 20,000 games: **53.320%**, all
winners unchanged, zero failed matches and teacher fuel exhaustion. The earlier
full bundle's no-exit policy caused its regression and remains excluded. Evidence:
[teacher audit](../astraeus-teacher-2026-11-06/AUDIT.md).


## 448: count every relevant camp member (astraeus_teacher, 2026-11-06)

Combat danger includes every qualifying awake camp member. Spell-clear goals
include all living strikers. StandReach uses dynamic multiword reach, home, kind
and living masks, with integer striker indexes and complete SIMD padding.
Small-group arithmetic and ordering, stand selection, reflection, average output
and tuned prices remain intact.

Unlimited teacher versus normal-fuel astraeus, 20,000 games: 53.300% versus 53.320%
(3 gained, 7 lost; no clear WR effect), zero failed matches or teacher fuel
exhaustion. Kept as a completeness fix under the user's correctness exception.
Evidence: [teacher audit](../astraeus-teacher-2026-11-06/AUDIT.md).

## 449: draft-side map facts, a draft that always finishes in its first turn, and a loud local guard (ocean, 2026-11-06)

`variants/oc-draftcond`, then `variants/oc-draftfin`, on `variants/oc-base10`; frozen as `bots/variants/oc-base11`.
Design, byte budget and fuel tables: [draft-features.md](../ideas-2026-11-06/draft-features.md).
- **Draft-memory channel** (`PlanFacts`, after `PlanHeader`): the map facts `condition_on_map` reads (spawn distance,
  altars, gems, big gems) are measured in the draft and read on the champion's first turn, which measures them
  itself without a plan. An outputs block carries up to 31 16-bit constants for a draft-side model, and a done bit
  records whether the precompute finished in draft round 0. `current_version` is 11.
- **Exact draft speedups** (picks, ward codes and plan bytes identical on 6400/6400 drafts):
  - the index written before the ward search;
  - unmasked ward scoring;
  - a sight_gap blocker table;
  - SIMD play mask, narrow and sight_gap rows (native and in-game feature parity, 6400/6400).
- **Cap backstop**: in the draft's first turn an optional part (dash fields, leads, attack tiles, index, ward sites)
  starts only if the fuel left covers its upper bound, the index's and 300k over the 500k reserve; otherwise its
  section is cut where it is and the analysis finishes. Only the map, facts, fields and steps can leave it
  unfinished.
- **Local guard**: local builds find `sdk/cpp/cambc_local.h` (the platform's SDK has none, checked through `cambc
  bundle` and a fresh `cambc init`). On an unfinished draft a local build prints `DRAFT-UNFINISHED` and resigns; on an
  unusable plan, `PLAN-CHECK`, also in `--release`. ab.py, run_batched, bench, tune.py and the lab tally them, and
  `DRAFT-CAPPED` marks a capped draft.

Evidence (real budget, own drafts, fast runner):
- draftcond against oc-base10: **50.2%** (49.5-50.9) on s630420-59, 20,480 games; round-1 OOF lines −44%.
- draftfin against oc-base10: **50.6%** (49.9-51.3) on s630600-39, 20,480 games; **52.1%** (50.1-54.2) on its
  1,172 maps of area 8100+, huge or maze (2,344 games). CAND had no handoff failures; REF resigned 4 games to
  PLAN-CHECK on one map, where its draft ran out of fuel before writing a plan. OOF turns −4.4%.
- First turn at unlimited fuel (3200 maps, 6400 drafts): max 13.9M → 12.1M, p99.9 12.0M → 10.5M.
- At 10M: 6400/6400 finished; 40 capped (0.6%); none of the 256 ladder drafts capped (max 8.06M,
  01big-world, at least 1.92M left).
- bench `--set wide` at 100M: 52/52 identical to oc-draftcond.


## 449: replan a blocked opening walk (astraeus_teacher, 2026-11-06)

When the first planned walk hits a hidden blocker, rerun the complete combat
search and pricing with the newly blocked tile. An iterative wrapper starts the
new attempt only after the old Search and its shared-table references leave
scope. Guards are restored and turn staleness checked at the retry boundary.
Each failed opening records another blocked neighbour, without a retry/fuel cap.
Blocked dashes and failures after successful actions keep the existing fallback.

Unlimited teacher versus normal-fuel astraeus, 20,000 games: **53.280% versus
53.300%** (12 gained, 16 lost; no clear WR effect), zero match errors or teacher
fuel exhaustion. Kept under the user's correctness/completeness exception.
Evidence: [teacher audit](../astraeus-teacher-2026-11-06/AUDIT.md).

## 450: astraeus's fuel campaign 7 merge 10 (CHANGES 437) in ocean (ocean, 2026-11-07)

Fuel only, on `variants/oc-base11`, from `fc7-m9`..`fc7-m10`. The strike search's members are left unzeroed and, on
big maps, its grid boards are read in place. The wakers' and the camp threats' champion lists are made once, and farm's
clear is priced last. Two changes were made by hand. find_wakers keeps ocean's `enemy_latest_slot` for enemies in the
near list. `passing` returns `affordable(g)` for the farm group: astraeus's returns true, which would make the reorder
inexact. The recall-feint readings 439 and 440 were tested as knobs and left out, since both were level
(research/ideas-2026-11-07/astport2.md). bench.py at 100M against oc-base11 is byte-identical (16/16 default, 52/52 wide), with
total fuel -0.06% on wide. Own drafts, fast runner, real budget, against oc-base11: **50.45% (50.0-50.9) of 40,960**
on unused fresh 680201-680280 (50.3% and 50.6%), out-of-fuel turns **-1.3%** (369.3k against 374.3k). Frozen as
`bots/variants/oc-base12` (= `bots/ocean`). Evidence: EXPERIMENTS "Ocean vs astraeus and astport2 (ocean, 2026-11-07)".

## 451: ocean becomes astraeus with ocean's changes ported in (ocean, 2026-11-07)

`bots/ocean` is now astraeus 8c0343f5e (CHANGES 440) with ocean's 407, 408, 416, 429, 434's lock bands, 438, 441 and
449 ported in, each from its frozen variants' diff, rejects merged by hand; it replaces oc-base12 (CHANGES 450), and
`bots/astraeus` stays at 8c0343f5e. So ocean now also has astraeus's changes it lacked: 409-412's accuracy fixes, 424's
centre fields, 426's TeamPower, 3076ffa9's farm reserve and bounds, 439 and 440 (437 it had as 450).
- 407, 408 (home Monolith siege on Monolith-only maps; one-altar altar control, `economy/altar_guard.cc`): from
  `astraeus-port1` -> `astraeus-port2`. 416 (home sieges on mixed maps, `home_reach_avoid`): `oc-fuel4` -> `oc-spawn2`;
  `siege_ready`'s home scaling merged under astraeus's `TeamPower`.
- 429 (the timed lock, the 100-gem deny, the merged altar site): `oc-retest-clean` -> `oc-base5`, with 434's static
  per-altar bands in the lock plan's wait.
- 438 (draft6, F92 model): the draft is ocean's, draft.cc included, so astraeus's CHANGES 412 is left out and the draft
  reads `draft_recall_health_fraction` (0.227): tuned5 moved `recall_health_fraction` to 0.315, far from what 412
  tested.
- 441 (the pool, tuned5 and map conditioning; `combat/fixc.cc`, `economy/comeback.cc`, `model/turn_window.{h,cc}`):
  all but r1 (the banking walk reserve at 60%), since astraeus's own state-sized `after_loop` reserve replaced that
  reserve (r1 read 50.0 in 441's leave-one-out). Adapted: the comeback pull in astraeus's `beaten_near` (both branches);
  ptw's `enemy_latest_slot` in 437's wakers near-list; b1's altar choice through 410's `lock_turns(belief, facts, walk)`;
  t1b's `reactive_over` reads the forecast's `items` (396), and `prices()` / `affordable_prefix()` key on the bag from
  `trib_min_bag` gems, which t1b's Tribute price reads.
- 449 (PlanFacts, the draft's cap backstop, the local `DRAFT-UNFINISHED` guard).
- Dropped from ocean: 406's remaining farm fuel steps (the ally_rate memo, may_expect's list, the early last prune),
  measured redundant or worse in astraeus; ocean's `shopping`-only learned emblem (astraeus's 396 forecasts kept) (EXPERIMENTS "ocean's farm-turn fuel steps (CHANGES 406) ported to astraeus").

Own drafts, fast runner, real budget, against the ocean it replaces (`variants/oc-base12`, CHANGES 450) on unused fresh 880000-880078
(`merged/astport-oc-40k`): **50.3% (49.8-50.8) of 40,448**, out-of-fuel turns 331.0k against 367.4k (-9.9%), no failed
matches or draft handoff failures; capped drafts 245 each. oc-base11 had beaten 8c0343f5e 56.7%. Frozen as
`bots/variants/astraeus-ocport` and `bots/variants/oc-base13` (= `bots/ocean`). Evidence: EXPERIMENTS "ocean ported into astraeus (2026-11-07)".
