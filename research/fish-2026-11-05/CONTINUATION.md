# Fish continuation: farming targets, stuns, holders and banking

**Later work:** [DECISIONS.md](DECISIONS.md) adds a third, independently confirmed cohort for
action decisions, final-turn recall and lower-holder departures, plus failed new-destination
models. This report and its frozen results are preserved below.

The strongest new results are a persistent camp-group target model, a Cassi stun-target
model, and a partial capture-holder ordering. Opening farm destinations and the timing of
retreat/banking remain unresolved. This continuation deliberately moved across behaviors
instead of refining the already strong priority encoding. No bot source was changed.

## Evidence and validation

The original 124 games are discovery data, including the previously inspected holdout.
A separate local corpus supplied **96 distinct replays**, pinned in
[confirmation-manifest.json](confirmation-manifest.json). Its source is
`replays/bush-ladder/matches.tsv` and `replays/bush-ladder/games/`: 102 Fish file entries,
filtered against the original hashes and deduplicated by bytes. The match creation times
span November 4, 18:10–22:00 ET; manifest timestamps use UTC. All replay engines are `v3_0_0`.
The ordered drafts of both sides match the source metadata in **96/96 games**, independently
checking the Fish side assignment; see [metadata audit](confirmation-metadata-audit.json).
Fish submission versions and this source's match-group ids are unavailable. This is an
additional earlier cohort under the same engine, not proof of one unchanged Fish submission.

The farming and tactical predictors were frozen before inspecting confirmation decisions.
Their hashes are in [farm-freeze.json](farm-freeze.json) and
[tactical-freeze.json](tactical-freeze.json). The holder model was frozen **after** the
farm/stun/Prism confirmation results were inspected, but before extracting confirmation
holder observations. Its second-cohort result is labeled exploratory replication, not a
fully untouched holdout; see [holder-freeze.json](holder-freeze.json).

Inputs are the actor's own saved perspectives and its earlier basic attacks. Static map
camp groups are rebuilt by coordinates, mirroring and cardinal connectivity, rather than
assuming canonical map indices are live replay ids. Altar-lock state was additionally read
through the actor's API at adjacent altars, checking cached position, health, gems and channel
against the raw pre-decision snapshot. No hidden opponent state is fed to a predictor.

The independent raw replay audit checks **1,300,367 inputs and 505,474 completed turns** in
96 games, exactly matching the new cache; see [confirmation-audit.json](confirmation-audit.json).
Counts below measure agreement across correlated turns, not independent statistical trials.
Per-game counts and every failed prediction are saved in the result/error artifacts.

## 1. Camp attacks: persistence, then low health and coordinate ties

At an observed basic attack, when visible living camps are in basic range and no visible enemy
champion is in basic range:

```text
previous_group = group of this actor's most recent basic attack on a visible camp
                 (all earlier such basic attacks, including when enemies were present)
if previous_group has a candidate in current basic range:
    restrict candidates to previous_group
choose minimum (camp health, y coordinate, x coordinate, camp id)
```

The memory is separate per actor and starts empty. This fitted model keeps it across death,
recall and long gaps; it does not claim Fish uses that implementation. No earlier spell or
ally attack is used to update this memory. If the previous group is unavailable, the model
falls back to minimum health across the currently available camps.

| Exact target prediction | Discovery | Confirmation |
| --- | ---: | ---: |
| All eligible basic attacks | 132,809 / 134,032 (99.09%) | 106,606 / 107,825 (98.87%) |
| Multiple camp targets | 22,571 / 23,789 (94.88%) | **19,440 / 20,646 (94.16%)** |
| Multiple targets within one group | 18,996 / 19,882 (95.54%) | 15,032 / 15,709 (95.69%) |
| Multiple groups: exact target | 3,575 / 3,907 (91.50%) | 4,408 / 4,937 (89.28%) |
| Multiple groups: group only | 3,585 / 3,907 (91.76%) | 4,459 / 4,937 (90.32%) |

The informative persistence test has multiple groups available **and** the previous group
still available. Fish attacks that group in **3,387/3,453 discovery** and
**4,170/4,286 confirmation cases (97.29%)**, spread over 61 confirmation games. The remaining
116 confirmation choices are retained as counterexamples. When the previous group is
unavailable, the fallback chooses the group correctly in only **289/651 (44.39%)**.
This recovers persistence much better than selection of a new group.

On the same 20,646 confirmation multi-target inputs, lowest health with an id tie-break gets
16,162 (78.28%), and lowest health with a `(y,x)` tie-break gets 16,992 (82.30%). Thus both the
coordinate tie-break and group memory matter. Per-game mean multi-target accuracy is 93.89%
over 95 games, close to the pooled result.

These are **target predictions conditional on an attack**, not an attack/move policy or a
farm-route planner. Attacks that target something other than a candidate camp remain errors. Fish also makes
ordinary basic attacks on altar tiles (539 discovery, 537 confirmation), so it does remove altar locks.

## 2. Cassi's pure stun: prioritize Strength

For Cassi's slot-1 stun, among visible enemies within 4:

