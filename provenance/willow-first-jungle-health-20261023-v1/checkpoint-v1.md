# First Jungle Health sibling of 2ae

Exclusive ignored variant: `bots/variants/willow-first-jungle-health-work`, cloned src-only from frozen first-protection 2ae. Canonical, other item arms, crew arms and upstream integration remain separate and untouched. No build/runtime or script implementation.

Standard aggregate convention: inside a bot, `shasum -a 256 src/* | shasum -a 256`.

- Parent: `2ae444fa1e7fbbacd661847110991d1a084fa1bdc64c58b7d5c66386b274327d`.
- Candidate: `3b8159029a5786f6ebbf54b7b28ef5c18a5a35058ed50642a3342b9251c5da76`.
- Canonical reverified unchanged: `a67dc0a32d4b9d001a8c514dc86aa1d9f4aa9d91bc380f2df2ce59b649ce6d21`.

Only `best_emblem` in `bot.cpp` changes against 2ae: inside its existing fresh first-protection override, replace only the selected Jungle Strength return with `value(jungle, health_stat)`. The surrounding Willow, no Treasure partial, neither protection completed, and selected protective-family conditions remain exact. All earlier begun-item returns, Durability choice, later Treasure resumption and other build candidates remain. Completing either protective family disables the override, without new state or native queries.

Actual Health stats, completion cost and modeled saving flow through the existing chooser, prices, affordable prefix and purchase loop. No Strength proxy, healing-as-damage credit, price-cache repair or telemetry is added. A small or zero Health saving remains small or zero. No qualifying purchase is not proof of no policy effect: the chooser also supplies quotes and gold value.

Health reasoning is saved in `research/willow-health-selection-and-first-protection-review.md`, SHA `25495e0c33454928833aa34862fdbe48bb7839724d0ae6762d75b05653626684`. It compares actual first Jungle Health/Strength stats and model costs, explains the existing support/burst and quote limitations, and does not claim survival/healing improvement from HP alone.

Pre-build preserved artifacts: `parent-2ae-src/`, `parent-2ae-files.sha256`, `candidate-src-v1/`, `candidate-v1-files.sha256`, and exact patches:

- `candidate-v1-vs-2ae.patch`, SHA `e43df1c1767afc5c6cdc0394d10701ceb900fabc758f5fd72d2ace3d3879bf3c`.
- `candidate-v1-vs-a67.patch`, SHA `562297f1771ca7c32c95d98bc72cae2277f44ec95fb531cfdc98114ec96d1f1a`.

Snapshot equality, ignored destination and clean diff whitespace checked. Parent was hash-verified before cloning; canonical was rehashed after preparation. Astra independently hashed 3b815902 and returned actual-source PASS without corrections; review `research/willow-first-jungle-health-source-review.md`, SHA `74efe079dd998b7c10752aec8f9c42eff3727a650be01f62f596bb1e6be02f33`. The direct performance control is frozen 2ae, with runtime activation and economic/fuel effects untested.
