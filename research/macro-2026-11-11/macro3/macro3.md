# macro3: macro work on ocean against ocean-ref-b7c87cf (2026-11-11)

**Outcome: the 60% target was not reached.** The best candidate is `bots/variants/macro3-eoq2`, now also in
`bots/ocean` on branch macro3-20261111. It replaces the fixed 25-gem bank floor with a per-champion
economic-order-quantity floor, using an online estimate of the bag-carrier hazard.

| Games | Sets | Win rate | 95% CI |
|---|---|---|---|
| 30,720 | ladder-v2 A, B, C (53.4 / 53.1 / 52.8) | 53.1% | 52.5-53.7 |
| 5,120 | `--mix varied` stress maps | 53.4% | 52.0-54.8 |

Out-of-fuel turns at 2x fuel equal the reference's. Every other idea, about twenty fight-, coordination- and
farm-targeting changes, was level or lost. The bank floor was the one fixed quantity whose principled replacement
paid. The running log is [macro3-log.md](macro3-log.md) and the brief is [macro3-brief.md](macro3-brief.md).

## The design: a bank floor from the economic order quantity

A champion banks a bag only once it holds at least `bank_floor` gems; a winning bag or a closing game still
overrides this. The reference used a fixed `params::min_bank = 25`.

Banking is an inventory problem:
- Each trip has a fixed cost: the walk or recall to an altar, the tribute's one fixed turn, and the way back. The
  remaining tribute turns, one per 10 gems, are paid whatever the bag, so they are not part of the fixed cost.
- Each gem carried has a holding cost: a carrier's death loses the bag and the killer gains it, a swing of 2x the
  bag by the rules.

The optimal batch is Q* = sqrt(2KD/h), with:
- K = T·D, the gems forgone during a trip of T rounds;
- D, the champion's own gem income per turn alive, from the existing `income_rates` prior;
- h = hazard × 2.

So the floor is Q* = D·sqrt(2T/h), clamped from below to one tribute turn's worth (10 gems), and from above to the
gems short of the win or what a tribute can still score (`src/economy/bank.cc` `bank_floor`).

**What it does in practice.**
- High-income champions far from an altar carry 40-70 gems before banking.
- Low-income champions, or any champion next to an altar, bank small bags of 10 or more.
- Map size enters through T, which is 5-20 rounds on 28x28 maps and up to about 110 on 100x100.

**The hazard.** In eoq it is the measured 0.86e-3 deaths per carrying round. In eoq2 it is a team-wide Gamma
posterior mean, (1 + deaths) / (1/0.86e-3 + carrying rounds):
- the prior is worth one death at the measured rate;
- it is updated every round from the team's carriers. An ally's death is readable for everyone, and its bag comes
  from vision or the posted comms bag.

Against an opponent that kills carriers more often, the floor falls on its own.

**Why it wins.** The floor is gated by its own A/B decomposition on set A:

| Variant | Win rate |
|---|---|
| Floor = max(25, Q*): only raising | 51.8 |
| Floor = min(25, Q*): only lowering | 50.3 |
| Both (eoq) | 52.5 |
| Online hazard (eoq2) | 53.4 |

Most of the gain is high-income champions on long trips no longer walking home with 25 gems, at the 1.4 points
per 1% of farm turns measured below. The reference's own probes had read min_bank 40 at 50.4 and 15 at 47.6: no
single constant fits all champions and maps, but the quantity derived per champion and trip does.

**Refinements that did not add:**

| Variant | Win rate (set A) |
|---|---|
| eoq3: chain limit set to the same floor | 52.4 |
| eoq4: per-champion hazard shrunk to the team's | 52.5 |
| eoqc: eoq2 + collapse | 53.0 |

## Setup

- **Reference.** `bots/variants/ocean-ref-b7c87cf`, never edited. It is identical to `bots/ocean` at the start.
  `bots/variants/macro3-base` is a byte-identical copy, and every candidate was built from it.
- **A/B setup.**
  - Command: `py tools/ab.py variants/macro3-X variants/ocean-ref-b7c87cf --no-test-draft --fuel 200000`, on the
    fast runner, 10,240 games per set (20 ladder-v2 suites of 256 maps, both sides).
  - Set A is seeds 300001-300020, set B 300021-300040 and set C 300041-300060, all in /home/ubuntu/wt/macro3-maps/.
  - The mirror is deterministic: base against the reference reads exactly 50.0%.
  - The 95% CI on 10,240 games is about ±1.0 point.
- **Studies.** 1024 debug mirror games on study-309901/309902 (seeds in range), analysed by a read-only replay
  agent. Implementation agents also ran paired batches of 200-1000 games against base on the same maps.
- **Process.** All bot code was written by implementation subagents, each audited by a read-only subagent.

## What the measurements say about the game and the reference

### Champion time is the currency
Two handicap probes made the reference stand still on a share of its plain `farm()` turns:

| Farm turns skipped | Win rate |
|---|---|
| 5% | 42.7% |
| 10% | 36.2% |

That is about 1.4 win-rate points per 1% of farm turns, roughly linear. A bot with about 7% more effective farm time
should therefore win about 60%. The teacher bot's 65% is consistent with a macro edge of that size.

