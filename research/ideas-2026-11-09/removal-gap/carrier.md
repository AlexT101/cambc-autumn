# Carrier features (CHANGES 441's b1, gf, b5, b3w): what they exploit in ocean

Fork of the removal-gap study, 2026-11-09. Scripts are in `tools/`. Data and traces are in the scratchpad
(`gap/car/`), not kept.

## Method

- **Per-feature arms:** `bots/variants/gap-ana-<arm>` is ocean-rm2 plus one feature, rebuilt from the removal diff
  (`tools/split.py`). Each plays ocean-rm2 on `merged/ocrm-1921` (40,960 games), and `tools/flips.py` pairs it with
  the rm2 mirror (`gap-mirror`).
- **Replays:** `merged/gap-car-2k` is a 1,000-map sample of ocrm-1921, run with every replay kept (`gapcar-*`,
  release).
- **Traced copies:** `bots/variants/gap-trc-<arm>` print when the feature changes a decision (debug, against
  ocean-rm2 on gap-car-2k):
  - gf: the boosted chase taken where the unboosted one is lost;
  - b1: the altar switch;
  - b5: the pack-zone verdict flipped by the 2.0 ratio;
  - b3w: the escort's walk at an enemy.
- **Opponent side:** `gap-trc-sge` / `gap-trc-sge2` are ocean-rm2 with a line on every `stop_game_ender` turn, and
  `DEAD` on its first dead turn.
- **Live:** ~4,300 live games of v86-v96 against Fish (inte) and Mite (`~/tmp-offload/handoff/gate/analysis`), all
  four features on. Compared with 1,000 kept mirror replays of ocrm1 vs ocean-ba65375 (`local`).

(Results below; see the summary at the end.)

## Per-feature arms on ocean-rm2 (ocrm-1921, paired with the rm2 mirror)

| Arm (rm2 + one feature) | Paired Δ win % | Flips | Fires (traced, gap-car-2k) |
|---|---|---|---|
| b1 | -0.04 ±0.10 (40,960) | 1.2% | altar switch 0.22 a game, in 5.5% of games |
| b3w | +0.04 ±0.11 (40,960) | 1.4% | escort walks in 14% of games, 4.3 lines a game |
| b5 | +0.17 ±0.17 (40,960) | 3.5% | zone verdict flipped 0.28 a game, in 12.5% of games |
| gf | +0.31 ±0.41 (40,960) | 30.5% | boost decides a chase 7.9 times a game, in 81% of games |

In rm2's context b1, b3w and b5 are worth nothing measurable: under ±0.3 points, with few flips. gf is the only
one of the four with a broad effect.

## The weakness found: ocean's risk-blind stop of a game-ending bag

`stop_game_ender` runs ahead of every other branch, with the step guard off and the travel dash forced: "into reach
of the enemy whose bag ends the game, whatever the risk".

Every rm2 turn in that branch was traced (`gap-trc-sge2`, 2,000 debug games against rm2):
- **Walking ender:** 15,003 body-turns, and 16.7% die within 2 rounds.
- **Tributing ender:** 8,780 body-turns, 15.0% die.
- In games where the branch runs, 26% of the traced team's deaths come within 3 rounds of one of its turns.
- A walking-phase death hands over 28 gems.

Winning-bag episodes are runs of rounds where a body's bag plus its score reaches 1,000 (`tools/winbag.py`). The
table counts enemy bodies dying within 6 of that carrier, per episode. The local column is ocean-ba65375 against
ocrm1 (1,000 replays); the live columns are v86-v96 against Fish and Mite (4,279 games).

| Carrier | Map | Opponent: Fish | Opponent: Mite | Opponent: ocean (local) |
|---|---|---|---|---|
| ours | one-site | 1.53 | 1.77 | 2.63 |
| ours | multi-site | 0.20 | 0.31 | 0.87 |
| theirs (ocean stoppers die) | one-site | 2.92 (Fish's) | 1.39 (Mite's) | 3.06 |
| theirs (ocean stoppers die) | multi-site | 0.82 (Fish's) | 0.34 (Mite's) | 0.96 |

- Ocean bodies close in on an enemy winning carrier more than Fish's or Mite's do. Most enemies within 3 at once,
  multi-site: 0.40 against 0.22 and 0.21.
- They die near it 2-4x as often on multi-site maps, and ~1.6x on one-site maps.
- The weakness shows live too: ocean's stoppers die 2.92 an episode by Fish's one-site winning carriers.

**b3w exploits exactly this.** Its escort walks at a stopper (B3TRC, 2,729 episodes against rm2), and the target is
killed by us within 10 rounds 61% of the time, while the escort dies 4%. Live, Fish and Mite bodies come close less
often, so the escort has less to kill. In rm2's context, b3w moves no results all the same (about 1.5% flips): the
stoppers it kills mostly die or fail anyway.

## gf: chases of carriers with our health x1.3

`boost = min(0.3, 17.5 g / 276.6)` saturates at 5 gems, so gf is in effect "+30% health in every chase of a carrier
of 5+ gems".

**What the trace shows** (GFTRC, against rm2):
- The boost turns a lost chase into a taken one 7.9 times a game, in 81% of games.
- The target's median bag is 23 gems (p10 7, p90 85), and the target is usually 5-8 away.
- In those chases, the target is killed by us within 10 rounds 7.5% of the time, and the chaser dies 2.4%: about
  3:1, where rm2's own chase sim called them lost.
- The gap closes within 4 rounds only 29% of the time.

