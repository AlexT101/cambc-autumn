# Camp crew initiation before the tank arrives

Two frozen candidates are under test against full `oc-campsh-498`. The approved camp-partner shield stays in place. Queue ops owns launches; the livelock owner owns interpretation. No candidate has been merged.

| Candidate | Real budget | 200k diagnostic |
|---|---|---|
| `c107-wakeheal2` | Running, seed 206 | NARROWED: 0.000 ±0.224 pp fresh, 1,024 units |
| `c107-wakecrew3` | Queued, seed 208 | Queued, seed 207, eight blocks |

Both gates use standard fgate, fresh ladder-v2, Flp4/Mt3q, release/own drafts and engine 5.0.1. High H0 alone is not rejection. The doubled-fuel result is unresolved, not a demonstrated gain or statistical rejection; ladder +0.195 ±0.244 pp, pooled +0.098 ±0.166. All intervals here are 95% half-widths. Source seals, admissions, logs and large artifacts live under `~/tmp-offload/camp107-mechanism/`.

## Exact reported failure

Fish 03honeycomb, our side A, match `01a1c508-acce-73ac-ad07-55e9090bca53`. The exact live source (`live-wd-campsh-gen`), platform SDK, committed mask and puppet opponent reproduce all 21,011 inputs and all 681 round-start hashes in release and debug. Queue ops owns the aggregate v107/v105 readout (commit `b3797c31b`); this investigation covers the mechanism.

At round 28, Issac has 200 HP and dashes from (2,14) to (2,16), then wakes the Elk at (2,17). The group also contains gem and gold clusters; hitting any member wakes the Elk. Four camp phases kill Issac at 32 and linked Cassi, who still has 600 HP. No shield partner withdraws on the initiating turn.

The exact trace says `CREW PICK 28 2 g20 J trips 0 tank 0 expected 1 output 236 damage 0 hp 200/900`. Vesper is the planned tank but remains outside Elk range. The damage-sharing plan admits allies arriving up to two walking rounds later, and ignores Issac's immediate travel dash. More fundamentally, charging a future healing trip does not require that trip before an unsafe first engagement: correcting arrival estimates raises the price to 780 damage and one trip, but Issac still enters and dies.

## Self-initiation guard

[Wakeheal2](wakeheal2.patch) checks the actual position before waking a sleeping crew target, including after movement/reveal and before the attack. It compares health with both estimated solo-clear damage and straight-walk retreat exposure from every living striker. If neither fits, it commits the existing camp retreat until a heal. It skips our spawn and requires attack reach; Monolith staging stays separate. There is no map key or fixed HP threshold. The retreat exposure is an estimate, not a terrain-aware escape proof.

The historical counterfactual is identical through Issac's round-28 dash. At step 6567, it replaces his Elk attack with retreat. He keeps 200 HP through recall and is healed by round 34; Cassi survives. Release and debug are identical across the resulting 569 rounds. The later puppet win is not strength evidence.

## Another ally can still wake the camp

On fresh `gen-ladder-131200200111`, the paired debug baseline and wakeheal2 match until round 493, when Issac defers his Golem attack. HoR also preheals. Prism nevertheless wakes the Golem at 494 while they recall nearby. Baseline Issac and linked Cassi die at 497; wakeheal2 delays the deaths to 501. This is an existing failure that self-initiation protection does not resolve, not a newly introduced death. Both selected games eventually win; those outcomes are not strength evidence.

[Wakecrew3](wakecrew3.patch) extends wakeheal2 to a sleeping group with one living striker. Before a basic attack or camp spell, it identifies the current nearest champion using the next camp phase's tie order. If that is another ally who cannot survive the estimated retreat exposure, it defers the wake. It allows actual finishing damage, credits a stun of that striker, exempts the ally's spawn and directly confirms asleep state before refusing. Thus stale beliefs after an earlier action cannot suppress damage to an already-awake camp.

