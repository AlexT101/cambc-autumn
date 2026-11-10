# Completed live v111 Greed readout, 2026-11-10

**Decision: no Greed merge or exploiter promotion from this evidence.** The older local gate did not establish a positive fresh-map effect; the completed live comparison is small and confounded by the submitted priority-mask change. Keep the already-authorized current-mask v105 control as the prospective cleaner comparison. No new scrims, tests, downloads, source edits or repins were performed for this analysis.

## Collection and source checks

Scheduler finished v111 at 21:23:34 UTC. Independent local-ledger validation found all 104 normal pinned groups created and durably collected:520 finished raw matches, 8 explicitly marked fillers excluded, 512 unique nonsuspect map/side/opponent-pin cells. The two unpinned `oppcheck` groups are excluded. Every collected row matches its planned map ID and side. Fish remains r2; Mite remains r5.

Submitted v111 is archived at `/home/ubuntu/tmp-offload/handoff/sched/build/live-wd-greed-1794333702`. Its frozen source differs from `live-wd-fsnh` (v105) only in the 12-line `economy/shop.cc` Greed rule, exactly the existing `sm-greed` patch: Vesper with Strength main may choose Greed if its saving per gold, discounted for the time required to afford it, exceeds the best stat emblem. This is a timing/cost comparison motivated by Greed's 40-shards-for 25 rule, not an unconditional emblem override.

The **actual submitted** v111 versus 105 differs in that shop block **and** `model/prio_stream.h`'s key. The remaining mask integration changes are shared. The C++ SDK trees are identical. v111 shares the newer mask/SDK with 106 and 107, but those arms contain reserve+queue recovery and camp shield respectively, so they are diagnostics rather than isolated Greed controls.

## Completed paired outcomes

Intervals below are descriptive approximate 95% normal intervals after averaging the two sides within each map, then treating maps as clusters. This reused deterministic ladder suite is not unused-map confirmation. Neither statistical multiplicity nor selection among prior live arms is corrected by these intervals.

| Reference | Opponent/pin | Paired cells/maps | v111 wins / reference wins | Flips for / against | Map-cluster delta, pp |
|---|---|---:|---:|---:|---:|
|105, intended base but old mask|Fish r2|256 /128|160 /164|2 /6|−1.56±2.16|
|105, intended base but old mask|Mite r5|80 /40|44 /42|2 /0|+2.50±3.42|
|106, same mask; reserve+q1 instead of Greed|Fish r2|256 /128|160 /184|30 /54|−9.38±7.59|
|106, same mask; reserve+q1 instead of Greed|Mite r5|256 /128|160 /153|42 /35|+2.73±6.64|
|107, same mask; shield instead of Greed|Fish r2|256 /128|160 /165|13 /18|−1.95±4.40|
|107, same mask; shield instead of Greed|Mite r5|256 /128|160 /169|7 /16|−3.52±3.29|

v111 totals are **160/256 against Fish and 160/256 against Mite**. v105 has only 80 matching Mite r5 cells; its older Mite-pin games are never mixed in. The same-mask diagnostics cannot assign their differences to Greed, reserve, q1 or shield separately, even where a descriptive interval excludes zero.

All paired rows match ordered own/opponent picks, full draft, seed, reported engine/build hash, map ID, pin/refset and exact pin source-group ID. Reported platform engine metadata is `3.0.0`/`96ce858f548c`; matching these opaque fields is a context check, not a claim that this platform is the local CLI's3.0.0 engine.

## Raw replay checks

Raw `replay.repl26a` members are compared by size/CRC, with SHA256 computed to confirm every potential equality. Against 105, no raw members match, despite equal score fingerprints in 209/256 Fish and 66/80 Mite pairs. The changed submitted priority encoding means raw inequality is not evidence that Greed changed meaningful decisions in every game.

