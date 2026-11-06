# Handoff: continue reverse-engineering Intercontinental Fish

## Latest: farming, engagement, micro and a forced-vs-free audit (2026-11-06, third subagent round)

[FARM3.md](FARM3.md), [ENGAGE.md](ENGAGE.md), [MICRO.md](MICRO.md). New untouched **seventh
cohort**: [seventh-manifest.json](seventh-manifest.json), 265 games / 56 groups, 21:40–23:40 UTC
November 5, pinned with [seventh-freeze.json](seventh-freeze.json) before decoding, audit exact
([seventh-audit.json](seventh-audit.json)); raw `replays/fish-seventh-raw`, cache `replays/fish-seventh`.
Each study froze its rules (`{farm3,engage,micro}-seventh-freeze.json`) before reading seventh play
and scored it once. All seven cohorts are now used; pin the next one with `pin_cohort.py`.

- **Camp choice uses team-shared camp memory.** Scoring farm2's features on the newest sighting by
  any earlier-acting teammate: seventh **63.11%** vs 60.69% own memory, 48.72% wait (54/56 groups).
  Observer truth adds nothing beyond it, so Fish knows what its team saw (presumably the 8 shared
  bytes), mostly respawn timers. Refuted: astraeus `rate()` closed form, per-map circuits, claims,
  deciding at payout, score lead. Openings are deterministic per map but unexplained.
- **No strategic engage mode.** At range 4–8 the step is momentum (70.8% free rows vs 54.5%); the
  farm route bends by danger (min-danger step 69%, 88% when hurt); camp hitting falls with enemy
  distance (96% none → 44% at 4 → 18% within 3). No pursuit beyond sight, no hunting, no rally by
  allies without sight. Walking retreat is a weak health tendency, homeward (89% vs 43% random).
- **No team targeting.** Basics go to min EHP (93.6% seventh); convergence is a by-product. The first
  capable actor kills (84–89%); holding a hit for a teammate < 1%. Ranged champions that walk pick a
  tile 3+ from melee (90%), but whether to walk is ~55%. Bushes are a path preference (73% vs 44%),
  not ambushes. Fish never drafts Ryth, Tavi or Stellar.
- **Forced-vs-free audit** (user request: do not rediscover game rules). Every rule was re-scored on
  rows where the alternative was legal (`rule-audit-{farm,engage,micro}.json`; appended "Audit"
  sections in COMBAT, TACTICS, DECISIONS, ECONOMY, TEAM, FARM-CHOICE, CHOICE, ROUTES). Downgraded:
  "damage spell / Prism / Ren cast iff still" (walking forbids it; free rows = always cast; the real
  choice, stand-and-cast vs walk, is 69% from turn start), Cassi's "unless" (always-stun is better),
  ward 10-round gap (the recharge), melee "beside the weakest" and Marcella's re-hit (target rule),
  TEAM 3a "stays in camp range" (76% forced; leaves ~half the time when one step suffices), TEAM 3d
  Willow (below a random step), walk-home iff ≤ 5 (= recall length), kill securing (98.5% → 84–89%).
  Real choices kept: positioning, kill override, chase, HoR shield, heal trigger, reset, spawn wait,
  targets, destinations (1–3% forced), camp target (94% on multi-target rows; 81% of camp attacks
  have one target).

Open: what Fish writes to shared memory; the opening's joint plan; whether to stand-and-cast or
walk; the healthy "spacing" retreat; why kill gold doesn't send Fish home; Prism/Ren stun targets.
**Before reporting any new rule, run the forced-vs-free split.**

## Latest: economy, turn order and tactics (2026-11-05, second subagent round)

[ECONOMY.md](ECONOMY.md), [TEAM.md](TEAM.md), [TACTICS.md](TACTICS.md); fit on the four oldest
cohorts, held out fifth+sixth. Headline rules: recall/home gate hp <= 0.63 or gold >= 30; walk home
iff <= 5 steps; priority = -rank - (N+1)*L with exact modes (contact sign = who starts next round);
the order steers tied camp hits; spell targets weigh gems; escape dash minimises danger. The user
asked to stop adapting the camp-target model (overfitting risk). Open: what seeds the "late" mode,
the small "early" mode, why only 44% of healthy actors with gold >= 30 go home, bushes and wards in
fights. All six cohorts are used; pin new games with `pin_cohort.py`.

