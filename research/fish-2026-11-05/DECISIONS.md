# Fish: new destinations, holder departures and action decisions

Later work: [route memory, incoming entry and earlier economic trips](ROUTES.md), with a
fourth untouched cohort of 46 games. The frozen results below are preserved.

This continuation adds executable **approximate action predictors**, tested on 43 genuinely
untouched games. It does not recover an exact retreat or destination policy. The useful gains
are a final-turn recall classifier, a lower-ranked holder departure classifier, and attack /
heal / damage-cast decisions. New camp destinations remain weak, including after spawn.
The earlier priority, targeting and holder-order models/results are preserved.

## Cohort and causal inputs

The original 124 games supplied fitting data. Both those games and the earlier 96-game cohort
were already inspected; neither is presented as fresh confirmation here. Downloading the
latest 16 Fish groups produced 80 files. Removing known groups and duplicate replay hashes
against **both** old cohorts left **43 games in nine groups**, pinned in
[third-manifest.json](third-manifest.json). They were created November 5, **12:20–13:40 ET**.
Two groups contribute four games after deduplication; seven contribute five. There are seven
opponents. Submission versions remain unavailable, so unchanged Fish source is not established.

[decision-freeze.json](decision-freeze.json) records predictor, fitted-tree and feature-code
hashes **before decoding any third-cohort play**. No model was refitted after confirmation.
The third cohort is now inspected data and cannot serve as a fresh holdout next time.

All 43 use replay engine `v3_0_0`. Both ordered drafts match their match metadata in 43/43
games. The independent raw audit accounts for **513,726 inputs and 199,550 completed turns**,
exactly matching extraction. [decision-audit.json](decision-audit.json) verifies frozen
hashes, disjoint hashes/match ids, known group ids, drafts, and every observation's actor,
step and self-state against its cached start perspective. The previous 96-game source lacks
group ids; its byte and match-id overlaps are nevertheless removed.

Predictors accept only `x`, a turn-start feature dictionary, and frozen fitted parameters.
Labels are separate `y` dictionaries. Camp memory is per actor, updated only from that actor's
earlier recorded perspectives and the current start. Public static map connectivity is used
to reconcile live camp-group ids; no future camp state enters memory. An unseen group's last
observed respawn countdown can be advanced by elapsed rounds, but this does not prove it has
respawned: occupation may postpone it. Unobserved groups retain public map stats and unknown
state. Teammates' hidden positions, future damage and eventual rewards are never inputs.

Sampling requires alive, unstunned, normally completed turns, excluding active tribute and
teleport. A prepared recall is allowed: cancelling it is itself a policy choice. Reported
coverage is within the stated sampled opportunities, **not all bot turns**. Turns are
correlated; per-game counts and means are saved, without treating each turn as an independent
statistical trial. Some map/opponent combinations recur despite disjoint game bytes/groups.

## 1. Choosing a new camp: still unresolved

Destination episodes begin at either:

- A payout observed while the actor was holding the same tile: its previous end perspective
  had an empty group and its current start has that group respawning.
- The first actionable spawn turn after returning/respawning. Openings are extracted for
  accounting but excluded from the new-destination model fitting and scores below.

The outcome is the next unambiguous camp-directed attack/spell, or occupation of a different
empty group, within 40 rounds. Enemy sightings anywhere in the included recorded turns,
tribute attempts, death, a return to spawn after departure, timeout and ambiguous hits are
censoring outcomes. Later events are used **only to label/censor**, never to score candidates.
This selects clean observed trips; it is not a classifier for whether to farm rather than
bank, fight or recall, and an incidental first hit can differ from intended destination.

There are **1,827 clean labels / 3,765 non-opening episodes (48.53%)** in confirmation:
619/1,793 after payout, 1,208/1,972 after spawn. Every scored map offers multiple static groups.
The main competing baseline minimizes:

```text
max(walking_distance_to_group, remembered_respawn_rounds_remaining)
```

Walking uses eight-neighbor BFS, static walls/holes/altars/enemy spawn, and currently visible
living camps as blockers. It approaches an adjacent tile for live/unknown groups or a camp
tile for known empty/respawning groups. It ignores dashes, range, allied occupancy and future
clears. Ties use the reconstructed static group id, not a claimed Fish tie-break.

