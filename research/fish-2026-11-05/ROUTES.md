# Route memory, capture entry and earlier economic decisions

Continuation on November 5, 2026. No bot source changed. The earlier models, caches,
results and failures are preserved. The strongest new transferable observation is that
the existing holder ordering also predicts **incoming capture entry**, approximately.
Destination memory helps little, and neither an exact replacement policy nor an earlier
tactical retreat rule has been recovered.

## Evidence and independence

The 124-, 96- and 43-game cohorts were already inspected. This pass fits on the original
124 games, uses the 43 games only as exploratory replication, and confirms on **46 untouched
games in ten new match groups**, pinned in [fourth-manifest.json](fourth-manifest.json).
They were created November 5, **15:10–16:40 ET**. The ten newest available downloaded groups
would supply 50 games; four replay hashes already occurred in inspected data and were removed.
Known group ids, match ids and hashes are disjoint from all three earlier cohorts. The
96-game manifest lacks group ids. Recurring maps/opponents and unknown submission versions
still limit independence and version attribution.

[routes-freeze.json](routes-freeze.json) pins feature code, predictors, fitted parameters
and manifest **before any fourth-cohort play was decoded**. No predictive model was changed
after confirmation. All 46 replays use `v3_0_0`; both ordered drafts match metadata in every
game. [fourth-audit.json](fourth-audit.json) independently accounts for **582,762 inputs and
228,085 completed turns** exactly. [routes-audit.json](routes-audit.json) verifies frozen
hashes, provenance bounds, visible holders and self-state for every observation.

The endpoint audit near the end of this report was added **after** confirmation failures
were inspected. Its changed outcome definition is retrospective, not another independent
confirmation. The frozen entry predictions remain unchanged.

## 1. New camps: modest memory gain, no recovered route policy

These are the same post-payout and post-spawn destination episodes defined in
[DECISIONS.md](DECISIONS.md), with causal actor-local history added. Opening episodes are
retained but excluded from fitting and scores. Of 3,824 non-opening opportunities, only
**1,726 (45.14%)** yield the clean next-camp label within 40 rounds. Enemy sightings,
tribute attempts, home returns, death and timeout censor the camp prediction.

History records previous camp-directed hits and occupation of an empty camp, collapsing
consecutive visits to the same group. Transitions are counted between distinct visited
groups; returning to spawn resets the route origin to a spawn token. This uses only the
actor's earlier recorded perspectives, never teammates' hidden histories or future labels.
The public territory feature is the minimum Chebyshev distance from the group to own spawn
minus that to enemy spawn. Recent allied occupation means this actor previously saw an
ally on a camp tile, not that the ally is still there. Gaps in intermediate perspectives,
unobserved shared-buffer data, and stale respawn timers remain limitations.

The selected 192-combination discovery grid minimizes:

```text
max(walk, remembered_respawn_wait)
  + 4 * never_previously_visited_by_actor
  + 0.25 * max(0, own_spawn_distance - enemy_spawn_distance)
  - 4 * previously_observed_transition_from_this_origin
  + 8 * ally_seen_on_this_group_within_previous_10_rounds
```

Ties use reconstructed static group id. These are fitted coefficients, **not source
constants**. The full grid is retained in [routes-trees.sweep.json](routes-trees.sweep.json).
Walking and respawn estimates inherit the earlier model's limitations, including no dash
model and potentially postponed respawns under occupation.

| Camp prediction | 124-game discovery | 43-game used replication | 46-game untouched confirmation |
| --- | ---: | ---: | ---: |
| Travel plus respawn wait | 2,235/4,560 (49.01%) | 844/1,827 (46.20%) | **823/1,726 (47.68%)** |
| Fitted memory/territory score | 2,371/4,560 (52.00%) | 921/1,827 (50.41%) | **847/1,726 (49.07%)** |
| Restrict to previously visited groups, then wait score | 2,105/4,560 | 765/1,827 | **735/1,726 (42.58%)** |
| Most frequent prior transition, then wait score | 1,985/4,560 | 744/1,827 | **726/1,726 (42.06%)** |

