# fix-combat: LOSSES.md candidates 2, 3, 4 and 9 (2026-11-06)

Base `bots/variants/oc-retest-clean` (= `bots/ocean` = live v78). Dev copy `bots/variants/oc-fixc-dev`, knobs in
`params::fixc::` (all off = the base). Candidates `bots/variants/oc-fixc-<name>`. Fresh ladder-mix suites
539000-539039 merged in `maps/suites/merged/fixc-dev`. Scripts in the session scratchpad `fixc/`
(`fixc_metrics.py`: lethal round ends, bag deaths and openings from extracted replays).

Sparring partner `bots/variants/fishmarc-1106`: `astraeus-now-1106` with Fish's per-pick-count drafts
(Marcella first: 3 Marcella/HoR/C&I, 4 + Vendetta, 5 + Willow; model draft and the Tavi override off) and its
Marcella buying Fish's build (Prospector-F, Treasure-F, Capture-F, Jungle-F, Monster-F, Bruiser-H, Durability-H,
Bruiser-F, Skirmish-H, Collectors-H, then Bruiser-F). It is weak (base reads 73.4% against it on the 128 ladder
maps, 256 games) but reproduces failure mode 2: base ends 3.98 round ends a game inside a ready lethal nuke's
range (3.27 of them Marcella's), 62% dying within 2 rounds (Fish live: 7.5 a loss, 57%).

## 2. Ready enemy nukes

### What is modelled

The model is complete; the decisions ignore it.
- `model/safety.cc compute_strike` adds every damage ability: Marcella's slot 1 at `2 x Focus` (Focus read from
  the visible champion, times Skirmish/Collectors `scale`) out to `reach()` 4; `strike_memo` takes each slot's
  readiness at the enemy's next turn round from the cooldowns read; `threat_strike` widens to a walk then the
  strike when it has two turns before ours. `Reach` places it on the map with its sight (bushes, walls).
  `Safety::blow(e, p)` and `lethal(p)` (every threat summed against our health and shield) read it.
- So neither a missing ability model, nor cooldown tracking, nor the threshold in `lethal()` is the gap.

### Why we end turns in range

