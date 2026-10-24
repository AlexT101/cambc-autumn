# One Bruiser Focus on the c71 development baseline

2026-10-23. Source-only port into exclusive ignored `bots/variants/willow-one-bruiser-focus-c71-work`, cloned with `src/` only from canonical 4db. No build, runtime, tooling scripts, canonical edits, root documentation edits, cleanup or deletion.

Parent aggregate: `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd`.
Candidate aggregate: `ae18438dcd2164bd81f27ade445b58ae36901b4bdf99f1fda2d2e53dbff86086`.
Policy source: frozen a67 child `bots/variants/willow-one-bruiser-focus-work`, aggregate `1657a09cd8b975cc8266e2a50ac306199319a81ef9a1734bf7590de78973dfe9`.
Aggregate convention inside a bot: `shasum -a 256 src/* | shasum -a 256`.
Exact patch: `candidate-v1-vs-4db.patch`, SHA `73c95030173b8038353afff6c6563b95f263b9abed43144d38f80588b6b96252`.

Full before and after snapshots are `parent-4db-src/` and `candidate-src-v1/`, each with 29 files and its per-file SHA256 manifest. The snapshot and candidate source match byte for byte. The exact parent delta contains only five added lines in `src/bot.cpp`; its whitespace check is clean. The candidate's full `best_emblem` function is byte-identical to the frozen 1657 function, verified by native text extraction and comparison.

The port retains every earlier partial-completion return, then the original Treasure priority. Only a fresh Willow winner of Bruiser Strength, after completed Treasure and at least one completed Jungle or Durability family, with no completed Bruiser Focus, returns `value(bruiser, focus_stat)`. A begun Bruiser Focus completes through existing partial precedence. A completed Bruiser Focus remains the inventory witness preventing another substitution; no new state is needed. Other champions, winning families and stats retain the original selection.

The existing `value` helper computes the actual proposed Focus stats, remaining price and own-upkeep saving, so shopping, quotes, prices and affordable-prefix calculations receive the same actual chosen item. No healing DPS or proxy Strength saving is invented. No Health or protection-first arm, demand gate, service coefficient, raw-output change, price-cache repair, new native read, scan, field, import or fuel gate is bundled.

This is a current-upstream counterpart for a later native five-pick comparison, not an asserted gain. Activation remains sparse when the model chooses Power rather than Bruiser; inspect qualifying choices, purchases and partials before allocating a broad panel. An absence of qualifying purchases alone does not prove a policy no-op because the chooser also supplies quotes. See `research/willow-demand-informed-focus-next-step.md` for why this fixed preference remains separate from a speculative healing-to-recovery valuation.
