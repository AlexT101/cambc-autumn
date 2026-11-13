# scylla: charybdis rebuilt around a fed Vesper (2026-11-12/13)

The user's brief: a "Fish version" of charybdis. It drafts Vesper Vale instead of Prism and feeds her, as
Intercontinental Fish r8 does; everything else may stay. The goal was the highest win rate head-to-head against
charybdis 525, at least 50%. Copying Fish was not the goal: where a rule or our code allowed something better, that
was built. Win rate was the only measure. Two rounds of implementers (each change audited by a read-only reviewer
before its gate); the draft lab refit was held and not run.

**Result: `bots/scylla` (CHANGES 526) wins 35.6% (35.0-36.3) of 20,400 games against charybdis 525 on maps no arm had
played, from 29.0% for the draft swap alone. The 50% goal is not met.** Against the Fish r8 and Mite bodies it wins
58.4% where charybdis wins 77.3% on the same maps. The summary and what is open are at the end.

## Bots

- Reference: `variants/chy-bagfocus-525` (= bots/charybdis 525). Never edit it.
- Base: `variants/vfish-b0` = 525 with the draft locked in `src/draft/draft_model.h` (`required` Vesper Vale,
  `banned` Prism). Never edit it: copy it (`./copybot variants/vfish-b0 variants/vfish-NAME`).
- Final: `bots/scylla` = `variants/vfish-kill` = `variants/scylla-526` (b0 + `patches/m1.patch` + `patches/kill.patch`).
- `bots/variants/` is gitignored. An arm's source of truth is its patch against b0:
  `diff -ruN bots/variants/vfish-b0/src bots/variants/vfish-NAME/src > research/ideas-2026-11-12/vfish/patches/NAME.patch`.

## Where the base stands

| against charybdis 525, 4,080 fresh ladder-v4 games (dev0) | win % |
|---|---|
| `vfish-b0`, the draft swap alone | 29.1 (27.8-30.6) |
| `vfish-b1` = b0 + mitefit's `rule_vcarry.py`, `rule_vesper.py 0 --build ...`, fishr8's `rule_gold.py 2.5` | 28.3 (26.9-29.7) |

The earlier fish-body layers do nothing here: with them Vesper's share of capture gold stays 0.56. Fish r8 itself won
43% of 340 live games against v118 (charybdis 520 + two changes).

## What Fish r8's Vesper does (244 live games, `vcard.py`; full card in `~/tmp-offload/vfish/cards/fish-live.txt`)

| | Fish r8 live | vfish-b0 | charybdis 525 |
|---|---|---|---|
| Vesper's gold earned by r100 / r300 / r600 | 465 / 1,605 / 3,366 | 273 / 948 / 2,088 | 214 / 812 / 1,789 |
| each teammate's gold by r100 / r300 / r600 | 39 / 154 / 376 | 46 / 185 / 389 | 59 / 236 / 532 |
| team gold earned by r100 / r300 / r600 | 640 / 2,301 / 5,054 | | |
| Vesper's share of capture gold to r300 / of capture gems | 0.71 / 0.57 | 0.56 / 0.36 | 0.43 / 0.22 |
| captures to r300: Vesper alone / another alone | 53% / 38% of 16.8 | 33% / 62% of 20.3 | 27% / 69% of 21.0 |
| champions dealing 10%+ of the clear on Vesper's captures, to r300 | 2.95 | 2.24 | 1.94 |
| rounds from a clear to its payout, Vesper's captures | 6.9 | | |
| share of teammates within 5 of Vesper, r1-100 / r100-300 | 0.59 / 0.36 | 0.41 / 0.27 | 0.42 / 0.27 |
| Vesper Strength / max health at r300 | 197 / 2,597 | 159 / 1,514 | 143 / 1,356 |
| Vesper Strength / max health at r600 | 431 / 5,957 | 295 / 2,706 | 254 / 2,384 |
| Vesper kills / deaths a game | 3.06 / 0.64 | 1.60 / 0.94 | 1.67 / 0.40 |
| team kills / deaths a game | 5.03 / 7.66 | 2.64 / 8.68 | 5.59 / 4.47 |
| Vesper's share of tributed gems | 0.58 | 0.41 | 0.32 |
| Vesper recalls / shop rounds a game | 10.8 / 11.0 | 13.7 / 12.4 | 13.9 / 12.0 |

