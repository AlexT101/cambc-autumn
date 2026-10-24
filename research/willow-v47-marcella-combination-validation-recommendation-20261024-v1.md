# Marcella combinations: evidence and generated-map validation

2026-10-24. Read-only review of completed480 native rows. No implementation, games, new extraction, fetch or release action.

## Primary candidate: M+H

`provenance/khaos-v34-ladder-intake-20261024-v1/marcella-combination-screen-480-v1/RESULT.{md,json}` reports all480 outputs complete, expected drafts/body counts, zero statistics botFaults and diagnostic codes. Updated after the completed pinned native phase audit: zero Bot error events in every phase and zero draft/other rollovers. Candidate/opponent play rollovers are M+X254/266 versus f475 and256/557 versus v33; M+H258/248 and288/551; triple253/267 and294/542. These whole-trajectory totals do not isolate routine cost or establish fuel equivalence.

Sources are pinned in `research/willow-v47-marcella-combinations-source-checkpoint-20261024-v1.md`: M+H `709ba31a186fb1e5b27a180ac58d50a913af10cba42ccbc31151ae36c04f26f4`; M+H+X `d6b2a89e1926508b3d299fd0463df152a4e2ec8c5e897937b23919c317ee1f6d`; M+X `f38d7ce7f940cc90e57565a5129ab17221acfb5858a77342584732d7e8737d51`. M is delayed Marcella tribute value, H ordinary farm hop, X mixed-camp approach qualifier. All retain f475 drafts and omit escape/v48 overlays.

| Arm | Wins vs f475 | Wins vs v33 | v33 A/B |
|---|---:|---:|---:|
|M|42/80|47/80|25/22|
|H|39/80|47/80|21/26|
|H+X|41/80|46/80|20/26|
|M+X|41/80|47/80|23/24|
|M+H|44/80|52/80|26/26|
|M+H+X|43/80|50/80|24/26|

Common-v33 f475 control is45/80 (A22/B23). These are deterministic development-set outcomes, not independent samples or pooled cross-opponent rates. The modest44/80 direct-parent result and larger common-v33 result warrant generalization checks, not a conclusion that the arm universally dominates.

## Exact map/side changes

Joined explicit candidate physical side/map rows with `f475-v33-complete-output-v1/RESULT.json`, `marcella-tribute-value-release-v1/RESULT.json`, and `f475-farm-hop-160-output-v1/RESULT.json`.

M+H gains12 baseline losses: Gemfight A, Reverse Spiral B, Ambush A, Gem Fields B, Lanes A, Lost World A, Road of Riches A, Split A, Islands B, Starvation B, Yellow Brick Road A/B. It loses5 baseline wins: Elkring A, Great Wall A, Lanes B, Big World B, Fracture A.

Against M's common-v33 outcomes it gains6 (Gem Fields B, Road of Riches A/B, Split B, Starvation A/B) and loses1 (Great Wall A). Against H it gains8 (Gemfight A, Gem Fields B, Lanes A, Lost World A, Road of Riches A, Split A, Islands B, Yellow Brick Road A) and loses3 (Elkring A, Lanes B, Big World B).

M+H leaves all12 three-pick control outcomes unchanged,7/12. Its four-pick results improve9→11/16 and five-pick29→34/52 against v33. This localization is compatible with Marcella's actual roster eligibility, but is not proof the bonus or a hop activated. Code generation, changed candidate coverage and terminal handling still may affect decisions.

Adding X to M+H changes14 cells: gains Fragment A, Rushbait-v2 B, Corners B, Elkring A, Great Wall A and Boss Battle A; loses The Farm A, Interlock A, Reverse Spiral A, Swirl B, Gem Fields A, Lanes A, Split A and Starfish B. Thus the triple is a reasonable secondary validation candidate, not a justified map-name switch. M+X has no aggregate common-v33 improvement over M and is lower priority for the next broad panel.

## Mechanistic plausibility, without claiming activation

The reviewed union preserves distinct economic terms: M can rank a new productive destination higher by its delayed tribute→shop→return value, while H tests whether a locally legal hop accelerates that selected destination enough to pay its real replacement cost. Future tribute income never enters H's immediate worth or present gold budget. That is a plausible complementary mechanism. **Gem Fields B and Road of Riches A** are useful nominations because M and H both lost but M+H wins. They do not prove synergy internally: neither hop use nor M's value term is recorded in these result rows.

Do not hold the broad validation for more traces. For one subsequent explanatory read, use an existing replay's first accepted divergence in either nominated cell, then inspect actual teleport use/capture recipient/tribute/purchase/next productive work. A positive economic sequence is stronger than a cast count or final win. If the change precedes eligible M/H decisions, retain a cost/codegen explanation instead. No single bad cell is an automatic rejection gate.

## Native validation plan: development versus untouched holdout

1. **Freeze M+H as primary now**; triple is secondary. Preserve sources, Release binaries, tool/SDK pins, native drafts,100k fuel and both physical sides. Complete phase audits independently of the outcome analysis. No further tuning based on the published40 before this panel.
2. **Broad development validation:** use both existing256-map generated suites (`maps/gen` and `maps/gen-s1`) with current file/index hashes frozen before launch. They are previously used development suites, not untouched holdouts; historical same-name suites/seed statements are insufficient identity. M+H versus frozen f475 on all512 maps/both sides gives1024 generated cells, supplementing the80 published cells already available. Read map-family, pick-count and side breakdowns rather than treating a handful of maps as independent proof.
3. **Common-opponent check:** predeclare a balanced subset of128 generated maps across the two suite indexes/presets, independent of outcomes; run both M+H and f475 against frozen v33, both sides (512 rows). This tests whether the published common-v33 gain persists rather than relying solely on direct-parent play. Exact previously completed matching cells may be reused once. If triple capacity is available, compare it on this same subset, rather than searching a different favorable subset; its results remain secondary development evidence.
4. **Untouched confirmation:** generate and hash a new suite in a new destination with an unused fixed seed through the existing mapgen tool, preserving all old suites. Select/pin its recipe/seed before examining results; keep it unopened for outcome-driven tuning. After choosing the frozen release candidate from development evidence, run that candidate and matched controls on the fresh suite/both sides. A256-map suite gives512 direct-parent cells; an additional common-opponent block can use the same predeclared coverage if resources permit. Do not call any old generated suite held-out merely because this exact child has not run it.

If fresh results are used to switch from primary to triple or tune policy, label them validation rather than untouched confirmation; preserve their findings and make the changed-candidate decision explicit. No arbitrary win threshold or one-loss veto is proposed. Judge practical paired gains, regressions, native reliability and their consistency across map families/opponents. The workflow follows the repository's distinction between broad generated-map judgment and a new-seed confirmation, without requiring another feature rewrite or overfitted selector.
