# Separate Willow item experiments from a67

2026-10-23. Source-only preparation; no build/runtime. Each new ignored variant contains only copied `src/`, with one `best_emblem` edit in `bot.cpp`. Read `research/willow-support-items-and-treasure-review.md` and confirmed gates with Astra. These arms are independent, not combined.

Parent frozen source: `bots/variants/willow-comms-cached-endpoints-work`, aggregate `a67dc0a32d4b9d001a8c514dc86aa1d9f4aa9d91bc380f2df2ce59b649ce6d21`.
Aggregate convention: inside each bot, `shasum -a 256 src/* | shasum -a 256`.

## A: first protection before Treasure

Variant: `bots/variants/willow-first-protection-work`.
Aggregate: `2ae444fa1e7fbbacd661847110991d1a084fa1bdc64c58b7d5c66386b274327d`.
Patch: `first-protection-v1-vs-a67.patch`, SHA `98910ec40d3132b066959fc2c3c061416ef84331909d78749172f06c1184b4aa`.

Preserve existing begun-item returns. The original Treasure-partial loop additionally records whether any Treasure shard is owned. Before forced Treasure, Willow may return the existing upkeep winner only if no Treasure partial exists, neither Jungle nor Durability is completed, and that winner is Jungle or Durability. Its chosen stat and actual saved/cost values are retained; Health is not forced. Owning either completed protection closes the exception, so Treasure resumes after that one initial protective emblem. Begun Treasure and other partials retain their original priorities.

## B: one newly selected Bruiser Strength becomes Focus

Variant: `bots/variants/willow-one-bruiser-focus-work`.
Aggregate: `1657a09cd8b975cc8266e2a50ac306199319a81ef9a1734bf7590de78973dfe9`.
Patch: `one-bruiser-focus-v1-vs-a67.patch`, SHA `5d6e702e8f66c7908b30748b118450f79aa4f7304dcf54f8bb95a7c112541d33`.

After all existing partial returns and original Treasure priority, replace only a fresh Willow winner of Bruiser Strength, only with completed Treasure and at least one completed Jungle/Durability, and only while no Bruiser Focus emblem is owned. Return `value(bruiser, focus_stat)`, which recomputes saved rounds and remaining cost from the actual Focus build. Existing begun Focus partials finish before this gate; the resulting owned Focus emblem disables later substitutions. Willow cannot sell items, so this is an inventory-based once-only condition without new state/query. All other newly selected items, including Power and survival alternatives, retain their original outcomes.

Both `prices` and `affordable_prefix` consume `best_emblem`, and buy_shards consumes its family/stat. B therefore advertises and buys the same Focus shards, uses their actual Strength/Focus/HP completion stats in quotes, and retains whatever own-upkeep savings those stats really produce, including zero. Neither arm changes `raw_output`, counts healing as damage, credits future heals to admission, or fabricates saved rounds/service benefit.

Activation is a runtime question. Current a67 BigWorld/Boss item evidence mostly selects Power, so those two witnesses do not establish that B activates. Astra found 10 completed Bruiser Strength builds among 52 Willow games in existing exact337f published80 metadata, with no Bruiser Focus. That older source shares the item policy but can follow different trajectories; it shows B is not intrinsically inert, not an a67 activation count. No substitution to Power was added.

Pre-build preservation: `parent-a67-src/` and manifest; `first-protection-src-v1/` and `first-protection-v1-files.sha256`; `one-bruiser-focus-src-v1/` and `one-bruiser-focus-v1-files.sha256`; exact parent patches above. Snapshots match working variants. Both destinations are ignored. Canonical a67, frozen6901, and frozenfd99 were rehashed unchanged. No new scans, native queries, fuel gates, tracing, or runtime artifacts. Astra read both full actual diffs, independently verified both aggregates, and returned source PASS without a blocker; see `research/willow-support-item-arms-source-review.md`. Activation, performance, and heal-threshold effects remain runtime questions.