```text
exclude Marcella
exclude an enemy with a stun buff whose timer is positive
choose greatest current Strength, breaking ties by lower champion id
```

A zero-timer stun buff is not excluded: it can remain visible after the enemy has already
lost its turn. The model abstains if no candidate remains. This is a target model for an
observed cast, not a prediction of when to stun.

| Exact target prediction | Discovery | Confirmation |
| --- | ---: | ---: |
| At least one eligible enemy | 1,056 / 1,070 | 1,076 / 1,088 |
| Multiple visible enemies before filtering | 209 / 223 (93.72%) | 242 / 253 (95.65%) |
| Multiple eligible enemies after filtering | **117 / 131 (89.31%)** | **147 / 158 (93.04%)** |

The last row is the meaningful choice subset; it spans 50 confirmation games. Lowest raw
health among all visible candidates gets only 127/253 on the middle confirmation row.
The proposed rule remains approximate. Example failure: `4e46c36a68962046`, r192, actor 2,
step 31787: it stuns Heart of Ruin rather than the higher-Strength Issac in range.

Do not generalize this to damage spells. In discovery, minimum effective health gets only
104/130 multi-enemy Cassi damage casts and 337/432 Marcella damage casts. Their target
policies remain open; further tuning those simple scores was deferred.

## 3. Capture holders: a useful partial ordering

Discovery pairwise departures suggest this ordering over well-represented types:

```text
Marcella > Vesper Vale > Vendetta > Heart of Ruin > Cassi > Issac > Willow
```

The narrow predictor says **stay on the group** when self is highest in this ordering among
self and the other currently visible allied holders. It abstains when self is lower or any
holder's type is unsupported. Prism, Ren and Varg are not assigned ranks from their sparse
observations. This is an empirical ordering, not a proven source constant or reward formula.

Sampled opportunities start on an empty group (`state == 2`), with another visible ally
already standing on the same group's camp tiles, no visible enemies at turn start, self
alive and unstunned, no active tribute/teleport, and a completed turn. A prepared recall is
allowed. The outcome is whether self ends the turn on any tile of that group. It does not
use the eventual recipient or future ally movements as features.

| | Discovery | Later exploratory replication |
| --- | ---: | ---: |
| Sampled opportunities | 4,874 | 4,366 |
| Predicted stay | 1,595 | 1,535 |
| Correct | 1,585 (99.37%) | **1,519 (98.96%)** |
| Coverage | 32.72% | 35.16% |
| Always-stay baseline on all sampled opportunities | 3,068 (62.95%) | 2,831 (64.84%) |

Marcella stays in 418/418 predicted discovery cases and 321/322 replication cases. All ten
discovery prediction errors are Vendetta; replication has sixteen errors across several
types. Results and the pairwise stay/leave matrices are in
[holders-discovery.json](holders-discovery.json) and
[holders-replication.json](holders-replication.json).

**The reverse implication is unsupported.** A lower-ranked holder often remains temporarily.
For example, in discovery Issac leaves when paired with Cassi in 62/94 cases, whereas Cassi
leaves when paired with Issac in 0/46. The ordering does not explain departure timing,
blocked escape tiles, future arrivals, capture countdowns or why holders sometimes share.
It also does not yet model who travels to take over a capture.

## 4. Banking: Prism's winning-deposit hypothesis is close, but not exact

The frozen necessary-condition hypothesis was:

```text
self gems + team score + gems of visible allies already tributing >= 1000
```

All **33 discovery Prism tribute starts** satisfy it (six games). One would fail if the ally
term were omitted: `2b8186f4ea2fa71f`, r512, actor 1 has 561 gems and team score 408, while a
visible ally is tributing 84. This makes the hypothesis more specific than a fixed bag size.

Confirmation has **21/22 compatible starts**, across just three games. The counterexample is
`2f0390ba522dd27e`, r691, actor 4, step 74870: Prism starts with 668 gems and score 305, totaling
973. A visible Marcella carries 42 but is recalling, not tributing. This **refutes the exact
necessary condition as written**. Counting other allied bags is a possible next hypothesis;
it was not retrofitted into the frozen model or reported as independently confirmed.

The gate is also insufficient: treating it as the whole start/no-start policy gets only
42/63 discovery and 26/46 confirmation adjacent-altar frames correct. Prism often declines
while the total is sufficient. Its safety, combat and other action priorities remain open.
Repeated interrupted channels contribute many observations, so this is a small number of
independent episodes despite dozens of starts.

For the other types, even quiet, unlocked adjacent-altar frames contain both small-bag starts
and much larger bags declined. Discovery Marcella starts at 4 gems but declines at up to
208; Vendetta starts at 4 and declines at up to 147. A fixed gem threshold is insufficient.
The exhaustive integer threshold sweep, per type, is in
[breadth-exploration.json](breadth-exploration.json).

