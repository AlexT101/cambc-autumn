# Independent ready-heal source checkpoint

2026-10-23. Separate source-only child `bots/variants/willow-audit-ready-heal-work/src` of frozen c71fc, implementing Astra's `willow-independent-ready-heal-design.md` and root's approved two-scalar admission plumbing. Only `bot.cpp` changes: 109 insertions/4 deletions. No builds, engines, extraction, scripts, new fuel gates, canonical/release edits or EXPERIMENTS changes. This is an unqualified future gameplay experiment.

| Artifact | SHA-256 |
| --- | --- |
| Frozen c71fc parent source aggregate | `c71fc5730dc64f0463faea9c2edd6ef3a849332b86e5264ae4720c223b482d83` |
| **Child source aggregate** | **`06b266efc20e36955c22ea9db743e1a71ea9ab9eb82463825f8284f0af33f68f`** |
| Changed `src/bot.cpp` | `b5fec677cc38f3aa40279bebe7c9a9edffc3cfba151f3b00a44a0c2d8ecaf5cd` |
| Full parent→child `research/willow-audit-ready-heal-source.patch` | `d293e57cc8b1a9b36d90104b8d45ccb4c3a86d2102c1febe617b1934a7b4c2de` |
| All29-file `research/willow-audit-ready-heal-source-manifest.sha256` | `06b266efc20e36955c22ea9db743e1a71ea9ab9eb82463825f8284f0af33f68f` |
| Reviewed design | `c74eb43b38530e1e714d8c8ce12a3a42e3287bf8681ec4b4142b68ce23125bde` |

Aggregate recipe: `shasum -a 256 src/* | shasum -a 256` from the bot directory. The manifest contains that first command's exact output. Parent aggregate rechecked unchanged; child contains only `src`, with no `.cambc`.

## Admission plumbing and preserved behavior

`willow_economy_or_escape`4465 gains an optional protected-work output, initialized conservatively true. It is filled only from the original actually computed capture/bank/shop booleans; imports, short circuit order and all existing decisions remain unchanged. Its act-tail caller uses the default null output. `decide`5106 keeps the result without a second economy query.

`local_support`4830 gains an eligibility output initialized false. It becomes true only after the original mate alive/visible/can-act/live-record gate and existing observed-channel/kept-recall test. The original controller still runs first with its original protected-work calculation and ordering. Eligible but stunned Prism remains eligible: `can_act` checks life/respawn only. Missing-Prism rosters do not enter formation and leave eligibility false. No duplicate mate live-record, kept-recall or shop query is added to determine helper admission.

The new caller5125 requires Willow, no mend/leave/strikes/stun/protected economy, no eligible mate and no support ownership/retreat. An existing controller action returns first. All non-Willow actions and eligible-Prism controller decisions remain behaviorally unchanged apart from the bounded scalar stores/arguments.

## Immediate service contract

`willow_independent_heal_step`4758 requires actual movement and ready heal/cast with no own channel. It reuses the existing cached nine stations/guard and strict enemy/camp safety, with additional stun/imminent rejection at origin and destination. No path search, field, board construction or camp query was added. Cleared camp tiles cannot become new heal destinations. All latest teleport-aware threat and transit behavior remains inherited.

Visible living off-spawn allies within5 use fresh visible records, actual capped gain and generic `worth_healing`/kept-recall rules. Recipients can be stunned or channeling where generic healing allows it; mate can-act restrictions are not copied. Any worthwhile current visible ally in range4 declines the walk before the new price threshold. Root explicitly approved that live unit visibility plus range is actual unit-heal reach, including ward sight; candidate movement still requires `attack_viewers`/`support_view` sight certification. No hidden target is admitted by distance alone. Target storage is bounded to the existing eight-slot convention and contains copied positions, values and sight masks, not live pointers.

New movement requires actual gain strictly greater than three current Monster-adjusted basic hits, without the low-health exception bypassing that price. `immediate_camp_finish`4742 uses existing nearby groups and current visible member observations only. A member in current basic range that could die to two basics vetoes; stale/ambiguous health, including zero health in an alive group, also vetoes. Fresh known cleared/respawning groups skip. This charges the ready-reset upper bound even when reset is unavailable and may conservatively reject a useful heal; it is deliberately not a prediction that reset can actually be spent. No readiness call, future heal credit or recall-saving estimate is added.

Selection maximizes real gain, then lower target HP fraction, then retains deterministic existing station order. One move is attempted after stale validation. Both success and failure call `see_again`; all cached target/station choices end before refresh and are not reused afterward. Success marks ephemeral `support_owned`, performs fresh real `heal_ally`, sets decision `h` and owns the turn even if the target disappears or healing fails. Existing act-tail ownership prevents reset/farm/strike/recall followup; no Memory claim, formation timer, mailbox or offered/requested health promise is written. Failure returns to ordinary selection with fresh guard/World; newly unsafe origin uses existing support-retreat handling, preserving at most one successful walk. No same-target retry loop was introduced.

Debug-only `WIH` records a selected move and present gain/price, and `WIH-DONE` records actual move/heal outcome. These are mechanism lines, not a full diagnostic framework.

## Review and runtime handoff

Read actual full delta and caller/refresh/act-tail seams; whitespace check emits no diagnostics. All28 other source files are identical to c71fc. No compile or runtime validation is claimed. Root/Astra actual source review must precede Luna's build. Review priorities: conservative output initialization, exact mate eligibility and existing short-circuit/import ordering, no heal-target pointers across refresh, failed-move fresh safety, at-most-one successful move, real current healability including ward sight, and bounded camp-finish veto. Runtime should first establish legality, bounded cost and actual admission/benefit, including no-Prism four-pick rosters, unavailable/channeling versus eligible-stunned Prism, current-tile heal, blocked move, recipient change, small gain and resource finish negatives. Broader comparative results remain necessary before qualification.
