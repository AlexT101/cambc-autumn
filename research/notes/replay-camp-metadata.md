# Replay camp metadata correction (2026-11-10)

The replay extractor's static group join was wrong after a self-mirrored camp. This is an extractor indexing error, not a game-rule contradiction. The active draft and emblem training pipelines do not consume those fields. Existing datasets, replay caches, bot bodies and ward gate source seals are unchanged; the validation output is separate.

`buildMap` formerly joined a runtime camp index `i` to canonical index `i >> 1`, and found its mirror at `i ^ 1`. A camp on the symmetry axis produces one runtime camp rather than two, shifting subsequent indices. The runtime group members, types and tiles were correct, but copied group gems/gold/respawn and the mirror group could be wrong. Schema 3 joins canonical groups and runtime mirrors by coordinates. It retains the replay engine's own static rewards, so it does not impose today's stat table on old engines. The internal map-cache hash now includes schema 3, preserving `maps/<map-hash>.json` for consumers that derive the filename; older blobs are not overwritten. This internal key is separate from the platform mapHash used by the hourly checker.

Read-only audit of the same 40 maps used in the Mite r4/r5 fidelity study: 868 runtime groups, 69 with at least one wrong reward/timer field (61 gems, 57 gold, 23 respawn), 52 wrong mirror references. Seven maps had reward/timer differences: `00quarry`, `01boss_battle`, `02guardians`, `02treasure_box`, `03one_gem`, `04wheel`, `adgato_gemcombat5`. Nine maps contained self-mirrored camps; some wrong joins happened to copy equal values. These are counts in this cohort, not an estimate for the entire archive.

## Downstream impact

| Consumer | Impact of old decoded metadata |
|---|---|
| `tools/replay/macro_stats.py` | Clear reward labels, idle gem supply and total gem-rate estimates can be wrong. Capture totals use observed shares and are unaffected. |
| `tools/replay/analysis/camps.py` | Static camp-value rankings, gems per effort/cycle and damage per gem can be wrong. |
| `tools/replay/analysis/{economy,tempo,audits}.py` via `data.py:own_group` | Team-B group labels and per-group/side attribution can be wrong; actual total capture payout remains observed. Audit reset gem labels also use copied metadata. |
| `tools/replay/narrative/mapinfo.py` | Reward legends and mirrored landmark pairing can be wrong. |
| `tools/replay/walk_audit.py` | Camp gem labels and supply/cycle estimates use copied values. |
| `research/notes/ideas-2026-11-08/big-levers-tools/{clears,clear_tables}.py` | Reward-weighted stolen-clear summaries can be wrong; event counts and observed damage are separate. |
| `research/notes/ideas-2026-11-08/gemzone-tools/zone_stats.py` | The `gems > 0` group filter can change zone attribution even though payouts use observed shares. |
| `research/notes/ideas-2026-11-09/losses-tools/captures.py` | Capture rows copy group base gold/gems; reward sums can be wrong. Capture count/time/side is separate. |
| `research/notes/ideas-2026-11-09/losses-tools/situ.py` | The gold/single-holder predicate can select wrong situations on affected maps. The raw `00expanse` map has no self-mirrored camp; `00quadrants` has one, so exact original decoded cohort validation remains necessary. |
| `research/notes/ideas-2026-11-09/camphp-tools/abandon.py` → `h2h.py`, `why.py`, `cmp.py` | Stored reward tuples and reward-weighted abandonment summaries can be wrong; damage, timing and abandonment counts do not use them. |
| `research/v66-replays/scripts/second_order/{q1_holdwalk2,q1_holdtrace}.py` and `opponent/{feat,examples,agg_camps}.py` | Group-value labels and opportunity/capture value sums can be wrong. |

Treat historical reports produced by these consumers as potentially stale in their affected fields, including earlier macro supply and camp-value findings. No broad numerical correction is claimed without re-running the exact original input cohort into a new output. Fresh-game A/B winners and gate decisions come from actual engine outcomes and are not invalidated by this metadata issue. The corrected Mite fidelity note already reconstructs base gold from actual member types and keeps it separate from observed payout.

## Active training and other checked paths

- `tools/draftlab/features.mjs` decodes raw `.map26a` files through `mapgen/wasm.mjs`, then `Grid.fromMap`/`Grid.groups()` reconstruct cardinal camp components from coordinates and sum member rewards. It does not read extractor map JSON. `draftlab/lab.py:ladder_data` takes drafts and outcomes directly from API `group.json` records.
- `tools/draftlab/outcome.mjs` reads replay engine snapshots/statistics directly; no `buildMap` or copied group reward is involved.
- `tools/emblab/lab.py` obtains map features through the draft feature pipeline; `finish_batch` joins bot `EMB` stdout decisions with the direct outcome extractor. `dfit.mjs` and `mapdr.mjs` consume these map features, decisions and game winners. The active r4 data and fits need no regeneration for this issue.
- `tools/fish/{econ_rows,decision_data}.py` use `breadth.static_groups`, which reconstructs coordinate components and sums camp types independently. `research/draftfarm-2026-11-08/tools/osim.py` also reconstructs its own components/rewards.
- `research/notes/ideas-2026-11-09/oppmodel/build_ds.py` reads champion priority/state and game metadata, not static reward/mirror fields.
- The current warding study uses actual group tiles/types, events and vision; its camp state comes from clear/capture/respawn events, not copied respawn duration or mirror-group labels. Its ten sealed gates remain valid and queued separately by fuel budget.

## Validation and artifact provenance

`node --test tools/replay/test_map.mjs`: five tests cover horizontal and vertical symmetry-axis camps, ordinary rotational pairs, arbitrary runtime ordering, and failure on an absent mirrored correspondence. Direct start-state validation uses 40 downloaded live replays, one per map: all 868 corrected groups match member-type rewards under the current engine, exact reflected tile sets and mirror involution. Coordinate joins also reproduce the engine's own static group reward values, avoiding an assumption that the runtime order matches canonical order.

Audit and validation scripts/results are in `~/tmp-offload/mite-r5-fidelity/`: `metadata-impact.mjs`, `metadata-impact.json`, `validate-map-fix.mjs`. Full extraction validation uses a new `map-fix-validation/` root only. Legacy map blobs are copied there as sentinels to check that versioned map writes preserve them; originals remain unchanged. Dataset migration is deliberately separate: choose a new output root, rerun the exact needed cohort, compare unaffected events/outcomes, then explicitly update a consumer. Do not patch sealed map blobs or regenerate active training.

Full extraction passes on `00quarry`, `01boss_battle`, `02treasure_box` and ordinary `00ambush`: zero hard validation errors; decompressed events and rounds byte-identical to schema 2; result, draft and champion records exactly equal. All four original map files and copied legacy sentinels remain byte-identical. Corrected map hashes differ and resolve through both `mapFile` and `maps/<meta.map.hash>.json`. Seven pre-existing soft validation notes remain; this fix does not claim to repair those unrelated diagnostics. Evidence: `map-fix-validation.json` and `check-map-fix.py`.