### Where the time goes
Reference mirror games, as a share of alive champion turns:

| Activity | Share |
|---|---|
| Hitting camps | 17.2% |
| Walking out from spawn | 17.4% |
| Walking between camps | 26.3% (12.5% of it with a bag) |
| Walking to an altar | 7.7% |
| Support (Prism/Willow) | 6.0% |
| Retreat | 5.9% |
| Recall | 4.4% |
| Holding captures | 3.9% |
| Idle in farm | 4.2% |
| Tribute | 1.9% |

Dead time is a further 6.4% of all turns.

Walking out from spawn follows recalls: 57% of them come after bank-bag recalls, with paths close to the shortest.
Walking on legs abandoned before arrival is 20% of alive rounds, or 12% net of progress toward the next target.

### Where the reference's value lies
Ablations, one subsystem off, 10,240 games each (set A). The figure is the ablated bot's win rate:

| Subsystem turned off | Win rate |
|---|---|
| Fight-model retreat exit (`stand_lost_at`) | 37.2 |
| Strike search when not holding | 40.6 |
| Chase | 44.4 |
| Recall-to-farm | 46.2 |
| Capture handoff | 47.8 |
| contest_capture | 48.9 |
| Game-ender stop | 49.1 |
| Pack-zone exit | 49.2 |
| Siege/kite | 49.4 |
| Local support | 49.6 |
| fixc commit | 49.9 |
| Altar guard | 49.9 |
| Wake ring | 50.0 |

Joining allies' groups is also worth about 8 points: an agent's paired 200 games with no joins won 42%.

Single-parameter probes all sit at their optimum, reading level or losing in both directions:
- home_power 0 / 2: 48.1 / 48.6
- stickiness 1.5: 49.5
- min_bank 40 / 15: 50.4 / 47.6
- recall 0.7: 49.6
- bolder retreat: 49.8
- horizon x2: 49.4

### How games are decided (mirror)
- Winners die 2.2 times a game against 6.0 for losers. P(win | lost the first champion) = 0.33.
- Gem swing, meaning bags lost at death and gained from kills, predicts the winner:
  - counted to round 300 it gives AUC 0.66, and to round 500 0.72;
  - a lead of 50 or more swing gems wins about 77% of the time.
- Most lost gems come from a few big bags. Prism keeps its bag for Focus and carries 274 of 389 bags of 50 gems or
  more (mean 190).
- Deaths happen under visible danger. A killer was seen the round before the first hit in 87-89% of deaths, and
  only 5-7% of deaths had no killer seen in the 10 rounds before. Fog is symmetric and not a lever.
- Local HP share predicts contact outcomes (AUC 0.69) better than numbers (0.58).
- The most common death, at 33-45%, is a group fight lost at even or better numbers. The attackers focus the
  edge body of a loose farming group, while our nearby allies keep farming or retreat. In 60% of these deaths they
  dealt no damage.
- Retreats run at 98 a game. The verdict starts 79% of them, and 63% are never followed by damage, an enemy
  within 3 or a death. Two things explain most of this:
  - The enemy, running the same model, backs off from us 81% of the time.
  - Most "lost" verdicts, 28 of 41 per game among those where every hitter was visible and in reach, are lost even
    with us striking first.

## Every A/B (against ocean-ref-b7c87cf, `--fuel 200000`, `--no-test-draft`)

| Candidate | What it does | Games | Sets | Win % | 95% CI |
|---|---|---|---|---|---|
| macro3-window | Numbers windows: farm weight home^(m·f), where f counts the enemy bodies that can be at a group by job end (dead ones by respawn and walk) against ours; prey lifted when f<1 | 30,720 | A, B, C | 50.4 (50.7 / 50.0 / 50.4) | ~49.8-50.9 |
| **macro3-collapse** | Team counter-commit: when an ally within pack radius is struck and the local fight is not lost, its attackers become prey wherever they stand, and the commit holds through want_home | 30,720 | A, B, C | **50.5** (50.3 / 50.9 / 50.3) | ~49.9-51.1 |
| macro3-stack | window + collapse | 30,720 | A, B, C | 50.1 (50.5 / 50.5 / 49.3) | ~49.5-50.7 |
| macro3-linked | Life value × bodies removed (C&I = 2) in kill and protect values | 10,240 | A | 50.0 | 49.0-50.9 |
| macro3-commit | claim_beaten: an ally that would start work on our claim sooner takes it, and we price a crew share | 10,240 | A | 50.0 | 49.0-50.9 |
| macro3-hold | Skip the stand exit at a camp when locally even (Lanchester parity), able to strike back and not hurt | 20,480 | A, B | 50.1 (50.3 / 49.9) | ~49.4-50.8 |
| macro3-intent | Enemy whereabouts and intent model (Luce choice over our own valuation), discounting contestable groups | 10,240 | A | **47.1** | 46.1-48.0 |
| macro3-deny | Same model with the opposite sign: a zero-sum denial term in place of the discount | 10,240 | A | 50.4 | 49.4-51.3 |
| macro3-pause | Stand-verdict retreats keep the claim | 10,240 | A | 49.2 | 48.3-50.2 |
| macro3-flow | Farm throughput; final: unseen claimers' work estimated on joined groups | 10,240 | A | 49.7 | 48.7-50.7 |
| macro3-deter | Mutual deterrence: a Beta belief of the enemy's back-off rate decides whether to stay in first-strike-only lost stands | 20,480 | A, B | 49.95 (50.1 / 49.8) | ~49.3-50.6 |
| macro3-team | Team-marginal join value: claimers' time saved × rate, our share treated as a transfer | 10,240 | A | **42.0** | 41.1-43.0 |
| macro3-join | Base's share plus the team bonus, so more joining | 10,240 | A | 49.1 | 48.1-50.1 |
| macro3-eoq | EOQ bank floor, fixed hazard | 30,720 | A, B, C | 52.6 (52.5 / 52.9 / 52.5) | 52.1-53.2 |
| macro3-eoq-hi / -lo | Floor max / min(25, Q*) | 10,240 each | A | 51.8 / 50.3 | ±1.0 |
| **macro3-eoq2** | EOQ floor, online Gamma carrier hazard | 30,720 + 5,120 varied | A, B, C, varied | **53.1** (53.4 / 53.1 / 52.8; varied 53.4) | 52.5-53.7 |
| macro3-eoq3 / eoq4 / eoqc | Chain limit = floor / per-champion hazard / + collapse | 10,240 each | A | 52.4 / 52.5 / 53.0 | ±1.0 |
| Probes and ablations | See above | 10,240 each | A | | |

