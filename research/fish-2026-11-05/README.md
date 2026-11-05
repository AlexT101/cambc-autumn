# Intercontinental Fish: recovered priority encoding and attack targets

**Latest continuation:** [route memory, incoming capture entry and earlier trips](ROUTES.md)
adds 46 untouched games in ten groups. Holder rank transfers to incoming entry; route memory
improves camp prediction only slightly; earlier recall completion fitting fails. A separate
retrospective payout audit exposes the limits of short occupation labels. All four evaluated
cohorts are now inspected. No bot source changed.

**Previous continuation:** [new destinations, holder departures and action decisions](DECISIONS.md)
adds 43 untouched games in nine groups. It independently tests approximate recall, holder,
attack and cast decisions; new destinations remain weak. All three cohorts are now inspected.

**Continuation:** [farming targets, Cassi stuns, capture holders and banking](CONTINUATION.md)
adds a separate 96-replay confirmation cohort. It confirms approximate camp-target and
stun-target models, finds a partial holder ordering, and records failed destination/banking
hypotheses. The original results below are preserved. Both cohorts are now inspected data.

This is a first, narrow reverse-engineering result, not a reconstruction of the whole bot.
The main result is an exact numerical encoding for its ordinary negative priorities, with an
unresolved branch condition. A prospective predictor for quiet priority writes generalizes
to held-out games. Basic-attack targeting has a useful, imperfect predictor. Farm destination,
retreat, altar selection and tribute thresholds remain unresolved.

## Data and validation

- 125 downloaded files in `replays/ladder-post`, all dated 2026-11-05; 124 distinct SHA-256s.
- All use replay engine `v3_0_0`, the engine in the current cambc 5.0.0 release.
- Fish's submission versions are absent from the metadata. These are observations of this
  dated corpus; we cannot prove every game used the same Fish submission.
- The saved [manifest](manifest.json) pins each replay, SHA-256, match id, match group,
  side, opponent and split. Whole groups are assigned by SHA-256(group id) modulo 5.
- Training: 109 games in 22 groups. Holdout: 15 games in 3 groups. Exact duplicate replay bytes
  are removed before analysis. Every holdout map/opponent combination is absent from training;
  four holdout games also use maps absent from training. The other maps overlap.
- Predictors were frozen before decoding/evaluating the holdout. Model and rank-table hashes
  are in [training results](train-results.json) and [holdout results](test-results.json).
- States come from the game's own WASM decoder, using the acting champion's perspective
  **before** each input. Target candidates are alive, personally visible champions in range,
  including that actor's ward vision. No opponent gold, hidden positions or future actions are
  used by the predictors. Observer reads supply timeline/roster metadata and validation only.
- Priority writes are checked against `nextPriority` and against the champion's priority at
  its next turn. [audit.json](audit.json) independently checks recorded input identities and
  completed-turn counts against the raw timeline. A recall arrival is a phase-14 Move event,
  not a walking input; the audit explicitly distinguishes these.

Accuracy below is conditional on the action being taken. These models predict the value of a
priority write or the target of an attack/heal; they do **not** predict when to make that action.
Turns within games are correlated; counts are descriptive agreement, not thousands of
independent trials. The holdout has only three match groups.

## 1. Negative priority encoding

For an ordinary negative priority, the recovered formula is:

```text
N = number of allied champion bodies, including dead allies; Cassi and Issac count separately
rank = roster-specific integer in [2, N+1]
h = min(1, (current health + current shield) / maximum health)
if carried_gems > 0: h *= 0.65
band = max(0, floor(4 * (1 - h)))
ordinary_priority = -rank - (N+1) * band

observed small_negative_priority = ordinary_priority - (N+1) * branch_penalty
branch_penalty is either 0 or 5
```

"Small negative" here means -100 < priority < 0. This is an **output-conditioned encoding
check**, distinct from predicting which branch Fish will choose:

| Encoding check | Ordinary formula | Additional penalty 5 | Other |
| --- | ---: | ---: | ---: |
| Training small negative writes, alive | 26,761 | 4,177 | 0 |
| Holdout small negative writes, alive | 4,255 | 369 | 0 |

