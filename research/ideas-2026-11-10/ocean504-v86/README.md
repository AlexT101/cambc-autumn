# Quick shipped506 versus v86 benchmark

The user requested “a quick one vs v86 latest/best vs v86”. This supersedes the initial larger preparation before any games: fixed **2,048 new ladder-v2 maps, both sides, 4,096 fresh games plus256 ladder games,4,352 total**, explicit100k fuel, own drafts, release/native engine5.0.1. There is no optional stopping, candidate selection, repeat or automatic extension. The128 ladder maps run first for fast sanity, then four sequential512-map chunks allow complete cached chunks to survive an interruption; no decision is made between chunks.

Candidate `variants/oc-dfuel-506` is exactly Ocean commit183a1295c. Root explicitly selected506 after main advanced during preparation, before any heavy work. Artifact/job/cache names retain504 for compatibility; results identify506. Reference `variants/oc-base23` is exactly Ocean commitdd7002a8f85d4a543e68dfc5bad99c4c2fa6d40a and the source of v86-reup/v97. Both source sets are sealed and rebuilt unchanged with the current SDK/engine. We do not upgrade v86's parameters, draft, stat tables, source or priority mask. This asks how the old source plays under today's engine; it does not reproduce pre5.0.1 live v86.

Seeds2416000–07 are reserved;2416008–11 are only prospective content-duplicate replacements. The remainder of the earlier reservation stays unused. Before games, content is deduplicated against ladder maps, the old standard and conditional gate pools, and draft10 training maps. This is an explicit bounded novelty scope plus unused registry seeds, not a universal historical archive claim. Map source hashes and chunk assignment are sealed before the first game. Map generation is pooled1 with explicit`--jobs1`.

Report fresh and ladder separately, with a descriptive fresh-minus-ladder gap; never pool them as the primary. Report direct candidate win rate with map-paired95% normal uncertainty, averaging both sides of each unique map. A conservative empirical-Bernstein interval is also reported so an all-split sample does not imply zero uncertainty. Neither interval is a live win-rate prediction. Require every expected map/side exactly once, release100k/5.0.1 metadata and zero execution errors. Retain all OOF, early-loss, handoff and draft-cap counts; guard failures stay counted outcomes. No map exclusions based on outcomes.

Queued exclusive job`ocean504-v86-100k`, shared86 pool, weight1, at most64 game workers. Before first heavy work, verify the explicitly selected506 and v86 historical source identities. The selected benchmark stays frozen even if main advances again. No builds, map generation or games occur during preparation or`--check`. Source/input drift or a partial interrupted batch holds for review instead of silently replaying cells. Ops owns temporary scheduling/drain and restoration of the running cleared-ward controller; this wrapper does not signal other processes.

Artifacts: `~/tmp-offload/ocean504-v86/{manifest.json,protocol.json,maps.json,result.json,paired-scores.json}`. Existing comparison context is separate: full504 logic already beat503 in the teammate's61,440-game mirror,50.63%[50.23,51.02]; the tested source differs only by three comments. Completed live111 versus post-switch v86 reupload97 is160 vs163/256 Fishr2 wins, paired−1.17±7.25pp, with a mask confound; Mite pins differ. Neither supplies the missing direct504-v86 benchmark.

## Completed result

All4,352 planned games completed on2026-11-10, with no execution errors, early losses, handoff failures or capped drafts. Both historical source seals, raw result hashes and every expected map/side cell passed the final audit. Only the initial eight fresh seeds were needed; no replacement or extra games ran.

| Panel | 506 wins | Win rate | Map-paired95% interval |
|---|---:|---:|---:|
| Fresh ladder-v2 | 2,355 /4,096 |57.50%|55.94–59.05%|
| Ladder128 |139 /256|54.30%|47.59–61.00%|

Fresh-minus-ladder is+3.20 percentage points, descriptive95% interval−3.68 to+10.08. This does not establish a ladder-specific overfit gap. Fresh maps support that shipped506 beats exactv86 head-to-head under current5.0.1, release100k conditions; this is a cumulative comparison, not attribution to a particular feature or prediction against Fish/Mite. The conservative bounded fresh interval is54.91–60.08%.

Reported exhausted turns were24,473 versus37,489 on fresh maps, and1,613 versus2,406 on ladder maps (506/v86). These are descriptive counts, not an isolated fuel-change test. The same ward controller PID4112940 resumed after the benchmark process group drained; the benchmark exited0 and dispatch was restored.

Durable evidence: [result.json](result.json), [audit.json](audit.json), [protocol.json](protocol.json). The sealed launcher is [run.py](run.py), its preparation helper [seal.py](seal.py), and the pairing/uncertainty checks [test_run.py](test_run.py). Manifest SHA256`97cb7bf34db6c3485d6b94ef07860abc5750bfe139ce1e5b5e12f4222e7e3d5e`; result SHA256`1281f6b605ec66d1bdbdf579457d2d05baf257d13a3705d4588eaf4eab517a91`.
