# Big World branch witness: bounded action-equivalent trace

One default-fuel trace game completed from the start against the frozen Release Fish-roster emulator. This is an action/state-equivalent diagnostic, not a strict fuel-exact reproduction: the source-matched recorder differs by +40 fuel for actor3 at round4 and +896 for actor4 at round470. Under strict fuel criteria, trust ends after round3.

## Validation and boundary

All five actors' recorded segment hashes and call counts match the tracer for rounds35–75 (205/205 segments). The tracer reproduces all four native rollover points and has no `@!` through round75. Its first `@!` is actor4 segment267 at round268; recorder stdout is incomplete after round267, so later errors are outside this witness window.

Original-vs-trace and recorder-vs-trace comparisons first differ at round279, on actor4's Move from (76,9): original goes to (75,8), trace to (75,10). Round hashes first differ at round280. Thus rounds35–75 precede the first observed action/state mismatch. Full-game outcomes differ: original ends at round905, 588–1006; trace ends at round979, 723–1001.

## What the witness shows

At round41 both actors start at 700 HP. Prism0 assigns local claim8 to farm group12; Willow3 remains on group4. During rounds42–45, Willow observes Prism's cached group12 claim while Prism's position remains invisible/stale at round38; Prism likewise sees Willow's cached group4 claim while Willow's position remains invisible/stale at round39. The farm split therefore precedes Prism's first logged HP loss (620 at round45).

At round46 Willow sees Prism's current position and claim12, enters branch `h`, and clears its local claim to -1. This is a local-information transition only. The trace does not expose rejected farm alternatives, internal scores, or a specific support/heal target. See [the round table](target-window-summary.md) and [raw rows](bw-rows-r41-r46.txt).

## Reproduction pins

- Candidate gameplay source: `337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39`.
- Instrumented source aggregate by manifest recipe: `e27b52f8c6f8c1efd3541cd727cabae267dc57d314565f00669f0834d195a6e7`.
- Instrumented source aggregate by standard `shasum -a 256 src/* | shasum -a 256` recipe: `12a6ae812694f6ab14248b56c72878bd00b7a71ea0945a8a800b139fbdaf09b2`. These are separate aggregate recipes and are both recorded in [build pins](build-pins.json).
- Fixed emulator Release raw/injected SHA-256: `22fc50dfd1ab33d1e442e8882b1fe89572d61cb96980a7b629f774a5c255169b` / `f7873b5a06649bc0dfd9ae3bd9575fb629834b9b47e7823a09f517d0f5833175`; rechecked after its debug-workspace build.
- Trace debug raw/injected SHA-256: `117870ecd5b168287d6e689d7220fe7df8dfac86460a859573ba373a508fd3f2` / `6ed8ae4b7465ea30cea21a89a0bc4ffaae4d06d1c4cd8340ac28ba380908cdfa`.
- Engine SHA-256: `029ecd290dc400e75418178ec386d72cbd7d9f2fc2a2e451bf594ca23566df48`; CLI SHA-256: `69617aa6a074415bd8ba8e254d1584df3392d95d1f9e2e2d46db66ff6e187171`.

Build command from the isolated `workspace` directory:

```sh
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 \
  /Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc \
  build bots/willow337f-trace
```

Run command from the isolated `workspace` directory:

```sh
nice -n 19 env CMAKE_BUILD_PARALLEL_LEVEL=1 \
  /Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc \
  run-batch /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/replays/bigworld-branch-witness-20261023/phase3-trace/one-game-manifest-absolute.txt \
  --jobs 1 --color never
```

The manifest names the trace bot, fixed emulator, map, and this run's replay output. See [window validation](validation-window.json), [original comparison](compare-original-vs-trace.json), [recorder comparison](compare-recorder-vs-trace.json), [build pins](build-pins.json), and [run log](run-batch.log). The workspace/runbook history and phase1/2 results are documented in `../RUNBOOK.md`.
