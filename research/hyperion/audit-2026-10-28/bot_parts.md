# Audit: bot_parts.h

`bots/astraeus/src/bot_parts.h` holds declarations, small shared structs and per-turn globals; nearly all logic lives elsewhere. Every declared function is defined in the file its section names, and every declaration and type is used.

## Changed

Commit `70cfbc74` (cleanup). Comments only. The bench replays are byte-identical (8/8), with fuel +0.00%.

- `decision`: the letter list was missing `h` (Willow's heal or formation, support.cc) and `r` (Prism's recovery, support.cc:528). It now also says that act() and farm read the letter (`'W'`, `'C'`, `'F'`), so it is more than a trace.
- `sieged`: siege.cc sets it, and so does bank.cc:748 (the siege's heal trip). The comment now says both, and that act() keeps the siege because of it.
- `support_requested / offered / retreat` had no comment. They now say what they feed: the turn end's `comms::support_intent`, and the hand-off to `retreat()`.
- `SupportExposure`: the comment cited `Safety::damage_bound`, but the code uses `Safety::bound`. It now defines every field.
- `Station / Stations`: documented `open` and the cache key, and made `guard`'s meaning precise.
- `AltarAccess`: rewrote the comment, which was hard to parse, as `open`/`opened`/`blocks` semantics checked against `rebuild_altar_access` (bank.cc:175).
- `AltarWalk` / `altar_walk_pending`: both referred to `warm_altar_walk`, which does not exist. The warm-up is in `prepare_next_turn` (bot.cc:373). The comments also named `tributes_walked` without saying it belongs to `StaticMap`.
- `cycle_horizon`: the comment now says it is `rate()`'s horizon and how it scales with map size.
- `Emblem`: the comment listed only Power, Jungle and Durability. `best_emblem` also weighs Bruiser, Monster, Jungle-Health for healers, forced passives and others, so the list was already stale. It is now general.
- `HomeTrip`: the comment had a broken line wrap and an unclear order. I rewrote it to follow `rounds()`, and documented `short_gold`'s default.
- `Income::spent` is reset at each turn's start (shop.cc:587), not at "the start". Also added one-line comments on `CampAttackTarget(s)`, `CampLeft` and `PurchaseQuote`, and noted at the top that play_turn resets the per-turn flags.

There is no fixes commit: nothing in this file was an obvious, non-arbitrary bug.

## Considered, not changed

- **Sorting the includes** (`params.h` sits among the `model/` ones). This is cosmetic, and since some headers may rely on include order, it isn't worth the risk.
- **Dropping includes the header doesn't use itself** (`<bit>`, `<cmath>`, `<limits>`, `<memory>`, `<span>`). The `.cc` files get them through this header, so dropping them would mean editing those files.
- **Reordering `HomeTrip::rounds`** to test `unreachable` before the sum. `unreachable` is a `uint16_t` (65535), so the sum can't overflow, and the current order is fine.
- **Raising `CampAttackTargets`' capacity to 48** (all tiles within ranged range). See suggestion 1: the cap also bounds failed-attack throws, so this is a judgement call that belongs in camps.cc.

## Suggestions

1. **camps.cc:35, bot_parts.h `CampAttackTargets`: candidates are truncated before they are ranked.** `camp_attack_targets` fills `found[16]` in `positions_within` scan order and only then sorts by score. A ranged champion reaches 48 tiles, so next to a big group (or several groups) the best-scored member can be dropped unseen. Fix: keep the top 16 by insertion while scanning; it is just as bounded.
   - Fuel: `attack_camp_targets` tries targets in order, and each refused attack throws (about 3.9k). Sixteen unseen live tiles (bush-hidden camps, stale beliefs) could cost about 62k. A cheap visibility test before each `attack()` would bound that without a fuel gate.
   - Severity low to medium; effort small.
2. **camps.cc:163 and farm.cc:762: the horizon formula is duplicated.** Both compute `cycle_horizon * max(1, max(W,H)/50)`. A `float cycle_horizon(const StaticMap&)` in bot_parts.h would leave one place to tune it. This is pure cleanup and should be byte-identical. Severity: maintainability; effort trivial (two other files).
3. **`decision` drives behaviour.** act() reads `'W'` and `'C'` (bot.cc:404/407), and farm reads `'F'` (farm.cc:393). Branch logic keyed on a trace letter is fragile: renaming a letter, or setting `'F'` from capture.cc:220, silently changes farming. Suggest an `enum class Branch`, or explicit flags such as `sieged`. Severity low; effort small.
4. **Declarations that could leave the shared header.** `CampLeft` and the `min_camp_damage(CampLeft*, ...)` overload are used only in camps.cc, and `spawn_steps` only in shop.cc, after its definition. Moving them into their own file narrows the header. Effort trivial, but it means editing those files.
5. **shop.cc:572 `note_income_start`: a payout and a tribute in the same window are lost.** A capture payout that arrives in the same window as our tribute completing is not recorded. Tribute completes at our turn end, after `note_income_end`, so the next start sees `gems < gems_at` and skips the payout. The rules let a channelling champion on a camp tile hold it, so this can happen whenever we tribute from a camp tile next to an altar. I haven't checked how often the bot does that. The result is that Prospector/Capture passive pricing (`income.holds`, `prospected_*`) runs slightly low.
   - Exact fix: also record in `note_income_end` that a tribute is about to complete (`my_channel_time() == 1` with channel tribute), and take `gems_at = 0` for the next start.
   - The same applies to Marcella's tribute gold, which arrives in that window.
   - Severity low; effort small.