Variants dropped after paired batches, without an A/B:
- macro3-logi: logistics. Emblem-stop worth, no capture recall under min_bank, and round-trip-priced recalls were
  all level or lost.
- flow's plan-order insertion, arrival-order ceding and stale-health fixes: level or lost.
- pause's job-ward minimal retreat and anti-ping-pong guard: each about -2% of captures, with CIs that exclude 0.
- deter's always-stay: tribute at r300 +3.4%, but win rate -0.3.

## What failed and why

- **Fight-level coordination: window, collapse, linked, hold, deter.** Level. The fight model is calibrated at its
  boundary, as earlier research found. The mirrored opponent already backs off from stands it would lose, so the
  "symmetric false alarm" is real, but staying is EV-neutral: about 3 rounds saved per episode, at +4 points of
  death risk.
- **Avoiding contested groups (intent): lost 2.9 points.** In a stand-off, the holder captures 68% of the time
  against the leaver's 4%. Yielding gives the camp to the enemy without saving lives, and the reference's
  persistence is right. Flipping the sign (deny) recovers to level but adds nothing: the Luce intent probability is
  spread too thin to change many picks.
- **Throughput: commit, flow, logi, pause.** No change raised capture throughput in paired batches.
  - The waste is real: abandoned legs are 20% of alive rounds and retreats about 20% from start to back-to-work.
  - But it comes from decisions that are locally right given the information. Switching after an ally takes the
    group, ping-pong at the edge of a lost stand that puts us back on the job as soon as the threat moves, and the
    recall and heal-and-shop balance all stand up.
  - Every attempt to remove a piece of this waste cost as much as it saved.
- **Join valuation: team, join.** Valuing joins by the claimers' time saved, with our share treated as a transfer,
  cut joins by about a third and lost 8 points (captures -4-5%). Joint clears concentrate the team on the big
  groups. Valuing joins more (+18% join decisions) was level to slightly negative. The selfish-share valuation sits
  at a local optimum, and joins are worth more than a time-saving model credits.
- **Tuning:** every macro knob probed is at its optimum.

## Lessons

1. Replace fixed quantities with derived ones. The one gain came from a hand-set constant (min_bank 25)
   replaced by the economic quantity it stood for, per champion and per trip. Other fixed bag and trip constants
   may hide the same kind of gain: brake_bag 19, chain_bag_limit 26, the recall line.
2. Measure the currency first. The farm-turn handicap probe (1.4 points per 1% of farm turns) is cheap and turns
   every idea into a time budget. Ablations of the decide() ladder show where the value lies.
3. A deterministic mirror rewards only asymmetric edges, and the reference's behaviour is close to a best response
   to itself. A symmetric inefficiency, such as 63% false-alarm retreats or 20% abandoned walking, is not
   exploitable when removing it unilaterally costs what it saves.
4. Observational replay findings mislead about counterfactuals. "Staying went with twice the captures" (stand-offs,
   retreats) did not survive implementation, because the bot's own verdicts select the situations.
5. Small paired batches (200-1000 games) gave false positives several times, e.g. flow's 52.9% of 1000 was 49.7% of
   10,240. Only 10k-game A/Bs decide.
6. What has not been tried here, and is still a candidate for the teacher's macro edge: a coherent alternative
   economy rather than a tweak to this one. One example is a team plan that changes the recall-walk-out cycle (17%
   of alive time walking out of spawn). Another is cohesive group movement that makes the opponent's spread
   farmers the outnumbered side before contact, rather than the reactive collapse tried here.