## Latest: farm2 camp choice confirmed on a sixth cohort (2026-11-05)

[FARM-CHOICE.md](FARM-CHOICE.md) supersedes CHOICE.md's model: `farm2-fit-A.json` gets
**59.36%** of next camps on 53 untouched games (sixth-manifest.json, 11 groups) vs 54.43% for
the CHOICE logit and 44.67% wait; 11/11 groups. Use `farm2-fit.json` (all five earlier cohorts)
as the best current fit. Pin future cohorts with `tools/fish/pin_cohort.py NAME --raw DIR
--freeze FILES...`, which excludes every `*manifest.json` in this folder. Combat rules: COMBAT.md (checked on the sixth cohort). Shopping/locks/teleports/wards/openings:
MISC.md (note its spawn-bounds correction: cached `spawnA` maxima are exclusive).

## Latest choice/draft continuation (2026-11-05, after all sections below)

Read [CHOICE.md](CHOICE.md) and [DRAFTS-EMBLEMS.md](DRAFTS-EMBLEMS.md) first. No bot source
changed; all earlier artifacts are preserved and their hashes match.

- **Destinations:** a conditional-logit camp score (`choice_model.py`, frozen weights
  `choice-fit.json`) gets **61.56%** of next camps on 94 untouched games vs 52.42% wait baseline
  (payout 69.2%, spawn 56.8%; gain +6.0 to +12.2 points by group bootstrap). Fifth cohort:
  `fifth-manifest.json`, frozen by `choice-freeze.json` before decoding; caches in
  `replays/fish-fifth/` (`choice-v1.jsonl.gz` per cohort cache). It is now used data too.
- **Ruled out:** shared/draft memory is not in replays (`probe_shared.mjs`); Fish's stdout is
  never in bundles; observer-truth teammate positions add <=0.4 points; closer allies attract
  (no claim/assignment); labels are 92% real destinations.
- **Frozen ROUTES models confirmed on the fifth cohort:** entry through observed payout 89.75%
  (rank 88.62%, never 79.93%); trip forecast 70.0% vs 61.0%.
- **Drafts/emblems:** one pick order per map; per-champion emblem orders verified against engine
  statistics. Tables in `drafts-emblems.json`.

Next: post-spawn choice (57%) — unknown/long-unseen group estimates, crew requirements before
Elk/Golem, choosing at recall start. New confirmations need games after 21:10 UTC November 5
(`fetch_replays.py --team "Intercontinental Fish" --kind all --since ...`, dedupe against all
five manifests).

## Latest route/entry continuation (2026-11-05, after all sections below)

Read [ROUTES.md](ROUTES.md) first. New code and frozen evidence are separate; no bot source
or earlier predictor changed. All four evaluated cohorts are now inspected. The new
**46 games in ten groups**, November 5 **15:10–16:40 ET**, are pinned in
`fourth-manifest.json`; four duplicate replay hashes were removed from the planned 50.
`routes-freeze.json` predates decoding. Raw audit: **582,762 inputs / 228,085 completed
turns**, exact. All use `v3_0_0`, ordered drafts match metadata, submission versions unknown.

Findings and failures:

- Actor-local visits, previous transitions, public spawn territory and remembered allied
  occupation improve new camp prediction only to **847/1,726 (49.07%)**, vs travel/respawn
  wait **823/1,726 (47.68%)**. Paired group interval for gain: −0.82 to +3.55 points.
  After payout the fit loses 370/608 to 373/608; after spawn it improves 477/1,118 to 450/1,118.
  Hard visited-group restrictions and following the most frequent prior transition fail.
  The saved `72fe83115d197144` r189 actor 0 example still fails; group 18 has a recent ally
  sighting and group 19 does not. Do not tune one coefficient to fix that example.
