# Audit: bots/astraeus/src/economy/camps.cc

Branch `worktree-agent-accd7be985c101623`; commits `9b3751a3` (cleanup) and `993774e7` (fixes).
Bench: `00ambush 00lanes 01hooks 00interlock`, test drafts, against `audit-base.json`.

## Changed

**Cleanup (`9b3751a3`): byte-identical, 8/8 replays; total fuel -0.00% (2211802776 -> 2211773191).**
- `member_at(G, p)` replaces the two "scan every member, skip unless at p" loops (camp_attack_targets, breach). It returns on the first match, which is the only one.
- `live_health(world, g, i)` replaces the two copies of `health > 0 ? health : max_health`, and its comment says why the fallback exists: a live tile whose belief still says dead means the camp respawned unseen.
- `collectors_scale(owned, added)` holds the Collectors factor, which `camp_dealt_with` and `champion_dealt_with` each had a copy of. Both are now one line. It is `always_inline`: without that the bench read +0.01%.
- Comments:
  - The ranking rule moved from `attack_camp` to `camp_attack_targets`, where the score is computed, and `camp_attack_targets` got a real header in place of the bare "Keep the ordinary list's bound...".
  - Removed `spell_output`'s "they reach 4, past the camps' 3". It is wrong: elks and golems reach 4, which is why `spell_clear_rounds` rejects them.
  - Rewrote `spell_clear_rounds`' header. The old one ("Negative if no spell can reach an attacker") did not describe what the code tests: no spells, no live attacker, or an attacker reaching `ability_range`.
  - Dropped the guard comment in `rate()`.
  - Explained why the reflect path gets a copy of `sorted`. The `copy_n(...) - n` pointer trick is now a plain assignment.
- Renamed `mixed` to `harmless` in `safe_targets`. The flag is true for all-harmless groups too.

**Fixes (`993774e7`): changes behaviour for Varg only. The bench drafts no Varg, so replays are still 8/8 identical and fuel +0.00%.**
- Varg's splash deals Strength to every camp within 1 of its target, from any group (rules: varg passive), and damage wakes a group (camps.wake). `camp_attack_targets` skips monolith groups other than `siege_group()`, but a target diagonally next to such a Monolith's tile still woke it through the splash. `breach` had the same hole.
- The new `splash_wakes_monolith(world, p)` checks the 8 live neighbours of p and runs only for Varg. Targets it flags are skipped in both places. A splash on a Monolith is a hit on it, so this is the same rule the code already applies to direct hits.

## Considered, not changed

- **Using `camp_scale(world.me())` in `breach`'s `turns`.** It reads the belief's health rather than `my_health()`, so it could differ mid-turn. Not worth a behaviour change.
- **A shared helper for the "fresh ? max_health : belief.health[i]" pattern** (min_camp_damage, spell_clear_rounds, fastest_clear, reflected_clear). Each is already a one-liner with `fresh` hoisted, and a helper risks re-testing the state per member.
- **Folding the four `static std::array<Kept, 256>` caches into one template.** Each keys on different inputs, so a template would hide more than it saves.
- **The `int64` sentinel in `safe_targets`.** It is ugly but free: constant-initialised static storage.

## Suggestions

1. **Varg's splash wakes other non-Monolith groups too** (camps.cc:38-62, and `reset_and_attack_camp` in combat/self_abilities.cc:289). Two cases:
   - Farm's harmless "resource" hits on a cluster can wake a diagonally adjacent wolf, elk or golem group.
   - An `allowed` filter (siege's `h == g`, support's harmless-only) can wake a group it rejected.

   Whether that is acceptable is a judgement call (sometimes the neighbour is next anyway), so it is unfixed.
   - Suggested fix: for Varg, reject a target whose splash reaches a live camp of a group `allowed` rejects and that is not already `fully_awake()`.
   - `reset_and_attack_camp` also needs the Monolith check added here, because it picks its own target. It belongs in self_abilities.cc.

   Severity medium for Varg drafts; effort small.
