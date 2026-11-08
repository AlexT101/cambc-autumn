# Willow's macro role: early carry, DPS shop, farmer or hybrid (ocean, 2026-11-08)

The idea (the user's): Willow's base Strength (55, the highest of the ranged types; growth 3) gives her early carry
potential, so move her from support to early-game carry and DPS, or to a farmer. Base: `variants/oc-base25`.

**Conclusion: no Willow change ships.** Every role arm (carry, DPS shop, farmer, mid-game farm) and every turret window
was H0 or fell short on its screen; the one screen H1, the idle shot (ti2000), was H0 held out on oc-base26. Her
current role, the follow's poor escort, is already the winning pattern.

## Data

**Archive** (big-arm `.oarena/archive`, 11-05 and 11-06, both complete days, engine 3.0.0; 757k games): one row per
Willow side in games of 150+ rounds. Groups: ours (proteus to v82, before CHANGES 457's follow), Fish, "top" (other
sides rated 2000+) and the rest. Script `/home/ubuntu/tmp-offload/willow2/scripts/arch.py`, output `arch.txt` there.

| | sides | win | camp gems | gold | kills | deaths | champ dmg | monster dmg | healing | heal share |
|---|---|---|---|---|---|---|---|---|---|---|
| ours | 2,826 | 67.5% | 105 | 375 | 0.10 | 1.3 | 670 | 11.7k | 10.2k | 44% |
| Fish | 5,471 | 82.1% | 29 | 160 | 0.40 | 0.7 | 617 | 11.8k | 11.6k | 47% |
| top (2000+) | 72,061 | 53.3% | 49 | 249 | 0.40 | 1.9 | 1,523 | 11.0k | 11.5k | 47% |
| rest | 176,751 | 48.0% | 79 | 459 | 0.80 | 3.6 | 2,471 | 11.6k | 7.9k | 33% |

"Heal share" is healing / (healing + damage dealt).

Willow's share of her team's totals:

| | camp gems | gold | kills | champ dmg | monster dmg |
|---|---|---|---|---|---|
| ours | 12.1% | 7.3% | 1.5% | 2.3% | 14.8% |
| Fish | 3.0% | 2.4% | 4.3% | 4.6% | 11.8% |
| top | 6.1% | 4.4% | 5.0% | 6.0% | 12.7% |
| rest | 12.2% | 11.0% | 10.7% | 11.8% | 15.9% |

- **Good teams keep Willow poor.** Fish's Willow earns 160 gold a game and buys no emblem in 66% of games; when it
  buys one, it is Prospector of Health. Among top teams, Health comes first (54% of their first four emblems),
  then Strength (27%) and Focus (19%). Only the rest buy Strength (Power, Monster) and Focus first.
- **Win rate by role** (Willow's share of the team's camp gems; with mean rating gaps):

| share | ours | Fish | top | rest |
|---|---|---|---|---|
| support, under 5% | 65.8% (+76) | 82.1% (+502) | 54.6% (+34) | 47.1% (-29) |
| 5-15% | 72.0% (+140) | 82.0% (+452) | 54.5% (+34) | 51.8% |
| 15-25% | 66.6% (+176) | 84.3% (+322) | 50.4% (+20) | 51.4% |
| farmer, over 25% | 48.4% (+96) | n < 30 | 38.4% (+18) | 43.6% (-9) |

  A logit of the win on the rating gap, the z-scored camp-gem share, kills, healing, deaths and pick count gives the
  camp-gem share -0.29 (se 0.05) for ours, -0.06 (0.01) for top teams, +0.12 (0.04) for Fish and +0.01 for the rest.
  A farming Willow goes with losing, as willow.md found for her share of camp damage: partly a sign of weak allies.
- **By first emblem stat**, top teams: Strength 55.6% (rating gap +25), Focus 59.9% (+44), Health 59.0% (+43).
  Strength-first is the weakest of the three, though the rating gap explains part of it.
- **Early fights** (willow.md, "Early aggression"): the gap to Fish is in fights, not camps. Our Willow already does
  Fish's camp damage, and fighting is now CHANGES 463 (stand and chase to round 250). s2's turret port takes that
  further (`params::s2::turret_until`), so these arms leave fights alone except `fight` in the farm window.
- **Live scrims** (games.jsonl): Willow games are now our better games. In v86, against Fish 67.2% with Willow and
  64.3% without; against Mite 70.3% and 65.0%. In v78-v80 they were level or worse.

So the data runs against the idea: carry and farmer patterns go with losing in every group, and top teams buy Health,
not Strength. The arms test it anyway, since these are associations.

## Where ocean sets her role

- `economy/capture.cc` `hold_shy`: Willow hands captures to the others (CHANGES 457).
- `combat/support.cc` `willow_follow`: on a farm turn more than 2 from the group, she steps back to it instead of
  farming, and hits the followed ally's claimed group (CHANGES 457). It runs before `farm()` in `bot.cc`.
- `bot_parts.h` `willow_early` / `params::willow_fight_until` (250): early fights (CHANGES 463).
- Heal steps: `local_support` (the Prism formation), `willow_independent_heal_step` and `willow_bank_heal_step`
  (support.cc), all through `heal_target` and `heal_ally` (self_abilities.cc).
- Shop: `economy/shop.cc` `best_emblem`, with the learned table `emblem_table.h` (Willow: Durability or Jungle
  Health first, then Tribute or Prospector).

## Switches

`variants/wr-dev` is oc-base25 plus `params::willow_role` (params.h), all off by default:
- a farm window `[farm_from, farm_until)` that ends early once our tributed gems reach `farm_gems` (0: no gem end).
  Inside it:
  - `drop_follow` (on) turns `willow_follow` off, so farm turns go to `farm()`;
  - `drop_shy` (on) lets her hold captures;
  - `heal_below` (0: off) heals only allies under that health fraction, the heal steps included;
  - `fight` extends the early fights through the window.
- `shop`, the whole game: 1 prices Willow's emblems with Strength as her main stat and without the learned table; 2
  also takes a Skirmish emblem of Strength first.

With every switch off, `bench.py` at 100M gives 16/16, wide 52/52 and wide test-draft 52/52 identical replays. Total
fuel is +0.0004%, from codegen. Arms are `variants/wr-<name>`, made by
`/home/ubuntu/tmp-offload/willow2/scripts/mkarm.py`.

**The turret joins the group** (coordinator, 2026-11-08): s2's Willow turret arms (`oc-s2-wt-*`, never run) moved
here, so that every Willow change is tested as one ablation group. The port is `willow_role::turret_until`, the same
`willow_turret` and the same `bot.cc` hook; bench identity was rechecked with it off.

Design:
- every single factor (T and each role arm) is screened against the base;
- then the best turret value is combined with each role arm that passes;
- the final candidate is the best combination, confirmed held out, then ablated one component at a time.

The turret shoots only while escorted (an ally within 2). The pure farmer drops the follow for the whole game, so
the turret would almost never fire: the two are treated as mutually exclusive, and the farmer arms get no turret
combination. A carry or hybrid window leaves the turret its rounds outside the window, and the shop arms touch
nothing it reads.

| family | arm | settings |
|---|---|---|
| A, early carry | c250, c500 | farm window to round 250 / 500 |
| | c250h5, c500h5 | the same, healing only allies under half health |
| | c500f | to 500, with fights through the window |
| | cg150 | until our tributed gems reach 150 |
| B, DPS shop | s1 | Strength main stat, no learned table |
| | s2 | s1, with Skirmish of Strength first |
| C, pure farmer | farm | the whole game (window to 2000) |
| | farms1 | farm with s1's shop |
| D, hybrid | m250-600, m250-1000 | follow early, farm 250-600 / 250-1000, then follow again |
| T, turret | t250, t500, t1000, t2000 | s2's turret before that round (`turret_until`) |

D comes from willow.md's finding 6: for our v82 ladder games, staying near the carry in rounds 250-500 went with
losing (-0.99, se 0.44), while in rounds 1-250 it went with winning.

## Tests

The test standard is `~/tmp-offload/handoff/TEST-STANDARD.md`: real budget, own drafts (`--no-test-draft`; every
directory's `test_draft` is off), fast runner, against oc-base25.

**Willow maps.** Only games with a Willow change. ocean's draft, in a 1-round mirror per map
(`/home/ubuntu/tmp-offload/willow2/scripts/dscan.sh`, then `tools/replay/drafts.mjs`), says which maps those are.
Screens run on those maps only. There, `--sprt 0.50,0.5025` is a looser bar than on all maps: H1 at +0.25 on
Willow games is about +0.08 overall. Held out runs on all maps at the standard's bar.

Maps (seeds 1030000-1039999, ladder mix unless noted; `maps/suites/merged/`):
- `wr-scr-1030` (1030000-1030199, 51,200 maps): the screens; `wr-scr-1030-w` is its Willow maps.
- `wr-held-1031a` / `wr-held-1031b` (1031000-1031079 / 1031100-1031179): held out.
- `wr-varied-1032` (1032000-1032019, `--mix varied`).
- `wr-panel-1033` (1033000-1033039): the panel.

## Mechanisms and predictions (written before the screens)

Effects are on Willow games (maps where ocean drafts her: ~32% of games on prior suites, mostly 4- and 5-pick).
Failure cases from real replays follow in "Forensics".

- **A, early carry** (c250, c500, cg150). *Mechanism:* early farm turns go to `farm()` instead of the follow, and
  she keeps capture shares, so more early camp gold reaches her and is spent on shards. *Against it:* CHANGES 457 (the
  follow plus shy) won +2.2 on Willow maps, and early proximity goes with winning in every group (willow.md, finding
  6). A carry window gives part of that back. *Prediction:* -0.5 to -1.5 on Willow games, worse for c500 than c250;
  H0. If anything gains, it is on 3-4 pick maps with spread camps.
- **Heal gate** (c250h5, c500h5). *Mechanism:* a top-up heal uses the turn's one cast, which the reset (a 55+ hit)
  would otherwise use. Healing only allies under half health gives those casts to resets. *Against it:* the heal
  thresholds lost before (heal_least 0.5: 48.3; 0.25: 45.8), and Fish heals early and often, as top-ups.
  *Prediction:* below its carry arm without the gate.
- **B, DPS shop** (s1, s2). *Mechanism:* Strength shards add 3 a hit (+5%), and Skirmish adds 10% against champions.
  She earns ~300-375 gold a game, so about two emblems' worth: +15-30 damage a hit late. *Against it:* top teams buy
  Health first, and Strength-first wins least among them; the learned table was fitted on self-play outcomes.
  *Prediction:* level to -0.5; if anything gains, it is late (fights after round 600).
- **C, pure farmer** (farm, farms1). *Mechanism:* the follow and shy off all game, as before CHANGES 457.
  *Prediction:* about -2 on Willow games (the reverse of 457's +2.2): a fast H0.
- **D, hybrid** (m250-600, m250-1000). *Mechanism:* keep the early follow, which goes with winning, and farm in rounds
  250-600, where our v82 ladder games' proximity went with losing (-0.99, se 0.44). *Against it:* 457's mechanism run
  showed the follow's gain comes from fewer Willow deaths and more heals, which are no less useful mid-game.
  *Prediction:* level to -1.
- **T, turret** (t250-t2000). *Mechanism:* when escorted and in an enemy's reach, she shoots it at once instead of
  running the strike search or stepping away: Fish's escort deals twice our champion damage. *Against it:* s2's
  smokes were 49.2-50.4, and the near-identical turret on oc-base17 was level at the real budget (50.3 of 27,912) with
  more out-of-fuel turns. *Prediction:* level to +0.5; t250 best, since the window matches the early fights.

## Forensics: the current behaviour's failure cases in real games

Data: 863 of our Willow sides in the v84-86 scrims against Fish and Mite (decoded; 67.2% won), against Fish's Willow in
the same scrims (538 sides) and in its 11-05 ladder games (2,373). Rates are per 100 rounds Willow is alive and off
spawn; "escorted" is an ally within 2. Win associations are logits controlling for the gem and gold lead at round
250. Scripts and tables: `/home/ubuntu/tmp-offload/willow2/forensics/` (`scripts/wf.py`, `rep.py`, `rep2.py`,
`rep.txt`).

| factor | failure case found | how often | ceiling |
|---|---|---|---|
| T, turret | escorted, in an enemy's reach with it in her range, no attack: twice Fish's rate | 7.8 a game (Fish 3.6) | about +0.5 (association +3-5, confounded) |
| D, mid-game farm | weak: being escorted in rounds 251-600 goes with losing for us, not for Fish | about 100 rounds a game | about +1 on Willow games |
| heal gate | a top-up heal on an ally above half health that takes a ready reset's hit; Fish ~never | 2.9 a game, 163 damage | about +0.1 |
| A, C, carry or farmer | none: idle-while-escorted rates match Fish's (38 / 37 / 39 by phase, Fish 39 / 33 / 31) | camps left unused: 3 groups a game early, 70% taken later | A about 0, C negative |
| B, shop | none: she earns 65 gold a game, 54% of games buy nothing, first purchase ~round 334 | 0.002 kills a game flipped | 0 alone |

- **Turret.** In the no-attack rounds she steps away 56% of the time, makes other moves 16%, heals 11% and idles 3%,
  at 87% or more health. Within 5 rounds, the enemy dies after 10% of these rounds and 24% of those where she
  attacks; Willow dies after 13% and 8%. Our win rate by tercile of her miss share is 79 / 61 / 55% (z -0.44, se
  0.11); Fish shows nothing. Fleeing from fights already going badly explains part of this.
  - `01a1b94a-c315…/4-01starfish` (v85 against Fish), rounds 30-41: she heals or idles beside Issac, Vendetta and
    Heart of Ruin, then steps away from Cassi. An ally died within 5 rounds in 3 of 4.
  - `01a1b8d1-f603…/2-03ambush_field`, rounds 250-251: at 80% health she steps away from Issac twice.
- **Carry and farmer.** By round 250 our Willow has 17 gold and 8 camp gems, against her allies' mean of 264 and 59.
  Fish's is as poor (43 and 7). Our team still leads at 250 on gems (287 against 223) and is level on gold. In the 250
  games we trailed at 250, Willow was *less* idle. Her early camp gems do not predict winning (z -0.09). The camps
  she leaves (for example `01a1b907-be0d…/2-03reef`, rounds 100-103: a wolf and two gem clusters free) are about 1%
  of a game's gems, and 70% of them are taken by us later.
- **D.** In games reaching round 600, idling escorted in rounds 251-600 goes with losing (z -0.23, se 0.09), and so
  does the escorted share (z -0.28); for Fish the escorted share goes the other way (+0.21). Allies pulled back to
  defend keep her escorted, so this is likely confounded.
- **Heal gate.** 45% of these heals restore under half a heal; 53% go to allies above 80% health. The 163 damage a
  game is 96% on camps (1.4% of her camp damage), with no win association.
  - `01a1b8f6-81a8…/3-00eight` (v85), rounds 391, 510 and 542: Heart of Ruin at 91-94% healed for 100-180.
- **Shop.** Enemies she hit that survived within +9 damage a hit: 0.024 a game; within +18: 0.05. Bought Health
  saved her 0.09 near-deaths a game.

So the data predicts: only T (and weakly D) can gain. The carry, farmer and shop ideas have no failure case to fix
in current ocean: shy and the follow have already made her Fish's poor escort, which is the winning pattern in
every group of the archive. By the method's rule, A, B and C would not have been built. They were built before this
analysis, and their screens remain as tests of the prediction.

## Screens

Willow maps of `wr-scr-1030` (`wr-scr-1030-w`): 25,584 of 51,200 maps. ocean drafts Willow on both sides or on neither,
so on this ladder-mix pool 50% of games change (fresh-1031000..1031079: 10,237 of 20,480). All runs are
`--sprt 0.50,0.5025`, each with its own `--sprt-seed`, real budget, own drafts, against oc-base25. Rates are of Willow
games; SPRT-stopped rates come from a partial sample.

| arm | Willow-game win % (95% CI) | games | SPRT | OOF cand / ref |
|---|---|---|---|---|
| t250 | 49.80 (49.37-50.23) | 51,168 | undecided at the pool's end, LLR -2.34; upper bound +0.23 | 738k / 758k |
| t500 | 49.65 (49.20-50.10) | 48,223 | H0 | 692k / 713k |
| t1000 | 49.40 (48.86-49.95) | 32,853 | H0 | 462k / 479k |
| t2000 | 49.28 (48.70-49.87) | 27,995 | H0 | 396k / 407k |
| m250-600 | 48.17 (47.21-49.14) | 10,305 | H0 | 151k / 154k |
| m250-1000 | 48.48 (47.60-49.37) | 12,272 | H0 | 173k / 176k |
| c250 | 47.77 (46.90-48.65) | 12,624 | H0 | 172k / 180k |
| c250h5 | 43.98 (42.55-45.43) | 4,588 | H0 | 60k / 61k |
| cg150 | 44.99 (43.71-46.28) | 5,779 | H0 | 79k / 83k |
| farm | 44.77 (43.44-46.10) | 5,397 | H0 | 72k / 78k |
| s1 | 49.76 (49.14-50.37) | 25,336 | H0 | 375k / 376k |
| s2 | 50.04 (49.61-50.48) | 51,168 | undecided at the pool's end, LLR -0.47 | 761k / 761k |
| ti250 | 50.13 (49.70-50.56) | 51,168 | undecided at the pool's end, LLR +0.20 | 766k / 764k |
| ti2000 | 50.28 (49.76-50.81) | 34,426 | **H1**, LLR +2.97 | 513k / 511k |

- **Turret:** rejected at every window; later windows lose more. t250's upper bound is under the +0.25 a screen asks
  for, so it is rejected too. The turret saves fuel (2-3% fewer out-of-fuel turns) but loses games, missing the
  prediction (level to +0.5) on the low side.
- **Why the turret misses** (`/home/ubuntu/tmp-offload/willow2/tforensics/`): 1,000 kept t250 games, each paired with
  a base mirror of the same map and side; candidate minus base, mean ± se.
  - In rounds 1-250, Willow's deaths rise +0.113 ± 0.016 (base 0.161, so +70%). Her damage dealt to champions and
    taken from them both rise +68: she trades health for damage 1:1, then spends 60 rounds dead.
  - In the turret situation (escorted, in an enemy's reach, with that enemy in her range), the base stands and shoots
    58% of the time and steps away 32%. When it stands, she dies within 5 rounds 1.6% of the time. The turret stands
    95% of the time and she dies 10%. The strike search keeps her there only when it is safe.
  - Where the base stepped away or kited (walk, reset, shoot; n 96), the turret costs Willow +0.23 deaths within 20
    rounds.
  - Where the base stood without shooting (n 30), the turret gains: kills by round 250 +0.9 ± 0.4, wins +13 ± 13
    points.
  - Example, `1060-gen-classic-103000401029-21`, round 30: at 500/700 beside Marcella and Tavi, the candidate shoots
    Marcella for four rounds and dies in round 35. The base walks away, survives on 4 hp and wins 1031-82.
  - So the forensics' failure case was not one: stepping away is right for our bot (Fish's escort can afford it with
    more health bought). What remains is the idle turn: **`idle_until`** (arms ti250, ti2000) shoots only when the turn
    ends with Willow's walk and attack unspent.
- **D, mid-game farm:** -1.5 to -1.8, a fast H0: the bottom of the prediction (level to -1). The weak association
  in the forensics (escorted in rounds 251-600 goes with losing) was confounded, as suspected: the follow's value
  holds mid-game.
- **A, early carry:** c250 -2.2, cg150 -5.0: fast H0s, below the prediction (-0.5 to -1.5). The heal gate costs
  another -3.8 on top of c250 (c250h5 44.0), as predicted (below its carry arm). c500, c500h5 and c500f were cut
  without a run: c250 already loses, and the longer window only gives back more of the follow.
- **C, pure farmer:** farm -5.2, a fast H0: worse than predicted (about -2); farms1 cut.
- **B, DPS shop:** s1 -0.24, H0; s2 +0.04, undecided over the whole pool. The prediction (level to -0.5) holds.
  There is no failure case to fix (she buys little before round 334), and s2's upper bound (+0.48 on Willow games,
  about +0.15 overall) leaves no gain worth a held out.
- **Idle shot:** ti2000 (the whole game) H1 at +0.28 on Willow games; ti250 +0.13, undecided. As predicted from the
  turret forensics, the gain is the idle turns, and it grows with the window. It goes to held out on oc-base26.

## Confirmation on oc-base26

`variants/wr-ti26` is oc-base26 plus only the idle shot (`params::willow_idle_until` = 2000, the `bot.cc` hunk);
the panel copy is `wr-ti26-td`. Gates (seeds: held 1031901, varied 1032901):
- held out on all maps of `wr-held-1031a` and `-1031b`, `--sprt 0.50,0.5025 --sprt-min-games 40960`;
- varied `wr-varied-1032` at 0.4975,0.50;
- panel on `wr-panel-1033`: wr-ti26-td against oc-base26-td, and both against gp-panel-astraeus-td and
  gp-panel-proteus-td, pooled with `panel_sprt.py`.

| gate (against oc-base26) | result |
|---|---|
| held out, all maps (1031a + 1031b) | 50.0% (49.6-50.5) of 41,282 games; **H0** (LLR -3.02, past the 40,960 minimum) |
| held out, Willow maps of 1031a | 50.15% (49.19-51.11) of 10,390 games (non-Willow maps 50.03% of 10,358) |
| varied | 50.1% (49.2-51.1) of 10,240 games; undecided (LLR +2.17 at 0.4975,0.50), not H0 |
| panel, pooled (30,720 map units) | +0.00 pts; H1 at 0.4975,0.50, H0 at 0.50,0.5025 (base-td -0.09, astraeus-td +0.00 ±0.20, proteus-td +0.08 ±0.16) |

**Why the idle shot did not hold up:**
- It changes only Willow games (half the ladder mix), so the held out's +0.25 overall needs about +0.5 on Willow
  games, twice what the screen asked. The screen's +0.28 on Willow games (34,426) halved to +0.15 on 10,390 held-out
  Willow games: together about +0.2 on Willow games, +0.1 overall.
- Its ceiling is small: in the t250 forensics the situation it fixes (base stands escorted, in reach, without
  shooting) came up in 30 of 1,000 games, worth +13 ±13 win points there, so about +0.4 on Willow games even at
  face value. A gain that size cannot clear an all-maps held out.

No merge, no live-queue line. Seeds 1030000-1033039 are marked used in maps/SUITES.md; the SPRT seeds were 1031901
(held), 1032901 (varied) and 1033901 (panel pooling).
The variant dirs are deleted; their code is kept as patches: `~/tmp-offload/willow2/wr-dev.patch` (every arm's
switches, on oc-base25) and `wr-ti26.patch` (the idle shot, on oc-base26).
