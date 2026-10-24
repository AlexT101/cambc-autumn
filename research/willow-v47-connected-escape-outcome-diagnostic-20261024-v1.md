# Connected escape: common-opponent downside nomination

2026-10-24. Read-only completed result/statistics analysis. No new game, decoder, own-view export or helper. Source4b5a71e6 is the reviewed isolated connected-escape arm on f475; v33 is the common reactive opponent.

`provenance/khaos-v34-ladder-intake-20261024-v1/connected-escape-160-output-v1/RESULT.json` reports36/80 versus f475 and37/80 versus v33 (A16/B21). Joining the latter by exact map/side to `f475-v33-complete-output-v1/RESULT.json` yields27 shared wins,25 shared losses,10 gains and18 lost baseline wins. This is a much wider outcome footprint than hop's six flips. It does not isolate geometry from changed admission, dash coverage, computation/caches or existing fuel cutoffs. Native own errors/draft errors are zero;289 own play rollovers versus baseline260 over different durations do not identify cost causality. Combination testing remains worthwhile, but this single arm needs a concrete downside diagnosis before promotion.

## Nominate one cell: Elk Arena A versus v33

Baseline wins1044–108 at1291 completed rounds; escape loses144–1008 at1322. Near-equal durations make the aggregate collapse easier to interpret than a much shorter defeat, though not a controlled common-horizon trajectory. Own ending bags are zero in both. Baseline Prism/Vesper/Marcella collect and bank84/312/408; candidate all three collect0. Willow144→36 and HoR96→108 account for all candidate banked gems. Candidate monster damage also falls markedly across the roster. This is loss of ordinary conversion/control, not simply retained Prism gems failing to bank.

Candidate Vesper1 first dies at141 to enemy Prism. Candidate HoR4 later dies to a camp at423; other own deaths are PvP. Baseline's six deaths are all PvP (Vesper1025 and HoR154/338/415/592/1161); there is no baseline camp death. These global facts nominate an early allocation/retreat divergence, but neither the first death nor the later camp death proves an actor-known defective move. Do not skip directly to423 and assume the connected path caused it.

Request the existing accepted-input/state comparator first, baseline→escape, then at most one bounded actor window around its first meaningful decision. If the fork is in ordinary opening farming before any camp exposure, inspect lazy-cache/cost initialization and existing cutoffs. If it is retreat/health admission, inspect known blockers/goals, ray versus native result, route distance, selected next endpoint and camp/enemy exposure. If it is a dash, check whether exact-ray partial labels or the connected flag suppresses a previously useful landing. These are discriminants, not a presumption of the branch. A useful refinement preserves connected geometry while fixing the identified admission/execution/cost limitation; no map-name exception or blanket reversion is proposed.

Exact replay paths relative to intake:

- `f475-v33-complete-output-v1/f475-v33__01elk-arena__f475-A.repl26a`, verified SHA256 `41cb085bab336dd88cec7e7b4aba26107ef19e2f5461bb65b0a970f8819c36b0`.
- `connected-escape-160-output-v1/escape-vs-v33/escape-vs-v33__01elk-arena__escape-A.repl26a`, verified SHA256 `e92a81ce426fa07a38026bcff62ea5b76780d2d79482a4fda6e568635a84819e`.

Statistics are the same stems with `.statistics.json`. Source-ready review remains valid as a bounded correctness review; these outcomes supply evidence to improve the experimental policy, not a claim that the prior review certified strength.

## First-fork and own-view addendum

The completed comparator `first-fork-comparisons-v1/escape-elk-arena-A.json` finds input375, round10, step1748: baseline rollover versus candidate HoR4 moving (23,24) to (23,23). The two existing `own-view-firstfork-v1/escape-{baseline,candidate}/window.json` exports show the same round10 start: 790/1000 HP, Strength30, Focus100, cooldowns[4,0], no channel or carried gems. Vesper6 (26,25), Marcella7 (27,25), Willow8 (29,24) and HoR9 (26,24) are fully visible. The awake Elk pair is also known. Coordinates here are raw physical-A coordinates.

Candidate then dashes to (25,23), attacks, and rolls over. Baseline does nothing before its round10 rollover, then executes that same move/dash/attack sequence in round11 at 730 HP and rolls over again. Candidate's round11 starts at (25,23), 790 HP, and attacks/moves to (26,23)/starts recall. Thus this first observable fork is an action timing/budget boundary, not evidence that the candidate chose an inferior geometric endpoint. Recall type1 in the exporter is ordinary recall, not teleport.

Source excludes one tempting explanation: `connected_camp_dash` (candidate bot.cpp:393–398) immediately refuses visible enemies. It cannot own this four-visible-foe dash under the current observation. Ordinary combat or retreat machinery can still produce it; accepted actions do not identify that caller. Nor does an earlier action necessarily improve the eventual fight.

There is nevertheless a distinct admission hypothesis worth separating. Candidate `camp_trapped` (bot.cpp:2901–2913) replaces f475's healthy shortcut with a connected exit result. Its walls include current native occupants and the installed guard (pathing.cpp:393–404). Exhausted/unreachable, or unresolved nonexact results, return trapped at any HP. A temporary ally blockage or a camp body that productive work could kill can therefore change admission, while current camp damage times the whole escape distance does not credit a foreseeable clear. The old geometric upper bound was unsound around holes; this observation does not justify restoring it as a safety proof.

Minimum diagnostic: source-known HoR4 round10, adding round11 only to locate resumed work. Record actual existing want_home short-circuit/caller; whether camp_trapped ran; its already-computed damage, ray/native distance, exact/exhausted/result; and the caller of move/dash/attack with existing fuel/rollover context. Do not invoke an extra Safety query or recompute the baseline policy inside the trace. This distinguishes admission from cheaper work, resumed computation, ordinary fight search or retreat direction.

A useful isolated control is connected direction/dash with original admission, explicitly labeled as retaining the old admission limitation. It is a causal control, not a claim that old admission is correct. If admission is implicated, the refinement should distinguish durable terrain disconnection from a transient occupied route and known imminent camp removal; treating every snapshot obstruction as an HP-independent mandate to leave is the concrete behavior to evaluate. Do not weaken actual next-step legality or widen dash exposure merely to reproduce a win.