| Exact group prediction | Discovery | Untouched confirmation | Confirmation nearest-new baseline |
| --- | ---: | ---: | ---: |
| Travel plus respawn wait, after payout | 965/1,580 (61.08%) | **352/619 (56.87%)** | 278/619 (44.91%) |
| Travel plus respawn wait, after spawn | 1,270/2,980 (42.62%) | **492/1,208 (40.73%)** | 330/1,208 (27.32%) |
| Combined | 2,235/4,560 (49.01%) | **844/1,827 (46.20%)** | 608/1,827 (33.28%) |

Nearest-new excludes the actor's current group, avoiding a trivial baseline that selects
the just-paid-out group at distance zero. The wait baseline considers all groups, including
that group with its newly observed respawn timer. No scored label returns to the same group.

A 54-combination reward-rate sweep selected this discovery surrogate:

```text
(group_gold + 0.25 * group_gems) /
(4 + max(walk, respawn_wait) + group_hp / (200 * (1 + 3 * nearby_visible_allies)))
```

The fighting term is zero for a known empty group. “Nearby” means within three of a camp
tile. Static full group HP is used otherwise. This gets only **714/1,827 (39.08%)** in
confirmation, worse than the wait baseline. The coefficients are failed fitted parameters,
not a recovered scoring formula or a port recommendation. Full sweep results are retained.

Concrete failure: `72fe83115d197144`, r189 actor 0, predicts group 18 (walk 4, respawn 10),
but Fish next attacks group 19 (walk 19, remembered timer already expired), at r202. Discovery
also contains deliberately long waits: `a01c1f9f1c54417d`, r43 actor 0, next hits a previously
visited group at r81 despite an unknown group being closer under the wait baseline. Route
memory, assigned territory and evaluation of unexplored groups remain plausible missing
inputs; these examples do not identify which explanation is correct.

## 2. Lower-ranked capture holders: useful timing predictors, not a handoff policy

Use the previously frozen holder ordering. New fitting is restricted to actors with a
**higher-ranked visible ally already on that empty group's tiles**, no visible enemies, and
all holders' types supported by the ordering. The label is leaving the group by turn end;
walking inside a large group still counts as staying.

A depth-three tree simplifies exactly to:

```text
self_timer = remaining recall timer, or 0 if not recalling
best_timer = timer of the highest-ranked visible allied holder, or 0 if not recalling
r = self_hp / self_max_hp

if best_timer > 3:
    leave = r > 0.40594059405940597
else:
    leave = self_timer > 3 and apparent_free_exits > 3
```

An exit is an in-bounds adjacent tile outside the group, unblocked by public terrain or a
currently visible unit. Hidden blockers and walking direction are not modeled. These are
empirical split points, **not recovered source constants**. Timer 1–3 does not necessarily
mean the channel progressed: a Home emblem can shorten its original duration.

| | Discovery | Confirmation |
| --- | ---: | ---: |
| Lower-holder tree | 2,306/3,181 (72.49%) | **801/1,065 (75.21%)** |
| Always leave, same lower-holder cases | 1,767/3,181 | 638/1,065 (59.91%) |
| Both self and best holder recalling with timers 1–3: predict stay | 505/535 (94.39%) | **143/148 (96.62%)** |

The last partial predictor covers **13.90%** of confirmation lower-holder cases and spans
33 games. Its always-stay baseline is identical on that selected subset; the contribution is
the causal selector, not a more elaborate classifier within it. The full tree covers all
1,065 eligible lower holders, or 13.32% of 7,994 quiet empty-group holder observations.
Its errors are mostly premature departures: 219 predicted leaves actually stay; 45 predicted
stays actually leave. It does not select an incoming replacement.

With **no other visible holder**, Fish stays in 6,341/6,400 confirmation cases (99.08%). This
is a descriptive baseline, not proof of being the sole holder: unseen holders may exist.
The 59 departures refute an exact “never leave without a visible replacement” condition.

