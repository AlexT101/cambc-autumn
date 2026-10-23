# Willow support item arms: actual source review

2026-10-23. **Source-only PASS**, no blocker, for both isolated a67 children. Independently rehashed:

- First protection: `2ae444fa1e7fbbacd661847110991d1a084fa1bdc64c58b7d5c66386b274327d`.
- One Bruiser Focus: `1657a09cd8b975cc8266e2a50ac306199319a81ef9a1734bf7590de78973dfe9`.

Reviewed complete actual bot.cpp diffs against frozen cached-endpoints a67. Exact patches/snapshots/manifests are under `provenance/willow-support-items-20261023-v1/`. No build/runtime or gameplay changes by this reviewer.

A only bypasses the existing Treasure override for Willow when no Treasure partial and neither protective family is completed, and the existing model's winner is Jungle or Durability. It returns that actual winner unchanged. Existing partial returns precede it. Once protection completes, original Treasure priority resumes; it does not force Health or change other champions.

B runs after existing partial returns and Treasure priority. It substitutes only a fresh Bruiser Strength winner for Willow with completed protection and no completed Bruiser Focus. Returning `value(bruiser, focus_stat)` computes actual proposed stats, remaining cost and own-upkeep saving, consistently consumed by shopping and quotes. A begun Focus completes under existing partial precedence; its completed emblem is a permanent once-only witness for Willow, who cannot sell. It does not alter raw_output or assign fictitious healing DPS/savings. No new native call, field, scan or persistent counter.

Activation is sparse but plausible: existing exact337f published80 metadata contains52 Willow games;16 started Bruiser Strength,10 completed it,0 completed Bruiser Focus. These share a67's item policy but do not guarantee identical a67 trajectories. Saved Boss-A `analysis/acf01862623d745a` completes Treasure298/Jungle342 and buys a fresh full Bruiser Strength1024. Lanes-B `40d8ca1ba3e43860` completes Jungle681 and begins Bruiser Strength in the same shopping turn. The first is an unambiguous final-inventory gate witness; the latter also exercises same-turn shopping refresh and partial completion. A small activation check should precede broad performance testing.

In the saved Boss witness, post1024 heals are324,375,375,375. A Strength→Focus substitution raises nominal heal375→435: at most180 additional HP on the recorded schedule, potentially zero;324 gains none. None falls in the changed225→261 ordinary worth threshold band. Full-cap events alone do not reveal above-cap deficit or saved recovery time. Actual quote changes may also alter shopping timing, so this is an opportunity bound, not a counterfactual outcome prediction.
