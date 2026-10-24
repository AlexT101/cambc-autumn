# Marcella combinations and the Stampede reversal witness

2026-10-24. Read-only matched-result/source/own-view review. No builds, games, new extraction or source edits. Exclude manipulated Willow-first batches; no public replay submission attribution is assumed.

## Matched outcomes justify combinations, not promotion

Evidence under `provenance/khaos-v34-ladder-intake-20261024-v1/`:

- `marcella-tribute-value-release-v1/RESULT.{json,md}`: candidate8701885d,42/80 against f475 (A28/B14),47/80 against v33 (A25/B22), zero native errors. Candidate play rollovers248/245 in the two separate panels.
- `f475-v33-complete-output-v1/RESULT.json`: exact common-opponent baseline45/80 (A22/B23).
- `missing-factorial-pairs-v1/hop-mixed-published-160-v1/{RESULT.json,results.json}`: candidate7e5dc37a,41/80 against f475,46/80 against v33 (A20/B26), zero native errors;304 candidate play rollovers against v33.

Join by exact map and candidate physical side, using explicit source roles/winner sides. Marcella versus common v33 gains9 baseline losses and loses7 baseline wins; hop+mixed gains9 and loses8. Marcella and hop+mixed disagree on21/80 cells:11 Marcella-only wins and10 hop+mixed-only wins, with36 shared wins. Their57-win union is an oracle description, not a forecast for a combined bot.

Marcella's gains over baseline: Ambush A, Gemfight A, Lanes A, Lost World A, Reverse Spiral B, Split A, Islands B, Yellow Brick Road A/B. Losses: Elkring A, Lanes B, Road of Riches B, Split B, Big World B, Fracture A, Starvation A. The two arms share gains on Ambush A/Lanes A/Reverse Spiral B/Yellow Brick Road B, and share losses on Elkring A/Fracture A.

| Marcella wins / hop+mixed loses | Hop+mixed wins / Marcella loses |
|---|---|
|Gem Fields A; Gemfight A; Lost World A; Quadrants A; Reverse Spiral A; Split A; Swirl B; Boss Battle B; Islands B; The Farm A; Yellow Brick Road A|Corners B; Fragment A; Gem Fields B; Lanes B; Road of Riches B; Split B; Big World B; Boss Battle A; Starvation A/B|

These changes are heterogeneous and strongly side-dependent. They are not direct evidence that a delayed-income bonus or teleport fired in each cell. Three-pick P/V/HoR contains no Marcella; a changed result there cannot establish passive-income activation. Existing fuel cutoffs/code layout and changed trajectories remain possible contributors. Escape-execution43/80 versus f475 and38/80 versus v33, compared with full escape36/37, remains a separate diagnostic rather than a reason to add escape to these next unions.

## Recommended three unions

Build/source-review **Marcella+mixed**, **Marcella+hop**, and **Marcella+hop+mixed** on exact f475. This completes interpretable interactions among income valuation, approach casting and mobility without requiring any individual arm to pass first. Preserve exact draft/opponent/map settings and compare each to the existing relevant parents against the same frozen opponents; both sides of all40 published maps are already the matched frame. Reuse existing parents rather than rerunning deterministic cells. A later fresh-map comparison is needed before release, not as a gate to testing these combinations.

- Marcella+mixed has separate-file edits (bot.cpp versus abilities.cpp). It tests whether better value selection and the reviewed attainable multi-target approach cast complement each other. No exposure or cast gate should be relaxed in the union.
- Marcella+hop shares the final solo-farm comparison/best-selection area in bot.cpp. Preserve Marcella's independent-health eligibility before partner rescue, all three optimistic pruning bounds, original claim mask, delayed rate and no-budget-credit rule. Preserve hop's independent quote, current topology/version checks, three source camp phases, landing phase4 and terminal-channel ownership.
- Triple should be the exact semantic union of those two, with abilities.cpp identical to the mixed parent. Verify opposite-order reconstruction where possible; any unavoidable adaptation must be documented rather than silently introducing a new policy.

**Important overlap:** `FarmHopQuote.worth` is the existing immediate `gems+gold`, while Marcella's bonus enters final selection as a separate `rate(B, delayed_cycle)`. Do not stuff B into the immediate hop numerator or spend it on the crystal. The simplest union leaves hop's existing economic comparison unchanged: the destination can win through delayed tribute value, while a hop must still justify its10-gold replacement cost through the old immediate quote. This conservatively omits the extra acceleration benefit for future tribute income; it neither double counts that income nor creates free shopping credit. Pricing that acceleration would be a distinct future policy experiment, not necessary for these unions.

Priority cells for interpreting any changed result are the existing conflicts (Gem Fields A/B, Boss Battle A/B, Starvation A/B, Big World B) plus the shared Fracture A loss. They are diagnostic strata, not a small cherry-picked replacement for the common panel. Follow the first actual action/quote divergence before explaining outcomes; no new broad trace request is made now.

## Stampede own-view: reversal is real; safe engagement is not established

Public Mite match `e36d7ae5-08c4-490a-82e9-67bbd9a75344`, own physical B Prism5. Payload `39b779628916b581cef73b2039c17d942b01a11bc28201de615e9f377e38b03d`. Read `ranked-refresh-v2/mite-prism-ownview/ANALYSIS-r506-514.md` and `stampede-mite-B-prism-B-r506-514.json`. Source/build unknown. Raw coordinates below; B own-frame uses y=49−rawY.

Prism has700/700HP,35Strength,80Focus, zero gems and no visible allies throughout. It moves55,29→54,30 at506, then alternates54,30↔53,31 through514 with no attack/cast. Its AoE cooldown reaches0 at511. Timer4 channel cancellation/restart is recall cadence (channel1 per the existing exporter mapping), not itself a defect.

At506 it sees awake damaged Elks11/13/15 at400/400/480HP and cluster45 at40HP, but the later observations contain no dynamic camp records. This must not be replaced by observer knowledge of a clear/hold. Enemy Vesper/Vendetta are visible at distances7–8 on most turns; none is visible at510. At511 Vesper is raw56,23,130Strength/100Focus,1924.4HP, reset cooldown3/dash ready; Vendetta57,23 has184Strength/110Focus,970.8HP, both slots ready. No allied support is currently visible. Approaching a nearby gem group is not the same as being able to contest it safely, even with both Prism casts ready.

The concrete useful question is why the chosen safe endpoint at54,30 becomes a retreat/alternate-goal endpoint53,31 on the following turn, including the511–514 repeated state. Possibilities remain threshold/contact-horizon changes, goal/guard mismatch, or deliberate waiting near a contested objective. This does not prove a remembered-camp route defect; f475 already contains the prior routing work and a bounded wider-route fallback (pathing.cpp637–650), and the public source is unverified. Do not reintroduce the Band repair from this visual pattern.

No further broad own-view is needed now. If exact source reproduction becomes available, the smallest useful private diagnostic is actor5 rounds511–512: actual home/leave reason, selected goal/group and dispatch, already-computed threat/stand outcome, guard status and selected endpoint. Determine whether the move is genuinely farm→retreat before altering it. Without that, retain the observed unproductive reversal and objective-allocation hypothesis, not a forced-engagement or no-reverse rule.