This extension matches wakeheal2 until Prism's round-494 attack, waits during 494–497, and lets Issac and HoR recall and heal at 498. Cassi survives. Prism then wakes the camp, takes its own hits, and escapes with 90.9 HP at 503. Its historical honeycomb release also preserves the precise round-28 fix.

## Fuel and behavior diagnostics

The 100M wide benchmark plays 52 games against fixed Flp4. Behavior changes mean these are not fuel-only equivalence claims.

| Comparison | Identical replays | Fuel change on identical games | All-game mean |
|---|---:|---:|---:|
| Wakeheal2 vs full 498 | 44/52 | +0.06% | +0.2%, behavior-confounded |
| Wakecrew3 vs full 498 | 44/52 | +0.09% | +0.3%, behavior-confounded |
| Wakecrew3 vs wakeheal2 | 50/52 | +0.03% | +0.1%, behavior-confounded |

Each candidate also played a bounded 256-game debug census on fresh f0 against fixed Flp4, with two shared CPU slots and no errors. This measures mechanism frequency, not release strength.

- Wakeheal2: six preheal calls in five games (1.95%); one before round 50. Five guarded champions reach a heal before their next death; the retained Golem case is the exception.
- Wakecrew3: the same six preheal calls. Ally protection adds 11 basic/spell refusals over six distinct champion-rounds in two games. Episodes last four and two rounds; no prolonged wait was observed.
- The second ally trigger, `gen-classic-131200301015` at 688, is conservative: baseline's stun and Prism taking over the hits already keep 120-HP Cassi alive. The extension delays two rounds and lets her recall at 695. It is not counted as a saved death. Its debug outcome flips to a win, but changed trajectories do not establish why.

[summarize_guards.py](summarize_guards.py) reproduces the census counts. `census2-recovery.json`, `census2-trajectories.json`, `censuscrew3-guards.json`, `failure-base-compare.json`, `wakecrew3-vs-wakeheal2-failure.json`, `second-case-compare.json` and paired decoded replays retain the local evidence.

## Failed hypotheses and superseded sketches

| Sketch | Finding |
|---|---|
| [Arrival0](arrival0.patch) | Removing two-round arrival tolerance raises priced damage 0→52 but leaves the reported death unchanged; first action divergence is round 91. |
| [Arrivaldash](arrivaldash.patch) | Crediting the ready dash raises pricing to 780 damage/one trip, still without enforcing a heal before entry. Same unchanged death. |
| [Crewstart](crewstart.patch), crewstart2 | Taking the cheapest member's own damage incorrectly treats a harmless cluster as a harmless wake. Moving the check before pocket routing does not fix this geometry error. No preheal action; no gate. |
| [Wakeheal](wakeheal.patch) | Precise reported-case success, then superseded before either gate launched to exempt spawn and require attack reach. Old sources/evidence remain distinct. |
| Wakecrew, wakecrew2 | A full-health-only condition misses the retained Golem, which had already been damaged and gone back to sleep. No waits in that case; no gate. |

An initial historical diagnostic was stopped before play after detecting the wrong SDK from its launch directory. Its corrected platform copy has a distinct identity. The first external-output census played zero games because run-batch could not find its project; its 256 error entries are not outcomes. A task-owned project file and SDK/cmake links corrected the environment before the successful `census2` run. None of these failures is statistical evidence.

## Queue provenance

Wakeheal2 normal and doubled gates were admitted at 12:48:19 UTC and started at 13:05/13:06. Old wakeheal entries were held before launch. Final files: `fg-wakeheal2.log` / `wakeheal2gate.pid`, `fg-wakeheal2200.log` / `wakeheal2200.pid`; seal `wakeheal2-source.json`, admission `admission-wakeheal2.json`.

Wakecrew3 gates were admitted separately at 13:16:43 after bush200k, preserving active jobs and all previous source/cache identities. Files: `fg-wakecrew3.log` / `wakecrew3gate.pid`, `fg-wakecrew3200.log` / `wakecrew3200.pid`; seal `wakecrew3-source.json`, admission `admission-wakecrew3.json`. Neither gate was independently launched by this owner.