- **Incoming entry** with a free adjacent camp tile and visible incumbent: highest holder
  rank predicts **1,475/1,749 (84.33%)**, fitted tree **1,476/1,749 (84.39%)**.
  Two-turn occupation proxy: rank **1,536/1,747**, tree **1,541/1,747 (88.21%)**.
  The tree differs only by declining at capture timer <=1 with own gold <=12; those are
  weak empirical splits, not source constants. This predicts entry, not confirmed replacement.
- **Label warning:** two-turn occupation can still be a transit across a large camp.
  `d3e831065afbc6a8` r7 actor 5 crosses two camp tiles and leaves r9. A retrospective audit
  added after confirmation follows entrants to payout: 344 paid, 135 left first, six censored.
  Unchanged tree gets **1,580/1,743 (90.65%)**, rank 1,569/1,743; this endpoint is **not**
  independently confirmed. It can include shared payouts, not just incumbent replacements.
  Freeze this longer endpoint before a future untouched test.
- **Earlier economic trip forecast:** farm/home/successful tribute **1,951/2,727 (71.54%)**,
  versus always farm 63.29%; post-payout only **800/1,441 (55.52%)**, post-spawn 89.50%.
  Labels require actual home arrival or successful tribute, not recall preparation. The
  gold/altar/score split formula is in ROUTES.md and remains an approximate forecast.
- **Timer-4 same-channel arrival classifier fails:** 98.76% vs always-no-arrival 98.75%,
  detecting only **21/1,848 arrivals**. Do not promote its accuracy or health split as a
  retreat rule. `d3e831065afbc6a8` r28 actor 3 returns at 90% health with 42 gold, then shops.

New scripts: `routes_data.py`, `routes_model.py`, `fit_routes.py`, `evaluate_routes.py`,
`pin_routes.py`, `audit_routes.py`, `summarize_routes.py`, `audit_incoming_payout.py` in
`tools/fish/`. Data are `routes-v3.jsonl.gz` in `fish-model`, `fish-third`, `fish-fourth`.
Raw fourth cache: `replays/fish-fourth/<SHA16>.json.gz`; old decision observations were also
built there as `decisions-v2.jsonl.gz`. Ignore incomplete route v1/v2 files (dead-coordinate
errors); retained for diagnosis. Do not overwrite any old cache or frozen artifact.

Artifacts: `routes-{discovery,replication,confirmation}.json`, every sibling error gzip,
`routes-trees.json`, full `.sweep.json`, `routes-summary.json`, `routes-audit.json`,
`fourth-audit.json`, `incoming-payout-audit.json` and its full `.rows.jsonl.gz`.
All old frozen model hashes still match. Downloader and analysis jobs finished/stopped.
Extra downloaded raw games outside the fourth manifest were not decoded in this pass;
check hashes, matches and groups against **all four manifests** before pinning any as new.

Next priorities: remembered teammate commitments/occupation and whether a candidate really
becomes available; incoming entry through payout versus transit and sharing; deliberate
economic departure episodes and causal threat memory. Preserve the timer-4 failure and do
not relabel recall starts or brief waiting as retreat. Avoid further targeting-rule polish.
Update EXPERIMENTS and these reports; leave bots and unrelated changes alone.

## Latest decision continuation (2026-11-05, after the continuation below)

Read [DECISIONS.md](DECISIONS.md) first. The investigation now includes actual action/no-action
opportunities, final-turn recall decisions and post-payout/spawn destination episodes. The
older reports, predictors, results and caches were preserved. No bot source changed.

New independent confirmation: **43 untouched games, nine match groups**, pinned in
`third-manifest.json`, created November 5 12:20–13:40 ET. Downloaded 80 games with the existing
fetch script into `replays/fish-third-raw`; removed known groups and hashes from both prior
cohorts. Code/model hashes were frozen in `decision-freeze.json` before decoding any new play.
All use `v3_0_0`; submission versions unavailable. Raw audit: **513,726 inputs / 199,550
completed turns**, exact. Both drafts match metadata in 43/43 games. All three cohorts are
now inspected; a fourth cohort is needed for a new independent confirmation.

