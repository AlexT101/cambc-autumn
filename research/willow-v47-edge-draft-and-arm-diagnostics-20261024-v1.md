# Edge draft screen and bounded arm refinements

2026-10-24. Predeclared analysis using frozen f475, existing completed panels and the corrected public-map inventory. No new runtime, helper, source change or selector. Willow-first manipulation batches are excluded. Cambridge Battlecode rules remain authoritative.

## Economy strata and draft screen

Use only `provenance/khaos-v34-ladder-intake-20261024-v1/economy-inventory-v2/RESULT.{md,json}`; JSON SHA256 `16b31ee66e5dd98bb12b8ac2bbd2d42dfccaade467a0f34a27fdfe4fbdd463eb`. Version1 counted canonical-half storage incorrectly and is superseded. Version2 expands existing symmetry-aware map objects and crosschecks Gem Fields, Fracture and Big World against native extracts. Supplies are whole-map totals, not a team's accessible income. Ordinary rewards exclude entire groups containing a monolith.

The 40 maps comprise six three-pick, eight four-pick and 26 five-pick maps. The informative five-pick contrast is:

| Stratum | Maps and ordinary gem/gold supply | Question |
| --- | --- | --- |
| No ordinary gems | Contest: 0/640, no gem clusters, two monoliths | Is a non-Prism carry useful before any boss payout or stolen gems? |
| No gem clusters, rich ordinary gems | Boss Battle: 780/6800, two monoliths | Negative control for the incorrect rule “no gem clusters means no Prism growth.” |
| No gold clusters | Gem Fields: 364/600; Quadrants: 763/1320 | Does accessible gold conversion, rather than cluster count alone, justify replacing Vesper? |
| Low positive gem supply | Elk Arena: 72/1260, six gem clusters, no monolith | Later continuous-economy check without making zero a universal cutoff. |

No published map has zero ordinary gold. Vesper's eligible capture bonus applies beyond gold clusters; Prism grows from all carried gems. Contest is the only zero-ordinary-gem example here, not proof of a broad threshold. Fragment's two gem clusters and Fragment/Reverse Spiral's six gold clusters are the minimum positive counts, but they have three/four picks: the current five-pick substitutions do not test them.

Proposed small screen, scheduled by root and reusing exact existing cells where possible:

1. Contest and Boss Battle, both sides, versus the same frozen v33: the reviewed generalist-support Prism cost control, Stellar and Cassi recipes (12 cells). Keep all other draft slots/order fixed. This tests the support-enabled alternative while contrasting two zero-cluster economies with opposite ordinary-gem supply.
2. Gem Fields and Quadrants, both sides: unchanged Prism/Vesper recipe versus the existing Vesper-to-Vendetta recipe (8 cells, including reusable screen cells). These preserve the Prism/Willow pair. Compare actual Vesper gold uplift/recipient income, ordinary group conversion and combat losses; absence of clusters alone is not the decision rule.

The existing six-cell fixed-role screen is baseline3/6, Stellar1/6, Cassi3/6 (both Big World sides), Vendetta2/6. It is insufficient to set a selector, and the alternatives previously lost dedicated Prism/Willow service. Cassi occupies one draft pick but supplies two linked bodies, so count both bodies' work, deaths and bags; do not equate five picks with five actors. The support control may itself alter existing computation cutoffs, which is why it is retained rather than silently substituting the old baseline result.

Track outcome plus ordinary captures, first useful carry growth, support uptime/realized healing, camp clear/capture timing, carried losses and native statuses. These are mechanism readouts, not new pass/fail gates. A later revealed-pick experiment can put the flexible carry last, but needs a matching reordered-Prism control because actor IDs and activation order change. Only completed opposing picks may affect it. An observed short-range approach-heavy prefix can nominate Stellar as the alternative to test; it does not prove future enemy picks or justify an identity-specific rule. Map economy and actual ready roster remain necessary context.

## Approach casting: truth of a rejection is not value of a cast

The trusted `gem-fields-action-trace-prep/TRACE-RESULT.md` proves round6 Prism0 selected g4 and rejected value400 at center(21,23) because only one harmful member was hit. Round7 refuses damaging camp exposure. Mixed approach changes that first qualifier; it preserves exposure, value and native-target checks. Its 44/80 versus v33 is close to baseline45/80, while its 39/80 versus f475 and combination results do not establish a reliable benefit. No rigid one-loss veto is proposed.

The concrete missing comparison is action opportunity cost. `abilities.cpp:164–214` ranks capped weighted damage across live targets. `cast_at_camp_on_approach` (604–637) executes before bot.cpp:2429–2430 obtains attack-tile movement. A successful cast consumes the activation's movement opportunity and one cast slot/cooldown. At the known round6 state, 400 total damage does not mean 400 damage to the group's critical surviving attacker or that any cluster is killed. Immediate HP removal can overlap work an already committed teammate would perform; arrival/basic timing or the alternate unit spell can matter more than total damage. None of this proves the round6 cast is bad, and none licenses ignoring the round7 safety refusal.

Minimal next evidence, after a changed mixed-arm cell is nominated: first accepted cast/move fork, current live target HP and which members die, damaging-member contribution versus total, own action/cooldown state, already-known teammate claim/readiness, and actual following clear/capture sequence. The useful refinement candidate is to compare the attainable cast's reduction in remaining clear work against the one-turn route/basic delay using the selected group's existing quote and actual spell geometry. Do not substitute an arbitrary higher damage threshold, credit uncommitted future allies, or add a per-group grid solver before establishing this fork. Harmless cleanup and a cast that kills the last attacker are distinct cases from damage spread over several survivors.

## Existing hop and escape forks narrow the next diagnostic

Read `first-fork-comparisons-v1/` and `own-view-firstfork-v1/` under the intake. Hop Reverse Spiral B first omits HoR7's priority14 publication at round4, replacing it with end turn. Hop Fracture A round6 Prism0 starts (6,6), full700 HP, zero gold/gems and empty consumables; both cancel recall and move to (7,7), then baseline records a blocked movement at (7,9) before recall while candidate goes directly to recall. No camps/enemies are fully visible in that start view. Channel type1 is recall, not teleport. The recorded block does not by itself identify the production caller or the cause of its omission.

These are pre-activation candidates for changed search/cutoff/bookkeeping, not demonstrated farm-hop execution. Zero purchases alone is weaker than accepted teleport/consumable records because initial inventory/other acquisition must be checked. Existing altar-channel terminal handling also changed in the arm. Before refining teleport economics, identify whether the actual first differing caller is quote work, normal path fallback, priority tail or terminal ownership, using a bounded exact-prefix trace only if needed.

Escape Elk Arena A is more specific: at round10 HoR4's same 790HP start with four visible enemies, baseline rolls over before actions; candidate moves/dashes/attacks then rolls over. Baseline executes that same action sequence in round11. The new no-visible-enemy camp dash cannot own the observed dash. The separate escape outcome note gives the minimum admission-versus-fight/retreat trace and a direction/dash-only control. Keep that admission hypothesis separate from hop's omitted blocked attempt and from approach-cast value; they are different first forks, despite sharing final losses.
