# v47 hop + connected-escape union checkpoint

2026-10-24. Source-only exact combination authorized by root after independent single-arm source reviews. No build, game, helper/script/test implementation, SDK/tool change, canonical edit, EXPERIMENTS change, release or submission.

Child `bots/variants/willow-v47-hop-escape-work`, src only, no `.cambc`; 29-entry `research/willow-v47-hop-escape-source-v1-manifest.sha256`, aggregate `05d0f07c46c50c0951d86c6f60cb9ce473384be528b0089d0292463f460e41db`.

Frozen inputs, rehashed unchanged: hop `bots/variants/willow-v47-farm-hop-work`, aggregate `63f5deb00dbf445d3e60261f78b359d4931939751d0eb00f843750a8ecaa7f8f`; escape `bots/variants/willow-v47-connected-escape-work`, aggregate `4b5a71e6535bb7b0ccfec3ad26fa6a1c5cef066807576792384e9966efdc0343`. Both descend from frozen service-base-f7/f475 `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`.

Exact union proof: clone escape then apply immutable corrected hop v2; separately clone hop into a temporary verification directory then apply immutable escape v1. Every resulting source file compares byte-identical; temporary verification copy removed. No conflicts or new gameplay logic. The hop hunk/context bodies also match the vs-escape delta after removing paths/index/location headers. Git's vs-hop patch aligns two unchanged closing braces differently from the frozen escape patch; opposite-order full-file reconstruction, not diff text alone, verifies that arm.

Reviewable deltas:

- Versus f475: `research/willow-v47-hop-escape-source-v1.patch`, SHA256 `a75db142abbf2353bd1890cc3f20355fdf3cc769ee0f2ac88d8276df6eb299aa`; 8 files, 394 insertions/55 deletions.
- Versus escape (adds only hop): `research/willow-v47-hop-escape-vs-escape-source-v1.patch`, SHA256 `e807db67f2a1079f737737d23329d911cc2f3fc3693195779827adf519423b8f`.
- Versus hop (adds only escape): `research/willow-v47-hop-escape-vs-hop-source-v1.patch`, SHA256 `ba61ba64a0de20fe191c201ed1ae9408ee1043761f9e16964ab63f0ede063e66`.

The eight changed files are bot.cpp/h, pathing.cpp/h, safety.cpp/h, self_abilities.cpp/h; other21 files match f475, including params and all default draft sources. No finishing-recall, shield-pricing, dasher altar-distance, capture-allocation, midturn enemy update, deadline-bound, sighting, boss or mixed-camp-cast delta is included. No whitespace diagnostics, backups/rejects or `.cambc` remain.

Both reviewed arms' limitations remain. Hop uses the corrected3-phase/credible-fog/melee/terminal v2 arm, not rejected v1. Escape retains ray-only endpoint coverage, the existing current-DPS health heuristic and potentially costly lazy searches/current-board imports. Teleport arrival follows the normal next-turn update, so the escape arm receives fresh actor-known inputs rather than a retained hop plan. This is source integration evidence only; independent integration review and factorial runtime remain separate, without a requirement that each single arm win first.
