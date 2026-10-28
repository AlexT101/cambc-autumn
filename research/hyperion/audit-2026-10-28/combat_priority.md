# Audit: bots/astraeus/src/model/combat_priority.h

The "teacher" turn-order priority: dead 13, danger 14..23 (tenths of a one-turn kill, ours of an
enemy or theirs of us), else `idle_priority` by role and health. `turn_order.cc` uses it
whenever no band wish is made, and in its fuel shortcut.

## Changed

Commit `560ce633`, `astraeus audit (combat_priority): cleanup`. The bench replays are byte-identical (8/8). Total fuel
2211802776 -> 2211790165 (-0.0006%), from dropping one `std::floor` call.

- Comments: the type enum's comment now points to the static_asserts that tie it to
  `cambc::champion_type`. `role()` gets a comment: it is the idle tie-break and also marks, by -1,
  the champions that bid for turn_order's bands. `strike()`'s comment now says what the function
  is: compute_strike at one distance, without stuns, with the cooldown-0 caveat. The
  priority-scale comment is reworded. Inline notes from compute_strike are copied over: ranged
  walk spends the attack; walk, reset, attack; landing then attack; excludes walking but not the
  attack.
- `strike()`'s dash branch now uses `a.lands()` and `walk + a.reach()` in place of
  `a.multiplier > 0` and `walk + a.range() + a.radius`. The values are the same for every
  champion in the table, and it now reads like compute_strike.
- `std::floor(...)` on the clamped, non-negative ratio became a plain int cast, which gives the
  same result.

## Considered, not changed

- **Self cooldowns `!= 0`** (`strike`, line 54). The comment says this is deliberate ("raw
  cooldown zero"). Changing it changes behaviour and is a judgement call. See Suggestions 1.
- **`Unit::type = prism` default.** Every caller sets the type, so the default is never used.
  Changing it to -1 would be cleaner but gains nothing.
- **The redundant `enemy.alive` and `enemy_hp > 0` checks.** `live_start_enemies` only passes live
  enemies. The checks cost almost nothing and keep the function safe for other callers.
- **Renaming the namespace `teacher_priority` or the file to match each other.** This is a
  cross-file rename (turn_order.cc, world.h). Left to the orchestrator.

## Suggestions

1. **Our own cooldown-1 slots count as not ready** (combat_priority.h:54, with the self cooldowns
   read at turn_order.cc:33-36). `priority_self` reads our cooldowns before our turn-end tick. A
   slot reading 1 will be 0 at our next turn, and the bot's own model agrees: `read_strike` uses
   `ready_round = round + cooldown`, ready when `cooldown <= 1`. So our `outgoing` undercounts
   abilities that come ready next turn. For enemies, the raw value read at our turn start is right
   for their next turn. Fix: compare `self.cooldowns[slot] > 1` for self only, by passing a
   threshold or adjusting `priority_self`. Severity low-medium (it shifts when we enter the danger
   band); effort trivial; needs an A/B.
2. **Role champions never bid for the bands** (turn_order.cc:392). Prism, Vesper, Ryth, Vendetta,
   Marcella and Heart of Ruin, which are exactly the usual draft, skip four checks:
   - `offer_kills`: an exact team kill check that acts before the enemy;
   - `offer_channel`: protects our ending recall or tribute;
   - `offer_escape`;
   - `offer_heal`.

   They rely only on this heuristic, which uses a single-champion kill ratio, start-of-turn enemy
   health and no allies. The bands look strictly more informed, so A/B enabling them for every
   champion. Severity possibly medium; effort trivial plus an A/B.
3. **Stale inputs**:
   - `outgoing` divides by the enemy's health and shield at our turn start (world.cc:1694), so
     damage we dealt this turn is not counted.
   - `stunned` is also from turn start, so an enemy we stunned this turn still counts as
     `incoming`.

   `live_enemies` in turn_order.cc already reads current health per enemy, so threading
   health and a fresh `stun_pending` into `live_start_enemies` would be cheap (one raw read per
   enemy). Severity low; effort small.
4. **We ignore our own pending stun.** `priority_self` never sets `self.stunned`. If we lose our
   next turn, `outgoing` should be 0. Low, since a stunned champion can still set its priority on
   the skipped turn.
5. **Missing damage modifiers.** The target's Durability (`taken` 0.9) is ignored, as are our
   Skirmish (+5% to champions) and Collectors bonuses (`ChampionBelief::dealt`). Camp damage is
   also missing: it lands in the camp phase before next round's champion turns, so
   `incoming / (self_hp - camp_damage)` would be closer. Low; small.
6. **Duplicates compute_strike** (safety.cc:758). `strike()` is compute_strike without stuns and
   at one distance. The two have to be kept in sync by hand: a new champion or a rules change
   must be made in both. Calling compute_strike costs more: it fills a 7-entry array per call
   (up to 12 calls per priority), but stays well under 1k per turn. Alternatively, make it a
   constexpr template over an `add(reach, damage, stuns)` sink and use it in both places. Low;
   small-medium effort, cross-file.
7. **Simplify the type enum** (combat_priority.h:11). `Type` mirrors `cambc::champion_type` and
   needs 13 static_asserts in turn_order.cc:41-53. `role()` could switch on
   `cambc::champion_type` directly, since champions.h already includes cambc.h. That would delete
   the enum and the asserts. Cosmetic; cross-file.
8. **A dead champion still holds a turn slot.** `World::slot` counts all allies, and
   `dead_priority` (13) puts a dead champion ahead of idle living allies. That pushes the living
   ones one alternation later, after another enemy turn. This may be intended (idle champions
   prefer to act late), but the effect should be stated or A/B'd: with it below idle, the living
   would act earlier. Severity unknown; trivial to test.