Failure of the timer selector: `f4cf29c1050629a8`, r130 actor 1, has self timer 3 and a
higher-ranked holder's timer in 1–3, but cancels and dashes off. All five such confirmation
failures are retained. Countdown alone and available exit count alone did not explain timing;
these negative discovery checks motivated the small joint predictor.

## 3. Recall: classify the last keep/cancel decision

Sample only surviving recall channels at **timer 1**, where Fish can either cancel now or
allow completion at its next turn start. This is a later decision, not a label on recall
starts or on one additional turn of waiting. The main label is the observed keep/cancel
action; actual next-turn arrival is a separate outcome.

The fitted tree simplifies exactly to this executable surrogate:

```text
r = self_hp / self_max_hp
if standing_on_visible_empty_group and capture_timer <= 4:
    keep = r <= 0.40594059405940597
else:
    keep = r <= 0.627 or self_gold > 28
```

It gets **2,692/3,432 (78.44%)**, versus always-cancel **1,779/3,432 (51.84%)**; discovery was
7,730/9,915 (77.96%). Per-game mean confirmation accuracy is 79.06%. These thresholds are
greedy training splits, not evidence that Fish contains those literals or that any one is
a necessary condition. The main failure is overpredicting completion: **684 false keeps**
versus **56 false cancels**.

Two simpler partial observations also transfer:

- On an empty group with health **above 40%**, predict cancel: **868/879 (98.75%)**, covering
  25.61% of final-turn opportunities, with 11 contrary keeps.
- Off an empty group with health **at most 40%**, predict keep: **536/570 (94.04%)**, covering
  16.61%, with 34 contrary cancels.

The constant baseline on each selected subset is the same prediction. These are approximate
conditional rules, not full retreat triggers. A champion can still cancel and immediately
restart recall; discovery `a01c1f9f1c54417d`, r558 actor 5 does exactly that at 31.4% health.
Confirmation `fb737a131b675f27`, r1123 actor 4 cancels at 23.6%.

Of the 1,653 confirmation keeps, **1,640 arrive**, 11 are interrupted before arrival, and two
are censored by match end. Predicting actual arrival with the same frozen model gives
2,679/3,430 (78.10%). This distinguishes intended completion from intervening events. It
still does not predict the earlier decision to walk away from danger or begin a homeward trip.

## 4. Taking actions, rather than selecting an observed action's target

These rows are selected from turn-start opportunities, including turns that decline the
action. The outcome is whether the action occurs during that turn. Moves, wards and casts
can change later range/vision, so start-state classifiers have a real information limitation.
They are marginal action predictors: melee champions can both attack and move, and a spell
does not generally exclude a basic attack.

| Turn-start opportunity / predictor | Confirmation | Relevant baseline |
| --- | ---: | ---: |
| Melee, enemy within 1, basic attack ready after any recall cancellation: predict an attack | **2,368/2,377 (99.62%)** | Always attack is this rule |
| Ranged, enemy in basic range: depth-three attack tree | **1,415/2,018 (70.12%)** | Always attack 1,176/2,018 (58.28%) |
| Willow heal ready, visible ally within 4: predict heal iff any is injured | **6,020/6,422 (93.74%)** | Never heal 4,759/6,422 (74.10%) |
| Same heal opportunities: depth-three tree | **6,046/6,422 (94.15%)** | Same baseline |
| Heal tree, injured ally already in range only | **1,584/1,855 (85.39%)** | Always heal 1,558/1,855 (83.99%) |
| Ready unit-damage/stun slot, visible camp/enemy within 4: depth-three cast tree | **5,877/7,630 (77.02%)** | Never cast that slot 4,758/7,630 (62.36%) |

All binary rows offer act/decline choices; unlike target-selection accuracy they are not
dominated by having only one possible target. The injured-only healing row is the more
informative check because fully healthy ally opportunities dominate the full table. Only
65 confirmation opportunities have a positive maximum ally injury of at most 20 HP; Fish
heals on **59/65** of them. Thus substantial missing health is not required, but “always heal
any injury” is not exact. The tree's modest 26-case improvement does not justify treating
its tiny learned injury threshold as a source constant.