The extra penalty's triggering condition has **not** been recovered. Visible enemy presence
alone does not explain it. Large positive/negative priorities and small positive priorities
are separate unresolved modes. Do not use the formula as a complete scheduler.

The carrying term tests **zero versus nonzero**, not bag size: one candidate coefficient
explains the observed ordinary writes across bags up to 1,199 gems. With the floor-formula
assumed, 4,601 training observations constrain the carrying multiplier to approximately
`0.649350649 < multiplier <= 0.65`. Thus `0.65` is a concise compatible value, **not proof of
that literal in their source**. [coefficient-bounds.json](coefficient-bounds.json) records the
constraint. Health-band boundaries without a bag are 75%, 50%, 25%; with the compatible
carrying multiplier, changes occur at 10/13 and 5/13 effective health. Equality enters the
lower-health band. Shield health is capped at maximum health *before* the carrying penalty.

Ranks were learned only from training observations and are stored for 11 observed roster
sets in [priority-ranks.json](priority-ranks.json). Unknown rosters cause the predictor to
abstain. In the common six-body roster they are:

| Champion | Rank |
| --- | ---: |
| Marcella | 2 |
| Heart of Ruin | 3 |
| Vendetta | 4 |
| Issac | 5 |
| Willow | 6 |
| Cassi | 7 |

For that roster, a full-health, unshielded Marcella writes ordinary priority -2 with no gems,
-9 with any gems, and -16 at half health while carrying. At exactly 75% health with no gems,
the ordinary value is -9. The unknown extra branch subtracts another 35.

### Prospective prediction, without selecting by the resulting priority

The frozen predictor returns the ordinary formula when the champion is alive, unstunned,
has a known roster, and sees no enemy at either turn start or immediately before the write.
It abstains otherwise. It uses no observed output to choose these cases.

| Split | Correct / predicted | Exact value accuracy | Coverage of all priority writes | Rank-only baseline |
| --- | ---: | ---: | ---: | ---: |
| Training | 13,818 / 13,901 | 99.40% | 20.50% | 5,111 / 13,901 |
| Holdout | 2,902 / 2,919 | 99.42% | 32.95% | 1,087 / 2,919 |
| Holdout on four unseen maps | 535 / 539 | 99.26% | — | — |

Every error is retained. Holdout errors include a -732 write, one extra-penalty write (-37
instead of -2), and 15 small positive writes despite no enemy being visible at the two sampled
times. These show that visible-enemy absence is not a complete mode selector. Memory and
intermediate sightings are possible explanations, not established ones.

The previous claim "positive in combat, negative otherwise" is false under even a narrow,
observable combat definition: a basic attack or cast aimed directly at an enemy champion
during the same turn. Training has **7,824 negative writes** on such turns; holdout has **894**.
This definition does not count pursuing, retreating or AoE aimed beside an enemy, so it is
sufficient to refute that implication without pretending to label every combat turn.

Concrete counterexample: game `ee053a1ab7e44f67`, round 51, actor 1 (Vendetta), priority -46,
write step 8339. The turn directly attacks an enemy champion. Inspect with:

```sh
python3 tools/fish/show_turn.py ee053a1ab7e44f67 51 1
```

## 2. Basic-attack target selection

At a recorded basic-attack input with at least one enemy champion visible and in basic range,
predict the enemy with minimum **health + shield**, breaking ties by lower champion id.
This is a fitted imitation rule, not an exact recovered targeting function.

| Split | All eligible attacks | Multiple enemy candidates only |
| --- | ---: | ---: |
| Training | 14,930 / 15,069 (99.08%) | 1,889 / 2,027 (93.19%) |
| Holdout | 1,637 / 1,650 (99.21%) | 169 / 181 (93.37%) |
| Holdout on four unseen maps | 313 / 319 (98.12%) | 33 / 38 (86.84%) |

