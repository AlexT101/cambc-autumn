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
