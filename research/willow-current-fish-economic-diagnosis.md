# Current Fish: history boundary and five-pick economics

2026-10-23. Existing source, metadata and finalized `analysis-corrected` exports only. No gameplay edit, engine, script or new export. The current live executables are **not source-identified**; no result below is attributed to local337f42a5 or to4c4eacc without deployment evidence.

## What4c4eacc establishes

Commit `4c4eaccefe61f63c5c7adc2ab06105e0ad36b8ec` is dated2026-10-23 15:06:05Z and adds a v40 baseline snapshot. The relevant historical comparator is **`bots/hyperion/src` at that commit**, tree `6445e26c4c3ffd3c1832467214927d302c2f6343`, not its newly added v40 directory. Its latest Hyperion source change was8e79338 (gold-paid valuation). Direct4c4→fbda803 comparison changes11 source files299+/83-, with no draft.cpp or draft_selection.h change: both use P/V/M/(density-selected Ryth or Vendetta)/HoR.

The presently saved Pantheon history pages01/02 establish the recent Fish342a group but do not link an older Fish match to a4c4 executable or establish its coinflip/slight-win rate. `research/hyperion/REPLAY-ANALYSIS.md` explicitly studies v38 at5b02a02; its830-game ladder aggregate and isolated Fish BossBattle win `ddbc8901-3` cannot be reassigned to4c4. The512-game50.2% reference to4c4 in CHANGES105 is an offline general-map comparison, not a Fish record. The user's commit identifies a meaningful source comparator; its date alone does not identify a deployed match.

The older saved Khaos_v32 Fish4–1 group is a separate record: five-pick2–1 on Monolith/Quadrants/BossBattle and four-pick2–0 on Swirl/Hooks. Its opponent used Cassi fourth/Ryth fifth. Recent342a uses Varg fourth/Cassi fifth, and a different five-pick map pair. Source, map and opponent lineup all differ.

## Current evidence and scale

Current group `342a1765-2345-4f3a-890e-79e83f6802a8`, created21:04Z/finished21:09Z, is1–4. Detail metadata SHA `6f9b98a71e8f605d92451fca24dbad5d47ec6eb773d6dd36ddacb7369df5e8ed` carries no submission version. Use `replays/Khaos-v-current-fish-history/group-342a1765/batch-run-01/analysis-corrected/`; original `analysis/` labels are superseded. All five-pick rosters decode to our P/V/M/W/HoR against Vesper/Vendetta/HoR/Varg/Cassi/Issac: five picks versus five picks, but five versus six bodies.

| Outcome, ours / Fish | Expanse | Big World |
|---|---:|---:|
| Score / end round | 658–1004 /820 | 536–1012 /964 |
| Captures | 59 /64 | 57 /54 |
| Capture gems | 777 /1004 | 994 /1049 |
| Final held gems | 119 /0 | 458 /37 |
| Camp damage, rounded down per actor | 137103 /144268 | 98358 /154503 |
| Deaths | 0 /4 | 0 /3 |
| Completed recalls | 51 /38 | 35 /44 |
| Willow actual healing | 1217 | 2259 |
| Native rollovers | 1 /unavailable | 7 /unavailable |

These are global outcome facts, not actor-known decision proofs. Native audits report zero BotError events for our team; opponent native error and rollover status is unavailable because its public timeline is absent. The zero own deaths rule out a death-driven explanation for these two losses. Healing was sparse in a mostly separate farm race. Instant conversion of final held gems would yield777 and994, still below1000; therefore simply banking the final bags sooner is not an established winning fix.

## Big World: low-growth harmless work and travel

Replay SHA `498c37cbd6fd6dbce563c048e863c83dba1fee81539803f8488eebf8d79ba828`, match `b51a5364-c7fc-4b94-9181-e694eae67834`, analysis directory `498c37cbd6fd6dbc`.

Willow3's engine totals show0 gold earned/spent,3965 camp damage,112 gems captured/submitted and2259 healing in seven casts. She makes825 moves and87 basics. All112 gems come from eight captures of group12: two harmless gem clusters,14 gems/0 gold. Its repeat payouts are142,244,345,489,594,691,796,896. Sampled Strength/Focus remain55/120. At345 she completes a14-gem recall from(13,15) to(78,11), then walks west. This is concrete repeated allocation with little stat growth and much travel, not proof that her particular route was avoidable.

Our Vesper1 also has limited growth:212 gold earned,0 spent,175 collected gems,5648 camp damage,635 moves and147 basics. He repeatedly captures group2 (three gem clusters,21 gems/0 gold), with occasional group0 (7 gems plus40 base gold). Fish's Vendetta earns2015 gold and does40465 camp damage; Varg earns1515 and does45963. Our Prism supplies62292 of98358 team camp damage while the other workers contribute much less. A Willow-only replacement would not automatically fix Vesper's allocation.

Prism's436-gem tribute begins943 for44 turns at altar(43,20), after group6's41-gem payout921. Fish wins964, before that channel finishes. Conversion timing matters, but our final capital is994, so neither the final tribute delay nor retained gems alone explains how to win. The early/midgame work allocation and growth deserve priority over a blanket late-bank veto.

