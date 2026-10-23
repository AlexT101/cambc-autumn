# Willow forecast formation source checkpoint

2026-10-23. Source-only isolated `bots/variants/willow-forecast-formation-work/src` from frozen a00fff. Implements the root-approved design `research/willow-forecast-formation-design.md`, SHA `ae5e4eba6bdb03e1bb92f6b98e02e0d473c8707222fa4c07be0b1e1642cca440`. No build, engine, extraction, runtime or scripts were invoked. Canonical, frozen parents, Monolith and four-pick sources remain unchanged; newly fetched upstream108 is not included. No new fuel gate, item/draft policy, mailbox or persistent state.

| Artifact | SHA-256 |
|---|---|
| Frozen a00fff parent aggregate | `a00fff454c1e48520968c9ba2d4c1ecdae0212ce019724dc06a6e959ddc3412e` |
| **Child aggregate** | **`0e989629893b451a0c164cac5757cf8b41eb1b2be36ef2766d1afc26a8bdfb59`** |
| Child `src/bot.cpp` | `803ad0f5f05b487a1f2ac93dfa7296087665537158c5715449a60fe4740d918c` |
| Full parent delta `research/willow-forecast-formation-source.patch` | `b2ae65a1587925ac5cdf40c552add256b2b555052870f9700f895573ea146ef7` |
| Independent29-file manifest `research/willow-forecast-formation-source-manifest.sha256` | `0e989629893b451a0c164cac5757cf8b41eb1b2be36ef2766d1afc26a8bdfb59` |

Aggregate recipe from each bot directory: `shasum -a 256 src/* | shasum -a 256`. The manifest is the exact first command output. Only `bot.cpp` differs:94 insertions/1 deletion. Child contains only `src`, no `.cambc`. Whitespace check is clean; all28 other source files match parent.

## Boundary and data

The unchanged `local_support` loop chooses its parent station first. The optional helper runs only for Willow with heal ready, no leave/protected work, unexpired formation, no active own clear, an already-selected move, zero current gain and no worthy current-heal target anywhere in the original bounded enumeration. The last condition deliberately over-vetoes even a currently worthy target whose LOS is unavailable. It never turns a parent stay into movement or changes Prism's branch.

Successful `visible_record` imports already made by the current-heal enumeration are copied before its worth filter and before any later import. The added scalar candidates require actual completed-turn state, positive current HP/top, range5, offspawn and no tribute/teleport or kept recall. No extra champion/readiness/channel/item/buff import is added. Candidate pointers refer only to stable World ally identities; native record pointers do not escape the copy. The helper and its scalar use finish before the original movement/observe path.

Nonself ally `shield==0` is not a shield-absence certificate: World only reads shield slots for enemies/self. This arm conservatively excludes every shield-capable recipient using champion facts, as agreed by root/Astra. Varg/HoR can still receive all parent current heals. Ordinary shield-free Marcella/Prism/Vesper remain eligible for forecast direction.

The helper requires a valid current comms claim, claimed-group cap16, current alive observation and observed damage this round. Actual current attack/hostile-ability reach must cover at least one positively observed live member. Forecast damage counts only current visible positive-health awake damaging members reaching the recipient, and only when that recipient is strictly nearer than every other currently visible live champion. Ties count zero; self position uses actual current origin. Unknown/nonpositive member HP never proves death. No group/awake/stun query is added. This is a conditional one-phase value forecast, not a guarantee against unseen or intervening actors.

Raw damage D must be positive and below recipient current HP. Forecast injury is0.63D, conservatively assuming both Jungle and Durability, with no future heals/shields or item ownership inference. Projected gain is capped by Willow's current heal amount and must pass unchanged `worth_healing` at projected HP. No forecast enters any health, escape, tanking or station-safety admission.

## Destination and preserved execution

Stationary-output veto is intentionally conservative: any visible live enemy within4, or any static camp spawn in the origin's7×7 basic square, retains the parent. This is at most49 direct grid reads, no target action or new camp import. Dead/unknown camp tiles can over-veto. This protects potential output rather than claiming an exact utility price; the approved open-terrain activation example still passes.

Qualified forecast recipients establish a conservative parent upper bound: every recipient within Chebyshev4 counts, even without LOS proof. A single finalist is ranked by projected gain, projected HP fraction, then stable champion handle. Only gain strictly above that bound proceeds to one exact recipient range4/LOS mask; if the current tile or parent already has access, retain parent. A failed finalist mask/access search does not try further recipients.

Alternatives reuse existing nine-station legal and strict-safe results, plus the original standability/cleared-camp-entry exclusion. Among stations reaching the finalist, nearer home wins, then fixed direction order. No new field/search/board or relaxation of enemy/teleport/camp safety is introduced. Willow's pre-support economy/escape path has already built these station results at this observation/origin.

Only `best` changes. The original one-move attempt, failed-move observe/fallback, successful observe/safety recheck and real `heal_ally` remain unchanged. Actual health/readiness decides the heal. Forecast success and alternate recipient are not productivity: no new claim, protocol, timer reset or route-progress term is added. Original actual output/healing and original Prism-work route-progress checks retain their effects; the four-turn formation budget is unchanged.

## Review and runtime handoff

Source inspection covers: parent stay/gain/protected work unchanged; not-ready/expired/active-clear decline; scalar copies before shared native-buffer reuse; completed-turn/channel/shield exclusion; current group damage/health/awake gating; unique-target ties; parent upper bound/equality; one finalist mask and deterministic station order; original refresh and expiry flow. No compiler or test runtime was used. Root/Astra actual review is required before Luna builds.

Native qualification should first demonstrate changed zero-gain moves and the approved two-round geometry, including both next-round actor orders and recipient departure/camp death. Measure actual delivered useful healing, subsequent recipient work/capture capital, lost output, expiry and fuel. Bound is at most8×16×visible-champion comparisons plus existing visibility tests,49 static origin cells and one finalist viewer mask. Extra scalar work still has fuel cost; no gain or safe saved turn is claimed from the forecast alone.