Results worth carrying forward, with limits:

- New camp destinations remain unresolved. Minimize `max(walk, remembered respawn wait)`:
  **352/619 (56.87%) post-payout**, **492/1,208 (40.73%) after spawn**, vs nearest-new 44.91% /
  27.32%. Clean labels cover 1,827/3,765 non-opening episodes. Reward-rate grid fits fail
  (39.08% combined); do not port the fitted coefficients. Inspect route/territory and long-wait
  examples rather than sweeping more opening/reward formulas.
- Lower-holder departure tree: **801/1,065 (75.21%)**, vs always-leave 59.91%. It uses self and
  best current holder's recall timers, own health and apparently free adjacent exits. Most
  errors predict departure too early. The simple timer-1–3 stay selector gets **143/148**,
  13.90% lower-holder coverage. This does not select incoming replacements.
- Recall **timer 1** keep/cancel tree: **2,692/3,432 (78.44%)**, vs always-cancel 51.84%.
  On an empty group at >40% health, cancel in **868/879**; off an empty group at <=40%, keep
  in **536/570**. These are approximate conditions, not source constants or retreat labels.
  Of 1,653 keeps, 1,640 arrive, 11 are interrupted, two are censored. Recall starts and one
  further waiting turn remain invalid retreat labels; low-health cancel/restart examples exist.
- Melee with an enemy initially in basic range: attacks **2,368/2,377 (99.62%)**; nine
  exceptions include teleporting instead. Ranged attack tree: **1,415/2,018 (70.12%)**, vs
  always-attack 58.28%. These predict marginal actions, not a mutually exclusive whole turn.
- Willow heal ready / visible ally in range: any-injury heuristic **6,020/6,422 (93.74%)**;
  tree **6,046/6,422 (94.15%)**. Injured-only tree **1,584/1,855 (85.39%)**, vs always-heal
  83.99%; only a modest improvement there. Heals on 59/65 small-injury opportunities (<=20 HP).
- Damage-slot cast tree: **5,877/7,630 (77.02%)**, vs never-cast 62.36%, but misses 1,389 of
  2,872 actual casts. This is a weak surrogate, not a recovered spell policy.

New scripts: `tools/fish/{decision_data.py,decision_model.py,fit_decisions.py,
evaluate_decisions.py,pin_decisions.py,audit_decisions.py}`. `decision_model.py` accepts only
causal `x` features and the frozen tree JSON; outcomes are separate `y`. Raw new caches:
`replays/fish-third/<SHA16>.json.gz`. Observations: `decisions-v2.jsonl.gz` in `fish-model`
and `fish-third`. Ignore temporary discovery `decisions-v1.jsonl.gz` (spawn censoring bug,
fixed before freeze). The original `breadth-v2.json.gz` caches are separate and unchanged.

Artifacts: `decision-trees.json`, its `.sweep.json`, `decisions-{discovery,confirmation}.json`,
sibling `.errors.jsonl.gz` with every failure, `decision-examples.json`, `third-audit.json`,
`decision-audit.json`. All hashes and audits pass. Prior model hashes remain unchanged.
Report gives definitions, exact simplified surrogate formulas, coverage and reproduction.

Inspect e.g. `show_turn.py fb737a131b675f27 804 2 --cache replays/fish-third` (teleport rather
than melee attack), or `72fe83115d197144` r189 actor 0 (farther next farm despite a nearer
respawn). High-value open work: destination memory/territory, incoming capture replacements,
earlier retreat and tribute choices. Avoid refining the already strong targeting rules or
the last percent of melee/healing. All work remains uncommitted among unrelated changes.

## Latest continuation (2026-11-05)

Read [CONTINUATION.md](CONTINUATION.md) before the preserved original handoff below.
The user explicitly wants breadth and warned about diminishing returns. They also clarified
that recall is deliberately prepared after other actions, saving a turn if Fish continues it
next turn and otherwise cancelling it. A recall start is not a retreat label; even keeping it
for one further turn can just be waiting for a camp to respawn.

New findings and their limits:

