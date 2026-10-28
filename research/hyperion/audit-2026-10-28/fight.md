# Audit: combat/fight.cc

Scope: `bots/astraeus/src/combat/fight.cc` (fights: `want_home`, `prey`/`chase`, the game-ender stop,
sure kills and `retreat`).

## Changed

Commit `astraeus audit (fight): cleanup` (236c5050). The 8 bench replays are **byte-identical**. Fuel
over all turns: total 2,211,802,776 -> 2,211,718,312 (-84k, -0.004%); 2906 turns cheaper, 10 dearer
(noise from codegen).

- `last_round_before_channel_ends(world, e)`: new helper for the "last round we act before its
  channel completes" logic, which was duplicated in `intercept_steps` and `prey`'s teleport filter.
- `intercept_steps`: the nearest-altar search keeps its best distance instead of computing
  `dist(from, altars[a])` again on every comparison. It still picks the first minimum, as before.
- `sure_kill`: health, Strength and max health came from three `my_record()` host calls, plus
  `champion_dealt_factor()` (an items read), on **every** call. `step_to_kill` calls it up to 1 + 8 + 25
  times. A new `OurHit our_hit(world)` reads them once, from one record, and `sure_kill(world, us, from, range)`
  takes it. The old signature stays as a wrapper for `retreat`, whose calls have attacks between
  them (Ren's retaliation changes our health). The float expression order is unchanged.
- `step_to_kill`: the lambda `strike` shadowed the global `strike(const ChampionBelief&, int)`, so I
  renamed it `hit`.
- `untouched(const Safety::Bound&)`: shared by `quote_prism_retreat_walk` (which had the odd
  `!(risk.doubled <= 0)`) and `hor_retreat_casts`.
- `hor_retreat_casts`: merged the two `!casted` branches that both ran `see_again` and cleared `reusable`. I
  fixed its header comment, which said only a killing landing goes before the escape. That is true
  only when the escape dash clears and lands untouched; otherwise `cast_at_enemies(…, false)` can
  spend the dash on a damaging landing.
- `retreat`: renamed `reserve` to `keep_dash`.
- Comments: reworded `retreat_step` and `want_home` (the old header, "an enemy that could kill us
  overrides finishing a camp", described one branch only).

## Considered, not changed

- The `debug_block` `CHASE-AVAIL` trace in `prey` and the `prey-cut-short` shortcut note: they look
  like leftovers, but the replay harness's `TRACE_SCHEMA.md` documents them, so I kept them.
- `chase` uses `clear_board`/`draw_square`/`and_into` while `stop_game_ender` uses the bitboard member
  functions. I didn't unify them: same meaning, and the free functions may exist for fuel reasons.
- `flee_camps` measures the walk out of camp reach as the crow flies (`any_within`), while
  `camp_exit_rounds` walks around walls. It is only a cost tie-break among neighbours, so I left it.
- `camp_exit_rounds` makes up to `max_camp_reach` (5) `reachable_tiles_into` host calls. One distance
  field would need its layers extracted, and that is not clearly cheaper.
- No behaviour fixes: each candidate below is a judgement call or needs an A/B.

## Suggestions

1. **`game_ender` ignores a walking carrier whenever our bag wins** (fight.cc `game_ender`, the
   `if (win && !(tributing && ...)) continue;` line). The comment says "our winning bag outruns a
   walking carrier", but that is not computed. If an enemy with `need` gems stands one step from an
   altar and we are 30 steps from ours, it lands first. `intercept_steps` already computes `theirs`
   (walk to the nearest altar + channel), so compare `turn_start(e, round + theirs)` with `win_lands`, as
   the tributing case does. Severity: high when it happens (it decides the game), but rare. Effort:
   small.
2. **Ren (and any dasher whose other slot is an enemy cast) can spend its escape dash's cast on a
   stun while retreating** (`retreat`, the else-branch `cast_at_enemies(world, escape_step_value)`).
   Only Heart of Ruin gets `keep_dash`. For Ren (stun slot 0 + dash slot 1, one cast a turn), a stun worth more than
   `cast_cost + walk` (40 + 210) costs both the walk (excludes walking) and the dash. Generalise
   `keep_dash` to "has a dash and its other slot hits enemies", or count the dash's escape value
   in the threshold. Prism's `prism_retreat_walk` rule (a cast may take the escape walk only if it
   kills or stuns the sole threat) similarly applies to every walk-excluding caster (Ryth, Stellar,
   Tavi, Ren, Cassi, Marcella slot 1), not only Prism. Severity: medium for those champions. Effort:
   small to medium; needs an A/B.
3. **A ranged dasher one step outside attack range walks instead of dashing** (`chase`'s `> range + 1` gate, and the same in
   `stop_game_ender`). For Vesper (the only ranged dasher) a walk spends the attack, and with its reset on
   cooldown it gets no hit this turn, while a dash then attack would land one. Gate on
   `dist > range + (ranged && !reset_ready ? 0 : 1)`. It is a judgement call (it spends the escape
   dash), so I didn't change it. Severity: low to medium. Effort: small; A/B.
4. **`intercept_steps` treats "in attack range" as stopping a tribute or teleport** (`stop = steps`).
   Damage interrupts neither; only a kill (or a stun or lock) stops them. Reaching range does not mean the
   bag is taken by `last`. A rough exact check: `effective_hp(e) / our damage per turn` turns of
   hitting must fit too, or drop `steps` from `stop` for tributes and teleports, leaving stun and lock.
   Severity: medium in endgames (it chases tributes it can't stop instead of other work). Effort:
   small.
5. **`intercept_steps` is one turn pessimistic for free or walk-compatible stops.** `stop <= last - round`
   counts walking `stop` turns and then acting the turn after. A lock placement is free (same turn as
   the last step), as is a melee attack or a non-walk-excluding stun (Cassi, Marcella's reset). Use
   `stop - 1` for those. Severity: low (conservative). Effort: small.
6. **`game_ender` considers single bags only.** Two enemies tributing at once (or Cassi and Issac
   each tributing their own bag) whose bags together reach `need` are not flagged, though stopping
   either keeps them short. Severity: low (rare). Effort: medium (sum the in-flight tributes like
   `gems_short`).
7. **`prey`'s self-delay test is ranged-only** (`delayed` for `a.is_self`). A melee champion two or
   more steps out (no dash) can't hit this turn either, and a ranged one at range + 2 or more stays delayed
   even with a reset. `strike(self, world.round).hits(dist)` (as for allies) would cover every
   champion and ability uniformly, if `Strike` models the ranged walk/attack allowance (its header
   says it follows the rules' action allowances). Severity: low to medium (chase decisions).
   Effort: small; A/B.
8. **Fuel gate: `prey`'s `fuel_ok(fight_cost_estimate() + reserve)` cut (`prey-cut-short`).** When
   fuel is short it stops simulating candidates, so no chase. The `lost` memo already dedups equal
   fights, and with at most 6 enemies the loop is bounded. If `chase_trade` could be bounded per
   call (a cap on simulated turns), the gate could go. Effort: medium (lives in safety.cc).
9. **`ally_stops` returns false for any enemy in a bush**, including the lock case, which needs no
   sight of the enemy, and Ryth's ground stun, which hits unseen enemies. Conservative (we stop it ourselves), so low severity.
   It also counts only an ally's current distance, not a walk before a non-excluding stun or a lock
   placement. Effort: small.
10. **`sure_kill` ignores our shield against Ren's retaliation** (`retaliation * taken >= health`),
   while `attack_target` uses health plus `my_live_shield`. Conservative: Varg and Heart of Ruin with
   a shield up skip a sure kill on a low Ren. Add the shield to `OurHit::health` (one `shield_value` read
   when `shield_slot >= 0`). Severity: low. Effort: tiny.
11. **`intercept_steps` uses `pair_gems` for a walking Cassi/Issac's channel length**, but each body
   tributes its own bag (`b = ceil(gems/10)` per body). It overestimates their channel, so we think
   we can intercept later than we can. Severity: low. Effort: tiny (use `e.gems`, or the max of the
   two bodies' channels).
