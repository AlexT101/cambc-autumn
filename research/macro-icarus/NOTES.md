# ICARUS: macro refactor of charybdis (2026-11-11)

Reference `bots/variants/charybdis-ref` (= charybdis at 81fc6f968). Every A/B: `tools/ab.py CAND
variants/charybdis-ref --no-test-draft --fuel 200000`, fast runner, release builds unless noted. Suites:
`maps/macro-dev` (5,120 fresh ladder-v2 maps, 10,240 games), `maps/macro-holdout` (1,280 maps) and the standard
`ladder,gen,fresh`. Smoke/study sets (subsets of macro-dev, never used for decisions): `maps/macro-study` (512 maps,
every 10th), `maps/mo7-mono-smoke` (its 146 Monolith maps).

## 0. The mirror (charybdis vs itself, 512 distinct debug games on macro-study)

Scripts: scratchpad `an/g*.py` over `replays/.analysis-mo7` (extract.mjs).

- Winners die 2.7 times a game against 7.3, kill 7.3 against 2.6, lose 65 gems at death against 247. Tributed gems
  by r300 are close (119 vs 97); by r600 they are not (525 vs 281). Games snowball from kills.
- The Prism (89% of games, both sides) kills 7.3 of ~10.5 champions a game; its deaths cost 231 gems a game (both
  teams). The team whose Prism dies first loses 86% (257 of 299). Prism Focus ratio at r300 >= 1.5: 86% wins;
  <= 0.67: 14%. At r100 the bands are 38-63%: the gap opens over r100-300.
- The carry economy starves everyone else: earned gold by r600 Prism 1,559, Vesper 1,592, Ryth 671, HoR 338,
  Issac 189, Cassi 181, Willow 28. Cassi is still ~760 HP at r600; Cassi & Issac (98% of drafts) die 1.7 times a
  team-game, mostly to the enemy Prism.
- The winning tribute is not where games are decided: the team whose Prism first starts a winning tribute wins
  92% (271 of 293), though it is cancelled ~3.4 times a game on the way (stun 1.7, lock 0.9, manual 0.8).
- **Monoliths are the one big unexploited objective.** 146 of 512 games (28.5%) have Monoliths (usually one per
  side, mirrored; often with 8 gem clusters = 270 gems, else 200, plus 300+ gold). 70% of Monolith groups are
  never captured (every other group type: 0-18%); in 89 of 146 games nobody captures one, mostly nobody even hits
  one. When captured (median r720-800), the first capturer won 45 of 57. A mid-game team clears one in 25-70
  rounds taking 3-7k damage. Holders are mostly not the Prism (Vesper, Vendetta, Willow, Issac): charybdis's carry
  pricing and sole-Prism holds explicitly exclude Monoliths.

## Experiments

(hypothesis, prediction, result, lesson; newest last)

### E1 `mo7-mono`: the Monolith as the Prism's bank (19:20)
Hypothesis: the Monolith is the largest gem bundle (200-270 gems + 300 gold); a sole Prism holder takes it all,
+300-405 Focus, which decides Prism duels. charybdis never prices it (carry excludes Monoliths) and rarely starts
its crew operation. Make the team take its Monolith when its Prism-priced crew value beats alternatives, with the
Prism as sole holder. Prediction: Monolith maps (29.5% of dev) from 50% to 60-65%; overall +3 to +4.5; non-Monolith
maps level.

