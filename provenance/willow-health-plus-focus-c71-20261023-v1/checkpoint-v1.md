# First Jungle Health plus one Bruiser Focus on c71

2026-10-23. Source-only combined hypothesis in exclusive ignored `bots/variants/willow-health-plus-focus-c71-work`, cloned `src/` only from canonical 4db. Only `best_emblem` in `src/bot.cpp` changes: 14 added lines and one replaced line. No new stat logic or additional policy is bundled. No build, runtime, tooling scripts, canonical edits, root documentation edits, cleanup or deletion.

Parent aggregate: `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd`.
Candidate aggregate: `279ddbf4df8ac94ecebffd3363388e91f6aa582328594d67d868d7eabd30188d`.
Aggregate convention inside a bot: `shasum -a 256 src/* | shasum -a 256`.
Exact parent patch: `candidate-v1-vs-4db.patch`, SHA `c56e7ecff9f00196c27c30301bb16b6bb5b2ba4c4a73fe21db082fd35b99955e`.

Full before and after snapshots are `parent-4db-src/` and `candidate-src-v1/`, each containing all 29 source files with a per-file SHA256 manifest. The candidate snapshot matches the working variant byte for byte. The exact delta passes the whitespace check. Frozen policies and canonical source were rehashed before the port.

## Exact components

The first-protection and Jungle Health component is copied exactly from `bots/variants/willow-first-jungle-health-work`, aggregate `3b8159029a5786f6ebbf54b7b28ef5c18a5a35058ed50642a3342b9251c5da76`. Before a new Treasure, only Willow with no Treasure partial and no completed Jungle or Durability may choose the existing upkeep winner's first protection. A fresh Jungle Strength winner returns actual `value(jungle, health_stat)`; other Jungle or Durability winners remain themselves. All earlier partial-completion returns remain untouched, including Jungle Health. Completing either protection closes the early override, and Treasure priority resumes.

The one-BruiserFocus component is copied exactly from `bots/variants/willow-one-bruiser-focus-work`, aggregate `1657a09cd8b975cc8266e2a50ac306199319a81ef9a1734bf7590de78973dfe9`. After existing partials and completed Treasure, only a fresh Willow Bruiser Strength winner with completed Jungle or Durability and no completed Bruiser Focus returns actual `value(bruiser, focus_stat)`. A begun Focus completes first; completed Bruiser Focus is the once-only inventory witness.

Native text comparisons verified both component blocks byte for byte against their frozen sources. Removing only the five-line Focus block from the candidate's full `best_emblem` yields a function byte-identical to frozen 3b. The remaining 28 files are unchanged from 4db. This preserves the partial/Treasure/protection closure ordering and combines the two policies without adding another gate or changing their candidate rules.

Both substituted items use the existing actual value helper and therefore their actual stats, remaining price and own-upkeep saving in shopping, quotes, prices and affordable-prefix evaluation. There is no proxy Strength saving, healing DPS, service coefficient, price-cache repair, new state, native import, scan or fuel gate. The independent-ready-heal movement price remains unchanged; altered Strength and Focus can affect that existing access test as well as heal size.

This is the bundled provider-survival and healing hypothesis alongside pure Focus arm `ae18438dcd2164bd81f27ade445b58ae36901b4bdf99f1fda2d2e53dbff86086`. It is not a promotion or a gain claim. Earlier lower healing in a three-cell Health comparison did not isolate the HP contribution. Activation, buying and quote changes, survival, service access, farming cost and outcomes remain runtime questions. Lack of qualifying purchases alone does not establish a policy no-op because best_emblem also feeds quotes. Source is frozen for later Astra review; no tests were run.