- Farm basic attacks: retain the actor's previous attacked camp group when available, then
  minimum `(HP, y, x, id)`. Fresh-cohort multi-target accuracy **19,440/20,646 (94.16%)**.
  Group retention with multiple groups available: **4,170/4,286 (97.29%)**. New-group selection
  when the prior group is unavailable remains poor (**289/651**).
- Cassi slot-1 stun: exclude Marcella and positive-timer stuns, then greatest Strength,
  lower id on ties. Fresh-cohort meaningful-choice accuracy **147/158 (93.04%)**.
- Holder ordering: `Marcella > Vesper > Vendetta > HoR > Cassi > Issac > Willow`. A partial
  predictor says the highest-ranked current holder stays; abstain otherwise. **1,519/1,535**
  in the later exploratory replication, 35.16% coverage. Lower-ranked departure timing is
  unresolved. This model was frozen after other confirmation metrics were inspected, so its
  replication is not called a fully untouched holdout.
- Prism winning-deposit gate (`bag + score + visible allies already tributing >= 1000`):
  33/33 discovery starts, **21/22 confirmation**, so the exact necessary condition is refuted.
  Counterexample `2f0390ba522dd27e`, r691 actor 4: bag668 + score305, visible Marcella carries42
  but is recalling. Counting other allied bags is an untested next hypothesis.
- Opening nearest-camp and a simple reward/time score remain weak: **36.6% / 49.4%** in
  confirmation. Do not port their fitted coefficients or spend the next pass polishing them.

New cohort: `confirmation-manifest.json`, 96 unique replays from the 102 Fish entries in
`replays/bush-ladder/matches.tsv`, older November 4 evening ET post-patch games, same engine
`v3_0_0`. Match-group ids and submission versions are unavailable. Raw inputs are independently
accounted for: **1,300,367 inputs, 505,474 completed turns**. No downloads were needed.

New code: `tools/fish/{breadth.py,farm_model.py,tactical_model.py,evaluate_breadth.py,
altar_context.mjs,commitments.py,holders.py,holder_model.py,evaluate_holders.py,
summarize_breadth.py,pin_confirmation.py}`. `breadth.py` observations are in
`replays/fish-model/breadth-v2.json.gz` and `replays/fish-confirm/breadth-v2.json.gz`;
raw confirmation caches are in `replays/fish-confirm/<SHA16>.json.gz`. Altar supplements:
`replays/fish-altars/`, `replays/fish-confirm-altars/`. Holder observations are `holders.json.gz`
in each feature directory; discovery recall continuation observations are `commitments.json.gz`.
`breadth.json.gz` in the original cache is an earlier temporary feature version; use **v2**.

Research artifacts: `breadth-{discovery,confirmation}.json` and sibling error gzips,
`breadth-exploration.json`, `holders-{discovery,replication}.json` and sibling error gzips,
three `*-freeze.json` files, `confirmation-audit.json`. Frozen models match recorded hashes.
The original report/model/results were preserved. No astraeus or other bot source changed.
All work remains uncommitted; preserve unrelated workspace changes.

Both cohorts are now used data. For another independently confirmed model, pin a new cohort.
Most useful next work: post-capture destination episodes with actor memory/teammate context;
lower-ranked holder departure timing; recall completion/cancellation episodes; attack/move,
cast/no-cast and retreat triggers. Avoid tuning the last few percent of camp/stun targeting.

## Original handoff (preserved)

## User objective and scope

Reverse-engineer specific, reproducible movement, combat, farming and banking decisions from
Intercontinental Fish's ladder replays. The user wants numerical thresholds and models/code
that reproduce decisions given the information Fish had. General strategy descriptions are
insufficient. Predicting a camp destination, retreat decision or combat target is useful;
predicting every walking step is unnecessary. Draft and emblem selection are lower priority.
Starting with narrow behaviors is explicitly acceptable.

Continue the investigation, not just this handoff. No changes to astraeus were requested or
made. Do not assume the fitted imitation rules are improvements worth porting into our bot.

## Start here

