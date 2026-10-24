# v47 fixed five-pick role-screen source checkpoint

2026-10-24. Cambridge Battlecode rules and full `research/willow-v47-map-economy-counterdraft-design-20261024-v1.md` read. Root authorized three fixed roster interventions before fitting any map/opponent selector. Source only: no build, game, test/helper/script implementation, SDK/tool edit, canonical change, EXPERIMENTS edit, release or submission.

All three are independent src-only clones of frozen `provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7`. Parent aggregate verified before/after: `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`. No `.cambc`, backup or reject files are present. Each manifest has29 entries and each child differs in exactly one inserted draft.cpp line; other28 files and all gameplay match parent byte-for-byte. No whitespace diagnostics.

| Variant under bots/variants | Ordered default five selections | Source aggregate |
| --- | --- | --- |
| willow-v47-stellar-five-work | Stellar / Vesper / Marcella / Willow / HoR | `0c166e820c493aaa222d5fd065fb56d9caff766c3f8caf8795d1898d4397a82d` |
| willow-v47-cassi-five-work | Cassi&Issac / Vesper / Marcella / Willow / HoR | `3eed096b658e5db51630d44c346a9cf3a07c6624885d80e4a5a2eed442641938` |
| willow-v47-vendetta-five-work | Prism / Vendetta / Marcella / Willow / HoR | `897529e6d30f8fca6cb3f3c732d3a90954c675c1e1e5259457f2309da0267871` |

Manifests are `research/willow-v47-{stellar,cassi,vendetta}-five-source-v1-manifest.sha256`; each manifest SHA256 is the corresponding source aggregate above.

Patches:

- `research/willow-v47-stellar-five-source-v1.patch`: `6e95053aaded9db24060b077d820c20df0c2e520bd5cdc3295c1856b12226c04`.
- `research/willow-v47-cassi-five-source-v1.patch`: `dcd51e70c414dbbe65c26486ba0ca71e0a8bee28866c35a3f3295d599030caeb`.
- `research/willow-v47-vendetta-five-source-v1.patch`: `7b9571118c23b11e051ea4bb1cf37c2134608f0e5e6d65900363d702693ebf6f`.

Each inserted line executes only inside the existing default draft_order initializer, after typed role conversion, and only when willow_draft is enabled and team_size equals5. Stellar/Cassi replace order[0]; Vendetta replaces order[1]. The other four slots retain their original positions. Existing first-call caching remains: these are fixed interventions, not dynamic counterpicks. No public-map summary, classifier, numeric replay ID or threshold is added.

SDK enum spellings were checked directly in `sdk/cpp/cambc.h:271–283`: `cambc::champion_draft::stellar`, `::cassi_and_issac`, and `::vendetta`. Cassi&Issac is one draft selection that creates two bodies, so this arm has five selections/six actors; it does not consume the second slot. Its linked death/activation/aggro consequences are part of the intervention, not a tank-health credit.

Other team-size lists, the four-pick swap, test-composition path, native_pick conversion, pick_first_available duplicate/unavailable handling, ensure_picked fallbacks and write-before-pick draft memory ordering are untouched. Params remain test_draft=false and willow_draft=true; params::draft_preference is unchanged for fallback and other sizes. The new condition reads the existing scalar team_size once during cached default-order initialization; no per-gameplay-turn or new map scan is introduced.

This checkpoint does not claim compiled roster validity, six-body runtime support, strength improvement or a fitted selector. Luna owns the predeclared24-cell screen: three public maps x both sides x baseline/three substitutions against frozen v33, with matching baseline6 reused where pins agree. Draft/body counts, native errors/rollovers and economy mechanisms must be verified in those runs. Later gameplay combinations and delayed/revealed-prefix draft experiments require separate explicit source pins; no hop/escape/recall/mixed-cast overlay is included here.