### E2 `mo7-sat`: Focus saturation (19:47)
Hypothesis: past 2x the enemy Prism's Focus, a gem's Focus premium buys nothing and costs a longer winning channel
and a low team score; Prisms hold 600-1,600-gem bags whose winning tributes are cancelled ~3.4 times a game (the
winner wastes ~55 rounds a game on them), and the first team to attempt a winning tribute wins 92% (271/293).
Zero the premium for a dominant Prism (dead enemy Prism counts as dominated) so allies keep and bank captures.
Prediction: small, +0.5 to +1.5, more on top of E1 (which makes dominance more common).
- E1 interim (implementer smoke6, 292 debug games on the 146 Monolith study maps): captures 243 vs ref 157, Prism-sole
  94 vs 27, median capture r639 vs r772, but 44.2% wins. Split by our own outcome: hit+captured 71% (83 games),
  +enemy captured too 45% (66), hit never captured 17% / 0% (29 / 22), never hit 39% (89; mirror 52%). Our bodies
  die to Monolith fire in our siege windows (Cassi 88, Willow 55, Prism 19): the siege puts 600-760-HP bodies
  nearest a 200-a-phase striker. Sent to the implementer: protect fragile bodies, don't start sieges the team
  cannot finish, find the never-hit regression.
- E2 implemented (`mo7-sat`; dev run `mo7-sat-s1` = its final code): `carried_bonus` 0, no sole hold, no
  'G'/'L'/'Q'/leave/prism_coming for a dominant Prism (Focus >= 2x every enemy Prism; dead counts at its bagless
  Focus; unseen enemy Prism aged by our team's gem rate). Smokes 48.9 / 48.7% of 1,024 (OOF 82 vs 57, from four long
  games). In truly dominant games the Prism's largest bag fell 659 -> 573 and cancelled-tribute gems 2,245 -> 1,366,
  but allies tributed only +25 for the Prism's -76: team score 995 vs 1,046, wins 0.87 vs 0.91 (selected subsets).
  The premium was not the only thing routing gems to the Prism; allies don't bank what the Prism stops taking.
- **E1 result** (`mo7-mono-s1` = implementer smoke9 code: Prism-priced Monolith ops, Prism sole hold incl. one-tile
  hand-off, exposure-aware stands, no whole-team availability): **50.15% of 10,240** on macro-dev (Monolith maps
  50.2% of 3,022, others 50.1%), OOF 580 vs 467. Level. On 600 Monolith-map games: we capture 353 Monoliths vs the
  ref's 230; after a Prism-sole capture our Prism is at Focus 1,142 vs 748, yet those games win only 67%; in the
  losses our team score sits at 100-500 while our Prism holds 600-2,200 gems in channels of 60-220 turns that keep
  being cancelled, and the enemy reaches 1,000 by ordinary banking. **Lesson: the Monolith's gems are wasted on a
  Prism that cannot convert them; Focus beyond dominance does not win the race to 1,000.**
- **E2 result** (`mo7-sat-s1`): **49.72% of 10,240** (Monolith maps 49.5%), OOF 621 vs 485. Level: allies did not
  bank what the Prism stopped taking.

### E3 `mo7-race` / `mo7-monorace`: conversion-risk banking (21:05)
Hypothesis: a tribute channel of b turns with per-turn cancel hazard h (stun, lock, death; ~0.04 measured) takes
E(b) = ((1-h)^-b - 1)/h rounds with restarts: exponential in b, unpriced today. The Prism should bank its bag once
ceil(bag/10) reaches the cap c where expected waste equals the channel, provided (a) no enemy Prism would then
out-Focus it, or (b) the enemy's projected time to 1,000 beats our conversion. Prediction: race alone +1 to +2;
with the Monolith (bigger bags) +2 to +4, Monolith maps most.
- E1 extra: `mo7-mono-s2` (the implementer's final code, after its audit fixes) **50.2% of 10,240** (Monolith maps
  50.5%). `mo7-mono-s1` on macro-holdout 50.9% of 2,560, ladder 49.2% of 256, gen 49.0% of 512, gen-s1 49.6% of 512.
- **E3 result:** `mo7-race` (gated: (a) no enemy Prism out-Focuses us after the bank, or (b) the enemy's projected
  win beats our conversion) fired in 13% of smoke games; **49.07% of 10,240** (Monolith maps 48.9%), OOF 584 vs
  467. `mo7-race-pure` (bank at the cap, no gates; fired in 55% of games): **42.4% of 4,410** (stopped early).
  **Lesson: even at 250+ gems and with exponential conversion waste, the bag is worth more as Focus than as
  score; the cancelled-channel waste is the price of the weapon, not a mistake.** Consistent with every earlier
  banking result (macro1 bank -13, bank0 -17).
