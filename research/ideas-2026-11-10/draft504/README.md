# One draft refit for Ocean 504

The user explicitly requested one draft lab, followed sequentially by one tuning run on 2026-11-10. This is **draft17**, a new decision; canceled automatic rounds draft11–16 stay canceled. Both running ward504 gates finish first. Queue operations admits draft17 as an exclusive, low-priority stage, then keeps tuning behind `draft17-reviewdone`, a coordinator-owned decision barrier.

The scientific reason is that draft10 learned the play of `ocean-16d6f78`, while current504 has different Prism, Issac and Vesper emblem policies, plus fuel and camp changes. These can change relative champion value. The lab isolates that change in play; it does not refresh the opponent model, repin live opponents, or rerun draft10's canceled gate.

## Sealed design

- Source: `variants/oc-emb5-504`, commit `08f4be1ce0e8ae1485f389abddc0508af971cd42`.
- Current-team sampler: a frozen copy of draft10-F92. Regenerating its header reproduces504's model byte-for-byte after provenance comments. There are no required or banned champions.
- Composition prior: draft10's top-eight ranked-team prior, generated Nov10 01:26 from Nov6–10, with48-hour decay. This is deliberately a controlled historical distribution, **not latest-meta data**. Its archive engine label3.0.0 is provenance, not the local simulation version. Current Mite's difference from pinr5 does not silently change this prior or the fixed local bodies.
- Training: one800,000-game collection (batch rounding allowed down to799,000), maximum18hours; 100,000 fuel, native release engine5.0.1. Production fuel teaches composition values for the actual game. No previous training games are pooled.
- New training seeds2412000–2412099, ladder-v2, up to25,600 maps. Held-out seeds2412900–2412903, up to1,024 maps. Exact byte duplicates are excluded within both pools and against the128 ladder maps, standard1,024-map gate pool and old draft10 training pool. This stated scope is not universal historical novelty. Map artifacts are preserved, while selected pools omit duplicates.
- Opponent shares: local FishFlp4 .3, MiteMt3q .3, mirror .2, frozen astraeus/proteus .1 each. This retains the preceding successful training design and some opponent diversity.
- Model: F25 guides collection; one finalF92 refit uses draft10-F92 penalties as its starting point, searching only existing `w,dev` groups once. No feature sweep, repeat collection, or best-of-many lab selection.
- Resources: shared86-slot pool, at most64 game workers; fits24, planning12, outcome readers8. The lab's internal stages use shared CPU slots; raw first-turn diagnostics reserve their actual worker count. Other local queue experiments cannot overlap this exclusive stage. Before its first heavy phase, the wrapper checks both the approved base policy and committed Ocean source against sealed504. A newer base holds for coordinator review before any map generation or training; a genuinely started experiment stays frozen through later main changes.

## Evaluation and review

Only the exported `draft/draft_model.h` may differ from504. Require a release build, native key/team parity, and first-turn measurements with no missing, unfinished, capped or over10M team-drafts. Tiny native floating-point feature differences are reported; team/key mismatches fail.

The first strength evaluation uses200k fuel on both teams against fixedFlp4/Mt3q, own drafts, both sides, the separate held-out map pool and the128 diagnostic ladder maps. Fresh units alone decide. Source identities, exact map/side coverage and engine/fuel/release metadata are audited before each block enters the existing sequential statistic. The precision-only stop is disabled. A standard ZONE stops for judgement; acceptance/rejection keep their meanings; the1,000-block cap stays unresolved.

The pipeline writes `review-required.json` after the200k gate. It **never** creates `draft17-reviewdone`, queues a normal-fuel run, promotes the candidate, submits it live or refills the lab. The coordinator must review the outcome and authorize any100k gate only after evidence of a200k gain. Tuning waits until that evaluation and the draft disposition are complete, then uses the deliberately selected base. A small local improvement does not automatically deserve a noisy live gate.

## Commands and artifacts

Preparation check (no games or map generation):

```
python3 research/ideas-2026-11-10/draft504/run.py --check
```

Queue command, after root admission and both ward gates:

```
python3 research/ideas-2026-11-10/draft504/run.py
```

A separately admitted normal-fuel evaluation, if justified:

```
python3 research/ideas-2026-11-10/draft504/run.py --normal-admission /absolute/path/to/coordinator-admission.json
```

Artifacts: `~/tmp-offload/localq/rounds/draft17/{protocol,config,manifest}.json`, input snapshots, generated/selected maps, lab/F92 data, first-turn reports, per-block audits, gate results and review marker. No heavy phase runs during preparation. Both original source and tool inputs are sealed; a changed input fails for review rather than silently mixing versions.