Confirmation also retains the weaker home-side restriction (797/1,726) and known-group
restriction (831/1,726). After payout the fitted score **loses** to the wait baseline:
370/608 versus 373/608. After spawn it gets 477/1,118 versus 450/1,118. The combined gain is
only 24 episodes; a paired ten-group bootstrap gives a descriptive 95% interval of
**−0.82 to +3.55 percentage points**. It is not strong evidence for porting this score.

The motivating old failure remains: `72fe83115d197144`, r189 actor 0. All four inspected
ready/visited/repeat/fitted predictors select group 18; Fish goes to group 19. Both were
visited twice. No prior transition from this origin has been observed. Group 18 has walk 4,
respawn wait 10 and an ally sighting one round ago; group 19 has walk 19, expired remembered
timer and no recent ally sighting. The fitted costs are 18 and 19 respectively. Do not adjust
the coefficient to repair this example. It suggests investigating remembered teammate
occupation/route assignment and respawn availability, rather than assuming a repeated route
has already been identified.

## 2. Incoming capture entry: holder rank transfers, with important label limits

Sample an alive, unstunned actor on a normally completed turn, outside a visible empty
group, with at least one apparently free adjacent camp tile and a visible allied holder.
There must be no visible enemies and all participating types must belong to the previously
frozen holder order:

```text
Marcella > Vesper > Vendetta > Heart of Ruin > Cassi > Issac > Willow
```

Each actor/group opportunity includes decline cases. A hidden blocker can still prevent
entry. The main outcome is occupation of that group at this turn's end. A second,
initially named `settled`, is entry followed by either an observed payout while still on
the group at the next start or occupation at the next turn's end. It is only a **two-turn
occupation proxy**: it does not establish a replacement, or even a stationary holder.

The simple predictor enters iff self outranks the best visible current holder. Both fitted
trees reduce to that rule with one exception: predict no entry when the group's capture
timer is at most 1 and own gold is at most 12. Those latter splits are fitted, not recovered
constants, and add almost nothing on new games.

| Confirmation outcome | Frozen tree | Rank alone | Always decline |
| --- | ---: | ---: | ---: |
| Enters by this turn end | **1,476/1,749 (84.39%)** | 1,475/1,749 | 1,264/1,749 (72.27%) |
| Two-turn occupation proxy | **1,541/1,747 (88.21%)** | 1,536/1,747 | 1,339/1,747 (76.65%) |

Two proxy labels are censored. Of 485 actual entries, the entry tree recognizes 273 and
misses 212; it also predicts 61 nonexistent entries. For the two-turn proxy, it recognizes
268/408 positives, with 66 false positives. Among actual entrants with noncensored proxy
labels, accuracy is only **338/483 (69.98%)**. Whole-opportunity accuracy is materially
helped by the many declines. Neither tree's improvement over rank alone survives even the
descriptive small-group bootstrap. Discovery and used replication results are retained.

Counterexamples inspected in raw actor traces:

- `d3e831065afbc6a8`, r7 actor 5: Cassi enters a group already held by higher-ranked
  Marcella. It crosses another camp tile next turn and leaves on r9. Both entry and the
  two-turn proxy are true, but calling this a replacement would be unjustified.
- `0a7fd1459279abea`, r105 actor 7: Vendetta outranks the visible HoR holder but dashes
  and walks away toward an altar instead. Entry and the two-turn proxy are both false.
- Old used example `72fe83115d197144`, r93 actor 1 enters despite a higher-ranked Vesper
  holder, then is outside the group by r95. Rank is a useful preference, not a prohibition.

The separate [incoming-payout-audit.json](incoming-payout-audit.json) follows entry through
up to eight later rounds, requiring continuous observed occupation until the group's
respawning state is observed on the actor's camp tile. Leaving before observed payout is
negative. Arrival/death and missing-end/timeout cases are censored: a payout may precede
a recall arrival and be hidden in the next actor-start perspective. Its full outcome rows,
including contradictions of the two-turn proxy, are retained. This audit still does not
prove that an incumbent was replaced: the entrant can share the payout with that incumbent.

Of the 485 entries, **344 reach an observed payout**, 135 leave first and six are censored.
Including the 1,264 declines, the unchanged entry tree predicts this retrospective endpoint
in **1,580/1,743 (90.65%)** cases, rank alone in 1,569/1,743 (90.02%), versus never-paid
1,399/1,743 (80.26%). The tree detects 256/344 payouts, with 75 false positives. These
numbers make through-payout entry a promising next fixed endpoint to confirm on untouched
games; they do not upgrade the two-turn proxy's confirmation into confirmed replacements.