Against same-mask 107, raw replays match in 94/256 Fish and 114/256 Mite pairs (score fingerprints 125 and144). Against 106, 8 Fish and 7 Mite raw replays match. Exact equality examples, chosen as the first sorted equal cell rather than for outcome:

- Fish r2, `00ambush` side A, seed 17465944590158198232: v111 match`01a1c70c-5031-7768-848c-b963d4a8aab4` equals v107`01a1c4c3-92c4-79ff-8b18-22f929f326b0` byte-for-byte.
- Mite r5, same map/side/seed: v111`01a1c712-f6db-784d-b202-5ad9908ecbb0` equals v107`01a1c4de-bfa6-702d-8f8a-df84f4ad12c1` byte-for-byte.

Full match IDs, contexts, paths and raw hashes are in the artifact directory below. Current-Mite versus pinned-r5 mismatch was already established by the separate per-version check; it is not a new opponent-change claim here and does not alter the pin used by this readout.

## Prior local evidence and prospective control

The completed `sm-greed` gate versus frozen `ocean-16d6f78` used Flp4/Mt3q, 36 noise blocks and 4,608 fresh paired units from the standard fixed pool: overall **+0.206±0.250pp**, Fish **+0.184±0.327**, Mite **+0.228±0.369**. It ended `NARROWED (ZONE crossed)`, with low LLR +5.098/high −6.448. This is neither a positive 95% interval nor high-test acceptance. Old local mechanism measurements found 0.21 Greed completions/game and slight stat/death improvements, but the bodies seldom fight Vesper as live opponents do. These observations motivate the hypothesis; they do not establish current 504 strength. See EXPERIMENTS “Shop against Mite's and Fish's builds” and `ideas-2026-11-09/shopmite-tools/sm-greed.patch`.

The already-queued `live-v105-currentmask-control` was independently rechecked now: its source still matches the sealed archived-v105 reversal and frozen fsnh; its previously prepared SDK and mask match 111; the prepared sources differ only in shop.cc. This is prospective evidence, not a completed control. Reverify its actual future submitted workspace, SDK/mask, pins and contexts. It is intended to supply 256 Mite r5 cells as well as 256 Fish r2 cells, unlike old 105's 80 shared Mite cells. No additional control was queued.

## Exact v106 bundle is absent from current 504

Read-only current-base check corrects an earlier loose “already-shipped attribution” description: frozen `oc-emb5-504` has **neither** v106's `after_loop -8000` farm-budget subtraction **nor** its global `queue_round` wrapper/`fuel_ok` guard. The current farm formula retains the full `end_reserve + after.base + chunks*after.per_chunk + chunks*after.quarters_per_layer*l/4`; `fuel_ok` checks fuel alone and queue.run has no such wrapper. Existing per-loop round checks are not the same global guard.

CHANGES503's non-quiet turn-order reserve 10k→12k (quiet 6k retained) is a different policy; see `research/fuel-2026-11-10-fifth/README.md`. The old local q1+8k bundle read +0.150±0.250pp, with Fish +0.014±0.339 and Mite +0.286±0.362. The later attribution programme was explicitly canceled and remains closed. Source absence is not authorization to reopen it or merge the bundle from the v106 live Fish lead.

## Reproduction and artifacts

Run `python3 tools/pooled.py 1 -- python3 research/ideas-2026-11-10/live-greed111/analyze.py` to recompute from already cached records. It refuses incomplete/suspect collection and performs no network call, build, game or queue mutation.

`/home/ubuntu/tmp-offload/handoff/codex/live-analysis/greed111/` contains `result.json`, `collection-proof.json`, `input-rows.json`, `provenance.json`, submitted-source patches, `raw-replay-proofs.json`, `identity-examples.json`, `control-preflight.json` and `current504-coverage.{md,json}`. Original local gate: `/home/ubuntu/tmp-offload/diverse/gate-logs/fgate-sm-greed--ocean-16d6f78p4q.json`. Source readout is frozen to this completed 111 run; later control results require their own explicitly checked comparison.