The banking frame is sampled before the first Submit input, otherwise before the last
Recall input, otherwise at turn end. It requires positive gems, no active channel/stun, an
unused tribute start, an adjacent altar and normal turn completion. It does **not** label
the earlier choice to depart for an altar. All 2,845 discovery Submit inputs in these frames
start a tribute channel; the supplemental lock check keeps enemy lock interactions separate.
There are 356/385 discovery/confirmation frames with all adjacent altars enemy-locked and
no Submit input. Some have already spent their attack, so these counts alone do not establish
a deliberate refusal of a legal lock attack. Only **one frame in each cohort** still has its
basic attack ready: almost all of the apparent refusals are mechanically uninformative.
Ordinary Attack inputs at altars show lock removal is a separate behavior.

## 5. Recall and opening destinations: avoid misleading labels and weak fits

The user clarified the reason for the repeated recall starts: Fish prepares recall after its
other work, saving one turn if it decides to continue next turn, and cancels otherwise.
The data agree: all **504,415 sampled eligible discovery endpoints** start recall. Eligibility
is alive, unstunned, off spawn, no active channel, recall not already started this turn, normal
turn completion; the state is immediately before a recorded recall or at turn end otherwise.
This result is evidence for the preparation pattern, not a health/gold retreat threshold.

`commitments.py` instead samples the next turn when a prepared channel survives. It records
434,104 unstunned completed-turn choices, of which 16,651 keep the channel for that turn.
Even keeping it for one turn is not a commitment to return home: `a01c1f9f1c54417d`, Willow
actor 5 at r80, waits one turn at full health and zero gold, then cancels at r81 and attacks a
camp. The same happens for Issac in `81e3a65896b028a3`, r156–157. A retreat study needs channel
outcomes or episodes, and a predictor using only their initial information. Simple HP/gold
thresholds on recall starts or single continued turns would mix different behaviors.

For first farming destinations, label each actor's first unambiguous camp-directed attack
or damaging/stunning spell, within 60 rounds and before any enemy appears in its recorded
perspectives. This leaves 584 discovery and 453 confirmation labels. Unobserved intermediate
sightings and first incidental hits can still obscure intent. Candidate features come from
the actor's first turn and the static public map: initial group HP/rewards and eight-neighbor
walking distance to an adjacent tile. Walls, holes, altars, all initial camps and enemy spawn
block this baseline; allies, dashes, range and later clears are not modeled.

| Opening destination baseline | Discovery | Confirmation |
| --- | ---: | ---: |
| Nearest by static walking distance | 244/584 (41.78%) | 166/453 (36.64%) |
| Maximize `(gold + 0.5*gems)/(1 + walk + group_hp/100)` | 306/584 (52.40%) | 224/453 (49.45%) |

This is a failed reconstruction of destination choice, not a recovered farm score. Do not
port these fitted coefficients into astraeus. The meaningful next experiment is a clean
post-capture departure episode with visible/remembered candidate availability and teammate
involvement, rather than more tuning of this opening baseline.

## Reproduction and artifacts

The original extractor, predictors, manifest and original result files are preserved.
New scripts use the existing raw caches; `replays/` caches remain gitignored.

```sh
# Re-pin the separate cohort and check its farm-model hash (already done).
python3 tools/fish/pin_confirmation.py
node tools/fish/extract.mjs research/fish-2026-11-05/confirmation-manifest.json replays/fish-confirm all

# Discovery observations; use confirmation-manifest / fish-confirm for the second cohort.
python3 tools/fish/breadth.py research/fish-2026-11-05/manifest.json replays/fish-model replays/fish-model/breadth-v2.json.gz
node tools/fish/altar_context.mjs research/fish-2026-11-05/manifest.json replays/fish-model replays/fish-altars
python3 tools/fish/evaluate_breadth.py replays/fish-model/breadth-v2.json.gz /tmp/fish-discovery.json --altar-cache replays/fish-altars
python3 tools/fish/summarize_breadth.py replays/fish-model/breadth-v2.json.gz /tmp/fish-exploration.json --altar-cache replays/fish-altars

python3 tools/fish/commitments.py research/fish-2026-11-05/manifest.json replays/fish-model replays/fish-model/commitments.json.gz
python3 tools/fish/holders.py research/fish-2026-11-05/manifest.json replays/fish-model replays/fish-model/holders.json.gz
python3 tools/fish/evaluate_holders.py replays/fish-model/holders.json.gz /tmp/fish-holders.json

node tools/fish/audit.mjs research/fish-2026-11-05/confirmation-manifest.json replays/fish-confirm
python3 tools/fish/show_turn.py 2f0390ba522dd27e 691 4 --cache replays/fish-confirm
```

[Discovery metrics](breadth-discovery.json), [confirmation metrics](breadth-confirmation.json),
and sibling `*.errors.json.gz` preserve every failed prediction, including weak baselines.
The holder results have their own error files. Frozen model hashes still match. Python
compilation and Node syntax checks pass. The raw-input audit and pre-altar snapshot checks
pass. No bot build or A/B was required because no bot source changed.

The confirmation corpus is now inspected data. A later tuned model needs another untouched
cohort for independent confirmation. Prioritize new destination choice, holder-departure
timing, completed recall episodes and combat/retreat triggers over squeezing the remaining
few percent out of the camp-target and stun-target models.
