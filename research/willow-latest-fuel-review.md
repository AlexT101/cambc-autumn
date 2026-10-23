# Latest Willow fuel review

2026-10-23, bounded read-only review of canonical `bots/hyperion/src` at
aggregate SHA-256 `337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39`
(`d4cf962`). Read `AGENTS.md`, `cambc-rules.yaml`, `docs/handbook/11-fuel.md`,
`research/hyperion/FUEL-GATES.md`, current Willow integration notes and fuel
results. No compiler, engine, replay, benchmark, data fetch or gameplay edit was
run. The only write is this review note.

## Finding

One small conditional source-backed cut merits consideration; no material repeat
in the nine-station safety or camp path is evident.

In `bots/hyperion/src/bot.cpp:4873`, `local_support` calls `visible_record(mate)`
to establish that the already-visible mate has a live native record. When Willow
is ready to heal, the target loop at `4901–4910` can call `visible_record(mate)`
again after confirming that mate is a worthy heal target. No action or observation
change occurs between those reads. A local copy of the first record can serve the
target loop when `&a == mate`; keep other targets on the current read path. This
would save one `sdk_champion` import on turns where the mate qualifies. Copy by
value: `visible_record` returns static scratch storage that its next call
overwrites (`util.h:121–127`). Preserve the first query's error behavior and
target-loop order. This is a narrow opportunity, with no measured fuel saving
yet.

The apparent station repeats are already cached. `willow_step_guard` returns its
nine station records when round, `support_vision`, and origin match
(`bot.cpp:4353–4377`), and `support_exposure` reuses those risks
(`4379–4384`). Camp contributions are read through the static per-tile
`willow_station_members_near` index (`world.h:146–152`). `see_again` invalidates
the relevant state after an attempted move or changed vision; preserving that
refresh is required. Do not simplify it based on repeated calls in the same
round.

The mate `Reach::Window` reuse is already documented and measured on an older
parent/child pair: all 16 Release replays were byte-identical, but total fuel
increased by 12,421 (+0.000408%) and mean/p99 did not improve materially
(`research/EXPERIMENTS.md`, “Mate-view reuse”; artifacts in
`replays/willow-heal-view-reuse-100m/`). It is therefore not a current fuel
recommendation. That comparison used `test_draft: false`; Willow was nevertheless
in the fixed five-pick draft on the 8-map default panel. It does not qualify the
current aggregate.

## Existing inputs if the record reuse is selected

Use the saved 8-map, both-side Release/100M panel in
`replays/willow-heal-view-reuse-100m-parent.json` and corresponding child JSON
as a practical initial input, with the current canonical source pinned as the
new parent. `tools/fuel/bench.py` documents the default maps (`00ambush`,
`00lanes`, `01hooks`, `00corners`, `00contest`, `00interlock`, `00fragment`,
`00expanse`) and `--set wide --test-draft` as the existing broader 26-map / 52-game
input. First compare exact replay payloads and per-turn fuel at 100M, as required
for fuel-only changes; only a material saving justifies the real-budget rollover
panel. No fuel gate or changed eligibility, threat timing, or invalidation is
part of this review.