A diagnostic copy (`bots/variants/oc-fixc-diag`, a `debug_block` at each turn's end) printed every turn end where
one visible enemy's blow at our tile kills us while its basic attacks alone would not. Against fishmarc on the
ladder maps (256 games): 5.9 a game, by branch:

| branch | turn ends | share |
|---|---|---|
| retreat (R) | 1,333 | 88% |
| stop game ender (E, by design) | 115 | 8% |
| farm (F) | 45 | 3% |
| chase, bank, siege, other | 26 | 2% |

Enemy: Marcella 564, Vendetta 416, Heart of Ruin 361, Issac 96, Cassi 75. Distance: 1-2 in 804, 3-4 in 594, 5 (a
walk and the cast, two turns before ours) in 121. The search chose the turn in only 117.

So we are already retreating when we end there: want_home sends us home only once the nuker is within 1-4, and a
one-step retreat cannot leave a radius-4 (5 with two turns) zone. The decisions that let it get that close:
- **want_home** (`combat/fight.cc stand_lost_at`) reads `lethal(p)` only to decide whether our own fall counts;
  the stand trade (`Safety::stand_trade`) focuses the enemy's damage on our weakest member, so a champion that is
  one-shot but not the weakest of those near does not retreat until the roster sim loses.
- **The step guard** (`combat/guard.cc step_guard`) only refuses tiles more exposed than our own; it never moves
  us off one, and a tile is guarded only if the stand there is lost (or we fall and it is lethal).
- **The strike search** (`combat/plan.cc plan_strikes`) prices an end tile's danger at `hit_given_reach`
  (0.236) x each foe's blow: a certain 840-damage kill costs 198 enemy-HP units, with no life value or bag. Only
  tiles at the grid's edge are dropped when `lethal`. Fish casts its exclusive damage spells in 95% of free rows.
- **Farm and the other economy branches** walk behind the work guard, which only adds the pack zone and recall line.

### Change (knobs)

A *nuke zone*: tile p where a single visible enemy's blow (its next turn, or two before ours) at p, by our
Durability, reaches our health and shield there (full on our spawn), while its basic attacks alone would not
(`combat/fixc.cc nuke_at`).
- `nuke_price` (death weight, 0 off): the strike search prices such an end tile at `nuke_price x (health + life_value
  + gem_value x bag_at_stake)` for that foe instead of `hit_given_reach x damage`; a plan that kills the nuker
  drops it as before (the trade-for-a-kill exception).
- `nuke_guard`: the step and work guards also refuse steps into a zone from a tile outside every zone.
- `nuke_escape`: at the turn's start (after channels, shopping and the game-ender stop), on a zone tile with no
  sure kill from here and no capture paying next round, walk (or dash, if ready) to the free tile out of every
  zone nearest our spawn, then the turn goes on from there.

## 3. Big bags under threat

62% of the gems lost to Fish (81% to Mite) were in bags of 100+, in few deaths (0.44 a game against Fish, 63% of
them Prism, which `economy/bank.cc retaining_gems` keeps for Focus until the bag wins or the game closes; 21 of the
35 against Fish were fights we opened). Locally against fishmarc: 0.24 such deaths a game, 82 gems.

Threat gate, per the mirror results (a 150 retain cap without one read 46.7%; gemfight's bag-scaled retreats read
48-50): only a pack that matches us, or a nuke zone, counts.
- `bag_big` (gems at stake, both bodies for a pair; 0 off) and `bag_ratio`: at or above it, the pack zone
  (`combat/guard.cc pack_members_of`) counts us hurt and outmatched once the pack's health x damage beats ours x
  `bag_ratio` (in place of 3.96, or 2.36 at home). The pack zone is the threat gate: it exists only with enemies
  in sight (or credible) near.
- `bag_bank`: Prism at `bag_big`+ stops retaining (banks) once threatened: in such a pack zone, or in a nuke zone,
  or a visible enemy within its strike reach + 2. Latched until the bag is below half of `bag_big`.
- With `nuke_price`, a nuke zone's death price includes the bag.

## 4. Opening a fight at a local deficit

Engagements (first champion damage after 8 quiet rounds) we opened at an EHP deficit within 8 went K69/D219 in
Fish losses. Locally against fishmarc we open 10.6 a game, 4.0 at a deficit (K1.7/D1.5).

What engages: the strike search (`combat/plan.cc`, from `search_strikes` and `strike_after`). Its plans are
scored by their hits' worth (`hit_worth`, kill_distance) less `hit_given_reach` x the end tile's blows and camp
fire; no plan compares the two sides' strength. prey/chase do (a fight won even when they strike first), and the
retreat's attacks are opportunistic.

- `open_ratio` (0 off): when nothing is under way (we struck nobody last turn, and no visible enemy or ally of ours
  within 8 lost health in the last 8 rounds), and our EHP within 8 (us and visible allies, health and shield over
  Durability) is below `open_ratio` x theirs (visible enemies within 8 and credible unseen ones whose possible tiles
  are within 8), the search offers no plan that damages or stuns an enemy champion without killing one.

## 9. Ryth against a stun-immune Marcella

Fish drafts Marcella in round 0 on 36 of 41 gem maps. `ryth_marcella` (0 off): when the enemy's round-0 pick is
Marcella, Ryth's model score is lowered by this many logits in our later picks (see `draft/draft.cc`).

## Bush play (BT1-BT3, the coordinator's addition)

Knobs from research/ideas-2026-11-05/bush.md's evidence (a hidden bush shooter is hit back 9.7% of the time on the
ladder against 27.9% in the open):
- `bush_step` 1 (BT1): pathing's first steps tied on pull and aim (`Pathing::route`, `closer_neighbours`) go to a bush
  tile first. It never lengthens a path; at the last step it picks the stand among the goal tiles.
- `bush_step` 2 (BT2): the same with a rank: a *hidden* bush (no visible enemy in its cluster, no enemy ward in sight
  on its cluster: rules vision.occlusion) before a seen bush before open ground; and retreat_step's ties after
  damage, stuns and steps home.
- `bush_threat` r (BT3, with BT2): while a visible enemy off its spawn holds a ready ability whose strike reaches us
  within its reach + r, the bush rank goes ahead of pull and aim in the first-step order, and ahead of steps home in
  retreat_step (after damage and stuns). `bush_margin` m: a hidden bush retreat step's damage is let off m x our
  health and shield. An unseen ward is not guessed at (Safety still prices it).

## Results

All A/Bs: own drafts (`--no-test-draft`), fast runner, CAND against `variants/oc-retest-clean` unless named.
"fresh" = `maps/suites/merged/fixc-dev` (seeds 539000-539039, 20,480 games); "held" = `maps/suites/merged/fixc-held`
(539100-539139, unused by any screen, 20,480 games); "ladder vs ast" = the 128 ladder maps, both sides, against
`variants/astraeus-now-1106` (256 games; base reads 56.2%). 2x = 200k a turn (400k first turn), both sides; real = the
100k budget. OOF = out-of-fuel turns, CAND against REF.

