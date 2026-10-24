# Focus plus safe optional yield: unnumbered source experiment v1

2026-10-23. Fresh exclusive ignored `bots/variants/willow-focus-safe-yield-work`, cloned `src/` only from canonical 4db. No builds, runtime, helper scripts, canonical/root-document edits, release numbering, submission, cleanup or deletion.

Parent aggregate: `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd`.
Combined aggregate: `9b405b0da9ddb7d9f79e698265546c2e69e42ce19c0fc0ea39bb19940bfa4007`.
Aggregate convention inside each bot: `shasum -a 256 src/* | shasum -a 256`.
Exact combined delta: `candidate-v1-vs-4db.patch`, SHA `d47d2ab16dbe855b1180dbbb6d530f3949f483bd4de09eb1b12b5073a2f7c734`.

Full 29-file parent/candidate snapshots and per-file SHA256 manifests are saved under `parent-4db-src/` and `candidate-src-v1/`. Candidate snapshot matches the variant byte for byte. Only bot.cpp and pathing.cpp differ from 4db; the exact patch passes the whitespace check.

The bot.cpp component is copied byte for byte from frozen Focus-only arm `ae18438dcd2164bd81f27ade445b58ae36901b4bdf99f1fda2d2e53dbff86086`: preserve partials and Treasure, then substitute actual Bruiser Focus value only for a fresh Willow Bruiser Strength choice with completed protection and no completed Bruiser Focus. The pathing.cpp component is copied byte for byte from frozen `03aaf746068a29d94f4e6d5245f89d97ca9bae123bb518fa32ab07a0a509797c`: narrow optional make-way ally lookup/priority-read catch for errors97/98, error-path freshness check, current-turn cache invalidation/false, other errors and StaleTurn propagated. No Health, protection-first, diagnostic or no-work conversion component is present.

Two full-source removal proofs are preserved. Replacing only the changed make-way file with its parent removes exactly that hunk: `without-make-way-src/` matches all 29 ae184 files byte for byte and its normalized aggregate is exactly ae184. Removing only the Focus hunk via its parent bot.cpp produces `without-focus-src/`, matching all 29 03aaf files and aggregate exactly. Both component pins and canonical4db were independently rehashed before combination.

This is a new compound artifact intended for its own future full1104 paired suite against released v33. The eight completed Focus-only games are separate evidence and are not reusable matches for this source. Independent source reviews do not establish a compound runtime gain or successful-path fuel equivalence. The make-way seam remains unproven as the cause of the exact Labyrinth incident; this candidate makes no incident-fix claim. Source is frozen, unbuilt and unsubmitted.
