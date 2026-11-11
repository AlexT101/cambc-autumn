# macro4: Prism as the team's harvester (2026-11-11)

Lead: macro4 orchestrator. Branch macro4-20261111. Every A/B: `--fuel 200000`, release builds, `--no-test-draft`,
against `variants/ocean-ref-b7c87cf` (= ocean at the start), on ladder-v2 mapgen suites under
/home/ubuntu/wt/macro4-maps (dev = seeds 400001-400020, cf = 400021-400038, fr = 400041-400060, ho = 400061-400080
held out to the end). Running log with timestamps: [macro4-log.md](macro4-log.md). Patches of every candidate
against ocean or against their base: [patches/](patches/). Briefs given to implementers: [briefs/](briefs/).

## Result

**bots/ocean = macro4-handfc** (frozen copy: `bots/variants/macro4-handfc`; patch vs the old ocean:
[patches/handf.diff](patches/handf.diff), the shipped source is handf minus its ablation scaffolding, bench-identical
to handf at 100M).

| suites (seeds) | games | win % vs ocean-ref | 95% CI |
|---|---|---|---|
| cf + fr + **ho held out** (400021-400038, 400041-400080) | 29696 | **56.3** | 55.8-56.9 |
| of which ho only (400061-400080, used once before, by handf) | 10240 | 57.0 | 56.1-58.0 |
| **h2, second held-out set** (400091-400110, never used before), handfc | 10240 | 56.1 | 55.1-57.0 |
| **all fresh suites: cf + fr + ho + h2** | 39936 | **56.3** | 55.8-56.8 |
| dev (400001-400020) | 10240 | 56.6 | 55.6-57.5 |
| varied stress mix (400081-400090), handf | 5120 | 54.1 | 52.7-55.4 |
| the 128 ladder maps (ab.py default), handfc | 256 | 57.4 | 51.3-63.3 |
| maps/gen (ab.py default), handfc | 512 | 54.7 | 50.4-58.9 |

Every merged suite is positive (55.4-57.9 per suite in the final run). With dev, over 50,176 ladder-v2 games: 56.3%. Below the 60% goal:
see Lessons. Out-of-fuel turns 1599 vs 1399 (the excess is spread over unrelated code: different game states).
Games without Prism in our draft (~20-26%) are untouched (an exact ocean mirror, 50%); with Prism ~58% (inferred from the overall rate and the no-Prism share; hub2 measured 56.0% with Prism, 49.7% without).

## Design (what shipped)

The game's only gem-scaling asset is Prism: +1.5 Focus per carried gem, and its two damage spells are 1.5x and 1x
Focus. A gem in Prism's bag is worth more than one in anyone else's until it is tributed. Ocean let gems reach
Prism only by accident (it hoards its own bag; allies bank theirs).

The shipped change is a **division of labour**: allies clear camp groups as before; **Prism walks to an ally's
clear and takes the capture hold, the ally steps off and goes back to work, and the whole reward lands in Prism's
bag**. Pieces (economy/hub.cc, economy/farm.cc 'Q' branch, economy/capture.cc yield/hand-over):
- **Premium rho**, derived, not tuned: one carried gem adds 1.5 Focus x (1.5 + 1) / cooldown 8 ~= 0.47 damage a
  round; converted to gems at the map's camp gems per health point; integrated over the rounds the gem stays carried
  (min(rounds left, race left) minus a walk margin) with the farm's own horizon discount h: rho = 0.47 x density x
  h ln(1 + H/h), clamped to [0, 2], fading to 0 at the end. Typical values ~1 early, 0.8-0.9 mid, ~0.1 late. Probes
  x0.5 (55.0) and x2 (54.4) vs 55.8 confirm it sits at the optimum.
- **Prism's 'Q' collection value** is the team-view marginal (the takeover_worth shape): rho x gems (the gems would
  have been scored by the ally anyway) + the holder-value gain + the ally's freed rounds x the farm's work rate,
  over Prism's walk + hold rounds. hub1 had counted the whole gems x (1 + rho), ~4x too eager (hub2: +1.6).
- **Hand-over**: the ally holds until Prism joins a multi-tile hold (YIELD, no reset) or, on a single tile, steps
  off as soon as Prism is due before the ally's payout and no threat can reach the tiles first (Prism's hold
  restarts anyway, so the ally's extra rounds buy nothing); one shared predicate (`hub_hands_at`) so Prism only
  walks where the ally will hand over. Prism commits to a Q pick instead of dropping and re-picking while the clear
  outlasts its walk; it joins a clear under way only if it can afford the camp fire.
- **Allies' choices are not distorted**: an earlier "hub" also multiplied allies' group values by (1 + rho) to route
  clears toward Prism; that half alone is worth nothing (hubA 50.9) and costs ~1 point combined (hub2 54.8 vs hubQ
  55.8).