- E3 mechanism (implementer, 132 firing smoke games): the Prism's largest bag 687 -> 506, Prism tributes 0.83 -> 1.85 a
  game, team score at r500 287 -> 394, outside cancels of Prism tributes (stun/lock) 368 -> 162; wins 0.71 vs 0.73.
  It does what it was designed to do and still does not win. `mo7-monorace` (E1 s1 + E3): 49.0% of 5,531 (stopped).
- `mo7-mono-s2` on macro-holdout 51.0% of 2,560, ladder 50.0% of 256, gen 49.4% of 512, gen-s1 49.8% of 512.
### E4 `mo7-mono-win`: Monolith ops only in enemy weakness windows (21:25)
Hypothesis: the siege's losses (aborted sieges, steals, ganks of the sieging team) come from enemy interference;
starting ops only while the enemy Prism is dead or two enemy bodies are dead (60-round windows, longer than a
25-70-round clear) keeps the gain and drops the losses. Prediction: Monolith maps +1 to +2 over E1. Smoke: our
Monolith captures fell to half the reference's (55 vs 113 in 292 games): the gate also blocks the reference's own
burst sieges, which it inherits.
- **E4 result:** `mo7-mono-win` **49.30% of 10,240** (Monolith maps **47.35%** of 3,022). Gating the start of
  Monolith ops on enemy death windows loses: the windows are rare and late, and the gate also removes the burst
  sieges the reference itself makes.

### E5 `mo7-dom`: a dominated Prism banks (21:38)
Hypothesis: Focus value is concave and only duels price it. E3-pure (bank at the cap, no gates) lost 7.6 points,
so the bag's Focus is worth far more than its score while duels are contested; but at under half the enemy
Prism's Focus our Prism loses its duels anyway (it dies ~half the time when it strikes first, kills ~4%), its bag
buys nothing and only hands the enemy Prism a kill-bag. Bank it (at least the EOQ floor) while dominated.
Prediction: fires in ~10-15% of games, which we win ~15-20%; +0.5 to +1.5.
- E1 confirm: `mo7-mono-s2` on fresh macro-extra1 (ladder-v2 seeds 89000-89019, 5,120 maps): **49.9% of 10,240**.
  Pooled with dev, holdout and the standard suites, ~50.1% of 24,320: level, not shipped.
- **E5 result:** `mo7-dom` fired in 29% of smoke games (median bag 46 at fire, enemy Focus estimate 831 vs ours
  224; the unseen-enemy estimator assumes the enemy Prism takes every gem its team takes, so it over-fires):
  **48.4% of 10,240** on macro-dev. Even a dominated Prism's bag is worth more kept.

### E6 `mo7-reach3` / `mo7-reach4`: carry reach probes (21:50)
Every result so far says gems on the Prism are worth far more than the carry premium's shard price (banking them
loses 2-8 points). Probe the carry economy's one distance bound, `carry_reach` = 2 x capture_time (the Prism's
'G'/'L'/'Q' picks and allies' leave-for-Prism), at 3x and 4x, to read the gradient. Prediction: +0.5 to +1 if the
funnel is under-reaching; level or negative if respawn delay and theft of left groups dominate (macro1's funnel2,
which restricted leaves to the capture time, beat funnel).
- **E6 result:** `mo7-reach3` **49.68%** and `mo7-reach4` **49.70%** of 10,240 each. The carry reach is at its
  optimum; the funnel is not under-reaching.

## Summary (22:00)

No candidate beat charybdis-ref; `bots/charybdis` is left unchanged (it equals the reference). Patches of every
variant against charybdis are in `patches/` (`bots/variants/` is gitignored).