1. Read the repository `AGENTS.md` and `cambc-rules.yaml`; acknowledge reading the Cambridge
   Battlecode rules as that guide requires. Rules override `docs/`.
2. Read [README.md](README.md), the complete findings, exact definitions and limitations.
3. Read [model.py](../../tools/fish/model.py), [features.py](../../tools/fish/features.py), and
   [extract.mjs](../../tools/fish/extract.mjs). They are small and explain what is actually measured.
4. Inspect a few counterexamples with `show_turn.py` before adding hypotheses.

Work from `/home/ubuntu/cambc-autumn`. The previous work is **not committed**. New work lives
in `tools/fish/` and `research/fish-2026-11-05/`; documentation was appended to
`tools/README.md` and `research/EXPERIMENTS.md`. The workspace already had many unrelated
modified/untracked files, including other bots and research. Preserve those changes.

## Existing data and artifacts

| Location | Contents |
| --- | --- |
| `replays/ladder-post/` | Current corpus: 125 Fish replay files dated November 5, 2026; 124 unique hashes |
| [manifest.json](manifest.json) | Original replay paths, SHA-256, match/group ids, date, side, opponent and fixed train/test split |
| `replays/fish-model/<SHA16>.json.gz` | Already extracted actor perspectives, turn boundaries and inputs for all 124 games |
| `replays/fish-model/train-features.json.gz` | Compact observations for 109 training games |
| `replays/fish-model/test-features.json.gz` | Compact observations for 15 original holdout games |
| [train-results.json](train-results.json), [test-results.json](test-results.json) | Exact metrics, per-game counts, model/rank-table hashes |
| `train-results.errors.json.gz`, `test-results.errors.json.gz` in this directory | Every failed prediction, its input features and exact game/round/actor/step |
| [priority-ranks.json](priority-ranks.json) | Learned rank tables for 11 observed roster sets |
| [coefficient-bounds.json](coefficient-bounds.json) | Identified interval for the carrying multiplier, conditional on the formula |
| [audit.json](audit.json) | Independent raw-input and completed-turn accounting |

The replay/cache directories are gitignored and local. Preserve the manifest and research
artifacts so the analysis remains attributable and reproducible. All current games use
replay engine `v3_0_0`, corresponding to cambc 5.0.0. Fish's submission version is absent from
metadata: do not assert that all games used an identical submission.

There are also 1,395 Fish replay files under `replays/ladder/`, dated October 29–30 and using
older rules. These were only explored initially and are **not** part of the reported corpus.
Do not pool their parameters with current behavior without checking for version changes.
An attempt to download more games failed because the sandbox could not resolve the ladder
host; the separate current cache was then discovered, so no new download was needed. The
fetch process was stopped. No investigation jobs were left running.

## Established results

### Priority: exact encoding within a limited output class

For an alive champion's small negative priority (`-100 < priority < 0`):

```text
N = allied body count, dead allies included; Cassi and Issac count separately
rank = roster-specific rank from priority-ranks.json, between 2 and N+1
h = min(1, (health + shield) / max_health)
if gems > 0: h *= 0.65
band = max(0, floor(4 * (1 - h)))
ordinary = -rank - (N+1) * band
observed_priority = ordinary - (N+1) * penalty
penalty ∈ {0, 5}
```

This accounts for **all 30,938 training and 4,624 holdout small negative writes**, with no
numerical exceptions. However, selecting these observations by their output does **not**
establish a complete predictive policy. The condition selecting penalty 5 remains unknown,
as do large signed and small positive priority modes.

`0.65` fits, but is not proven to be their source literal. Under this floor formula, the
training data constrain it to approximately `(0.649350649, 0.65]`. Bag size acts as zero/nonzero
in this encoding, not a proportional penalty. Shield is included, and the health ratio is
capped at 1 **before** multiplying for carrying.

The prospective quiet predictor abstains unless alive, unstunned, known roster, and no enemy
visible at turn start or just before the priority write. It then predicts `ordinary`:

- Training: **13,818 / 13,901 (99.40%)**, covering 20.50% of all priority writes.
- Holdout: **2,902 / 2,919 (99.42%)**, covering 32.95% of writes.
- Four holdout maps absent from training: **535 / 539**.
- The 17 holdout errors are one large negative, one penalty-5 value and 15 small positives.
  Memory or intermediate sightings could explain mode changes, but this is unverified.

The claim “positive in combat, negative otherwise” is **refuted**: training contains 7,824
negative priority writes on turns with a direct enemy-targeted basic attack/cast; holdout
contains 894. That is a deliberately narrow combat definition and does not label pursuit,
retreat or all AoE hits. Example: `ee053a1ab7e44f67`, round 51, actor 1, priority -46.

### Basic attacks: useful approximate target model

Conditional on taking a basic attack with at least one visible enemy champion in basic range,
choose minimum `HP + shield`, breaking ties by lower champion id.

- Holdout: **1,637 / 1,650 (99.21%)**.
- Multiple enemy candidates: **169 / 181 (93.37%)**. This is the informative choice subset.
- Raw-HP baseline: **168 / 181**; evidence for the shield refinement is modest.
- On previously unseen maps, multiple-target accuracy is **33 / 38**.
- Fish attacks a champion in 1,649/1,650 eligible holdout attacks; the single non-champion
  exception is counted as an error. Its key is `d2ed7663106f8e84`, round 392, actor 1,
  engine step 53420. Training also has one such exception.

These results do not predict whether Fish attacks, moves, casts or waits.

### Willow healing: weaker exploratory model

Conditional on casting a heal, maximize
`min(missing_health, 3 * Willow_focus) / ally_max_health` among visible allies within 4,
breaking ties by lower id. Holdout: **426/462**, or **312/348 (89.66%)** with multiple legal
allies. Lowest health fraction alone gets 311/348. No compelling improvement or exact
heal-trigger threshold is established.

## Evaluation rules for the continuation

**The original holdout is now used data.** Models were frozen before its first evaluation,
but its results and counterexamples have since been inspected. Use the 124 games for further
discovery if useful, but obtain and pin a fresh untouched holdout for a new confirmation.
Do not tune against these 15 games and call them independent confirmation again.

Original splitting was by whole match group: SHA-256(group id) modulo 5 equals zero for test.
There are 22 training groups and only 3 test groups. All 15 test map/opponent combinations
were absent from training, but only four test maps were absent. Exact duplicate bytes were
removed. Correlated turns are not independent statistical trials.

Keep these distinctions explicit:

- Exact compatibility of an encoding vs predicting which behavior branch runs.
- Predicting an action parameter vs predicting whether to perform that action.
- Accuracy on all opportunities vs the subset with meaningful alternatives.
- A compatible parameter interval vs proof of an exact source constant.
- A hindsight outcome label vs causal input features available at the decision time.

## Extractor details and traps

- `tools/replay/engine.mjs` provides the game's own versioned WASM decoder. `g.read()` is
  omniscient; use `g.read({team, champion})` for policy inputs. Existing extraction does this.
  Snapshot memory is reused by engine calls: copy needed values before another read/step.
- `extract.mjs` saves each turn's `start`, selected actions' `before`, and `end`. Before-state
  contexts are stored for attacks, casts, priority writes, recalls and tribute attempts.
  Every recorded move/ward/shop/etc. is retained as an action, but these do not each have a
  dedicated saved before-context. An analysis needing every intermediate sighting must extend
  extraction; do not silently equate turn-start vision with all vision during the turn.
- Contexts include self, visible allies/enemies, visible camps, visible group state and public
  scores. They omit item inventories, full unseen-ally liveness and explicit remembered state.
  Extend the schema if required. Do not reconstruct hidden information from observer truth.
- Cached `map` is `Game.map()`'s canonical map representation. Do not assume its camp/group
  list indices equal live replay ids. Context camps carry live `id` and `group`; the established
  `tools/replay/extract.mjs` also shows how to construct a full map indexed by live ids.