## 3. Earlier farm/home/tribute choices: useful forecast with weak payout discrimination

At the same payout/spawn decision starts, forecast the first event within 40 rounds:
another farm interaction, an actual home return, or a successful tribute start. Recall
starts and short continuations never count as home/retreat labels. A `Submit gems` input
counts as a tribute only if a stored later context shows channel type 2; a lock attempt is
separate. Enemy encounters before the endpoint, death and missing endpoints are censored.
Home return is checked before enemy visibility at that arrival; this accounts for 26 more
home endpoints than the older camp-label extraction, which censors those arrival sightings.

This yields **2,727/3,824 (71.31%)** clean non-opening trip outcomes. It predicts an eventual
economic endpoint, not an immediate mode switch or a tactical retreat trigger. Future
observations supply labels only; all predictor features are from the episode start.

The frozen pair of trees collapses to:

```text
if outside_spawn and gold > 59 and nearest_altar_Chebyshev_distance > 9:
    predict home
else if nearest_altar_distance <= 8 and gems > 7 and own_score > 75:
    predict tribute
else if nearest_altar_distance > 8 and minimum_camp_ready_time > 26 and gems > 4:
    predict tribute
else:
    predict farm
```

`minimum_camp_ready_time` is the minimum travel/respawn wait score. These are greedy split
points, not source thresholds. Confirmation is **1,951/2,727 (71.54%)**, versus always farm
1,726/2,727 (63.29%). The gain's descriptive paired-group interval is +4.56 to +12.23 points.
However, after payout it is only **800/1,441 (55.52%)**; after spawn it is **1,151/1,286
(89.50%)**, against always farm 1,118/1,286 (86.94%). Pooling those tasks hides much of the
remaining uncertainty.

The model recognizes 365/590 home endpoints and 220/411 tribute endpoints. It predicts
home incorrectly on 326 other trips, and tribute incorrectly on 155. In particular,
`0a7fd1459279abea`, r29 actor 6 has 36 gems, 90 gold, full health and altar distance 8;
the fitted low-score branch predicts farming. Marcella walks to the altar and successfully
starts tribute at r35. A second error, `617803df21349794`, r144 actor 5, predicts home
with 70 gold and altar distance 10, but Fish farms instead. Keep both rather than treating
the fitted gold or score splits as exact gates.

## 4. Earlier recall completion: rejected as a useful classifier

At recall **timer 4**, predict whether that same channel survives uncancelled to an actual
home arrival. There are 148,154 opportunities: 146,063 cancel, 1,848 arrive, 206 are
interrupted, 17 end in death and 20 are censored. This labels completed channels, not
prepared recall starts or one further idle turn. It also incorporates future interruptions
and therefore is not a direct label for the actor's intention.

The depth-three tree gets **146,293/148,134 (98.76%)**, versus always predicting no arrival
**146,286/148,134 (98.75%)**. It finds just **21/1,848 actual arrivals (1.14%)** and has
14 false positives. Its impressive-looking accuracy is essentially the negative baseline.
The sole positive branch is empty-group capture timer <=3, gold <=46 and health ratio
<=0.3668412534652218; this is a failed training surrogate, not a useful retreat rule.

`d3e831065afbc6a8`, r28 actor 3 recalls uninterrupted at 90% health with 42 gold and arrives
on r32, then shops. Conversely, `e23ed5323ea122e8`, r248 actor 6 keeps the low-health recall
for several turns but is interrupted before arrival. Both failures are retained. The next
earlier-retreat analysis needs deliberate decision episodes and remembered threat/camp
availability; merely adding more prepared recall turns is dominated by routine cancellation.

## Reproduction and retained failures

New code: `routes_data.py`, `routes_model.py`, `fit_routes.py`, `evaluate_routes.py`,
`pin_routes.py`, `audit_routes.py`, `summarize_routes.py`, `audit_incoming_payout.py`, all in
`tools/fish/`. Fitted model: [routes-trees.json](routes-trees.json). Results:
[discovery](routes-discovery.json), [used replication](routes-replication.json),
[untouched confirmation](routes-confirmation.json). Each result has a sibling
`.errors.jsonl.gz` retaining **every failure of every evaluated model/baseline**, with
separate input `x` and outcome `y`. [routes-summary.json](routes-summary.json) contains paired
group intervals and representative fresh failures; `routes-examples-discovery.json` retains
earlier examples. All metrics include per-game counts.