**Paired against the mirror** (gapcar-gf, 2,000 games): rm2 deaths +0.58 ±0.34 a game, ours +0.10 ±0.34. There is no
loss of rm2's farm tempo: gold at 600 -25 ±36, capture gems +2 ±12. gf's gain is extra kills.

**Live, ocean chasing small carriers** (5-39 gems; `tools/chase.py`, approach episodes):

| Target | Target killed | Chaser died |
|---|---|---|
| Fish | 0.076 | 0.086 |
| Mite | 0.119 | 0.082 |
| ocean (mirror) | 0.10 | 0.069 |

Escape rates (distance at +6 rounds) and the targets' support are alike across all three.

**Hypothesis (low-medium confidence):** Fish's carriers punish a marginal pursuit, and ocean's don't. So rm2's chase
sim is too pessimistic against ocean targets only, and gf's +30% buys real kills in the mirror and little live. It
doesn't explain Mite, whose numbers look like ocean's. No rm2-side behaviour was isolated as the cause.

## b5: our 100+ bag counts us outmatched at ratio 2

- **Where it fires:** the trace (B5TRC) flips the zone verdict 0.28 times a game, in 12.5% of games. The median bag
  is 211; only 5% of those bags win. On average 2.6 enemies are within 8, and the carrier still dies within 15
  rounds 20% of the time.
- **Does the mirror offer more of it?** No, the opposite. Non-winning 150+ carriers face fewer enemy bodies in the
  mirror than live:
  - within 8: 0.51-0.54 in the mirror, against Fish 0.74-1.02 and Mite 0.66-0.80;
  - within 4: 0.05-0.06, against 0.07-0.17.
  - Deaths per 100 such rounds are alike (0.07-0.17).
- **Value in rm2's context:** +0.17 ±0.17.
- **Mechanism: not found.** Ocean hunters press big carriers less than ladder hunters do, so no mirror-specific
  exposure explains b5.

## b1: a 150+ bag banks at the altar scoring best on arrival, channel, walk and cover

- **Where it fires:** altar switches 0.22 times a game, in 5.5% of games. 17% of the switched bags win.
- **Outcome:** after a switch the carrier banks 73% of the time and dies first 14%.
- **Value in rm2's context:** -0.04 ±0.10, 1.2% flips.
- **Mechanism: none in rm2's context**, since there is no effect to explain. One untested idea: ocean's carrier
  model (`carrier_tribute`) predicts a walking carrier's nearest altar, which a switch defeats.

## b3w

See the weakness section above. Mechanism verified, but worth +0.04 ±0.11 in rm2's context.

## The fix: `bots/variants/gap-fix-sgeguard2`

`ender_spares_a_turn` (fight.cc): an ender that is walking (not channelling) scores only after its walk to an altar
plus its whole channel (`carrier_tribute`'s `turns`). When our walk to that altar's stop reach, plus one turn, is
still under that, a turn's delay costs the stop nothing. In that case:
- **bot.cc:** a body that `want_home` would send home leaves; the game-ender branch no longer preempts its retreat.
- **stop_game_ender:** otherwise the shadowing walk keeps the step guard, with no forced travel dash and no
  `dash_to_attack`.

Once a turn's delay would let the tribute land, and through every tribute channel, the old risk-blind route runs
unchanged. There are no constants: the test is the intercept model's own timing.

v1, `bots/variants/gap-fix-sgeguard`, is the guard alone, without the retreat.

**Traced stopper deaths** (2,000 debug games against rm2; death within 2 rounds of a stop_game_ender turn):

| Version | Walking-ender turns | Death rate | Notes | Deaths a game |
|---|---|---|---|---|
| rm2 | 15,003 | 16.7% | | 7.27 |
| v1 | 18,596 spare | 11.4% | | 7.20 |
| v2 | 33,360 spare | 0.7% | plus 24,854 leave turns at 3.3% | 7.00 |

Tribute-phase turns die at 15-16% throughout, since that route is unchanged.

**Screens** (release, own drafts, ocrm-1920, against ocean-ba65375; reference rm2 there is 47.6%, 47.1-48.1):

| Version | Win % (95% CI) | Paired vs rm2's reference | Flips | OOF CAND / REF |
|---|---|---|---|---|
| v1 | 47.5 (47.1-48.0) | -0.09 ±0.14 | 2.1% | 479,487 / 465,606 |
| v2 | 48.1 (47.6-48.6) | **+0.46 ±0.42** | 18.5% | 478,996 / 470,388 (rm2's reference: 478,862) |

v2's out-of-fuel turns are unchanged.

v2 against ocean-rm2 directly, release, ocrm-1921: **50.5% (50.0-50.9) of 40,960**; out-of-fuel turns 491,393 against
rm2's 501,838 (-2%). So v2 gains on the mirror against both bases rather than trading one for the other.

The weakness it closes shows live too: ocean's stoppers die 2.92 an episode by Fish's one-site winning carriers, against
3.06 in the mirror. A live or dgate read would say whether it helps there. ocrm-1920 and ocrm-1921 were both used
for screening, so gap-1930 is the place to confirm.

## Summary

| Feature | What it exploits in ocean | Confidence | Worth on rm2 |
|---|---|---|---|
| b3w | ocean's risk-blind `stop_game_ender` walks bodies into winning-bag escorts; Fish and Mite close in and die 2-4x less | verified | +0.04 ±0.11 |
| gf | ocean's small carriers lose more to marginal pursuit than ocean's chase sim predicts; Fish's punish it | hypothesis, low-medium | +0.31 ±0.41 |
| b5 | not found: the mirror presses big carriers less than live does | none | +0.17 ±0.17 |
| b1 | not found | none | -0.04 ±0.10 |