How it looks in a replay (05abandoned_buildings, Fish with Vesper, Varg, Heart of Ruin, Cassi & Issac, Willow):
- The whole team walks out together and clears a Golem group by r29. Vesper alone stands on it; it pays her 212 gold
  at r35 (160 x 1.33).
- The others do not wait for the payout: by r36 they have woken the next group. Vesper catches up after the payout,
  holds that one alone too (187 gold at r53), then the next (106 at r67).
- A pure gem group nearby is held by Varg alone while Vesper holds a gold one.
- At r69 she recalls with 505 gold and buys Prospector-Strength, Capture-Strength and Treasure shards; she walks back.
- While she is away the second pick (Varg) takes the holds.
- Her build: Capture-S r52, Prospector-S r64, Treasure-S r70, Jungle-S r128, Prospector-H r129, Monster-S r166,
  Hunter-H r188, Durability-H r224, Collectors-S r245, Skirmish-S r276, Home-H r292, Tribute-H r319, Bruiser-S r354,
  Greed-S about r511, Greed-H about r591 (medians of first purchase).

## Rules that make a carry (cambc-rules.yaml)

- Vesper's passive pays +33% on her capture shares and kill gold; Treasure adds 10 points to it.
- A payout is split among the allies standing on the group's tiles at the payout. Gold and gems split the same way,
  so a group's gems go wherever its gold goes.
- A hold counts from the round a team first stands on a tile and resets only when the tiles are empty or contested.
  The holder at the payout need not be the one that began the hold: on a group of two or more tiles an ally can begin
  it and Vesper can join before the payout, the ally then stepping off. A one-tile group cannot be handed over
  (stepping off empties it).
- A Capture emblem's owner pays out at R+4 instead of R+6, or at min(R+6, J+3) when it joins in round J.
- A cleared group stays empty until captured, and its respawn timer starts at the payout: a group left waiting for a
  holder delays its next cycle by the wait.
- Gold and items survive death. Only the carried gems are lost, to the killer.
- A kill pays the champion that lands the last blow 100 gold (150 with Hunter), times its gold bonuses; assists pay
  nothing.
- Each shard adds its stat when bought. 25 Greed shards (750 gold) complete into the stats of 40, the 15 extra arriving
  with the 25th; Greed emblems stack. Shard stats stack across duplicate emblems; a passive counts once.
- Health bought on spawn heals by the amount gained.

## What the code already has

- The Prism gem-carry macro of CHANGES 507-512 (economy/capture.cc, economy/farm.cc, bot.cc): the takeover of an
  ally's counting hold ('G'), groups left to the Prism ('L', `leave_for_prism`, `prism_eta`, `carry_reach`), an ally's
  clear in progress ('Q'), `sole_capture_holder`, `prism_hold_tiles`, `yield_capture`, the hold cast.
- Gold-aware holders: `value_holder`, `holder_value`, `relative_efficiency` / `gold_efficiency`,
  `take_capture_handoff`, `takeover_gain`.
