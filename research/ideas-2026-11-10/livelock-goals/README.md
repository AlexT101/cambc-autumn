# Livelock: alternative goals and capture routing

2026-11-10. This continues the earlier [livelock investigation](../livelock/). Every release candidate uses the unchanged frozen base `variants/oc-coord-fuel497-f8a064fba6` (497). Ocean subsequently moved to 498; only a successful candidate's diff should be ported later. Nothing from this investigation has been promoted.

Large artifacts, logs and restart state are under `~/tmp-offload/livelock-goals/`. Current real-budget status (gains in percentage points, 95% CI half-widths):

| Candidate | Fresh gain | Fresh units | Decision |
|---|---:|---:|---|
| Altwalk | −0.051 ±0.250 | 11,264 | NARROWED, unresolved |
| Altdetour | −0.053 ±0.250 | 12,160 | NARROWED, unresolved |
| Yieldroute | −0.080 ±0.250 | 25,216 | NARROWED, unresolved |
| Farmleave | −0.537 ±0.354 | 16,768 | REJECT |
| Farmchannel | +0.119 ±0.249 | 11,776 | NARROWED (ZONE crossed), unresolved |
| Bankviahome | Pending | — | Queue-owned; targeted historical case improved |

No demonstrated overall gain from the completed arms. NARROWED is not statistical rejection. Bankviahome's independent 200k diagnostic is +0.244 ±0.750 pp over 1,024 fresh units, inconclusive. The sections below retain the sequence of hypotheses and historical intermediate reads.

## Capture routing: confirmed cause in local games

A 256-game debug census used fresh ladder-v2 pool f0, both sides against Flp4 noise 1, own drafts, engine 5.0.1, the native runner and shared CPU slots. `lg497-captrace` records successful capture yields (`LGY`) and decisions (`LGD`). These traces establish mechanism; release gates judge strength.

The baseline made 2,176 yield steps: 1,431 from its current farm/claim group, 727 while its goal and claim pointed to another group, and 18 without a farm goal. Of these, 389 were followed by returning to exactly the vacated tile next turn.

For example, in `captrace/246-mut-rushbait-v2-131200417027-21.repl26a`, champion 7:

- Round 220: yield capture 9, moving from (16,68) to (16,69).
- Round 221: choose farm 17 and walk back across capture 9 to (16,68).
- Round 222: yield capture 9 again, clearing the farm-17 claim and moving back to (16,69).
- Rounds 223–224: repeat the same cycle.

The occupied capture was not being selected as the farm target. It lay on the route to other work, and `yield_capture` interrupted that route with its first free step.

The original live Ryth replay could not previously be reproduced exactly. This confirms the same family of capture oscillation, without claiming an exact branch trace for that original replay.

[Yieldroute patch](yieldroute.patch): when the farm goal and claim refer to other work, and `holding_capture` already says we are not the holder, let ordinary goal selection and movement continue. There is no map-specific logic, threshold or persistent cooldown.

The corresponding 256-game debug census (`lg497-yieldtrace`) gives:

| Metric | Base | Yieldroute |
|---|---:|---:|
| Yield steps | 2,176 | 1,495 |
| Yields while aimed at other work | 727 | 114 |
| Immediate return to vacated tile | 389 | 193 |
| Yield-associated oscillation episodes, at least 6 rounds | 44 | 9 |
| Champion-rounds in those episodes | 288 | 56 |
| All oscillation champion-rounds | 7,667 | 7,671 |

Yield-associated oscillation falls 81%. Enemy-retreat loops dominate the total, which stays level. `antrace.py`, the `*-examples.json` files and `trace-mechanism.json` retain the evidence.

## Banking: another altar after a rejected approach

[Altwalk patch](altwalk.patch): a quiet bank-to-retreat reversal ending at the prior turn's start uses the existing `avoid_altar` mechanism to try another reachable altar for the duration of its walk. There is no fixed gem threshold.

The original case's preserved source is `~/tmp-offload/livelock/ws/bots/ocean`, which contains opponent/priority changes beyond 494. A first diagnostic on 494 therefore did not reproduce the live game. Corrected diagnostic variants copy that preserved source and add only the tested patch.

With `lg-live-alttrace`, champions' positions match the original through round 840. Prism first diverges in round 841, walks to the opposite altar, and completes its 536-gem tribute in round 917. The original game was won in round 1001. The opponent is a puppet following recorded inputs after divergence, so this demonstrates the route, not a strength gain.

