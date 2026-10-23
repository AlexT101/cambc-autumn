# Willow forecast value V2 source checkpoint

2026-10-23. Separate source-only `bots/variants/willow-fbda803-forecast-value-work/src`, cloned from frozen latest forecast647a. Root approved two bounded value-only admission changes and the recognized-state epoch dependency below. No canonical/draft/turn-order edits, build, engine, runtime, scripts or new instrumentation. Original647a remains frozen for gate measurements; no activation cause or performance gain is claimed from theory alone.

| Artifact | SHA-256 |
|---|---|
| Parent forecast aggregate | `647a10e00c51290b2ba4a38b4cdc93a5f6c258c331d40cb3b1a23610ddbfeb1d` |
| Integrated latest base aggregate | `337f42a54beb5890109e56b755237d8ea0d07abb240d095778f01e2098ab7b39` |
| **V2 aggregate /29-file manifest** | **`0bac63b780ffcb0437d6d1a387ee02df4f9394a91e0719140339d7f2d67b03fe`** |
| `src/bot.cpp` | `c6ca2199854d1fa78e158f331adc1fdae127c800b7454fbd01e1e60d1d860377` |
| `src/world.cpp` | `18929e4092cb102b15beaac65c001b4221ca6706c99e0fa028cab71598803f97` |
| `src/world.h` | `438025c204d553e634a32647917ff6993f595c2dbc4c29dfc09c81b53de3b6ab` |
| Delta from647a | `7b7e1a3320839d8dc6aef89f9b0a1ffd290c5b9e87a394f674c48940c0d697ca` |
| Combined delta from337f | `eaf2eaa4f54fce07515b4982435f50271523c37190dac38d42d795e60486ed56` |

Artifacts: `research/willow-fbda803-forecast-value-from-647a-source.patch`, `research/willow-fbda803-forecast-value-from-337f-source.patch`, and `research/willow-fbda803-forecast-value-source-manifest.sha256`. Aggregate recipe from each bot directory: `shasum -a 256 src/* | shasum -a 256`; the manifest is the first command's exact output. Parent delta is3 files,14 insertions/5 deletions; combined base delta3 files,105 insertions/3 deletions. All26 other files match647a/337f. Only `src` is present, no `.cambc`; whitespace check is clean.

## Two value changes

1. Copied current visible-worker admission no longer requires `completed_turn`. Every other record, positive HP/top, offspawn/range, channel/kept-recall, shield-capability, claim/work, fresh damaged/awake member, unique visible target and projected-worth gate is unchanged. This makes a conditional forecast from an unacted worker's present station; it does not promise that the worker stays, tanks, receives a heal or acts before an enemy. No turn-order policy changes.
2. The existing49-cell stationary-basic veto can skip a camp spawn only for a currently certified cleared/respawning group. Alive groups, including harmless live clusters, still veto; unknown and stale group information still veto. No member-coverage logic, extra grid extent, field or native read was added.

## Explicit freshness dependency

`World::update_camp` can stamp `state_round` even when raw group-state enum0 leaves a previous cached state unchanged. Therefore current `state_round` plus cached cleared/respawning alone is insufficient. Existing `asleep_read_epoch` already certifies recognized1/2 group-state success for Willow; V2 extends its stamp to recognized3 after the existing successful native group-state/cooldown return. No field or query is added. Header comment now states that this epoch also certifies recognized lifecycle state; asleep member bits remain zero for respawning groups.

The veto exemption requires **all three**: current `state_round`, matching `camp_observation_epoch`, and cleared/respawning state. At a new group observation the epoch and asleep bits reset before the native read. Unknown enum0 or an exception cannot earn a recognized epoch. `observe()` increments the observation epoch, so a same-round re-observe without fresh camps conservatively expires the exemption. Inferred/comms lifecycle updates do not create a recognized current-round certificate.

The only existing production epoch consumer is `sleeping_escape_members`: after its epoch/round guard it skips cleared groups and rejects every nonalive state. Thus recognizing respawning3 cannot admit a new sleeping transit; its asleep bits are still zero and no alive-member safety proof changes. Root/Astra reviewed this narrow dependency before implementation.

## Unchanged boundaries and handoff

Parent must still have selected a ready-heal zero-gain MOVE, with no current worthy heal, protected work, active own clear, leave or expired formation. Current enemy/output veto, one recipient finalist, parent upper bound, LOS, strict Willow station safety and real native healing stay unchanged. Forecast never enters an HP reserve; no future health, shield, damage sharing or saved turn is credited. Original move/refresh/failure behavior, claims, actual productivity/route-progress rules and four-turn expiry remain exact647a.

The broad old0e zero-marker observation and latest647a gate counts must remain separately attributed. This V2 intentionally combines two theoretically defensible false-negative removals; neither is yet a measured cause of zero activation. Root/Astra actual source review precedes any Luna compiler/runtime use, and further changes wait for actual original-gate counts. Future measurement must include recipient departure before camp phase, actual next-turn healing/work, wasted moves, expiry and fuel, not just an increased activation count.