- Crews for joint clears (economy/crew.cc), and an opening farm plan made in the draft (draft/open_plan.cc).
- Emblem pricing (economy/shop.cc `current_emblem`, `best_emblem`, the lab's `learned_arm` table in emblem_table.h),
  the shop trip (`wants_shop`, `home_trip`, `affordable_prefix`).
- The bank floor and tribute rules (economy/bank.cc), the fight model (combat/, model/safety.cc).

## Scripts

- `card.sh VARIANT`: VARIANT against 525 on the card suite (seed 8860010, 680 games), then the scorecard of both sides
  in `~/tmp-offload/vfish/cards/VARIANT.txt`. About 8 minutes. A mechanism check, not a gate: 680 games are +-3.7.
- `h2h.sh VARIANT SET [REF]`: the gate, on `~/tmp-offload/vfish/suites/SET`. `dev0` is seeds 8860000-8860005 (2,040
  maps, 4,080 games, reused as the development set); `g1` is the confirmation set.
- `vcard.py`, `vread.py`: the scorecard and its reader. `loss.py EXT`, `prism.py EXT`: how the candidate loses, and the
  reference's Prism (bag, tributes, kills). `kcard.sh`, `kstat.py`, `trib2.py`, `reach.py`: the kill package's card and
  tribute tables. `surv/`: the survive package's trace bot and death classifiers.

## Results

### Wave 1: the funnel and the build (2026-11-13)

Against charybdis 525 on dev0 (4,080 fresh ladder-v4 games an arm, the same maps; +-1.4):

| arm | what | win % | Vesper gold r300 / r600 (card) |
|---|---|---|---|
| `vfish-b0` | the draft swap | 29.1 | 984 / 2,092 |
| `vfish-hold` | Vesper the sole holder of gold groups; she joins a mate's count in time ('G'), mates wait for her claim ('L'), she picks a clear in progress ('Q') | 31.4 | 1,041 / 2,288 |
| `vfish-hold-nowait` | hold without the wait | 30.1 | 1,012 / 2,216 |
| `vfish-pack` | mates price gold near the payee as paid to her; her crews; the opening plan's gold weights | 29.2 | 1,110 / 2,294 |
| `vfish-pack-feed` | pack without the opening plan | 29.1 | 1,101 / 2,306 |
| `vfish-build-priced` | Greed bought by 150-gold steps and ranked against every emblem; the carry prices all 14 families; the game's rounds left as the horizon | 31.1 | 984 / 2,090 (Strength / health at r600 336 / 3,286 against 299 / 2,606) |
| `vfish-build-last` | priced, a passive that beats the best stat emblem always before Greed | 30.1 | |
| `vfish-build-trip` | priced, shop stops by gold waited | 30.5 | |
| `vfish-build-fish` | Fish's 13 emblems in order, then Greed | 29.7 | |
| `vfish-build-first` | Greed first | 22.4 of 680 (card only) | 1,798 at r600 |
| **`vfish-m1`** = hold + pack-feed + build-priced (`patches/m1.patch`) | | **33.3** | |

- The pieces add: +2.3 (hold), 0 (pack), +2.0 (build), +4.2 together. Out-of-fuel turns of m1 are 9% above the
  reference's (32,362 against 29,662).
- Fish's gold lead is mostly its maps: the maps where Fish drafts Vesper hold 27% more camp gold than dev0's.
  Reweighted, Fish's Vesper would earn about 370 / 1,260 by r100 / r300 on our maps; pack on hold reads 350 / 1,212.
  The funnel is near Fish's and worth about 2 points.
- Why `rule_vcarry` was inert: Vesper is within 6 steps of only a fifth of the gold others hold, and on 79% of her
  turns near a mate's gold hold the carry picks were never priced (the ranged hit in passing ends the farm turn first).
- Greed: a shard is 1.0 until the 25th, when 15 arrive; against multipliers (Skirmish, Durability, Monster) Greed-only
  is about +10% effective stats for Fish's gold, not +40%.
- What is left of the funnel: 0.28 of capture gold is cleared more than 12 steps from Vesper.

### Where the games are lost: the reference's Prism (b0's 400 games, `prism.py EXT`, `loss.py EXT`)

- Where the reference drafts no Prism (44 games) b0 wins 50%; against its Prism 29.5%.
- In our losses the Prism carries 237 / 389 / 478 gems at r300 / r450 / r600 (Focus 502 / 771 / 959, max health
  1,593 / 2,124 / 2,670) against our Vesper's 149 / 213 / 267 Strength and 1,420 / 1,960 / 2,430 health. Its two
  casts are 2.5 x Focus over two turns: more than her health from r300 on, and one cast kills a teammate.
- It kills 5.26 of ours a loss (2.03 a win), 98% by casts, median round 598; victims Cassi and Issac (34%), Vesper
  (17%), Ryth, Marcella, Willow. It dies 0.07 times a loss and 0.71 a win.
- It starts 7.2 tributes of 100+ gems a loss (median 658 gems at r697), 13% complete, the rest end by its own cancel
  (52%), a stun (30%) or a lock (19%); one of ours is within 8 during 95% of them, Vesper during 52%.

### Draft screen on m1: no single teammate lock helps (2026-11-13)

m1 with one more champion banned or required in `draft_model.h`'s team lock, 4,080 dev0 games an arm (m1 itself 33.3):
ban Ryth 33.9, require Cassi & Issac 33.5, ban Stellar 33.4, ban Marcella 33.3, ban Tavi 33.2, ban Ren 32.7, require
Varg 32.3, require Heart of Ruin 32.1, ban Heart of Ruin 32.0, ban Willow 31.7, ban Vendetta 31.6, require Ren 31.3,
require Ryth 31.2, ban Varg 30.9, require Vendetta 30.7, require Willow 30.5, require Tavi 29.8, require Stellar 29.6,
require Marcella 29.4, **ban Cassi & Issac 24.4**. Nothing beats the model's own teammates; Cassi & Issac, a third of
the Prism's victims, are worth 9 points to the team. The arms' copies are deleted (one line each).

### Wave 2, build round 2: health sized to the enemy's burst is level (2026-11-13)

Arms on m1 (`patches/b2-*.patch`, economy/shop.cc only), 4,080 dev0 games each (m1 33.3):

| arm | rule | win % | Vesper Strength / health at r600 (card; m1 377 / 4,108) | her deaths to the Prism on the card (m1 280) |
|---|---|---|---|---|
| `vfish-b2-floor2` | every shard Health while her max health is under two rotations of the largest enemy burst she has seen, projected to her next stop | 32.9 | 370 / 4,671 | 202 |
| `vfish-b2-duel` | the floor is the rotations the enemy lands while her Strength kills it | 32.5 | 372 / 4,262 | 229 |
| `vfish-b2-left` | a one-rotation floor, and fight power counted on the health above it | 32.1 | 330 / 5,118 | 190 |
| `vfish-b2-weight` | her fight share never under 0.53; no burst logic | 33.0 | 358 / 4,718 | 269 |

- The floors do what they were built for (her deaths to the Prism down 20-30%, losses with her under one rotation at
  r600 28% -> 13-17%) and win nothing: the Strength they cost is worth as much. m1's build stays.
- She first sees the Prism at a median r299-320 in losses (never in 21%); a teammate sees it at a median r95. The rule
  acts late; a sighting passed through the shared bytes was not built.
- Half her deaths to champions come with two or more rotations of health: focus fire, not burst.

### Wave 2, survive: the early deaths are the Prism's, and mostly not ours to avoid (2026-11-13)

Traces of m1 (debug build, 218 games on 110 dev0 maps, 274 of our deaths by r300; scripts in `surv/`):
- Killers: Prism 44%, other champions 43%, camps 13%. Without the Prism's kills our early deaths equal the reference's.
- 81% die at the end of a run of retreat turns (median 3 turns for 1 step toward spawn).
- 145 times one of ours stood within 4 of the Prism at its turn start, its stun ready, under its two casts; 94 died
  within 2 rounds. The victim's turn before: none in between 47, already retreating 56, farming 25, chasing 7. In 55
  the victim did not see the Prism (walls 42, a bush 13).
- From r301 on, `stop_game_ender` is the branch of 24% of the Prism's kills, and of 44% after r600.

`vfish-surv` (`patches/surv.patch`: `Safety::stun_kill`, a stun and the caster's following turn as lethal reach, in
`want_home`, the step and work guards and the retreat): 32.7% of 4,080 on dev0, and `vfish-surv-work` (the strike
search's guard untouched) 32.5%, against m1's 33.3; out-of-fuel turns 24% over the reference's (m1 9%). Kill-zone
deaths fall 94 -> 72 in the traces and total deaths do not move. Not merged.

### Wave 2, kill: denying the Prism's hoard tribute is worth 4 points (2026-11-13)

How the reference's hoard tributes (100+ gems) got through against m1 (card suite, 680 games, 618 with a Prism;
`trib2.py`, `reach.py`, `kstat.py`): 419 of 468 losses contain a completed one. Of 446 completed, 199 were never seen
while they ran (our nearest body a median 20-22 tiles off; 87% of unseen ones complete, 11% of seen ones), 194 were
seen with nobody within 4 of the altar, 30 had a body within 4 that did not stop it, 23 had none of ours alive. Only a
winning tribute (score + bag >= 1,000) had a stop branch, and 71% of the completions were not winning; a stop came at
once (a quarter into the channel), after which the channel restarts whole.

`vfish-kill` (`patches/kill.patch`, against m1; flags in params.h):
- `deny_hoards`: a tribute of half of what the enemy still needs, longer than a stun's cooldown, is stopped as a
  winning one is, by any body but the carry holding a lock or a stun.
- `deny_late`: the stop is timed for the channel's last turns (turns left minus our stop's walk at most 1 + the living
  enemy stunners), since a cancelled channel restarts whole.
