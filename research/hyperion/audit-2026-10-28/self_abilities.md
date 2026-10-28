# Audit: combat/self_abilities (2026-10-28)

Files: `bots/astraeus/src/combat/self_abilities.cc`, `bots/astraeus/src/combat/self_abilities.h`.

## Changed

Commit `astraeus audit (self_abilities): cleanup`. The fuel bench (`--test-draft`, 00ambush 00lanes 01hooks 00interlock) gave **8/8 identical replays, total fuel -0.12%** against `audit-base.json` (mean 50161 -> 50101). A second run on our own drafts (no `--test-draft`) against a frozen HEAD copy was also 8/8 identical, at -0.12%.

- **`landing_harmful`** replaces `wakes_camp` + `landing_suicidal` at all six call sites. Heart of Ruin's dash slot and radius are now looked up once per landing instead of twice. `landing_suicidal` now takes the radius.
- **`dash_across` reuses `travel_dash`**. `threats_near` gained a `camps` flag, and `travel_dash` passes it through. This removes a duplicate of the travel-dash landing filter and the second static scratch vector that copied out the enemy hazards.
- **`escape_landings`** is now shared by `dash_away` and `quote_escape_dash`, which had identical landing searches. A quote with no landings is now returned empty (slot -1). Callers can't tell the difference: `cast_escape_dash` already rejects `count == 0`, and `fight.cc` only reads `count` and `clears`.
- **`attack_target`**: its two `world.enemies` loops (Cassi/Issac partner, then shield and Durability) are merged into one.
- **`reset_and_attack_enemy`**: the long one-line condition is split into a named `kills`.
- **`reset_and_attack_camp`**: the group check (`group < 0`, a monolith group that isn't the siege group) now runs once up front instead of on every live camp tile. Removed: a `throw_if_stale()` straight after `cast()`, which `cast_slot` already does, and the `me` local.
- **`dash_to_attack`**: the "break if a target was given" loop is now `if (!target_given) { ... }`. Strength and our health fraction are only computed inside it.
- **`heal_ally`**:
  - Removed the `identity_of(c).team` check. The tiles come from ally occupancy, and a tile holds one unit.
  - `kept_recall` (two host calls) now runs after the cheap `worth_healing` test. `heal_target` does the same.
  - The redundant `slot_of` + `ready` pair is now a `heals()` early exit followed by `ready`.
- **`shield_if_needed`**: returns on the first enemy whose blow hits, and on the first dangerous camp group. Before, it ran every enemy's `blow` (which builds Reach lazily) and kept a `danger` flag through the loop. It also gained a `has(shield)` early exit.
- **Fuel note:** calling `ready()` first in `heal_ally` made almost every turn about 27 fuel dearer (+0.07%), even though `ready` returns at `slot < 0`. The `heals()` / `has(shield)` exits in front of `ready` account for most of the saving. Other `ready()` callers that run every turn may gain the same way.
- **Comments:**
  - `Rank` named `dash_to_kill`, which doesn't exist; it now says `dash_to_attack`.
  - `shield_if_needed`'s header said "Varg", but Heart of Ruin also casts through it.
  - `dash_towards(goals)`'s header now documents the 4-round pause after a failed search, which is shared across all goals.
  - `attack_target`'s header said "the weakest"; it takes the biggest kill first.
  - `reset_and_attack_enemy`'s header said "the weakest in range"; it uses `attack_target`'s choice and is held for Varg's shield.
  - Added: what `chase_health` means, why `danger` counts camps flat, and why `shield_wanted` exists.

**Coverage caveat:** the test drafts have no Willow, so the `heal_ally` / `heal_target` changes rest on reading the code: occupancy is per team and one unit fits on a tile, and `kept_recall` / `worth_healing` are pure reads. I didn't check whether our own draft picked Willow on those maps.

## Considered, not changed

- **`reset_and_attack_camp`: iterate the group's members instead of the tiles in range.** It would be cheaper, but tie-breaks between equal-health members follow tile order now and would follow member order, which changes behaviour.
- **An and-not helper for `goals & ~walls`** in `dash_towards`: `util.h` has none, and the and+xor pair with its comment is clear enough.
- **Dropping the `static` scratch in `threats_near` / `attack_target`:** they're there to avoid allocations, so they stay.
- **Merging `heal_ally` with `heal_target`:** `heal_ally` reads live tiles (allies come into sight as we move), while `heal_target` works on beliefs. Merging them would force one onto the other's inputs.

## Suggestions

1. **Camp threats ignore "nearest champion".** Files: `self_abilities.cc` `threats_near` (~line 63), `shield_if_needed` (~line 545). Medium severity, small effort.
   - The rules say an awake monster hits the nearest champion of either team in its range, with ties going by turn order.
   - Every awake monster in reach is counted as a threat to us. That inflates `danger`, so we escape or skip travel dashes needlessly. It also makes Varg and Heart of Ruin shield when an ally (or an enemy) stands nearer the monster.
   - The fix is exact and cheap: skip a member if a visible champion is strictly nearer to it. Visible champion tiles are already a host bitboard.
   - Equal distance needs the turn order (`rounds.champion_order`); counting ties as threats is safe.
2. **`shield_wanted` and `shield_if_needed` disagree (Varg).** Location: `self_abilities.cc` ~line 181 vs ~line 545. Medium severity, small effort (needs a `Safety&` in `reset_and_attack_enemy`, a cross-file signature change).
   - `reset_and_attack_enemy` holds the reset when `shield_wanted` sees any visible enemy within `threat_strike(...).reach`. That's coarse: no Reach pathing, no teleport destination, no camps.
   - `shield_if_needed` uses `safety.blow(e, here).hits` plus camps.
   - When `shield_wanted` says yes and the later `shield_if_needed` says no, Varg ends the turn with neither the reset nor the shield.
   - Fix: pass `Safety&` and use the same test in both.
3. **Varg's splash wakes camps, and it isn't modelled.** Location: `attack_target` ~line 245, `reset_and_attack_camp`. Medium severity for Varg, small effort.
   - Varg's basic attack also hits camps within 1 of the target. An enemy standing next to a sleeping strong group (wolves, elk, golem, monolith) is valued only for its champion damage, and hitting it wakes the group onto us.
   - `landing_wakes(world, t.pos, splash_radius)` already answers this; skip such targets unless the hit kills.
   - In `reset_and_attack_camp`, Varg picks the member nearest death and ignores the splash. Choosing the member whose 3x3 holds the most (or the most killable) members would be exact.
4. **`dash_to_attack` can dash to a target it then won't attack.** Location: ~line 386. Low to medium severity, small effort.
   - When no target is given, it picks finishable enemies without `attack_target`'s retaliation filter. If the pick is Ren and its retaliation would kill us, `attack_target` refuses afterwards. The dash is spent and leaves us next to the enemy.
   - Add `e.retaliation() * world.me().taken < my_health_and_shield(world)` to the filter.
   - It also ignores an enemy's `shield` in the "chase" fraction (`e.health / e.max_health`). That's a minor point.
5. **`danger` weighs every camp as 2.** Location: ~line 77. Medium severity, medium effort.
   - A wolf (20 Strength) counts the same as a monolith (200), and the same as an enemy two tiles inside its reach.
   - A damage-based score would be exact rather than a heuristic: monster Strength x `camp_hit_factor()`, and `threat_strike(...).at(d)` for enemies.
   - Stunned camps (`camp_stunned`) skip their next attack and could be dropped.
6. **The travel-dash pause is a throttle shared across goals.** Location: `dash_towards(goals)` ~line 345, `failed_search_pause`. Low to medium severity, small effort.
   - A failed search blocks every travel dash, for any goal, for 4 rounds. `farm.cc` calls this with two different goal sets (cleared group tiles, attack tiles), so a failure on one suppresses the other.
   - The search is bounded (about 1.5k + (20 + layers) per 8x8 chunk, capped by `max_steps`). Removing the pause, or keying it on the goal group, should be affordable; measure with the fuel bench and an A/B.
   - It isn't conditional on fuel, but it chooses worse to save fuel.
7. **Killing a linked pair is undervalued.** Location: `attack_target`'s `worth` (~line 235). Low severity, trivial effort.
   - A kill returns `s.health + life_value`, but killing Cassi or Issac kills both bodies (and hands over both bags). Adding the visible partner's health, when it is known, would rank a pair kill correctly.
8. **No shield on spawn.** Location: `shield_if_needed` ~line 550. Low severity; a judgement call.
   - Healing on spawn happens at our turn end, and enemies can attack into the spawn. A burst bigger than full health between our turns, from several enemies or a stun chain, would still be absorbed by a shield cast on spawn.
   - Worth an A/B only if spawn deaths show up in replays.
9. **The `ready()`-first pattern costs fuel.** See the fuel note under **Changed**. Callers that run every turn without a cheap facts check first (`shield_wanted`, and other files' `ready` equivalents) may be worth the same early exit. Fuel-only; check with the bench.
