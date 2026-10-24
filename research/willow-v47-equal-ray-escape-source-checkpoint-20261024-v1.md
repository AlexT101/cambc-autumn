# v47 equal shortest escape rays: source checkpoint

2026-10-24. Isolated implementation of approved `research/willow-v47-equal-ray-escape-design-20261024-v1.md`, SHA256 `37bcc1df36003e27a30464d55a7858ce659f6e328b5d8740f309a4403433dca3`. Cambridge Battlecode rules previously read. No scripts/helper/test implementation, git operation, build/run, native extraction, SDK/tools edit, canonical/EXPERIMENTS change, release or submission.

Parent `bots/variants/willow-v47-connected-escape-execution-work` verified before and after copying as aggregate `fcdf6007cebc9c248f8866142b39be614d38c4e273c983083cdfc722eba500d1`. Child `bots/variants/willow-v47-equal-ray-escape-work` contains src only; no `.cambc`, backup or reject files. Only pathing.cpp and pathing.h differ from the parent,13 insertions/8 deletions. All other27 complete files, including bot.cpp and Safety, remain byte-identical. The old camp_exit_rounds/camp_trapped/want_home block compares byte-identical to frozen f475; original admission is preserved.

- All29-file manifest: `research/willow-v47-equal-ray-escape-source-v1-manifest.sha256`,29/29 checks pass; manifest SHA256/source aggregate `c1e19d45475ca18d2a74c344da8372d9112cc9215c8261eb4023b987db02b4e5`.
- Component patch versus execution-only: `research/willow-v47-equal-ray-escape-vs-execution-source-v1.patch`, SHA256 `ae9ed06ae0d105cd578c0bf222efc045f8cbab4dc99ec7bca5abdfb730de5f17`.
- Complete patch versus frozen f475: `research/willow-v47-equal-ray-escape-source-v1.patch`, SHA256 `dea6d5418254890a3a9ee91dcf34dd0f6b0f4a372304bf4cb9968501bf81354c`.
- Child pathing.cpp SHA256 `1989225a0ec12acb76e7a5fe44d74da810a26a116deed2aec33f2aa3df0260f6`; pathing.h `4470710494785194a338a2775d9b428a4dcefa71a8551c42dd42dbb7354bb938`.

No added-line trailing whitespace found. The full f475 patch contains the existing execution-only component as well; the small component patch isolates this change. No support, hop, income, mixed-cast, roster, recall, v48, communications or Boss diagnostic overlay is added.

## State and exactness invariants

CampEscape replaces vec2 ray with uint8_t rays, bit i corresponding to the existing eight directions in util.h's north-first clockwise order. There is no heap/vector/board state for the mask. The discovery loop traverses the same eight rays with the same bounds/wall/goal checks and first-goal break as before. A strictly shorter found ray updates steps and clears rays before adding its bit; an equal found ray adds its bit; a longer ray adds nothing. Thus the old first minimum ray is always among retained rays, and no longer witness is assigned the minimum length.

The existing exactness proof is unchanged: after ray discovery, any_within(goals,origin,steps-1) must be false. A retained free ray of length R reaches a goal. At its point k, that goal is R-k away. Any closer goal from the point would be within Chebyshev k+(R-k-1)=R-1 of origin, contradicting the check. Therefore R-k is exact on every retained ray, not merely the first one.

CampEscape::at preserves the original valid/exact/in-bounds/current-wall checks and unreachable/exhausted, origin and steps==0 cases. For a positive ray-backed distance it takes k=dist(p,origin), refuses k>R, then checks at most eight mask bits for exact equality p=origin+directions[i]*k. King directions have components in -1..1 and at least one nonzero, so on the old ray this k equals the old loop index and the returned R-k is identical. Off-ray points, points beyond R, longer unretained rays and unchecked chords receive no label. It does not infer a label from proximity to a ray.

Mask0 remains distinct native-field mode after the original prefix cases. The existing steps_at label lookup and d<=steps condition are unchanged. Rebuild resets rays to0, and completed field fallback clears it to0 before publishing the result. Provisional/inexact or stale/interrupted results remain hidden by valid/exact, including a stale exception during field compute. Old label storage may remain allocated, as before, but cannot be read while a ray-backed result has a nonzero mask.

The current origin/walls/goals cache key and all existing invalidate/begin_turn/deferred-guard/occupancy behavior are unchanged. Invalidating sets valid=false as before; any old mask is inaccessible until rebuild, which clears/re-discovers it. Origin changes never translate rays. The complete walls include actual occupancy, camps, teleports, bumped tiles and the existing lazy guard. No stale mask bypasses their existing comparison.

## Execution and cost limits

No new search, native field/Safety query, board scan, fuel gate, fallback, enemy veto or scoring/ranking rule is introduced. Walking still ranks only labelled descending endpoints using the same camp/enemy exposure and home tie-break. Dash still uses legal native landings, its existing bounded unique endpoint evaluations and exact post-dash observation/topology/origin/followup revalidation. More tied labelled endpoints may now reach those existing checks; no off-ray continuation becomes authorised.

Mask updates add bounded scalar work to already-traversed ray discovery. Ray-backed at replaces the length loop with Chebyshev arithmetic and at most eight direction tests, after the unchanged native wall test. Newly available endpoints can increase existing Safety/home evaluations, and code layout can affect old fuel cutoffs; no fuel-equivalence or speed claim is made. The original execution-only limitations and emergency behavior remain.

This is a source proof/review receipt, not an executed geometry fixture, activation, loss attribution or strength result. Luna owns meaningful one/two/longer/blocked-ray, invalidation, field/unreachable/off-ray/post-dash fixtures and build/runtime controls. Root reviews the source before those runs; known adverse/gain stress cells remain diagnostic choices, never gameplay conditions.
