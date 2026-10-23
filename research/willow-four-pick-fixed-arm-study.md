# One fixed four-pick Willow arm

2026-10-23. Read-only design study; no source, tooling or runtime changes. Recommendation: after the current candidate is qualified, test exactly **P/V/M/W against P/V/M/HoR**, keeping the same gameplay code, first three picks, and all three-/five-pick choices. This is a plausible experiment, not a recommended replacement or map selector. Keep the pending Monolith policy out of this comparison so its objective admission change cannot explain a draft result.

## What the evidence establishes

`research/hyperion/CHANGES.md:362` gives HoR a strong baseline: replacing four-pick Ryth/Vendetta won 60.0% of 330 four-pick games and 62.5% of 168 fresh-suite games. Neither experiment compared Willow. Conversely, the two public policy-wonk losses do not establish that HoR is inferior to Willow. Their deployed sources are unverified, and the opponent changes **two** roles: M/V/Tavi/W versus our P/V/M/HoR.

The mechanism worth testing is sustained useful activity. `research/policy-wonk-four-pick-loss-review.md` records early capture-income leads for us in both games, followed by large opponent advantages in camp work and completed captures. Our lost bags were only 30 and 22 gems. Opponent Willow delivered 18,308 and 21,249 healing across Marcella, Vesper and Tavi. Own views show a real 360 heal in each nominated fight, but also real allied follow-up in Swirl and a newly revealed pack in Hooks. Those are service and engagement observations, not counterfactual proof that our Willow would have prevented the deaths.

## The actual trade

At base stats Willow provides a range-four, ally-only 360 heal with cooldown eight. Its benefit requires missing health, readiness, access and a recipient who subsequently survives and does useful work. She cannot heal herself; healing spends the turn's cast, preventing an attack reset that turn, while a ranged approach spends the basic attack. The heal itself does not exclude walking. The four-pick arm retains Prism, so existing Prism formation/recovery remains relevant; current all-ally heal ranking and the independent ready-heal helper also provide non-Prism service. It does not require a new mailbox or recipient policy to function.

It loses HoR's 1000 base HP, melee move-plus-basic economy, dash, area stun, shield and missing-health damage scaling. Marcella becomes the only melee frontliner. Willow adds a fragile ranged body, not an interchangeable camp anchor; keeping three teammates healthy is useful only where their own camp/fight admission permits work. Five-pick Willow results cannot answer this trade because that lineup retains HoR. Nor can theoretical 360/8 healing be treated as guaranteed health per round or directly compared with shield magnitude.

The resulting experiment tests a **draft plus the already implemented service behavior**, not an isolated champion-kit effect. A loss would not show that every possible four-pick Willow policy fails; a win would not identify which service rule caused it.

## Geometry and draft information

Use public geometry to interpret results, not select the arm. Relevant features are reachable camp-safe stations within heal range and line of sight of actual working positions; walls and choke widths that separate those stations; overlap between ordinary farming routes; and return-trip distance relative to useful work remaining. Long return trips can favor service but can also separate Willow from recipients. Dense camps can create repeated injury while eliminating safe support access. The Hooks wall visible in the own window illustrates why an apparently nearby retreat or rendezvous is not automatically legal.

At fourth pick the opponent's first three revealed choices can be known; its simultaneous fourth choice cannot. For the observed enemy order M/V/Tavi/W, Tavi can be known and Willow cannot. This fixed arm deliberately makes no counterpick decision. Do not derive a named-map rule from Swirl/Hooks or assume the enemy's final lineup was available at draft time.

## One valid comparison and its falsifiers

Freeze the accepted gameplay source, make only the native four-pick role swap, and verify actual rosters. `draft.cpp:244` gives `test_draft` precedence; its ten four-pick test compositions contain no Willow. Ordinary test-draft runs therefore do **not** test this arm. Use the existing native-draft evaluation mode, with both physical sides on four-pick maps across ladder, generated and gen-s1 suites, then a previously unused generated suite if the first comparison earns confirmation. Preserve three-/five-pick behavior as a regression check, not extra evidence for four-pick value. The published panel's 16 four-pick games are a screen, not a qualification; old CH102 samples cannot be reused as Willow observations.

Judge wins first, then these mechanisms with existing replay evidence:

- Useful healing actually absorbed, recipients' subsequent productive turns, and return/respawn downtime—not heal totals alone.
- Camp work converted into owned captures, gems and gold; cleared groups lost to the opponent; frontline deaths and interrupted holding.
- Lost burst, stun and mobility opportunities, including ranged walk/basic and heal/reset opportunity costs.
- Native errors and rollovers, decoded through each replay's actual actor roster rather than treating actor IDs as champion IDs.

The hypothesis fails if added healing mainly repairs damage that ordinary retreat already handled while reduced frontline/control loses more productive work, if service access is too rare, or if fuel costs consume the gained turns. A positive arm should improve realized activity and outcomes across held-out four-pick cells; neither large healing totals nor a reversal of the two live losses alone is sufficient. No selector, item change, further composition search or implementation is authorized by this study.
