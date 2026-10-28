# Audit: combat/support.cc (support)

Line numbers are for `bots/astraeus/src/combat/support.cc` after the cleanup commit.

## Changed

One commit, `astraeus audit (support): cleanup`. The bench replays are byte-identical:
- Required bench (4 maps, test drafts): 8/8 identical, total fuel -602. Only 00ambush A has a Willow, and it has no Prism.
- No game in that bench pairs Prism with Willow, and neither do the model drafts on 00ambush, 00lanes, 01hooks, 00interlock, 00gem-fields or 00oasis. So I also benched HEAD against the candidate, both copied with `map_model_draft = false`, which makes draft_five pick Prism + Willow. Maps were 00ambush, 00gem-fields, 00oasis and 00lanes, 6 of the 8 games had the pair, and both sides ran the recovery and formation code. Result: 8/8 identical, total fuel -66.9k (931 turns cheaper, 25 dearer).

What changed:
- **Comments.**
  - The file header now names Tavi as a possible protected mate.
  - The vague "tank may leave" comment in `exposure_at` is reworded.
  - `heal_viewers`, `immediate_camp_finish` and the Prism attack comment are rewritten; the last no longer refers to "the search", which doesn't run on that turn.
  - The banking-step comment moved next to the `<=` it explains.
  - `local_support` gets a header saying what each side of the pair does. The `support_turns` comment is split from it.
  - New short comments on the heal tie-break and the reset-vs-heal cast.
- **Helpers.** `attack_support_camp(world, work)` replaces two copies of the same `attack_camp` predicate. `drop_claim(memory)` replaces three copies of the claim/crew/siege reset.
- **Tie-breaks.** The lexicographic tie-breaks (gain, then fraction, then cost or support request) in `heal_station` and the target loop are each one nested comparison now. They are the same for all non-NaN values and stay false on NaN, as before.
- **Dead code removed:**
  - The `p == here ||` tie clause in the formation ranking. `here` is tried first (k = -1), when `found` is false, so the clause could never decide anything.
  - `memory.recovery_turns >= support_turns` in the recovery expiry. Recovery commits at most once a round, so `recovery_turns <= round - recovery_start` whenever a recovery is open.
  - Re-reading `support_exposure(my_position()).safe()` when Willow stays. `best == here` can only be chosen through the safety filter, and with no re-observe in between the stations cache returns the same value.
  - Two redundant `support_owned = true` and one redundant claim/crew/siege clear. `commit_support` had already done both.
  - In the reentry block, `!leave && protected_work() && holding_capture()` became `holding_capture()`. Both branches return false, and `protected_work()` is true whenever `holding_capture()` is. The new form also skips `contesting`/`bankable_bag`/`wants_shop` when we aren't holding.
- **Hoisted out of loops:** `stations()` out of `heal_station`, `heal_range` out of `heal_lands_from`, and `my_can_move()` out of the formation loop.
- `healed_before || heal_ally(world)`: once a cast is spent, the second `heal_ally` can't succeed.
- `stationary_support_output` reads the heal's cooldown through `slot_of(AbilityKind::heal)` instead of a hard-coded slot 0. This is the same value for Willow.

## Considered, not changed

- **Removing `(g == work && awake)` from `attack_support_camp`.** On a tile `exposure_at` calls safe, no live monster reaches us. Every monster's reach (3 or more) is at least a ranged attack range, so the clause only fires when a member's belief reads health <= 0 while it is alive. I left it in: it is harmless and guards stale beliefs.
- **The Prism-side `support_exposure` calls (`exposure_at`, enemies=true).** They could pass `credible_enemy_may_hit_within(p, 0)` as Willow's stations do, which would skip `bound()`. That is only equivalent if a blow that doesn't hit has damage 0, and I didn't verify that. The saving is small.
- **Renaming `prism`/`willow` in `local_support` to role names.** The protected mate can be Tavi. I left the names because bot.cc uses the same ones; the new header comment says so.
- **Unifying `exposure_here`'s memo with `stations()`.** The 1-tile memo exists so we don't cast 9 tiles after Willow's walk. Keep it.

