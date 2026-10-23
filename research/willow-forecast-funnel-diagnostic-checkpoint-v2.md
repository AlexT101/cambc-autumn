# Willow forecast funnel diagnostic source checkpoint

Date: 2026-10-23. This is a source-only Debug diagnostic clone of the reviewed latest-source arm. It adds bounded reason/counter output only; it does not change gameplay policy, add SDK calls, call a skipped evaluator for logging, or edit canonical/frozen sources.

- Parent arm: `bots/variants/willow-fbda803-forecast-work/src`, aggregate `647a10e00c51290b2ba4a38b4cdc93a5f6c258c331d40cb3b1a23610ddbfeb1d`.
- Integrated comparison parent: `bots/variants/willow-fbda803-integrated-work`, aggregate `337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39`.
- Diagnostic clone: `bots/variants/willow-fbda803-forecast-funnel-diagnostic-work/src`, aggregate `92578884b914a98649eab69fa7a3e95ecf7c81e8edc5c70c3681c402ba9a9da9`.
- Only changed file: `src/bot.cpp`, SHA-256 `63cf04958bb4ffee686e5e5295f4f605c7e0820e0b6b30875cdcd5963c47a1ad`.

Instrumentation emits `WFFEARLY` at the existing early local-support gates, one `WFFLOW` row for Willow calls that reach the station comparison (ready/leave/protected/expiry/active-clear, enumerated records, completed-turn/shield/channel counts, current worthy targets, selected parent candidate and zero-gain-helper eligibility), and `WFFG` only when the forecast helper is actually entered. `WFFG` reasons: 1 visible enemy in stationary reach; 2 public static camp in the protected neighborhood; 3 no claimed candidate survived; 4 candidate did not exceed parent-access upper bound; 5 here/parent already sees recipient; 6 no valid strict-safe visible station; 0 a station was selected. The accompanying counters distinguish claimed, current, working, damaging and worthy groups plus existing rejection stages.

All output is inside `debug_block`. The counters and the equivalent conditional refactor are present in the diagnostic Debug source and can alter Debug codegen/fuel; there is no claim of exact Debug fuel parity. They do not alter gameplay decisions or add SDK/API/evaluator reads. The shield-slot check remains after the same short-circuit preconditions, so its call count and decision semantics are unchanged. This diagnostic is for a single native five-pick Elk Arena pair against integrated parent, Debug/default fuel, and is not Release/payload equivalence evidence. The map is the existing `01elk-arena.map26a`; no generated maps or new scenario search.