| Variant | What | macro-dev (10,240 unless noted) | Other suites |
|---|---|---|---|
| mo7-mono-s1 | Monolith ops priced at the Prism's Focus premium, Prism sole holder, exposure-aware stands | 50.15 (Monolith maps 50.2) | holdout 50.9 of 2,560; ladder/gen/gen-s1 49.3 of 1,280 |
| mo7-mono-s2 | + audit fixes (ring bail, one-tile hand-off, cover predicate) | 50.2 (Monolith 50.5) | holdout 51.0; standard 49.7; fresh extra (89000-19) 49.9 of 10,240 |
| mo7-sat | no carry premium / sole hold for a Prism at 2x the enemy Prism's Focus | 49.72 | |
| mo7-race | bank the Prism's bag once its channel passes the restart-waste cap, gated on Focus or the race | 49.07 | |
| mo7-race-pure | the same with no gates | 42.4 of 4,410 | |
| mo7-monorace | mono-s1 + race | 49.0 of 5,531 | |
| mo7-mono-win | mono-s2, ops start only in enemy death windows | 49.30 (Monolith 47.35) | |
| mo7-dom | a Prism at under half the enemy Prism's Focus banks | 48.4 | |
| mo7-reach3 / 4 | carry_reach 3x / 4x capture_time | 49.68 / 49.70 | |
| mo7-shy | Cassi, Issac, Willow keep out of a lethal ready enemy Prism stun's reach (4, 5 on a double turn) | 49.9 | holdout 49.6; extra 49.6 of 10,240; standard 49.7 of 1,280 |

What the programme learned:
1. **The Prism's bag is worth far more as Focus than as score, at every size and state measured.** Banking it at a
   channel cap lost 7.6 points; banking only when dominant (gated) -0.9; banking while dominated -1.6; giving up
   the premium when dominant -0.3. The ~55 rounds a game the winner wastes on cancelled long winning tributes are
   the price of the weapon, not a mistake to fix.
2. **More gems on the Prism does not help past what the carry economy already routes.** The Monolith programme
   doubled our Prism-sole Monolith captures and pushed post-capture Focus to 1,142 vs 748, and was level: the
   siege costs (team time, fragile bodies killed by Monolith fire, aborted sieges, enemy steals) cancel the
   gain, and once dominant more Focus buys little. Carry reach 3x/4x: level.
3. **Selection traps in outcome splits.** "Games where we sieged and captured win 71-89%" and "first Monolith
   capturer wins 79%" are mostly who was already ahead; the causal read (all Monolith maps) was 50.2-50.5%.
4. Mirror facts for the next programme are in section 0 (Prism kills 7.3 of ~10.5 kills a game; first Prism death
   decides 86%; isolated Prisms die first; Cassi dies at exactly the enemy Prism's stun range 4 in a third of her
   Prism deaths; allies other than the Prism and Vesper earn almost no gold).

E7 `mo7-shy` (22:00) tested the first open lead directly: fragile bodies treat the tiles within a lethal, ready
enemy Prism stun's reach as guarded steps. Level on 24,320 games (49.9 dev, 49.6 holdout + extra). Open leads (not
built): a team response to the enemy Prism's long winning channel that kills rather than
delays it; a Monolith siege that keeps fragile bodies out of the Monolith's reach entirely (tank rotation) so its
cost falls without removing the reference's own bursts.

## Addendum (22:20): E8 `mo7-ender`, converge on a channelling game-ender

At the overseer's request, the fastest open lead. `stop_game_ender` (attack path) now also runs when a visible
enemy whose bag ends the game is channelling its tribute and we can reach attack range before the channel lands
(Chebyshev steps less our range, less a ready dash), not only with a stun or lock in hand. Hypothesis: a channeller
can only cancel, and damage that kills it takes the whole bag; the team that first starts a winning tribute wins
92%. Result: **49.7% of 10,240** on macro-dev; holdout 49.6 of 2,560, extra 49.8 of 10,240, ladder/gen/gen-s1
50.1 of 1,280. Level: the existing stun/lock stops already do what can be done against a visible channeller, and
most winning channels are not seen in time. Not shipped; charybdis unchanged.