That trace exposed a second failure: Issac repeatedly changed which altar it avoided because both routes began at the same unsafe step.

[Altdetour patch](altdetour.patch): retain the alternate-altar commitment for its travel time, and route around the observed rejected tile. The historical-source diagnostic gives these period-2 reversal counts during rounds 842–882:

| Ally id | Original | Altwalk | Altdetour |
|---|---:|---:|---:|
| 0, Vesper | 26 | 33 | 33 |
| 1, Cassi | 6 | 3 | 0 |
| 2, Issac | 13 | 10 | 5 |
| 3, Prism | 34 | 5 | 0 |

Vesper still loops: his trace begins with farm/retreat cycles at rounds 845–849, then changes to bank/retreat cycles from round 853. The `lg-live-bankreason` and `lg-live-workreason` diagnostic traces identify the miss: Vesper is really banking (`memory.banking=1`), but his bank step is a failed detour that increases altar distance (8→9). Retreat moves back (9→8), so the rerouter's directional check rejects it. No attack engagement is recorded on those turns. A follow-up [Bankgoal patch](bankgoal.patch) detects exact reversals after actual banking, including a failed detour; it keeps the quiet-action and alternate-goal commitment filters. Its historical-source smoke lowers Vesper's reversals from33 to21, but moves the loop onto a neighboring tile. Retaining every rejected tile during that commitment ([Bankedges patch](bankedges.patch)) lowers them to16 and explores more positions, but still does not leave the boundary until the enemy channel ends. Neither refinement has been release-gated: these are incomplete route fixes, not demonstrated wins.

### Fuel concern checked, not confirmed

The helper reserves one full distance field but could request several altar fields. A diagnostic-only trace (`lg497-altdcost`) measured 243 calls across 256 fresh-map debug games. All finished within the same round. Cost was median 870, p99 2,284, and maximum 2,342 fuel; at least 15,887 fuel remained afterwards. Fields were effectively already cached in these situations. This sample does not justify a fuel revision. Results: `altdcost-stats.json`.

## Farming: stop retrying the same blocked goal

The 256-game baseline census contains 4,803 exact farm-to-retreat reversals, 4,801 preserving the same farm goal, compared with 851 bank-to-retreat reversals.

[Farmleave patch](farmleave.patch): suspend that failed group, clear its claim, and let farm choose other work. The anchor is the nearest visible enemy at the failed approach—a proxy, not proven causal attribution. The suspension ends when that enemy moves, dies, or is no longer tracked. There is no time or gem threshold.

The historical-source puppet triggers this change as early as round 40. Its subsequent changed outcome does not isolate the reported late tribute.

## Tests

The immutable release candidates are `lg497-altwalk`, `lg497-altdetour`, `lg497-yieldroute`, `lg497-farmleave`, and `lg497-farmchannel`. Each uses standard fgate against frozen 497: fresh ladder-v2 maps, Flp4/Mt3q, release, own drafts, engine 5.0.1. High-SPRT H0 alone is not rejection. Logs are `fg-<arm>.log`.

Each also completed an eight-block 200k-fuel diagnostic using a private copy of fgate with distinct `e501f200k` cache names. Each has 1,024 fresh map units; entries below are paired gains in percentage points, with 95% CI half-widths.

| Candidate | Fresh gain | Outcome |
|---|---:|---|
| Altwalk | +0.024 ±0.637 | Inconclusive |
| Altdetour | +0.415 ±0.698 | Inconclusive |
| Yieldroute | −0.562 ±1.167 | Inconclusive |
| Farmleave | −0.366 ±1.383 | Inconclusive |
| Farmchannel | +0.024 ±0.414 | Inconclusive |
| Bankviahome | +0.244 ±0.750 | Inconclusive |

Real-budget gates continue. See `STATE.md` and the logs for their latest reads.

## Narrow channel response

The broad farm version starts changing routine contested farming in round 40 of the preserved game. [Farmchannel](farmchannel.patch) tests a narrower response: suspend the failed group only while the nearest visible enemy is actively tributing, and release it when that channel ends. Movement, death and lost tracking also release it. This tests channel standoffs without a gem cap or timeout. It does **not** fire in the reported historical case: Vesper's early F/R reversals take 12.6 camp damage, so the quiet filter excludes them, and his later loop is banking. The unchanged positions through that period confirm the coverage miss. It is a separate candidate, not a combination of other patches; its real and 200k gates are running under `fg-farmchannel{,200}.log`.

## First real-budget conclusion