Bench identity (all knobs off, 100M): default 16/16 and wide 52/52 replays identical to oc-retest-clean, after
every knob was added (total fuel +0.0008%, from the retreat option's extra fields).

Knobs added after the first screen (all in `params::fixc::`, off = the base):
- `bag_gate` (bag_bank's threats): 0 pack zone, nuke zone or a visible enemy within strike reach + 2; 1 the first
  two; 2 a nuke zone only.
- `open_retreat` (with `open_ratio`): when gated and inside an enemy's reach (`Safety::touched`), retreat_step home
  first. Not opening was not enough (forensics below).
- `commit_lost` (the coordinator's lead from the proteus turn-window port: lost chases): when want_home says leave
  but the visible pursuers within a step of their basic reach hit for our health and shield over the s - 1 turns home,
  and our basic attacks kill one of them first (`kill_turn`), we fight instead. 2 = strict: one enemy within 8, hit
  since last round, a turn to spare.

| variant | knobs | fresh, real | OOF real (CAND/REF) | ladder vs ast, real | fresh, 2x | held, 2x |
|---|---|---|---|---|---|---|
| oc-retest-clean | (base) | - | - | 56.2 | - | - |
| n1 | nuke_price .6, guard, escape | 49.6 (48.9-50.3) | 168.2k/158.5k (+6.1%) | 50.4 | 49.3 (48.6-50.0) | |
| n2 | nuke_price 1, guard, escape | 49.6 (48.9-50.3) | 168.0k/158.5k | 50.4 | | |
| np | nuke_price .6 | 50.1 (49.4-50.8) | 159.6k/156.7k (+1.8%) | 53.1 | 49.9 (49.2-50.6) | |
| np3 | nuke_price .3 | 50.1 (49.4-50.8) | 159.7k/156.8k | 53.1 | | |
| ng | guard, escape | 50.0 (49.3-50.7) | 167.2k/158.0k (+5.8%) | 53.5 | 49.3 (48.6-50.0) | |
| ngd | guard | 50.1 (49.4-50.8) | 165.9k/159.0k (+4.3%) | 53.5 | 49.9 (49.3-50.6) | |
| ne | escape | 50.0 (49.3-50.6) | 163.2k/159.2k (+2.5%) | 57.0 | 49.4 (48.7-50.1) | |
| b1 | bag 100, ratio 1, bank (gate 0) | 43.1 (42.4-43.7) | 162.5k/165.1k | 48.8 | | |
| b2 | bag 100, bank (gate 0) | 42.8 (42.2-43.5) | | 46.5 | | |
| b3 | bag 100, bank, gate 1 | 48.6 (47.9-49.3) | | 55.5 | 48.7 (48.0-49.4) | |
| b4 | bag 100, bank, gate 2 | 49.4 (48.7-50.1) | | 57.8 | 49.5 (48.8-50.2) | |
| b6 | bag 200, bank, gate 1 | 49.4 (48.7-50.1) | | 57.8 | 49.6 (48.9-50.2) | |
| b5 | bag 100, ratio 2 (no bank) | 50.2 (49.5-50.8) | 158.5k/158.1k | 56.2 | 50.2 (49.5-50.8) | |
| b7 | bag 100, ratio 1 (no bank) | | | | 50.2 (49.5-50.9) | |
| b8 | bag 200, ratio 1 (no bank) | | | | 50.2 (49.5-50.9) | |
| o1 | open_ratio 1 | 49.6 (48.9-50.3) | 161.3k/158.4k | 49.2 | 49.6 (48.9-50.2) | |
| o05 | open_ratio .5 | 49.6 (48.9-50.3) | | 53.5 | 50.1 (49.4-50.8) | |
| o075 | open_ratio .75 | | | | 50.0 (49.3-50.7) | |
| o15 | open_ratio 1.5 | | | | 49.2 (48.5-49.9) | |
| or1 | open_ratio 1, open_retreat | | | | 49.2 (48.6-49.9) | |
| cm1 | commit_lost 1 | | | | 48.8 (48.1-49.5) | |
| cm2 | commit_lost 2 | | | | 50.1 (49.4-50.7) | |
| ry | ryth_marcella 1 | 50.0 (49.3-50.7) | 158.5k/158.5k | 56.2 | | |
| bt1 | bush_step 1 | | | | 50.2 (49.5-50.8) | |
| bt2 | bush_step 2 | | | | 50.2 (49.5-50.9) | |
| bt3 | bush_step 2, threat 2, margin .1 | | | | 50.7 (50.1-51.4) | 50.3 (49.6-51.0) |
| bt3z | bush_step 2, threat 2, margin 0 | | | | 50.7 (50.0-51.4) | 50.3 (49.6-51.0) |
| bt3m | bush_step 2, threat 2, margin .25 | | | | 50.7 (50.0-51.3) | |
| bt4 | bush_step 2, threat 4, margin .1 | | | | 50.6 (49.9-51.3) | |
| bt3n | bt3 + n1 | | | | | 50.1 (49.4-50.8) |
| all1 | n1 + b1 + o1 + ry | 42.6 (41.9-43.3) | 176.1k/165.5k | 45.3 | | |

- **bt3 SPRT** (2x, 0.50 against 0.51, a third unused suite `maps/suites/merged/fixc-sprt`, seeds 539200-539279,
  `--sprt-seed` 0, the only SPRT on that suite): **H0 accepted at 4,687 games, 49.3% (47.9-50.7).** The BT3 family's
  50.6-50.7 on the screening suite is selection on one suite; held out it reads 50.3 twice and 49.3.
- At 2x every variant's out-of-fuel turns are ~1.2k against ~1.2k (both sides), so the 2x column is logic alone.
- Fish proxy, `fishmarc-1106` on the screening suite (20,480 games each): base 72.4% (real) / 72.4% (2x); np 72.1
  (real); ne 71.9 (real) / 72.8 (2x); ngd 72.3 (real); ng 72.2 (real); n1 73.0 (2x, 72.4-73.6). #2 moves the Marcella
  proxy by +0.4-0.6 at 2x at most, not significantly, and costs 0.7 in self-play.
- **No variant is significant: none is frozen for the live gate** (the rule: an SPRT pass or a held-out win on 20k+).

Forensics (why the level ones are level):
- **#2 nuke escape works mechanically but does not convert.** Self-play at 2x (ladder, diag copies, 256 games each):
  the base ends 10.4 turns a game in a nuke zone and dies within 2 rounds after 68.5% of them (81.2% within 10).
  n1 escapes 4.6 times a game; the escaper dies within 2 rounds 17.1% (35.7% within 10); its turn ends in a zone
  fall to 6.4 a game, mostly game-ender stops (E, by design) and tiles one step cannot leave. Our deaths fall 10.52 ->
  9.73 a game (theirs 10.86), but final gems are level (752 against 755) and our bag losses rise (200.6 against
  191.6 a game). The lives saved are cheap ones (the turn-window port found the same: saved deaths were gemless),
  and the steps out of reach cost farm and capture tempo. Against fishmarc the same: escape deaths 12.5% against
  62.7% in zone, deaths 7.70 -> 7.18 a game, ladder 73.4 -> 80.1 (256 games) but 72.4 -> 73.0 on 20k fresh.
  `nuke_guard`'s zone tiles cost the most fuel (+4-6% OOF at the real budget); `nuke_price` alone barely changes play
  (np and np3 read identically on the ladder).
- **#3 banking a big bag is wrong for Prism.** Every `bag_bank` variant loses (42.8-49.5): Prism's damage is its bag
  (gem Focus), so banking under threat disarms it in the very fights the threat predicts; the wider the gate, the
  worse (gate 0: 42.8, gate 1: 48.6, nuke zone only: 49.4). Breaking off instead (`bag_ratio`, the pack zone counting
  a big bag as outmatched sooner) is level at 2x (b5, b7, b8 all 50.2). Against fishmarc b1 cut gems lost in 100+ bags
  from 82.5 to 38.9 a game but deaths rose 7.70 -> 8.54.
- **#4: not opening hands the enemy the first strike.** o1's gate fires rarely (our openings 8.39 -> 8.08 a game, at
  an EHP deficit 3.33 -> 3.12), but the enemy then opens 9.11 a game (8.39) and wins them (K4.73/D3.72), so our
  deaths rise 10.10 -> 11.12. Adding the step home (or1) fires 34 times a game, cuts our deficit openings to 2.63
  and deaths to 10.08, and reads 49.2 at 2x: the retreats cost more than the fights they avoid.
- **Commit instead of a lost retreat**: cm1's gate fires 16.7 times a game (most retreats with any visible enemy in
  basic reach qualify) and reads 48.8; strict cm2 fires 1.4 a game (deaths 10.00 against their 10.43 on the 2x
  ladder sample) and is level (50.1).
- **#9 cannot fire.** Draft picks are simultaneous (rules draft.picks: both teams pick each round), and our model
  takes Ryth with its round-0 pick in all 76 of its Ryth games against fishmarc, before Marcella is seen. The re-rank
  in later picks finds Ryth already held. ry's games equal the base's (identical ladder results and OOF). Only a
  round-0 prior (opponent-agnostic) could change it.
- **Bush play fires but is small.** BT1 reorders 3.3 first steps a game, BT2 3.2 retreat choices more, the bush share
  of our round ends near enemies moves 9.16% -> 9.32% (BT1), 10.06% (BT2), 12.34% (BT3). BT3's threat flag is on for
  ~670 champion turns a game (any visible enemy with a ready ability near), and it cut gems lost in 100+ bags (84.9
  against 105.7 a game in the ladder mirror) but not deaths. Held out it is level (above). Ocean's Safety already
  prices bush sight exactly where it matters, as bush.md found.
- Self-play understates #2 (our lineage nukes less than Fish), but the 20k fishmarc runs bound the gain there to
  under a point.