The multiple-candidate column is the useful target-choice test; most overall cases have one
candidate. A raw-health baseline gets 168/181 on the holdout, so the evidence for the shield
refinement is modest. Unseen-map support is small and its accuracy is lower; the rule remains
approximate. Tie-breaking is included in these exact-id accuracies, not credited as "any tied
target is right."

Enemy precedence is strong: 15,068/15,069 training and 1,649/1,650 holdout basic attacks hit an
enemy champion when one was available. Each set has one exception. The rule predicts an
enemy on those exceptions and they count as errors. This does not say Fish attacks whenever
an enemy is available: movement, casts and idle turns are outside this evaluation.

For the holdout exception inspect `d2ed7663106f8e84`, round 392, actor 1, step 53420. The full
pre-input perspective and the actual target tile are preserved in the cache.

## 3. Willow healing: weaker exploratory fit

At an observed heal, choose the visible ally within range 4 that maximizes
`min(missing health, 3 * Willow focus) / ally maximum health`, breaking ties by lower id.

| Split | All heals | Multiple legal allies only |
| --- | ---: | ---: |
| Training | 3,572 / 3,780 (94.50%) | 2,634 / 2,842 (92.68%) |
| Holdout | 426 / 462 (92.21%) | 312 / 348 (89.66%) |

The simpler lowest-health-fraction baseline gets 311/348 on the same holdout multi-target
cases. The proposed refinement has not demonstrated a meaningful advantage there. This is
not an exact heal function, and no cast/no-cast health threshold has been established.

## What is not established

- The condition for the extra negative-priority penalty, or formulas for other priority modes.
- Whether to fight, flee, chase, cast, heal, recall, walk or remain on a capture tile.
- Camp-group destination choice, farming crew/holder assignment and capture handoffs.
- Altar destination choice or a gem threshold for starting a tribute journey.
- A universal tribute threshold. `Submit gems` timeline events include attempts against locks;
  they must not be treated as successful channel starts. The exploratory feature table calls
  these `tribute_attempt`; it is not used to claim a threshold.

The next useful extension is to recover the priority mode selector using only that actor's
remembered sightings, then evaluate first camp commitments with a full visible/remembered
candidate set. Labeling a destination from its eventual arrival is allowed for the outcome,
but future arrivals or clears must never be predictor inputs. Keep a fresh holdout for any
subsequent fitting; the current holdout has now been inspected.

## Reproduce and inspect

All analysis scripts are under [tools/fish](../../tools/fish/). They use only Python's standard
library and the existing Node/WASM replay decoder. No bot source was changed.

```sh
# Optional: reconstruct the manifest from this fixed downloaded corpus.
python3 tools/fish/manifest.py replays/ladder-post /tmp/fish-manifest.json

node tools/fish/extract.mjs research/fish-2026-11-05/manifest.json replays/fish-model train
python3 tools/fish/features.py research/fish-2026-11-05/manifest.json replays/fish-model train replays/fish-model/train-features.json.gz
python3 tools/fish/fit_priority.py replays/fish-model/train-features.json.gz /tmp/fish-ranks.json /tmp/fish-coefficient-bounds.json
python3 tools/fish/evaluate.py replays/fish-model/train-features.json.gz research/fish-2026-11-05/train-results.json

node tools/fish/extract.mjs research/fish-2026-11-05/manifest.json replays/fish-model test
python3 tools/fish/features.py research/fish-2026-11-05/manifest.json replays/fish-model test replays/fish-model/test-features.json.gz
python3 tools/fish/evaluate.py replays/fish-model/test-features.json.gz research/fish-2026-11-05/test-results.json
node tools/fish/audit.mjs research/fish-2026-11-05/manifest.json replays/fish-model
```

`extract.mjs` skips cached files, verifies source hashes, and asserts priority consistency.
If the extractor/schema is changed, use a fresh cache directory. `show_turn.py GAME ROUND ID`
prints the exact turn and all captured pre-input perspectives. `evaluate.py` writes every
failure to `train-results.errors.json.gz` / `test-results.errors.json.gz`, with game, round,
actor, engine step, actual result, prediction and relevant features. Manifest entries map the
game SHA prefix back to the original downloaded file and match id.