## Suggestions

1. **Prism's formation window points the wrong way at bushes.** support.cc:429, `formation_view = attack_viewers(world, mate->pos, ...)`. Severity medium on bush maps; effort small to medium. Needs a probe first.
   - `attack_viewers(t)` returns the tiles from which *we* would see `t`. For a recovery, the question is whether *Willow* at `mate->pos` sees Prism. Sight is symmetric except at bushes ("a bush tile cannot be seen from outside"), and there it fails both ways:
     - Willow is off a bush and Prism is on an adjacent bush tile. That tile is in `near` (`sight(t, false)` is the full 3x3 for a non-bush `t`), so Prism counts it as in view, but Willow can't see it. Prism can spend up to `support_turns` turns waiting for a heal that can't come.
     - Willow is in a bush. `attack_viewers` gives only her cluster's near tiles, so Prism gives up a recovery that Willow, who sees out, could heal.
   - Willow's own ward (`sdk_wards` lists owners) isn't counted either.
   - Fix: for the Prism side, test candidates against Willow's sight. When `mate->pos` is off bushes, one host call does it: `map.walls_and_bushes.shadow_cast(mate->pos, range)`, tested per candidate tile. In a bush, use `StaticMap::viewers`-style cluster casting, or that same cast as a conservative subset.
   - Caveat: the rules YAML doesn't say whether an ally-target ability needs the ally in vision. The code assumes it does (`heal_viewers`, `heal_ally` reads only live visible allies). A probe should confirm before anything relies on it.
2. **`immediate_camp_finish` and `forgone` count camps Willow won't hit.** support.cc:276 and :311. Severity low; effort small.
   - Both count any visible member, or any live camp tile, in attack range. That includes asleep monster groups and awake non-work groups, which the stationary attack (`attack_support_camp`) never targets.
   - An asleep, damaged wolf in range (camps never regenerate) therefore blocks the independent heal step, or raises its bar, for nothing.
   - Restrict both to `strength <= 0` groups, plus the work group when awake, matching the attack predicate.
3. **`formation_turns` survives a lost mate.** support.cc:399. Severity low; effort trivial, but it is a design call.
   - When the mate goes out of sight, only `formation_start` is reset. `formation_turns` carries over, so a later formation can expire early. That contradicts "in a row" in the `support_turns` comment.
   - Either reset both, or reword the comment if accumulating is meant.
4. **`SupportExposure::damage` is written but never read** (bot_parts.h:49, set at support.cc:32). Remove the field, or use it. Trivial.
5. **Exposure is all-or-nothing for camps.** support.cc:36-41. Modelling gap; severity low or unclear; effort medium.
   - Any live monster in reach makes a tile unsafe, even asleep ones or ones that a nearer ally draws (camp attacks hit the nearest champion).
   - That is deliberately conservative for Willow ("holds no fight"). But near a camp the team is farming, every tile in reach is ruled out, so Willow may hang back further than heal range allows.
   - An exact version would use `Safety::camp_area()` (nearest-champion aware), plus a margin for the ally leaving.
6. **`heal_station` and the formation loop skip cleared camp tiles for Willow only** (support.cc:232, :475). Prism may step onto one, which turns into `holding_capture` and so ends the support next turn. If the skip exists to avoid accidental captures or respawn blocks, it probably applies to Prism's recovery steps too. Check the intent. Low.
7. **`local_support` is ~200 lines for two roles.** Most branches are `if (prism)` / `if (willow)`. Splitting it into `prism_recovery` and `willow_formation`, sharing the candidate loop as a helper, would make it much easier to read. Medium effort; it must stay byte-identical, so bench with `map_model_draft = false` as above. The current test drafts never pair Prism with Willow.
8. **Bench coverage.** The audit bench (`--test-draft` on 00ambush, 00lanes, 01hooks, 00interlock) never exercises the Prism-Willow pair. The model drafts on those maps don't pair them either. Any future change to this file needs a `map_model_draft = false` copy, or a test composition with both.