- `deny_alarm`: a seer posts the altar and the channel's end in the shared bytes; teammates walk in time.
- `lock_first`: the lock is bought before shards.
- `deny_watch`: one teammate (the last pick that is not the carry, a linked body or a healer) leaves its ward for good
  beside the altar nearest the enemy spawn.

| arm, against charybdis 525 on dev0 (4,080 games; m1 33.3) | win % |
|---|---|
| **`vfish-kill`** (all five) | **37.5** (36.1-39.0) |
| `vfish-kill-deny` (no watch) | 34.8 |
| `vfish-kill-quiet` (no watch, no alarm) | 33.0 |

- On the card: completed hoard tributes 446 -> 295 (unseen 212 -> 87); the share of the channel run before our cancel
  0.25 -> 0.69 (lock), 0.24 -> 0.63 (stun). Stopping at once instead of late reads 29.9% of 680 against 38.4%.
- Our deaths rise 5.66 -> 7.80 a game (1.86 -> 4.63 of them within 8 of a hoard channel): bodies are spent on cancels.
- Winning tributes still complete as often (129 -> 137 on the card): 2.7 enemy bodies guard them against 2.4 of ours.
- Not built: the Prism kill's worth in the engage decision, the kill credit for Vesper, a stop holder pre-positioned
  from the enemy's score and bag. The Prism's deaths are unchanged (0.37 -> 0.36 a Prism game).