Melee opportunities span 40 games and 54.08% of all sampled enemy-in-basic-range turns.
Discovery was 6,817/6,825. Attacking is also the first action among attack/move/cast/tribute
in 2,311/2,377 confirmation turns. The other 66 include movement or spells first and the nine
no-attack turns; this is not a universal attack-first ordering. Counterexample:
`fb737a131b675f27`, r804 actor 2 starts a teleport instead of attacking an adjacent enemy.

The ranged tree uses own health fraction, minimum target HP divided by own Strength/Focus,
visible enemy count and cooldowns. Its confirmation errors include 453 missed attacks and
150 false attack predictions. The cast tree chiefly uses the two ability cooldowns, own
health and enemy distance. It misses **1,389/2,872 actual casts**, despite its 77% overall
accuracy; it remains an incomplete approximation. Discovery includes Cassi, Marcella and
Prism damage-slot opportunities; confirmation contains **4,880 Cassi and 2,750 Marcella**
opportunities and does not independently test Prism. The declared eligibility also supports
Stellar and Tavi, without claiming evidence for unobserved types.

Heal failures expose sequencing: discovery `a01c1f9f1c54417d`, r147 actor 5 first moves into
range of an injured ally, then heals despite no injured ally initially within 4. Confirmation
`9f9b6bbb2cb1e9bb`, r395 actor 5 declines an available heal and uses its attack reset instead.
These are retained failures, not relabeled successes.

## Artifacts, reproduction and next work

Code: [decision_data.py](../../tools/fish/decision_data.py),
[decision_model.py](../../tools/fish/decision_model.py),
[fit_decisions.py](../../tools/fish/fit_decisions.py),
[evaluate_decisions.py](../../tools/fish/evaluate_decisions.py).
Fitted trees and the full grid are [decision-trees.json](decision-trees.json) and
[decision-trees.sweep.json](decision-trees.sweep.json). Every evaluated model's failure,
including the travel-plus-wait model, is in the sibling `decisions-*.errors.jsonl.gz`;
constant and nearest-new baseline agreement is retained as counts. Representative discovery/confirmation
failures are also retained in [decision-examples.json](decision-examples.json).
[Discovery results](decisions-discovery.json) and [confirmation results](decisions-confirmation.json)
include confusion matrices, coverage, per-game counts and means.

```sh
# Existing pinned inputs; extraction skips existing caches and verifies raw hashes.
node tools/fish/extract.mjs research/fish-2026-11-05/third-manifest.json replays/fish-third all
python3 tools/fish/decision_data.py research/fish-2026-11-05/third-manifest.json replays/fish-third /tmp/fish-decisions.jsonl.gz
python3 tools/fish/evaluate_decisions.py /tmp/fish-decisions.jsonl.gz research/fish-2026-11-05/decision-trees.json /tmp/fish-decisions-results.json
node tools/fish/audit.mjs research/fish-2026-11-05/third-manifest.json replays/fish-third
python3 tools/fish/audit_decisions.py research/fish-2026-11-05/third-manifest.json replays/fish-third /tmp/fish-decisions.jsonl.gz /tmp/fish-decision-audit.json
python3 tools/fish/show_turn.py fb737a131b675f27 804 2 --cache replays/fish-third

# Refit only on the old inspected discovery data, writing new output paths.
python3 tools/fish/fit_decisions.py replays/fish-model/decisions-v2.jsonl.gz /tmp/fish-trees.json
```

`decisions-v1.jsonl.gz` in the discovery cache was a temporary build with overly aggressive
spawn censoring. Use **v2**, as pinned by the final feature-code hash and recorded results.
The original raw extractor and all older frozen model hashes still match. Python compilation,
Node syntax, raw input accounting and metadata/start-state audits pass. No bot build or A/B
was needed: **no astraeus or other bot source was changed**.

The most useful next destination work is to reconstruct remembered routes/territory and
observed candidate availability, inspecting the saved post-payout and spawn failures before
fitting more reward coefficients. Incoming replacement selection and tribute/departure
choices remain open. Further independent models require another untouched cohort. Do not
spend the next pass polishing the remaining melee/heal errors or the old target models.