2. **Ren's damage model ignores reach** (camps.cc:205-224, the reflect path of `min_camp_damage`). It charges every living attacker every round (`left[j].strength * k`). The non-reflect path charges only the strikers whose reach covers the stand tile (`fire`).
   - On spread groups (a line of golems, mixed elk and wolf), Ren's clear damage is overstated, so farm and finishing_camp turn down clears Ren could take.
   - Fix: charge `fire`-masked strikers. That needs `clear_fire`'s per-member masks, not just its sums.

   Severity medium for Ren; effort medium.
3. **Ground spells reach 5, not 4** (camps.cc:434, `spell_clear_rounds`). Ground casts hit the 3x3 around a tile within 4, so `AbilityFacts::reach()` is 5. An elk or golem (range 4) can be hit with no reply from distance 5 by Stellar's or Prism's ground spell, but the code rejects every group with an attacker of reach >= 4.
   - Exact model: ground-spell output only, against attackers of reach 4.
   - Value is low (Stellar's ground spell does ~12/turn against a 2400 hp elk), so it would mostly matter for finishing a wounded elk.

   Severity low; effort small.
4. **Spell kiting is ranged-only** (economy/farm.cc:662: `spells = ranged ? spell_output : 0`). Marcella's 2x unit spell and Ren's 1.1x reach 4 > wolf range 3 just as well, and `safe_targets` already handles melee basic attacks on harmless members. This looks like an arbitrary restriction. Severity low-medium (Marcella drafts on wolf maps); effort small, but it changes behaviour, so A/B it.
5. **`breach` charges one round of fire too many** (camps.cc:129). Our first hit wakes the group, and the killing hit lands before that round's camp phase, so `turns` hits cost `turns - 1` rounds of fire (as `min_camp_damage` does with `damage -= left[0].fire`).
   - It also ignores other awake groups reaching `here`, the attack reset (`reset_and_attack_camp` runs right after), and spells.
   - Today's version is conservative. `(turns - 1)` is the exact form, plus the reset if `has_attack_reset`.

   Severity low; effort trivial (behaviour change).
6. **`stand_reach`'s stand tile is a heuristic** (camps.cc:236-260). It uses `range` tiles out from the member, away from the group's middle, clamped to the map, ignoring walls and other camps.
   - Exact version: for each member, take the minimum over `standable` tiles within `range` of the striker mask. Choose by fewest strikers with everyone alive, or better, by the mask's strength.
   - It is static and built once per group and range: at most ~49 tiles x n members x 32 strikers. Build it lazily per group, as now, never all groups on round 1.

   Severity medium (clear damage feeds every farm decision); effort medium.
7. **Duplicate emblem readers.**
   - `has_family` (camps.cc:144) duplicates `owns()` in model/world.cc:84, and `camp_dealt_with`/`champion_dealt_with` duplicate `emblems()` (world.cc:89-101).
   - `camp_hit_factor`, `camp_dealt_factor` and `champion_dealt_factor` each make an `sdk_champion_items` host call. Several callers use two or three per turn (plan.cc 1131/1436, siege.cc 315/318), and each pays its own call plus up to ~45 item reads.
   - Fix: one per-turn read of our emblems, re-read after a purchase, with a single family test shared with world.cc.

   Severity low (fuel); effort small-medium (crosses files).
8. **The splash score reads stale health** (camps.cc:60). It counts neighbours with `health[j] > 0`, while the target's own health falls back to full when the belief says dead. After an unseen respawn, Varg's splash bonus reads 0. Use `live_health`-style logic on live tiles, e.g. `test(live, members[j].pos)`. Severity low; effort trivial.
9. **`min_camp_damage` assumes we stand at one tile per member** (camps.cc:191-202). It ignores rounds spent walking between stand tiles. For melee clearing a spread group that understates `rounds`, and the damage while walking under fire. This is a modelling gap, not an obvious fix. Severity low-medium; effort medium.