**Own-view follow-up,344–350:** `actor-windows-followup/bigworld-candidate-willow3-A-r344-350.json` (relative to the group directory), SHA `9b7bfe747e038bdb1a2a14c127571c202f37bae747838a4d59b9b72e9e9108df`; provenance sidecar SHA `64fd20e6fef5a9006a18d7b1ff4c1394dad86d1068f12225afebc4bd690ed408`. Source remains `unverified_public_replay`.

At344 she is at(13,15), full700HP, zero gems/gold/items, with a one-turn recall remaining. At345 the view begins at her own spawn(78,11), carrying14 gems and still full HP with both abilities ready. She moves to(77,10) and begins a recall. At346–350 she cancels the four-turn remaining recall, moves one tile northwest and starts another; the final destination is(72,5). Every other champion is identity-only throughout. The departure turns expose no local camps. There is consequently **no visible injured recipient or local productive camp action** that a healing/formation helper demonstrably missed here. This does not reveal distant remembered camp beliefs or shared claims.

The cancel/restart pattern does not itself waste a turn: current `bots/hyperion/src/bot.cpp:5222` deliberately starts a free end-turn recall, which `continue_recall` at4106 cancels when it no longer wins a retreat/bank/shop comparison. Each sampled departure turn actually moves. The observed capture-payout recall is compatible with `capture_recall` at3306, which can overlap the channel with a held capture and set banking; current Willow's banking protection at4472–4512 then precedes formation. Those are **source-compatible explanations, not recovered live branch identities**. The export omits shared memory, live altar usability and native movement readiness; it cannot show which altar/field or claim caused this particular route. Static altar coordinates alone do not certify the route through walls.

This window therefore narrows the economic issue to the repeated low-growth job/travel cycle, rather than proving a missed heal, unnecessary shop trip or recall-cancellation defect. The source-compatible route may be locally sensible after taking the14-gem job. A correction needs the earlier candidate comparison—selected group12 versus an actually reachable unclaimed growth job, with full clear/capture/bank travel and current HP—not a rule that zero-gold work is always bad. Keep the controlled draft/policy comparison below ahead of an ungrounded route patch; no further export is requested here.

## Expanse is a different economic case

Replay SHA `3f384ec685eb3d6cd07598f578717ca5270f05b0ca5a349763d02323e3c58a79`, match `65642cbd-2c7c-4cba-a769-5a612f817c1d`. Our team deals95% of Fish's camp damage but captures77% of its gems. Willow does20705 camp damage and earns712 gold; Vesper does33386 and earns2201. Thus the BigWorld zero-gold growth pattern does not generalize to both maps. Fish's six-body coverage, job reward mix and capture ownership are hypotheses; a missing heal or combat collapse is not supported. Do not request a second generic window until group-level resource choices identify a precise opportunity.

## Implication for a fallback experiment

The observed losses justify testing a pure economic-worker alternative on large public layouts with sparse useful healing, but not a named-team rule or an asserted source regression. A revealed-prefix experiment is feasible as described in `willow-counterdraft-observation-timing.md`; recent Cassi is fifth and remains unknown at our final choice. Keep separate controls for4c4 whole policy, latest teacher draft, and latest Willow draft, because changing the fourth role is not reverting107/108 or the support code. Reordered HoR-fourth detection additionally needs its reordered-Willow control. Establish current actors' knowledge and real alternative-job cost before changing farm valuation; neither zero gold nor low heal volume alone proves a feasible better choice.

For the initial controls, prefer **no draft reorder**. Freeze three arms: (A) exact4c4 Hyperion source and native teacher draft; (B) current337f gameplay with only its five-pick role list restored to teacher Ryth/Vendetta fourth, HoR fifth; (C) unchanged current337f Willow fourth, HoR fifth. B versus C isolates the role replacement on current gameplay; A versus B separates intervening policy/fuel changes while holding the native draft rule constant. A versus C alone conflates both. Keep three/four-pick drafting unchanged, pair map/physical side, and report actual roster and native rollover/error counts alongside economic outcomes.

If actual opposing WASM is unavailable, a **single frozen local opponent policy with the observed ordered roster** Vesper/Vendetta/HoR/Varg/Cassi&Issac is a composition emulator. Use the same opponent implementation for all three arms; never describe it as Fish's micro, training or item policy. Historical Cassi-fourth/Ryth-fifth is a separate roster-control cell. Expanse/BigWorld are mechanism checks, not a selector-fitting sample; use a separate five-pick panel to test any generalization.

An optional conditional fourth-slot child now matches the actually known Vesper/Vendetta/HoR prefix on native five-pick maps; it does not add a map-area threshold. It preserves existing pick order outside activation and reproduces teacher fourth/HoR fifth on activation. It cannot distinguish Varg versus Cassi continuation and accepts that uncertainty explicitly. No delayed fifth-pick decision is needed. The old-draft control and conditional are implemented as isolated source-only children, independently reviewed in `willow-fish-draft-controls-source-review.md`; neither changes canonical337f. Root authorized the initial12-game Expanse/BigWorld, both-sides comparison of exact4c4/current old draft/current Willow against a clearly labelled frozen roster emulator. Conditional runtime is not yet authorized, and no result from that comparison is claimed here.
