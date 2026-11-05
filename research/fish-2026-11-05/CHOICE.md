# Camp destinations as a scored choice, fifth-cohort confirmation

Continuation on November 5, 2026, after [ROUTES.md](ROUTES.md). No bot source changed; earlier
models, caches and results are preserved. The main result is a conditional-logit camp score that
predicts Fish's next camp after a payout or a spawn better than every earlier destination model,
confirmed on **94 untouched games**. Draft and emblem choices are in [DRAFTS-EMBLEMS.md](DRAFTS-EMBLEMS.md).

## Negative results first

- **Shared memory is not in replays.** The v3 engine exports `Game_Visualiser_GetSharedMemory`
  and `Game_Visualiser_GetDraftMemory`, signature `(game, team, offset, out, length)`. They read
  zeros all game for both teams, also in our own A/B replays, whose bot writes comms every turn;
  the replay has no memory-write step kind. `tools/fish/probe_shared.mjs` reproduces this.
- **No Fish stdout/debug.** Ladder bundles hold `team-a.{stdout,debug,fuel}` only when team A
  shares them; Fish's are never present.
- **No sign of hidden teammate knowledge.** Adding observer-truth features to the logit (true
  positions of out-of-sight allies within 4 of a group, groups allies interacted with in the last
  3 rounds) changes fourth-cohort accuracy from 55.2% to at most 55.6%. Fish chooses as if from its
  own sight and memory. (An "ally's next camp" variant uses the future and was discarded.)
- **Not a claim/assignment system.** A visible ally closer to a group than the actor makes Fish
  *more* likely to go there (weight +0.73), not less. Chosen camps are also an ally's next camp in
  61% of episodes. Fish joins, it does not partition. Pair co-location is loose: no pair is within
  3 tiles more than 47% of the time (Cassi + Willow); Cassi + Issac 37%.
- **Labels are mostly real destinations.** Steps after the first are on a shortest path to the
  labelled group 90% of the time (first steps 67%). Only 8% of labels are a brief hit followed by
  another group; relabelling them would fix 17 fourth-cohort errors.
- **"Return to where I was" fails after spawn.** The group nearest the actor's last off-spawn
  position is the destination in 17% of post-spawn episodes.

## The model

Episodes, labels and candidate features are those of [DECISIONS.md](DECISIONS.md) /
[ROUTES.md](ROUTES.md) (`routes-v3`): post-payout and spawn-exit starts with no visible enemy,
labelled by the first camp hit or empty-group occupation within 40 rounds; openings and censored
or ambiguous episodes are excluded. Candidates are reachable groups (walk < 999), excluding the
group just paid out. New causal input: the actor's visible allies at the start (`choice_data.py`).

Fish's choice is predicted as `argmax_c w · f(c)` (ties to the lower group id), with these
features of candidate `c` (`choice_model.py`):

| Feature | Definition |
| --- | --- |
| `wait`, `logwait` | `max(walk, remembered respawn wait)` / 10, and `ln(1 + that)` |
| `respawn_part` | `max(0, respawn - walk)` / 10: rounds spent waiting on arrival |
| `alive_fight` | if alive/unknown: fighter HP (wolf 1350, elk 2400, golem 5000, monolith 20000) / own Strength / 100 |
| `alive_dps` | if alive/unknown: summed fighter Strength / 100 |
| `monolith`, `golem` | alive/unknown group contains one |
| `clusters_only` | no fighters (gem/gold clusters only) |
| `unknown`, `empty`, `respawning` | remembered group state (else alive) |
| `gold`, `gems` | group reward / 100, / 10 |
| `allies_near` | visible allies within 3 of the group |
| `ally_recent` | actor saw an ally on the group within the last 10 rounds |
| `visited`, `route`, `last` | actor farmed it before; has seen this origin→group transition; it is the last group farmed |
| `terr`, `terr_neg` | `max(0, ±(own-spawn distance − enemy-spawn distance))` / 10 |
| `ally_closer` | a visible off-spawn ally is Chebyshev-closer to the group than the actor |

Every feature also has a `spawn*` copy (×1 for spawn exits), so payout and spawn have separate
weights. Weights of the frozen fit [choice-fit.json](choice-fit.json) (7,904 episodes, all 213
decoded games of the first, third and fourth cohorts; L2 0.1, Newton):

| Feature | After payout | After spawn |
| --- | ---: | ---: |
| `wait` | +0.191 | +0.096 |
| `logwait` | −3.439 | −1.579 |
| `respawn_part` | −0.889 | −1.616 |
| `alive_fight` | −0.639 | −0.430 |
| `alive_dps` | +0.349 | +0.458 |
| `monolith` | −1.630 | −0.230 |
| `golem` | −0.057 | +0.205 |
| `clusters_only` | −1.129 | −0.678 |
| `unknown` | −0.078 | −0.682 |
| `empty` | −0.540 | −1.939 |
| `respawning` | +0.724 | +0.341 |
| `gold` | +0.016 | +0.042 |
| `gems` | +0.061 | +0.057 |
| `allies_near` | +0.152 | +0.230 |
| `ally_recent` | −0.715 | −0.755 |
| `visited` | +0.625 | +0.887 |
| `route` | +0.801 | +0.693 |
| `terr` | −0.710 | −1.976 |
| `terr_neg` | −0.170 | +0.376 |
| `last` | +0.498 | +0.997 |
| `ally_closer` | +0.725 | +0.504 |

