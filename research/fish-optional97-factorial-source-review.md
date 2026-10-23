# Optional97 factorial: actual source review

2026-10-23. **Both children pass source review for the diagnostic.** No build, runtime, gameplay edit or release approval. Recomputed both aggregates and compared the complete source directories to their frozen parents; only `safety.cpp` differs, matching the pinned two-hunk patches.

| Child | Verified aggregate | Parent-relative delta |
|---|---|---|
| Native fbda + optional97 | `37c3ccb7aa7a21ba888ed109b0381a72fd8a35bab07f783def73e567c084311f` | 9+/3-,28 source files |
| Current teacher + throw97 | `e9a9a1824ed8567978d04a5f3683fd57e43f757dc7d56d374269cd8b9fac6902` | 3+/9-,29 source files |

Checkpoint `fish-optional97-factorial-source-checkpoint.md`, SHA `f6a4166293aa857b4f71cc58a223dac3c6253d5e6db13f23edc5d6a214a7d70a`; patches SHA `70b40d37e0075d2fa0a8a3e61b95d4d1f5279a2a57998b413846045aba0d8e28` and `a85127c99e57aeff27f05698816f84068040a5101b57fdb57d676a1e495418a7`.

The optional child retains one raw buff import and returns unknown on97 before reading its buffer. All other errors still pass through `ok`. Successful absent/duration0 stun is false; positive duration is true. Caller delays positive or unknown by one turn. Enemy/self/dead/invisible handling, visible ally acted timing, teleport delay and stun immunity gates are unchanged. The inverse child restores exactly the old bool/throw helper and caller. `<optional>` is already supplied by `safety.h`; no declaration/API mismatch or persistent state is introduced. Parent sources, roster and all remaining policy stay unchanged.

## High-fuel comparison: useful but diagnostic only

After the default-budget factorial, comparing safe-handler37c3 against safe-handlerb810 on Boss Battle A/B at100M is a reasonable **four-game diagnostic**. Use the same Release WASMs rather than rebuilding in Debug, identical map bytes/emulator/side setup, and verify actual native rosters. Compare extracted action/state timelines or normalized action payloads, not ZIP bytes polluted by source labels, logs or timestamps. Retain default100k results separately. If the budget override also applies to the emulator, say so: the high-budget opponent is a different operating condition despite identical WASM.

- If both safe-handler codebases converge to identical full gameplay timelines at100M while diverging at100k, that strongly supports a budget-mediated integration effect in these cells—rollover, existing search/analysis gates, or code-generation cost. It does not identify which cost or certify every other map.
- If they still diverge at100M with no relevant exhausted budget, inspect the **first** differing action/state and its prior observation/claim inputs. This nominates a residual active effect; it is not automatically a semantic-policy proof, since existing fuel-sensitive branches must still be checked.
- A shared winner or similar totals is insufficient for either conclusion. Different high-budget trajectories that happen to win do not validate a default-budget release. Caught97 can remain at high fuel, so retain candidate and emulator error audits.

Native fbda's actual strata also prevent an overstrong integration-only inference: teacher Vendetta4c4=18/24,fbda=13/24,current teacher=10/24; teacher Ryth13/28,17/28,15/28. The nearly equal whole-panel4c4/fbda totals hide an upstream dense-cell deficit and sparse-cell gain. Both upstream and integration interactions remain possible. The factorial isolates the integration handler boundary first; it does not erase the upstream question or authorize a whole-old-policy map exception.

Restored throws are an experimental factor only. If they improve outcomes, diagnose the continued action that became harmful and seek a correct continuation; do not release an exception-abort policy on that evidence.
