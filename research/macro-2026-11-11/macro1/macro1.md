# macro1: a Prism-carry macro for ocean (2026-11-11)

Result: `bots/ocean` = `bots/variants/macro1-hold6`, **58.3% of 40,960 games (95% CI 57.8-58.8)** against
`variants/ocean-ref-b7c87cf` at `--fuel 200000` on 80 fresh `ladder-v2` suites (seeds 100001-100080), 57.5% of 10,240 on
20 held-out suites generated late (100086-105; 58.1% of 51,200 over all 100), and 56.2% of 2,560 on a `varied` stress mix
(100081-85). The 60% target was not reached. The running log, with every number and timestamp,
is [macro1-log.md](macro1-log.md).

## Method

- Every A/B: `tools/ab.py CAND variants/ocean-ref-b7c87cf --no-test-draft --fuel 200000`, release builds, fast runner
  (native), 20 suites of 256 fresh `--mix ladder-v2` maps (10,240 games, both sides). Screening on seeds 100001-20,
  confirmation on 100021-40 and 100041-60, a final held-out check on 100061-80. Identical bots score exactly 50.0%
  (deterministic mirror). One 10,240-game run is about ±1 point; candidates on the same maps are compared suite by suite.
- Evidence first: 2,048 debug games of the reference against itself, then extractions of each candidate's games
  (`tools/replay/extract.mjs`, `turn_budget.py`, `fight_metrics.py`, scripts in `/home/ubuntu/wt/macro1-maps/study*`).
  Three studies were delegated (death taxonomy, our Prism's first deaths, farm target churn).
- All bot code was written by implementation subagents, each audited by a read-only subagent.

## What decides ocean-vs-ocean games (measured)

- Kills and gem transfers decide: more kills wins 88.7%, fewer gems lost at death 88.7%. 97% of games end on a team
  reaching 1000 tributed gems.
- **Prism is the game.** Both teams draft Prism in 80% of games. Prism gains 1.5 Focus a carried gem, and its stun (1.5x
  Focus) and AoE (1x Focus) scale with it; ocean's Prism keeps every gem until its bag wins. It holds 70-80% of its team's
  carried gem-rounds, and 100+ bag deaths (6% of deaths) are 62% of gems lost.
- **Prism duels are decided by Focus, not by who hits first.** Of 2,213 Prism-vs-Prism engagements, the side hitting
  first with under half the other's Focus died within 15 rounds 52% of the time and killed 4%; at over twice, it killed
  53% and died 4%. The side whose Prism dies first wins ~15%; the other ~86%. The Focus ratio at round 100 already
  predicts the game (ours <0.8x: 31% win; >1.25x: 66%).
- A Prism's life, without its bag, is worth about twice any other champion's (first low-bag death before r300: the
  victim's team wins 27.9% for a Prism, 41.1% otherwise).
- Coordination and farm: walking is ~50% of every champion's turns (bag to altar 16%, empty to camp 18%); only 0.3 allies
  arrive in the 5 rounds after a fight starts; farm targets change 5.3 times per 100 alive turns. But captures are equal
  between candidate and reference (54 a game each): every gain below came from where the gems go, not from farming more.

## The design that won: concentrate gems on our Prism

1. **Keep the hoard** (reference behaviour, confirmed): banking the Prism's gems loses badly (36.9%, 32.7%).
2. **macro1-carry**: Prism takes over allies' gem holds it reaches before payout and weights gold at half while it keeps
   gems. Allies hold for a claiming Prism, cancel capture recalls to yield to it, and step off. +4.3 to +5.7 points.
3. **macro1-carry3**: Prism claims ally-held or cleared gem groups up to 2 x capture_time away ('L' picks). Allies leave a
   group Prism claims (`left_for_prism`) while no enemy is in sight, and stale claims are dropped. +0.65.
4. **macro1-funnel / funnel2**: no dilution of a sole Prism holder (its payout is not shared: allies' steps are kept off
   its tiles, and it holds unless an enemy is in sight). Allies also leave fresh cleared gem groups for a nearby Prism that
   is not already dominant (our Focus under 2x the largest seen enemy Prism's). funnel2 does so only when the Prism's ETA,
   counting its current task, is within the capture time. Pooled over the same 30,720 games: carry3 55.7%, funnel 56.4%,
   funnel2 56.8%.
5. **macro1-hold2**: the sole Prism holder keeps its hold with an enemy in sight, unless a seen enemy contests the tiles
   or could take it below `hurt_health_fraction` of its health before the payout (the safety model's idle-harm time,
   generalised as `Safety::turns_to_harm_idle`). Allies' fight steps and in-sight step-offs keep off its tiles. In 48
   traced games, payouts the Prism shared with an ally fell from 21 to 14, with no Prism death within 10 rounds of any of
   238 kept holds. Better than funnel2 on all four suite sets (+0.9 pooled over 40,960 games).
6. **macro1-hold6**: hold2's remaining dilution leaks closed. Willow had no work guard, so her farm and follow steps
   ignored the Prism's held tiles, and her support formation kept her standing on them; a damaged ally out of sight never
   stepped off; retreat now prefers a step off the hold as a tie-break after its own safety keys. In 48 traced games,
   shared payouts fell from 23 to 13. Better than hold2 on all five suite sets (+0.5 pooled).

The mechanism, in the numbers: with funnel our Prism captures 489 gems a game against the reference Prism's ~320, and
fights go our way (deaths 4.1 vs 4.8 a game, kills 4.6 vs 4.0, kill share at equal numbers 0.53). The first Prism
death of a game is ours in 25% of Prism games and theirs in 38% (carry: 26% and 34%; a mirror splits evenly).

## Results (win % against ocean-ref-b7c87cf, 95% CI; 10,240 games a cell unless noted)

| candidate | idea | s1-20 | s21-40 | s41-60 | s61-80 |
|---|---|---|---|---|---|
| macro1-bank | Prism banks once its tribute exceeds the 11-turn window | 36.9 (35.9-37.8) | | | |
| macro1-bank0 | Prism never keeps gems | 32.7 (31.8-33.6) | | | |
| macro1-safe | farm destination refused if retreat would reject it on arrival; races lost to nearer enemies | 49.6 (48.6-50.5) | | | |
| macro1-carry | the team funnels gem captures to its Prism | 54.3 (53.3-55.3) | 55.7 (54.7-56.6) | | |
| macro1-duel | every champion avoids a dominant enemy Prism; ours hunts a dominated one | 45.3 (44.3-46.2) | | | |
| macro1-carry2 | carry + kill routing to Prism | 54.4 (53.5-55.4) | | | |
| macro1-hunt | carry + our dominant Prism hunts a dominated one | 54.4 (53.4-55.3) | | | |
| macro1-carry3 | carry + Prism claims ally-held or cleared gem groups up to 2 x capture_time away | 55.1 (54.2-56.1) | 56.2 (55.2-57.1) | 55.9 (54.9-56.8) | |
| macro1-guard | carry + end tile priced by P(enemy Prism hit) x (life + bag); tribute start/cancel discipline | 54.2 (53.2-55.1) | | | |
| macro1-plife | carry3 + a Prism's life priced 2x everywhere | 55.6 (54.6-56.5) | 56.1 (55.1-57.0) | 55.9 (54.9-56.8) | |
| macro1-deny | carry3 + a sentinel with a lock at a remembered winning enemy carrier's altar | 55.2 (54.2-56.1) | | | |
| macro1-claims | carry3 + farm claims refactor (posted claim = target, distance tie-break, commitment, join bar) | 52.3 (51.3-53.3) | | | |
| macro1-claimslite | carry3 + claims' information fixes only | 54.2 (53.2-55.1) | | | |
| macro1-yield | carry3 + our Prism never engages or stands in reach of a seen 2x-Focus enemy Prism | 55.0 (54.1-56.0) | | | |
| macro1-reaper | carry3 + any enemy our Prism's ready burst kills is preyable on its own ground | 55.3 (54.4-56.3) | | | |
| macro1-funnel | carry3 + no dilution of a sole Prism holder + allies leave cleared gem groups for a nearby Prism | 56.8 (55.8-57.8) | 55.5 (54.6-56.5) | 57.0 (56.0-57.9) | |
| macro1-hold | ablation: carry3 + funnel's no-dilution hold only | 56.2 (55.2-57.1) | 56.8 (55.9-57.8) | | |
| macro1-funnel2 | funnel, leaving only when the Prism's ETA is within capture_time | 56.4 (55.4-57.4) | 57.0 (56.1-58.0) | 57.0 (56.0-57.9) | 57.2 (56.2-58.1) |
| macro1-hold2 | funnel2, the sole Prism holder stays in sight of enemies that can't hurt it before payout | 57.8 (56.9-58.8) | 57.4 (56.5-58.4) | 58.2 (57.2-59.1) | 57.6 (56.6-58.5) |
| macro1-hold3 | hold2 with a kill-only threat test | 57.9 (56.9-58.8) | 57.7 (56.7-58.6) | 58.0 (57.0-58.9) | |
| macro1-hold4 | hold2's threat test for Tavi and Marcella sole holds too | 57.8 (56.9-58.8) | | | |
| macro1-hold5 | hold2's threat test also for our Prism's takeover and carry picks | 57.8 (56.9-58.8) | 57.8 (56.9-58.8) | 58.2 (57.3-59.2) | |
| **macro1-hold6** | hold2 + its remaining dilution leaks closed (Willow, damaged allies, retreat tie-break) | 57.9 (57.0-58.9) | 58.2 (57.2-59.1) | 58.9 (58.0-59.9) | 58.1 (57.2-59.1) |
| macro1-hold7 | hold6 + an ally never starts a recall on a sole Prism hold's tiles | 57.9 (57.0-58.9) | 58.1 (57.2-59.1) | | |

Fresh held-out suites s-100086..105, generated after hold2 was adopted (10,240 games each): funnel2 56.2 (55.3-57.2),
hold2 57.0 (56.1-58.0), hold3 57.3 (56.3-58.2), hold5 57.4 (56.4-58.3), hold6 57.5 (56.6-58.5). On the varied mix hold6
scores 56.2% of 2,560 (54.2-58.1), the same as hold2. hold6 over all 100 ladder-v2 suites: 58.1% of 51,200 (57.7-58.6). hold2 over all 100 ladder-v2 suites: 57.6% of
51,200 (57.2-58.0). hold3 and hold5 are level with hold2 (+0.07 and +0.19 pooled over 40,960 games on the same maps), and
hold4 fires in about 1% of games under our draft.

On the `varied` mix (s-100081..85, 2,560 games): funnel2 55.6% (53.7-57.5), hold2 56.2% (54.3-58.1). funnel2 on the 128
ladder maps: 55.9% of 256 (49.7-61.8).

The hold ablation says the funnel's gain is mostly the no-dilution hold (+0.9 over carry3 on 20,480 games); allies
leaving cleared groups adds ~0.2, within noise.

## What failed, and why

- **Banking the Prism's bag** (bank, bank0: -13, -17). The hoard is the team's weapon: without it, the kill share at equal
  numbers fell to 0.42, deaths rose from 3.6 to 5.0, and captures fell, because Focus also clears camps.
- **Avoiding the enemy Prism** (duel -5; safe -0.4). Avoidance by every champion barred farm groups across the map and
  ceded it. That matches the prior finding that giving way loses. Narrowing it to our Prism alone (guard; yield, vs a 2x
  dominant enemy) was level: the dangerous cases are rare (about 4 dominated Prism turns a game), and the duel is
  decided by Focus, not footwork.
- **Hunting and kill routing** (hunt, carry2, reaper: level). The fight model already takes the kills it can win; the new
  ones were rare (kill routing about once in 2 games) or refused by the fight simulation (reaper: 10% of the new prey taken).
- **Pricing a Prism's life at its measured 2x** (plife: level over 30,720 games). The ranking of fights barely changes.
- **Tribute discipline and denial** (guard, deny: level). Our failed big tributes are cheap: the Prism dies within 15
  rounds of a cancel only 2-3% of the time. Enemy winning tributes mostly complete unseen, and 68% have none of ours within
  5. But the threat is known only late (enemy score 930-998), and a lone sentinel dies at a crowded altar.
- **Widening the hold2 threat test** (hold3, hold4, hold5: level). A kill-only bar, the same test for Tavi and Marcella
  holds, and the same test for the Prism's takeover and carry picks. The kill bar changes few verdicts. Non-Prism sole
  holds in sight are rare under our draft. Carry picks have a long window, so nearly any enemy in sight still reads as
  a threat.
- **Recalls on the Prism's hold** (hold7: level, 7 fewer wins than hold6 over 20,480 games). The recall-channel leak
  hold6's trace found is a few gems a game.
- **Farm claims refactor** (claims -2.8; claimslite -0.9). The churn study counted 5% of alive turns lost to switching
  targets, and the refactor cut churn 16-29%. It still lost. Switching is mostly adaptive: it reacts to enemies, allies'
  progress and new information. A claim that follows a passing hit tells allies something useful.

## Lessons

- Look for the quantity that decides the game before tuning behaviour: here it was the Prism Focus ratio. The one large
  gain came from changing who holds the gems, with farm volume unchanged.
- Once a lever works, follow it into every code path. After the first no-dilution hold, three more steps on the same
  mechanic each won on every suite set: keeping the hold in sight of harmless enemies (hold2, +0.9), then closing the leaks
  a trace of shared payouts found (hold6, +0.5; Willow's paths had never seen the guard). The trace counted the exact
  failure, so the fixes needed no new constants. Widening the threat test to rare paths (hold3-5) was level.
- Measured cliffs make good thresholds: the 2x Focus ratio, capture_time as a commitment horizon, P(hit) by distance.
  But a correct threshold on a rare situation moves nothing: check how often a rule would fire before building it.
- Avoidance loses against this opponent, at every scope tried. Restricting a rule to our Prism made it level, not positive.
- Local "waste" (churn, idle, failed channels) is an upper bound, and most of it is adaptive or cheap: cutting it lost.
- The 20% of games without Prism are untouched by this design (~50%), so 60% overall would need ~62.5% in Prism games.
  The next gains likely need a lever for those games, or a way to turn r100 Prism dominance into wins more often than 66-70%.
  In the dominant games we lost, our allies died 6.6 times against 4.1 and were out-farmed (759 vs 397 tributed).

## Fuel

No fuel work was done. hold6's out-of-fuel turns at 200k are 479-661 per 10,240 games against the reference's 451-604. hold2's out-of-fuel turns at 200k are at the reference's level too (487-620 vs 461-603 per
10,240 games); its threat test is cached per ally per round and falls back to "threatened" when short of fuel. funnel2's out-of-fuel turns at 200k are at the reference's level (472-607 vs 459-605 per
10,240 games). funnel's per-group walking fields cost more, and funnel2 bounds them with crow-distance checks and fuel
guards. A real-budget (100k) check is still to do before shipping.