Read: wait dominates on a log scale (a 5-round difference matters far more near than far);
arrival waits on a respawn cost extra; camps it cannot beat quickly alone are avoided (Monolith
strongly after payout); a group's own reward barely matters; familiar groups and routes, its own
half, and groups beside visible allies are preferred; groups an ally was just seen on, and
remembered empty groups (probably being captured by someone), are avoided. These are fitted
weights of a surrogate, **not source constants**. Correlated features (`alive_fight`/`alive_dps`,
`wait`/`logwait`) should not be read individually. Feature choice used the third and fourth
cohorts, which are therefore not independent tests of it.

## Results

| Cohort | Logit | Wait baseline | Earlier fitted route score |
| --- | ---: | ---: | ---: |
| Third (43 games, used), discovery-only fit | 992/1,827 (54.30%) | 844/1,827 (46.20%) | 921/1,827 (50.41%) |
| Fourth (46 games, used), discovery-only fit | 978/1,726 (56.66%) | 823/1,726 (47.68%) | 847/1,726 (49.07%) |
| **Fifth (94 games, untouched), frozen fit** | **2,351/3,819 (61.56%)** | 2,002/3,819 (52.42%) | 2,077/3,819 (54.39%) |
| Fifth, discovery-only fit | 2,332/3,819 (61.06%) | | |

On the fifth cohort: after payout **1,012/1,462 (69.22%)** vs 925 (63.27%); after spawn
**1,339/2,357 (56.81%)** vs 1,077 (45.69%). Ranked games 492/846 (58.2%) vs 52.0%; unranked
1,859/2,973 (62.5%) vs 52.5%. The logit matches or beats the baseline in 18 of 20 groups; a
match-group bootstrap (10,000 resamples) puts the gain at **+6.0 to +12.2 points**. Rows whose
label is unreachable in the candidate set count as errors. The fifth cohort's baseline is higher
than earlier ones (52% vs 46-48%), so compare gains, not levels.

### The fifth cohort

[fifth-manifest.json](fifth-manifest.json): every downloaded Fish game not in the four earlier
manifests by bytes, match id or group id. **94 games, 20 groups**, created 18:50–21:10 UTC
November 5 (two groups downloaded earlier but never decoded, plus 18 fetched for this pass); 21
ranked, 73 unranked; all engine `v3_0_0`; submission versions unknown. Unranked games include
repeated scrimmages (Mite, BBL) and may use different opponents' test bots. `pin_fifth.py` wrote
the manifest and [choice-freeze.json](choice-freeze.json), hashing every model and feature
script, **before any fifth-cohort play was decoded**; all hashes matched at evaluation.
[fifth-audit.json](fifth-audit.json) (`audit.mjs`) accounts for **1,107,129 inputs and 429,339
completed turns** exactly.

### Earlier frozen models on the fifth cohort

Unchanged `routes-trees.json`, scored by the unchanged scripts ([routes-fifth.json](routes-fifth.json),
[incoming-payout-fifth.json](incoming-payout-fifth.json)):

- **Incoming entry through observed payout**, the endpoint ROUTES.md asked to freeze: frozen tree
  **3,256/3,628 (89.75%)**, rank alone 3,215 (88.62%), never-paid 2,900 (79.93%). The tree finds
  553/728 payouts with 197 false positives. This is the first untouched confirmation of that
  endpoint; it still does not distinguish replacing an incumbent from sharing its payout.
- Entry by turn end: tree 3,033/3,638 (83.37%), rank 3,008 (82.68%), never 2,622 (72.07%).
- Economic trip forecast: 4,384/6,259 (70.04%) vs always farm 3,819 (61.02%); after payout only
  1,945/3,449 (56.39%).
- Timer-4 recall arrival: 98.75%, equal to always-cancel; still a failed classifier.

## Reproduction

```sh
# Per cohort: visible allies onto routes-v3 rows.
python3 tools/fish/choice_data.py replays/fish-fifth replays/fish-fifth/routes-v3.jsonl.gz OUT.jsonl.gz
python3 tools/fish/fit_choice.py OUT.json replays/fish-{model,third,fourth}/choice-v1.jsonl.gz
python3 tools/fish/evaluate_choice.py replays/fish-fifth/choice-v1.jsonl.gz research/fish-2026-11-05/choice-fit.json OUT.json
```

Fifth-cohort decoding used `extract.mjs`, `decision_data.py`, `routes_data.py` as in ROUTES.md,
into `replays/fish-fifth/`. Results: `choice-fifth-fit.json`, `choice-fifth-fit-discovery.json`,
each with a sibling `.errors.jsonl.gz` of every failure. Scripts refuse to overwrite outputs.

## Next

Post-spawn choice is still the weak half (57%). Promising, untested: Fish's estimate of unknown
or long-unseen groups, e.g. assuming a respawn after its timer; wanting a crew before an Elk or
Golem; choosing at recall start rather than at spawn exit. The fifth cohort is now used too:
confirm anything new on games after 21:10 UTC November 5.