Altwalk reached NARROWED after 88 blocks / 11,264 fresh map units: −0.051 ±0.250 percentage points (95% CI), with Fish −0.098 ±0.349 and Mite −0.004 ±0.360. Low LLR +1.137, high −10.394. It is not promoted: the route change has no demonstrated overall gain. This is a precision stop, not a statistical rejection. The other four real-budget gates continue.

## Complete a retreat after a failed bank approach

A separate [Bankhome patch](bankhome.patch) tests another destination directly: after a quiet, exact reversal from actual banking, retain the decision to retreat until reaching spawn (or dying). It uses the existing retreat movement and recall safety checks, rather than a timer or gem cap. This is independent of the alternate-altar variants. The historical-source smoke lowers Vesper's reversals to5 and Prism's to2, but both complete several recalls and then walk back toward the same blocked altar. This replaces a two-tile loop with a longer trip; it has not been release-gated. The next [Bankviahome patch](bankviahome.patch) tests a recall fallback only after the alternate-altar route also reverses, retaining that alternate destination through the recall. This smoke produces useful departure: Vesper recalls in round860, walks to the alternate altar and finishes his20-gem tribute in round878, before the enemy finishes. Issac banks17 in round896. Reversals in the reported window are[6,0,4,0], versus original[26,6,13,34]. The opponent remains a puppet after divergence, so strength is unproven. A real-budget fgate against frozen497 has been handed to the priority queue; the independent200k diagnostic completed8blocks at+0.244±0.750pp, inconclusive. Source fingerprints are in `bankviahome-source.json`.

## A release failure case for broad farm refusal

A selected changed outcome from the fresh gate, `gen-ladder-131200100053`, our team B against `spar-dvn1-Flp4`, was rerun at release settings to retain complete replays. Both outcomes and round counts reproduce exactly: baseline wins in903 (1064–576 gems); farmleave loses in983 (667–1024). These retrieval reruns add no independent statistical sample.

The first observed state divergence is Issac's position in round394. Later trajectories change broadly, so the final loss cannot be assigned to one skipped camp from this trace alone. The candidate actually earns more total gold by its later finish (2772 vs2435), but loses Prism with263 gems at634 and42 at839; the baseline's only death is Tavi carrying16. Increased movement or income alone therefore does not establish a useful fix. The paired gate remains the decision evidence. Full replays/extraction and `farm-loss-evidence.json` retain this case.

The capture routing census's reduction also appears in both structural map classes: immediate yield returns fall110→56 on56 one-site games, and279→137 on200 multi-site games. This does not justify restricting the fix to one-site maps merely because that win-rate subset currently looks stronger. `yield_subsets.py` and `yield-subsets.json` retain the descriptive counts.

## Second real-budget conclusion

Altdetour reached NARROWED after95blocks/12,160fresh units: −0.053±0.250pp95%, Fish−0.012±0.344 and Mite−0.095±0.366; ladder−0.033±0.259, pooled−0.043±0.180. LowLLR+1.100, high−10.434. No demonstrated overall gain; unresolved precision stop, not statistical rejection, and not promoted. Three earlier real gates continue; Bankviahome's real gate is queue-owned.

## Farm suspension gates concluded

Broad Farmleave reached **REJECT** after131blocks/16,768fresh units: −0.537±0.354pp95%, ladder−0.587±0.359, pooled−0.562±0.252; Fish−0.340±0.486, Mite−0.734±0.515. LowLLR−3.156, high−8.906. This is a confidence-supported loss, consistent with the retained release failure case.

Farmchannel reached **NARROWED (ZONE crossed)** after92blocks/11,776fresh units: +0.119±0.249pp95%, ladder+0.079±0.262, pooled+0.099±0.181; Fish+0.170±0.343, Mite+0.068±0.360. LowLLR+3.785, high−7.856. No demonstrated overall gain; unresolved, not a statistical rejection. It misses the reported historical loop, as documented above. Yieldroute continues; Bankviahome remains queue-owned.

## Capture routing gate concluded

Yieldroute reached NARROWED at197blocks/25,216fresh units: fresh−0.080±0.250pp95%, ladder+0.275±0.223, pooled+0.097±0.167. Fresh Fish+0.206±0.336, Mite−0.367±0.366; one-site+0.178±0.449, multi-site−0.173±0.299. LowLLR+0.689, high−10.874. No demonstrated overall gain on fresh maps despite the measured81% reduction in yield-associated oscillation. Unresolved, not statistical rejection. All earlier arms are concluded; Bankviahome remains queue-owned.
