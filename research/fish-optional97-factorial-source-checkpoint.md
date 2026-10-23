# Optional97 factorial controls: source-only checkpoint

These two isolated exception-policy diagnostics complete the2×2 with the already run frozen parents. They are **not deployment candidates**. No source is changed in canonical337f or either parent; no build/runtime was run here. The intended initial four map/side cells are ElkArenaA/B and BossBattleA/B, subject to root approval after actual source review. Opponent remains the fixed roster emulator, not Fish's private bot.

| Cell | Directory | Source aggregate |
| --- | --- | --- |
| Upstream / throw (parent) | `bots/baselines/hyperion-upstream-fbda803` | `15dcd64d35c179a726c02d3e775b1e3f263f9a4c33b5a8c745e7b13f66dd802d` |
| Upstream / optional97 (A) | `bots/variants/fish-fbda-optional97-control-work` | `37c3ccb7aa7a21ba888ed109b0381a72fd8a35bab07f783def73e567c084311f` |
| Current teacher / optional97 (parent) | `bots/variants/willow-fish-old-draft-control-work` | `b8108db1504bc94d7125bb7af22d85b965cc7e66ac83e82f21218cbec1a9d48f` |
| Current teacher / throw (B) | `bots/variants/fish-current-teacher-throw97-control-work` | `e9a9a1824ed8567978d04a5f3683fd57e43f757dc7d56d374269cd8b9fac6902` |

A copies only the upstream parent's28 `src/*` files; B copies only the current teacher parent's29. Both contain no `.cambc`. The aggregate recipe from each bot directory is `shasum -a 256 src/* | shasum -a 256`. Independent manifests are `research/fish-fbda-optional97-control-source-manifest.sha256` and `research/fish-current-teacher-throw97-control-source-manifest.sha256`; their own hashes equal the respective aggregates above.

A changes **only safety.cpp**,9 insertions/3 deletions, reproducing the current parent's exact `stun_pending`/`make_slot` implementation. The raw buff import is unchanged; only error97 returns `nullopt` instead of throwing. The caller interprets unknown or positive pending stun as one allied arrival turn. Successful absent/duration0 stun adds no turn. Teleport handling, immune-ally exclusion, enemies/self/dead/not-visible branches and all other error handling are unchanged;98 still throws. No extra query, eager observation or persistent state is introduced.

B changes **only safety.cpp**,3 insertions/9 deletions, restoring the upstream parent's exact throwing implementation at those two hunks. Its other current teacher support/visibility/fuel code remains unchanged. Actual source slices covering the helper and caller were compared byte-for-byte to the relevant existing donor in each direction. Neither child changes draft, farm, role, gold, claim, move, or cooldown policy elsewhere. Canonical was independently repinned at337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39.

Full parent→child patches:

- `research/fish-fbda-optional97-control-source.patch`: SHA-256 `70b40d37e0075d2fa0a8a3e61b95d4d1f5279a2a57998b413846045aba0d8e28`.
- `research/fish-current-teacher-throw97-control-source.patch`: SHA-256 `a85127c99e57aeff27f05698816f84068040a5101b57fdb57d676a1e495418a7`.

Interpretation follows `research/willow-optional97-factorial-design.md`: report native rollovers, candidate/emulator caught errors and trajectories with outcomes. A caught throw truncates the remaining act; optional unknown changes both continuation and a conservative timing estimate. A no-caught cell can still differ through code generation/fuel or successful-path optional handling. Remaining upstream/current differences under the same handler are not automatically pure overhead. Preserve every parent and raw result rather than relabeling old runs.