- Off when we didn't draft Prism (~20-26% of games): those games are an exact ocean mirror.

## Every A/B (vs ocean-ref; games, win %, 95% CI)

| candidate | what | suites | games | win % | 95% CI |
|---|---|---|---|---|---|
| p-roster | fight/pack roster radius 4->7, 6->9 | dev | 10240 | 50.6 | 49.6-51.6 |
| p-prismbank | Prism banks like everyone (no hoard) | dev (SPRT) | 263 | 30.4 | - |
| p-stick | farm stickiness 1.2 -> 2.0 | dev (SPRT) | 394 | 46.4 | - |
| pact | engagement pact: contact posts, consistent roster, join when it wins, retreat into help | dev | 10240 | 50.7 | 49.7-51.7 |
| pact2 | pact, join whenever not lost | dev | 10240 | 50.4 | 49.4-51.3 |
| hub (preview) | carry hub: allies' premium + Prism collection + hand-over | dev | 10240 | 53.5 | 52.6-54.5 |
| hub (preview, later src) | same | cf | 9216 | 54.1 | 53.1-55.2 |
| hub1 | audited hub | dev+cf | 19456 | 53.2 | 52.5-53.9 |
| hub2 | hub1 + team-view collection value | dev+cf | 19456 | 54.8 | 54.1-55.5 |
| hub2 | | fr | 10240 | 55.5 | 54.5-56.4 |
| duel2 | hub2 + carrier death priced at its bag (safety/retreat/recall/heal) | dev+cf | 19456 | 49.1 | 48.4-49.8 |
| dA | hub2 + bag-at-risk heal credit | dev | 10240 | 50.1 | 49.1-51.1 |
| dB | hub2 + victim bag at Prism premium in targeting | dev | 10240 | 54.7 | 53.7-55.6 |
| dC | hub2 + carrier recall gate | dev | 10240 | 54.7 | 53.7-55.6 |
| dD | hub2 + trade-comparison fall rule + duel strike | dev | 10240 | 54.8 | 53.8-55.7 |
| p-heal50 / p-heal150 | hub2, heal credit x0.5 / x1.5 | dev | 10240 each | 53.9 / 54.0 | 52.9-54.8 / 53.0-55.0 |
| willow | hub2 + allies price Willow heals, Willow covers max gain | dev+cf+fr | 29696 | 54.9 | 54.3-55.4 |
| crew | hub2 + crew prices follow arrival times | dev | 10240 | 54.8 | 53.9-55.8 |
| crew | | cf+fr | 19456 | 55.1 | 54.4-55.8 |
| race / race2 | hub2 + rho by Prism race state (fixed tracker) | dev | 10240 each | 54.8 / 54.9 | 53.8-55.8 / 53.9-55.8 |
| hubA | hub2 minus Prism collection (allies' premium only) | dev | 10240 | 50.9 | 49.9-51.8 |
| **hubQ** | hub2 minus allies' premium (Prism collection only) | dev | 10240 | 55.8 | 54.8-56.7 |
| hubQ | | cf+fr | 19456 | 55.5 | 54.8-56.2 |
| q-r50 / q-r200 | hubQ, rho x0.5 / x2 | dev | 10240 each | 55.0 / 54.4 | 54.0-56.0 / 53.5-55.4 |
| q-gate | hubQ with ocean's sole_capture_holder gate | dev | 10240 | 55.8 | 54.9-56.8 |
| q-nohand | hubQ, allies never step off (Prism only joins) | dev | 10240 | 51.1 | 50.2-52.1 |
| gallq / g1 / g2 | stun window in the threat model, unseen-threat guard, game-ender, tribute cancel | dev | 10240 each | 55.9 / 55.1 / 54.7 | - |
| q-r0 | q-gate, rho = 0 in Q | dev | 10240 | 53.4 | 52.5-54.4 |
| take | q-gate + takeover generalised to any champion | dev | 10240 | 54.2 | 53.3-55.2 |
| **hand** | q-gate + hand-over sharpening | dev | 10240 | 56.6 | 55.6-57.5 |
| hand | | cf+fr | 19456 | 56.0 | 55.3-56.7 |
| hand2 | hand + Q starts only where Prism arrives before the ally's payout | dev | 10240 | 56.7 | 55.8-57.7 |
| hand2 | | cf+fr | 19456 | 56.0 | 55.3-56.7 |
| aoe | hand2 + camp clear model credits area damage | dev | 10240 | 53.5 | 52.5-54.5 |
| handf | = hand, frozen | ho (held out) | 10240 | 57.0 | 56.1-58.0 |
| handf | | varied stress | 5120 | 54.1 | 52.7-55.4 |
| **handfc (shipped)** | handf minus ablation scaffolding | dev | 10240 | 56.6 | 55.6-57.5 |
| **handfc (shipped)** | | cf+fr+ho | 29696 | **56.3** | 55.8-56.9 |

| hq-rate | handfc, Q's freed rounds at the ally's own rate | dev | 10240 | 56.7 | 55.8-57.7 |
| hq-relief | handfc, allies price their hold as ending at Prism's arrival | dev | 10240 | 56.5 | 55.6-57.5 |
| aoe2 | handfc + area model for non-Prism champions only | dev | 10240 | 56.1 | 55.1-57.0 |
| kbag | handfc + Prism's combat prices a victim's bag at (1 + rho) | dev | 10240 | 56.3 | 55.4-57.3 |

Fuel-only: handff (memoised Q branch) saved 0.1% of fuel, bench-identical; not shipped. Debug studies (no A/B):
pact debug study, Q-walk stalls (none real), hub loss study, Prism duel micro study (see the log).

## What failed, and why

- **Fight commitment (pact, pact2, roster radii): level.** Joining fights more consistently changed deaths a
  little (4.40 vs 4.73 in a debug study) but not outcomes; ~7 joins a game. Fights are lopsided because of who is
  there and with what Focus, not because allies fail to commit.
- **Caution for carriers (duel2, dA): -5 to -6.** Pricing a carrier's death at its bag made Prism and every 16+ gem
  carrier retreat and go home more; captures and gold fell more than the bags saved. The ablation pinned it on the
  heal-trip term (dA alone 50.1). Heal-trip pricing is at a local optimum (x0.5 and x1.5 both lose).
- **Accurate threat model (G: stun window, unseen threats): level.** Modelling a stun's lost reply turn and guarding
  against tracked unseen enemies is correct but didn't move results, and cost fuel.
- **Duel pieces (dB, dC, dD): level.** Bag-weighted targeting, a carrier recall gate, a trade-based fall rule.
- **Willow as a field spawn, arrival-time crew pricing: level.** Both changed their measured mechanism (more Willow
  heals; second dealer lag 5.5 -> 4.0 rounds on Elk) without moving the win rate.
- **Race-aware premium (race, race2): level.** The r200 Prism-bag lead predicts wins (72% at 60+ ahead, 20% at 60+
  behind) but is an outcome; dropping the premium when behind, or fading it when far ahead, changes nothing.
- **Routing allies to Prism (hubA): worth nothing.** Allies re-choosing groups for Prism's sake distorts the
  workers; the gain is Prism harvesting where they already work.
- **Generalised takeover (take): -1.6.** Freed hold time alone doesn't pay for a non-Prism taker's walk.
- **Prism last-hits on carriers (plast): nothing to redirect.** Measured before building (80 games): Prism already
  lands 69% of the 126 carried gems a game our kills take; allies killed a carrier Prism could also have killed in
  that round only 2.3 gems a game, all on victims that had yet to act (so never certain for Prism).
- **Kill-bag premium (kbag): level (56.3 vs 56.6).** Prism already takes most carried gems from kills; pricing them
  higher changes little.
- **Area-aware clear model (aoe): -3.2.** The old single-target model under-predicts Prism's camp damage x1.6 and
  Varg's x1.7; fixing it re-steers Prism toward clearing (away from harvesting) and costs fuel (OOF 722 vs ~565).
  An accurate sub-model can lose when the rest of the system is tuned around its bias.

## Lessons

1. **The win was a division of labour around the one scaling asset**: workers keep working, the carrier harvests.
   Its value splits into freed ally time (~3 points: q-r0 53.4 vs ocean 50) and the Focus premium (~2.5).
2. **Ablate every multi-part change.** The hub's first version carried a harmful half (allies' premium) and two
   neutral ones (the relaxed hold gate); half-ablations found the engine in two A/Bs and simplified the design.
3. **Caution is expensive.** Every change that made champions retreat, recall or heal more lost (duel2 -5.7, dA -4.7),
   consistent with older priors (squads, deathballs). Protecting the bag must not cost work.
4. **Measured mechanism shifts don't imply wins** (willow, crew, G): check the target metric moved, then trust the A/B.
5. **Predictors are not levers** (race): the Prism-bag lead at r200 predicts the result but steering on it is level.
6. Throughput: a 10k-game A/B is 1.5-5 minutes on the 86-slot pool; SPRT at 0.47/0.53 stops far too early (200-400
   games) for effects of 1-3 points — run fixed 10k blocks.
7. **Why not 60%.** The shipped change acts only when we draft Prism (~75-80% of games) and leaves the rest an exact
   mirror at 50%, which caps the overall gain at ~0.78 x the Prism-game gain. Every general change tried on top
   (fights, caution, healing, Willow, crews, threat and clear models, generalised takeovers) was level or lost
   against an opponent that is our own ancestor; the next gain probably needs a general economy mechanism we have
   not found, not more polish of the harvesting engine (its rho, rate and relief refinements are all at optimum).

