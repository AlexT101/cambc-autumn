# Audit: idle_priority (2026-10-28)

File: `bots/astraeus/src/model/idle_priority.h` (16 lines). Its only caller is
`teacher_priority::priority` (`model/combat_priority.h:93`), which uses it when no danger bucket is
set. `turn_order.cc:72` builds `lowest_raw` from `idle_step` and `health_buckets`.

## Changed

- **Comment rewritten** (commit `fc316def`, cleanup). The old comment ("falls by idle_step for each
  tenth of health missing") left out three non-obvious points, and the first matters most:
  - A higher priority acts first, and a camp's equidistant tie hits whoever acts first
    (`camps.attack`), so healthy champions take the tie hits.
  - Shield counts only up to max health.
  - Carrying any gems halves the health fraction, so a full-health carrier ranks with a gemless
    champion at half health.

  The comment also gives the value range, which `turn_order.cc`'s `lowest_raw` and the "idle at
  most 12" assumption depend on.
- **Return expression** `role + idle_step - idle_step * floor(...)` is now `missing` plus
  `role + idle_step * (1 - missing)`, the same form as `lowest_raw` in `turn_order.cc`. It is
  integer arithmetic only, and the float expression is unchanged.
- Bench: 8/8 replays byte-identical, total fuel 2211802776 -> 2211802776 (+0.00%).

## Considered, not changed

- **Dividing `effective_hp` by 2 instead of doubling the denominator.** It gives the same float
  result (power-of-two scaling is exact), but it isn't needed and could change codegen.
- **Float bucket boundaries.** `floor(10 * (1 - f))` can land either side of a boundary when f is
  exactly a tenth (e.g. 0.7). This is harmless: it moves a priority by one step at a knife edge.
- **A `max_health <= 0` guard.** It isn't needed: dead units return `dead_priority` before this
  is called, and live champions always have a positive max health.

## Suggestions

1. **Gems are a yes/no flag, but what a camp kill costs depends on the gem count**
   (`idle_priority.h:16`, `gems > 0`). Severity low-medium, effort medium.
   - A champion killed by a camp loses all its carried gems (`combat.camp_kill`). One gem and 80
     gems get the same halving.
   - The real question in a camp tie is whether the hit kills. That depends on absolute
     `health + shield` against the strength of the monsters in range (with jungle/durability
     emblems), not on the health fraction.
   - An exact version would rank allies by the cost of absorbing a tie hit:
     `life + gem_value * gems` if it kills, else roughly zero.
   - This is behaviour-changing and needs an A/B.
2. **`role()` gives -1 to every non-teacher champion** (`combat_priority.h:27-37`): stellar,
   cassi, issac, willow, ren, varg and tavi. Within a health tenth, these act last, so they never
   take a tie hit before a teacher champion. That is backwards for the natural camp tanks. Severity
   low, effort small, needs an A/B.
   - Ren reflects 0.2x Focus to monsters that hit it.
   - Varg's shield soaks hits.
   - Willow and the Cassi pair are fragile, so -1 suits them.
3. **No static guard that role never crosses a bucket.** The scheme needs the role span (-1..4,
   width 6) to stay below `idle_step` (8). It also needs `max role + idle_step` (12) to stay below
   `dead_priority` (13). A future role of 5+ would silently break both.
   - Suggest
     `static_assert(role(heart_of_ruin) + idle_step < dead_priority)` and a span check in
     `combat_priority.h`.
   - `role` is a switch, so the max isn't automatically derivable; a small constexpr loop over
     the types would do it.
   - Severity low, effort trivial.
4. **The priority is set a round late.** It takes effect from the next round (`rounds.team_order`),
   so the idle ordering protects against camp ties one round late. When a champion's health
   or gems change mid-turn (a capture payout, a hit), the next round's camp phase still uses this
   priority, which is fine because `set_turn_order` runs at the end of the turn. Only a stale case
   remains: the turn-order fuel shortcut (`turn_order.cc:379-389`) keeps the old rank. That is an
   existing fuel gate, but the idle computation itself is ~tens of instructions. The expensive
   part is the band logic and `priority_self`'s host reads, not this file. No action here.
5. **Wider question.** The idle ordering only matters for camp tie hits and for who reaches
   contested tiles or captures first. If (1) and (2) are fixed, consider dropping the
   health-fraction buckets entirely in favour of the exact "who should absorb a tie hit" ranking.
   Effort medium, needs an A/B.