- The feature rows contain diagnostics that are **not legitimate inputs to every model**:
  `first` is the champion's first observed priority output; `attacked_champion` and `actions`
  describe the whole turn and may include later actions. The frozen predictors do not use
  them. Do not feed whole feature dictionaries into a learner without a causal field whitelist.
- `Submit gems` events include attacks on enemy altar locks. The table is deliberately named
  `tribute_attempt`; a real tribute-start analysis must distinguish successful starts and
  legal opportunities, with lock state and channel restrictions handled.
- Recall arrival is also called `Move` in the timeline, but occurs in phase 14. Walking
  inputs occur in phase 10. The independent audit excludes arrival from input counts.
- Priority writes affect next round. Current priority and written next priority are distinct.
- An unseen unit can block an action and reveal its tile. Preserve these events and timing
  when developing movement or target availability models.
- `extract.mjs` skips existing cache files without schema invalidation. Use a **new cache
  directory** after changing extraction. Preserve the current results and frozen predictors;
  implement the next experiment separately or explicitly version it.
- Do not name a Python helper `inspect.py`; it shadows Python's standard library and breaks
  imports/argparse. The inspection helper is `show_turn.py`.

## Suggested next investigation

1. Inspect the priority exceptions and penalty-5 cases with actor-local history. Test concrete
   mode selectors, including intermediate sightings and remembered threats. Enemy presence or
   nearest distance alone did not explain the extra penalty in the initial exploration.
   This is a tractable continuation of the exact numerical result, not a confirmed explanation.
2. Move on to the user's central interest: **camp-group choice and movement intent**. Define
   decision episodes, such as the first commitment after a completed clear or after returning
   from spawn. Use subsequent camp-directed attacks/occupation only to label the destination;
   build predictor candidates and state from the decision time. Include empty capture groups,
   visibility/memory, reachable paths, teammate involvement and interrupted/censored trips.
   Begin with a narrow clean regime and compare explicit competing scoring formulas.
3. For retreat or tribute thresholds, collect both action and non-action opportunities.
   Successful actions alone cannot identify a threshold. For banking, separate departing for
   an altar, selecting the altar, attempting tribute and successfully starting its channel.
4. Freeze a candidate, evaluate fresh games, report coverage and meaningful-choice accuracy,
   and preserve every counterexample. Do not spend the entire continuation polishing an
   already strong priority predictor while leaving movement/farming unaddressed.

Useful existing references: `tools/replay/README.md`, `tools/replay/narrative/`, and
`research/fish-farm-2026-11-02.md`. The last has historical aggregate farming patterns, not
verified current decision rules; treat it as a source of hypotheses.

## Commands and verified state

The existing caches are ready; no need to repeat full extraction to resume.

```sh
# Inspect a proven negative-priority combat turn.
python3 tools/fish/show_turn.py ee053a1ab7e44f67 51 1

# Re-evaluate frozen models without overwriting the original evidence.
python3 tools/fish/evaluate.py replays/fish-model/test-features.json.gz /tmp/fish-check.json

# Re-run independent raw input accounting if extraction changes.
node tools/fish/audit.mjs research/fish-2026-11-05/manifest.json replays/fish-model
```

List the original holdout priority failures:

```python
import gzip, json
with gzip.open('research/fish-2026-11-05/test-results.errors.json.gz') as f:
    errors = json.load(f)
for e in errors:
    if e['metric'] == 'quiet_priority_write':
        r = e['observation']
        print(r['game'], r['round'], r['actor'], r['step'], e['predicted'], e['actual'])
```

Full reproduction commands are in [README.md](README.md); every script is described in
`tools/README.md`. Before handing off, the previous agent verified:

- Audit: **124 games, 1,668,248 inputs, 632,771 completed turns**, exact accounting.
- Rebuilt manifest and learned rank table reproduced exactly.
- Training and holdout metrics reproduced exactly after the last feature change.
- Python compilation, Node syntax checks and a real `show_turn.py` inspection passed.
- `git diff --check` passed. No bot build/A/B was needed because no bot source changed.

Record further results in `research/EXPERIMENTS.md` and a new or extended research report.
Keep claims bounded by their observed domain and retain counterexamples instead of explaining
them away.
