# Isolated a67 plus c71be8c source integration

2026-10-23. Exclusive ignored variant `bots/variants/willow-upstream-c71be8c-work`, copied src-only from frozen a67. No canonical/branch merge, build, runtime, or script implementation. No fd99 or item-arm changes are stacked. Research EXPERIMENTS/CHANGES remain untouched by this integration.

Source aggregates use each file hash labeled `src/<name>`, sorted by the shell glob, then SHA-256 of that manifest (`shasum -a 256 src/* | shasum -a 256` inside a bot):

- Parent a67: `a67dc0a32d4b9d001a8c514dc86aa1d9f4aa9d91bc380f2df2ce59b649ce6d21`.
- Upstream c71be8c: `0834f33c8725407be898588dbac99e9338c92563c7065c92033a6d8f050e44fb`; source Git tree `eaf2a3101208ebf5ab85de9ab60418e2bfc42da5`.
- Integrated v1: `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd`.

Eight source files change against a67: bot.cpp, main.cpp, pathing.cpp, pathing.h, plan.cpp, plan.h, safety.cpp, safety.h. All upstream 7d59e56 terrain-table queue changes apply directly. Upstream647662a pathing.cpp/pathing.h are byte-identical in this integration; main.cpp and plan.h also exactly match c71be8c. Existing local Safety changes coexist with its new terrain-warming helper/declaration.

## Deliberate conflict resolutions

1. The generic `step_guard` adopts upstream's captured `here/radius` signature. Local Willow dispatch moves to `guard_steps`: Willow still calls its eager nine-station `willow_step_guard` with Pathing and retains the original outer stale check, while other champions use upstream's deferred generic callback. Both original decide guard-setting sites call this dispatcher. All other Willow-specific station setup, movement, guard clearing/restoring, observation refresh and Safety reconstruction sites are unchanged.
2. Plan execution saves/restores upstream `held_guard`/`restore_guard`, preserving an unmaterialized non-Willow callback. It retains the local conditional that clears a guard only for non-Willow actors. Willow's guard therefore stays active through concrete plan movement, unlike blindly taking upstream's unconditional clear.
3. Upstream anchored-search geometry skips reading a guard when only the current tile is a legal ending; the current tile was already removed from guarded endings. This skips a query, not an allowed endpoint. Willow's underlying station guard still exists eagerly even on these turns.
4. The local restored-health heal objective in Search::read_mates, optional unknown-ally-stun handling, credible threat helpers, local support/economy/escape logic, station indexes, support mailbox/comms endpoint cache, draft policy and all other a67 work remain. No research-number conflict is resolved here; root handles that during a later actual merge.

## Preserved before any build

- `parent-a67-src/` and `parent-a67-files.sha256`: complete frozen parent.
- `upstream-c71be8c-src/` and `upstream-c71be8c-files.sha256`: complete upstream source, extracted from exact Git ref.
- `integration-src-v1/` and `integration-v1-files.sha256`: complete integration, verified byte-identical to the working variant.
- `upstream-eight-source-files.patch`: exact a5749c4-to-c71be8c source delta.
- `upstream-table-queue.patch` and `upstream-lazy-pathing.patch`: exact native patches used for nonconflicting source pieces.
- `integration-v1-vs-a67.patch`: complete actual parent delta, SHA `465697930cd821ea4c36f9f45d72e39d1eb106fa0ca481aba15b5c2b4cd8bd92`.
- `integration-v1-vs-upstream.patch`: complete residual local policy against upstream, SHA `e4a819fae3270d9455c98f11e7d48a38af1d2c277b4bb1e9a0605a3093fb14e4`.

Canonical rehashed unchanged at a67; existing variants were not edited. Destination ignore rule and snapshot equality checked; diff whitespace check emitted no diagnostics. Astra actual-diff review is pending.

This is intended as a fuel-only integration. Upstream's reported replay identity is evidence for its own a574-based source, not this combined Willow policy. Deferred generic evaluation still observes World/Safety at first need and uses existing fuel gates. The terrain queue changes cache timing and may reach cold helper allocation/work. After source review, require paired Release/100M byte-identical replay validation against frozen a67 under our actual Willow draft before any strength comparison, followed by separate real-budget fuel/error validation. No equivalence, fuel gain, or match gain is claimed at this checkpoint.
