# Deadline-bound Starvation diagnostic

Source aggregate `46c5b558…`; the only gameplay change is the reviewed optional walking-distance upper-bound in the existing deadline predicate. This four-cell diagnostic used the ordinary draft, Release, fuel quantum 100,000, and the pinned 01starvation map. It is not a promotion test.

| A | B | Result (A–B submitted gems) | Round | Play rollovers (A/B) | Bot errors |
|---|---|---:|---:|---:|---:|
| deadline | f475 | 1124–304 | 1893 | 10/0 | 0/0 |
| f475 | deadline | 408–1024 | 1953 | 2/2 | 0/0 |
| deadline | v33 | 176–1084 | 1558 | 1/16 | 0/0 |
| v33 | deadline | 1006–440 | 1965 | 19/2 | 0/0 |

The candidate went 2–0 against f475 in this map and 0–2 against v33. It recorded 12 play rollovers across the two f475 games (10 by A-side Heart of Ruin, then one each by B-side Willow and Heart of Ruin) and 3 against v33 (one A-side Heart of Ruin, then two B-side Heart of Ruin). f475 recorded 2 rollovers total; v33 recorded 35. Every game had zero bot faults. These four outcomes are descriptive samples, not a general strength estimate.

Native counts come from the pinned replay-status auditor using the v1_0_3 compact timeline. The table uses games started; completed rounds are one fewer because the final round is partial. See `DEADLINE-STARVATION-RESULT.json` and `deadline-bound-native-audit/` for seed, accepted-input count, rollover actor detail and hashes.