- Out-of-fuel turns 4% over the reference's in the gate (games are longer).

### The health rules on top of kill: level (2026-11-13)

`vfish-kill` plus each round-2 build arm, 4,080 dev0 games (kill alone 37.5): weight 37.7, duel 36.6, floor2 36.0,
left 36.0. Nothing added.

### Confirmation on unused maps, and the side read (2026-11-13)

Against charybdis 525 on g1 (seeds 8860100-8860129, 10,200 fresh ladder-v4 maps, both sides, 20,400 games an arm; no
arm had played them):

| bot | win % (95% CI) | out-of-fuel turns, ours / the reference's |
|---|---|---|
| `vfish-b0`, the draft swap | 29.0 (28.4-29.6) | 131,724 / 148,812 |
| `vfish-m1`, + the funnel and the build | 31.6 (30.9-32.2) | 157,702 / 146,459 |
| **`vfish-kill` = `bots/scylla`**, + the tribute denial | **35.6 (35.0-36.3)** | 171,613 / 173,054 |

- Held out, the funnel and build are worth +2.6 and the denial +4.0. dev0 read the same steps at 29.1 / 33.3 / 37.5:
  about 2 points of it were selection on a suite reused for every arm.
- No failed game, broken draft handoff, capped draft or loss by round 5 in any run.