```sh
node tools/fish/extract.mjs research/fish-2026-11-05/fourth-manifest.json replays/fish-fourth all
python3 tools/fish/decision_data.py research/fish-2026-11-05/fourth-manifest.json replays/fish-fourth /tmp/fish-fourth-decisions.jsonl.gz
python3 tools/fish/routes_data.py research/fish-2026-11-05/fourth-manifest.json replays/fish-fourth /tmp/fish-fourth-decisions.jsonl.gz /tmp/fish-fourth-routes.jsonl.gz
python3 tools/fish/evaluate_routes.py /tmp/fish-fourth-routes.jsonl.gz research/fish-2026-11-05/routes-trees.json /tmp/fish-fourth-results.json
python3 tools/fish/audit_routes.py research/fish-2026-11-05/fourth-manifest.json replays/fish-fourth /tmp/fish-fourth-routes.jsonl.gz /tmp/fish-fourth-audit.json
node tools/fish/audit.mjs research/fish-2026-11-05/fourth-manifest.json replays/fish-fourth
python3 tools/fish/audit_incoming_payout.py research/fish-2026-11-05/fourth-manifest.json replays/fish-fourth /tmp/fish-fourth-routes.jsonl.gz research/fish-2026-11-05/routes-trees.json /tmp/fish-payout-audit.json
```

Use new output paths: the new scripts refuse to overwrite evidence. Final observations are
`routes-v3.jsonl.gz` in `replays/fish-model`, `fish-third` and `fish-fourth`. The incomplete
v1/v2 route files are retained diagnostic failures, not datasets: dead champions lacked
coordinates, first at turn start and then following death during a turn. The v3 pass guards
both. `fourth-candidates.json` records the unsuccessful initial requirement for ten wholly
novel five-game groups; v2 allows partial groups after byte deduplication. The downloader
was stopped after the fixed cohort was available; extra downloaded games were not decoded
by this investigation. Freeze the exact uninspected subset before using any as a new test.

All four evaluated cohorts are now inspected. Continue with causal teammate occupation and
availability, entry through actual payout versus transient crossings, and earlier economic
departure opportunities. Do not tune the current coefficients on these confirmation errors
and claim a new independent result. Established targeting rules were not modified.

## Audit: forced vs free decisions (2026-11-06)

Added after the fact by `tools/fish/farm3_audit.py` ([rule-audit-farm.json](rule-audit-farm.json));
the text above is unchanged.

- **New-camp route score** (`route/fitted`).
  - Forced rows (at most one feasible candidate: reachable, not the paid group,
    `max(walk, respawn) <= 40`): fourth 48/1,726 (2.8%), fifth 39/3,819 (1.0%).
  - Free rows: fourth 834/1,678 (49.70%) vs wait 48.27%; fifth 2,050/3,780 (54.23%) vs 52.25%.
  - Verdict: as weak as reported, not inflated.
- **Incoming entry** (fifth, 3,638 rows): no row is forced.
  - The rows already require a free adjacent camp tile, no stun, and channel none (121) or recall
    (3,517), which can be cancelled.
  - The figures stand: entry by turn end 3,033 (83.37%) vs never 2,622; through the next turn
    3,201/3,637 vs 2,805.
- **Economic trip forecast** (fifth, 6,259 rows).
  - Tribute is impossible with 0 gems (rules: tribute needs at least 1), so 2,042 rows are a
    two-way choice. The tree never predicts tribute there (3 tribute labels).
  - On the 4,217 three-way rows (gems >= 1): **2,665 (63.20%) vs always-farm 2,137 (50.68%)**.
  - On the 0-gem rows: 1,719 (84.18%) vs 1,682 (82.37%).
  - Verdict: the 70.04% headline holds; most of its gain is on rows where all three trips are
    possible.
- Not re-audited here: the timer-4 arrival classifier (already a failure) and the early-home
  counts.
