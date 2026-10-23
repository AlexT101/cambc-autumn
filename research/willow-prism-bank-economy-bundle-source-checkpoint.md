# Willow bank/economy bundle source checkpoint

2026-10-23. Read AGENTS.md and the Cambridge Battlecode rules. Root authorized exactly the three pinned components below, combined in a new src-only candidate. No build, engine, extraction, new script, tooling edit, canonical/release edit, or EXPERIMENTS edit was performed. This is an unqualified candidate, without a numbered release designation; actual Astra review and combined runtime qualification remain pending.

Created `bots/variants/willow-prism-bank-economy-bundle-work/` from pure130 `src/`, copied the index donor's three changed files and dense donor's two draft files, then applied the existing bank-heal patch without conflict. Its directory contains only `src/`, without `.cambc`.

| Source | Canonical aggregate SHA-256 |
| --- | --- |
| Frozen pure130 | `130a17af668a432a8a5582ec0736b1ef13c22e05245bc5742e472f3d02a620a5` |
| Station-member-index v2 donor | `12f3a622d3907f31f32dd34e80e9436df75f84c59f2282c32fe6846b3b2840a9` |
| Willow bank-heal donor | `fab7c7b13e8271a933a6b7d250f4e3627f5112fc1a6d85c9d98f78b1982b7e7f` |
| Dense fifth-slot draft donor | `2dd4084d601fc89138afa7df45372d45260ad8d23313e3e6f56e249f1bb26a69` |
| New combined candidate | `a2794129e115abb70faaa5a7e3c66b9728898b0e52c5542fa7885091eaec0bb6` |

Aggregates use `shasum -a 256 src/* | shasum -a 256` inside each bot directory. The full pure130-to-bundle patch is `research/willow-prism-bank-economy-bundle-source.patch`, SHA-256 `59613055706a6928331b0125d3f7e08b736c317b28f03cc4ad2fc190b7aafa66`.

Exactly five source files differ from pure130:

| File | SHA-256 | Composition |
| --- | --- | --- |
| `src/bot.cpp` | `9e2e23fdfb2fbc8bf8f23e598144e445e2ff9bc6e17bf7f84ae4bcd350f08694` | Exact index-v2 delta plus exact bank-heal delta |
| `src/world.cpp` | `4c5ed2234703967b390d218df61be8e6aa03bbda7dcfdb0ce10490aa066587df` | Exact index-v2 donor file |
| `src/world.h` | `a22d239246f3d419090ef5eee32fdd7463b2814794b7ead21ea8dfd5c77ee1d8` | Exact index-v2 donor file |
| `src/draft.cpp` | `216f27819ea0386726fd771952488ffd557543bb9c6e8cc8586a2e50a825cac8` | Exact dense-draft donor file |
| `src/draft_selection.h` | `e42b6b7ef787ffb0d1a9e8cb33b5900b735ff251bb6162bd9a9f7887211f6154` | Exact dense-draft donor file |

## Exact reconstruction checks

Standard patch/copy/compare operations on temporary source copies independently recovered each complete donor:

- Remove the bank-heal patch and restore pure130's two draft files: recursive comparison is byte-identical to index-v2, aggregate `12f3a622…`.
- Remove index-v2's growth repair and original member-index delta, then restore pure130's two draft files: byte-identical to bank-heal, aggregate `fab7c7b1…`.
- Remove bank-heal and both index deltas while retaining the two draft files: byte-identical to dense-draft, aggregate `2dd4084d…`.
- Apply the new complete patch to another pure130 source copy: byte-identical to this bundle, aggregate `a2794129…`.

The four copied donor files also pass direct `cmp`. Recursive pure130 comparison and `git diff --no-index --check` confirm the five-file scope and no whitespace errors. No local-formation bb836, post-dash, price/cache, farming, P67 diagnostic, or unrelated change is present. Final rehashes confirm all three donors unchanged and frozen coordinated, canonical `bots/hyperion`, and `bots/Khaos_v30` still at130.

## Intended interaction and limits

The components retain their reviewed individual contracts: the station index changes repeated static-member lookup cost while keeping current strict exposure; the nonurgent bank step offers one actual current heal to any eligible frontline ally without increasing chosen-bank-field distance; dense native five-pick maps regain Vendetta in the fifth slot while retaining Willow and the first four picks. The index may offset some support work, but no combined saving or gameplay gain is claimed.

Root reports individual results of index544–560/1104 with2.15% fewer rollovers and2.68% Willow fuel saved on the exact100M sixteen-game panel; bank39–41/80,629 versus638 rollovers, no errors and a verified Cat89 move/heal360; dense43–37/80. These motivate the combination and are not an additive gain estimate. The combined candidate requires actual source review, then the planned1104 comparison and untouched512 confirmation if broad results justify it. Root owns the result record and scheduling.