Side read, `fgate.py variants/vfish-kill variants/chy-bagfocus-525 --pool v4 --fish-body fr8-g25 --max-batches 1`
(batch 0: 2,560 fresh maps, both sides, 20,480 games; the bodies unmetered): against the bodies scylla wins 58.39% and
charybdis 77.34%; scylla minus charybdis is -18.0 against the Fish r8 body and -19.9 against the Mite body (-17.6 on
the 128 ladder maps). Giving up the Prism costs as much against the bodies as head to head; the denial is worth
little where nobody hoards.

## Summary

| step | what | held-out win % against charybdis 525 |
|---|---|---|
| draft swap | Vesper required, Prism banned in the draft model's team lock | 29.0 |
| funnel | Vesper the sole holder of gold groups, joining mates' counts in time; mates price gold near her as paid to her | |
| build | Greed in 150-gold steps ranked against every emblem; the carry prices all 14 families; the game's rounds left as the pricing horizon | 31.6 (with the funnel) |
| denial | hoard tributes stopped late, an alarm in the shared bytes, the lock bought first, a ward left at the altar nearest the enemy spawn | 35.6 |

What was learnt:
1. **The reference's Prism is the whole deficit.** Without it in the reference's draft the swap bot is level; with it
   29.5%. Its casts make 44-59% of our deaths, and a completed hoard tribute is the loss in 419 of 468 card losses.
2. **Feeding Vesper to Fish's level is worth about 2 points.** Fish's gold lead is mostly its maps (27% more camp gold
   where it drafts Vesper). The remaining funnel is cohesion: 0.28 of capture gold is cleared more than 12 steps from her.
3. **More stats on her, in either stat, do not turn the matchup.** Health sized to the Prism's burst cuts her deaths
   to it by 20-30% and wins nothing; neither does a build 20% richer in stats on the same gold beyond +2.
4. **Our early deaths are mostly not decisions.** Of 145 moments inside the Prism's two-cast reach, 47 had no turn to
   react and 55 could not see it; 81% of early deaths end a retreat already under way.
5. **Stopping a tribute late is what pays.** A cancelled channel restarts whole, so a stop a quarter of the way in
   buys little (the same build stopping at once reads 8.5 points lower on the card); the watch ward and the alarm,
   which let a stop holder see the channel at all, are worth 2.7 and 1.8 points on dev0.
6. **No single teammate lock helps**, and Cassi & Issac are worth 9 points though they are a third of the Prism's
   victims.

Open (also in research/hyperion/TODO.md):
- Winning tributes still complete as often as before (2.7 guards against 2.4 of ours).
- Not built from the kill brief: the Prism kill's worth in the engage decision, the kill credit for Vesper, a stop
  holder placed ahead of the reference's `closing` rule.
- Vesper sees the Prism at a median r300, a teammate at r95; the shared bytes have no room left for a sighting.
- The build's and the round-2 arms' switches are still in `economy/shop.cc` as `constexpr` choices, and the kill
  flags in `params.h`; the unused values can go.
- The draft refit on scylla's own games was not run.
- For charybdis: the carry picks are skipped on turns the ranged hit in passing ends first (measured on Vesper with
  the Prism's machinery, 79% of her turns near a mate's hold); the shop's pricing horizon; its Prism's tribute is
  cheap to deny (an opponent with a ward at the altar and late stops takes about 4 points). Interrupting Fish's own
  tributes was already level on charybdis (EXPERIMENTS "Interrupting Fish r8's big tributes"), stopping at once; late
  stops were not tried there.

Seeds (all `--mix ladder-v4`, under `~/tmp-offload/vfish/suites/`): dev0 8860000-8860005, card 8860010, g1
8860100-8860129. Working data: `~/tmp-offload/vfish/` (logs, cards, extracts).
