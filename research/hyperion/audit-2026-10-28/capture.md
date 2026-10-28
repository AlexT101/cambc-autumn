# Audit: economy/capture.cc (capture)

File: `bots/astraeus/src/economy/capture.cc`. Line numbers below are as of the fixes commit.

## Changed

### Cleanup (commit 1, `astraeus audit (capture): cleanup`)
Byte-identical: the bench (00ambush, 00lanes, 01hooks, 00interlock, test drafts) gave 8/8 identical replays. Total fuel -0.05% (2,211,802,776 -> 2,210,692,448; 6269 turns cheaper, 2294 dearer).

- **Shares:** `split_share` + `capture_share(world, int g)` + `gold_share(world, G)` became one `our_share(world, G, amount, cluster)`, with `gem_share` / `gold_share` wrappers that take the same kind of argument. `allies_on` used to be called again for the Prospector sharer count; now it is called once. Removed the duplicated two-comment header.
- **`prism_capture_holder`:** added a doc comment. It had none, and its name hides that it also picks Marcella (Stellar maps) and a Prospector Tavi (gold groups). Removed the dead `enemy_on` (it returns false whenever `enemy_seen` is false, which had just been checked) and folded the `!three && gems <= 0` early-out into `prospector_gold_holder`'s own `economy_three` check. Pulled out `enemy_may_see` (the enemy-pressure loop was copied twice, without short-circuiting) and `fit_on` (alive, visible, healthy, on the tiles). The Marcella loop now runs the pressure loop only for Marcella, not for every ally.
- **`prospector_gold_holder`:** the solo and split gold sums are now one `held_gold(a, owned, gold, n, lowest)`. For n = 1 it is the same integer and float arithmetic, so the result is unchanged. Removed the dead `if (count <= 1)`: Tavi is a visible non-self ally on the tiles, so `count >= 2`. Added `position_of(a)` for the repeated `a.is_self ? my_position() : a.pos`.
- **`yield_capture` / `join_marcella_capture`:** the "throw_if_stale; try_move; write memory; throw_if_stale" sequence they shared is now `walk_then(world, pathing, p, on_moved)`.
- **`holding_capture`:** fixed the comment, which said "no lower-id ally also holds"; the real test is fewer than `holders(G)` lower-id allies. Uses a local `G`.
- **`capture_recall`:** removed the redundant `c.state != CampState::cleared`. Its only caller (bank.cc:736) calls it right after `holding_capture`, which requires a cleared group. Added a comment on the Prism-only ride-home branch.
- **Comments:** removed the "v61" experiment tags. Rewrote `ally_engaged`'s comment, which only described its fuel shortcut, to say what the function returns. Clarified `capture_rounds(world)` and `gold_share` (before bonuses). Added a comment on `join_marcella_capture`'s `<= 1` timer test. `capture_taken` computes the distance once and skips allies already on the tiles first.

### Fix (commit 2, `astraeus audit (capture): fixes`)
- **New `enemy_hold_pays` (capture.cc:166), used by `contesting` and `contest_capture`.**
  - **contest_capture:** it never checked `pays_too_late`, so it could walk to contest an enemy hold that pays after round 2000.
  - **contesting:** it kept a body on a contested or unheld group in the final rounds. In those rounds even a hold begun now (at the soonest R+4, with a Capture emblem) cannot pay.
  - **Why the bound is safe:** it is conservative. It stops only when nothing can pay, never because the gems could not be tributed in time. Gold paid by such a hold is a tiebreak, and none is paid either.
  - **Effect on the bench:** the bench games end before round 1997, so the replays stayed identical (8/8). Fuel -0.05% against the base, about the same as the cleanup.

## Considered, not changed

- **`hold_capture`'s `free_hit` (capture.cc:487):** it uses `c.awake != Awake::asleep && c.asleep == 0`, which counts `Awake::unknown` as already awake. `CampBelief::fully_awake()`, used for the same "a hit wakes nobody" test in farm.cc:306, needs `awake == Awake::awake`. The group's state can be `unknown` while the member we hit is visible: world.cc:2209 sets it when the group is partly in view and a health drop was seen. Switching to `fully_awake()` would be the conservative reading, but it changes whether we wake a group while holding, which is a judgement call. Reported below.
- **`take_capture_handoff`'s `dash < 0` guard:** after `has_dash()` it is likely dead. Left as a cheap defensive check.
- **Renaming `prism_capture_holder` to something like `sole_capture_holder`:** it is used in farm.cc and siege.cc, so the rename is cross-file. Suggested below.
- **Memoising `holding_capture`:** a fuel idea, but it is not cleanup-safe without knowing every mid-turn world update. Suggested below.

## Suggestions

1. **`holding_capture` is evaluated many times per turn** (capture.cc:173). Callers: bot.cc:277, fight.cc:112/177/186, support.cc:238/334/376, bank.cc:736, farm.cc:327/433, plus `join_marcella_capture` and `take_capture_handoff`. Each call re-runs `prism_capture_holder`: allies × enemies loops and, on 3-pick gold groups, up to about 6 `sdk_champion_items` host calls. A per-turn memo keyed on (round, my position, a world observe counter) would make the later calls nearly free. Severity: fuel, medium. Effort: small, if world exposes a version or observe counter.
2. **Prospector rounding disagrees between two places.** `prospected(cluster, n)` (capture.cc:28, used by `our_share`, farm.cc and shop.cc) takes 25% of the floor share only. `held_gold` (capture.cc:82, the Tavi decision) takes 25% of the share including the remainder. The rule ("25% of its share of the cluster members' rewards") does not settle whether the lowest id's remainder counts. A probe should settle it, then one formula should be used. Severity: low (a gem or gold or two). Effort: probe plus a one-line change.
3. **Gold-only groups are never contested.** `contesting` (capture.cc:356) and `contest_capture` (capture.cc:464) both require `gems != 0`. An enemy on a gold-cluster group, or an enemy Tavi with a Prospector emblem, captures it freely, even when we are standing next to it. Gold is the first tiebreak and buys shards. Whether to deny it is a judgement call, but a cheap contest of a group already in reach could be worth A/B testing. Severity: low to medium on Tavi-gold maps. Effort: small, then an A/B.
4. **`enemy_hold_left` ignores an enemy's Capture emblem** (capture.cc:406). When the hold's count is not read, it falls back to `capture_rounds(false)` = 6. The world already stores `fast_capture` for enemies (world.cc:1716). When a visible enemy on the tiles has it, the bound should be 4, and the joining rule `min(R+6, J+3)` should apply. Usually the timer is read and this is exact, so the fallback matters only for unread holds. siege.cc:430 shares it. Severity: low. Effort: small.
5. **`free_hit` treats an `unknown` group as awake** (capture.cc:487). See above. This is a modelling gap: a holder can wake a possibly sleeping group, whose fire then contests our hold through damage or a retreat. Consider `c.fully_awake()` for consistency with farm.cc:306. Severity: low. Effort: one line plus an A/B.
6. **The time-left tests use map size as a stand-in for the walk to an altar.** `prism_capture_holder` (capture.cc:138, 152), `join_marcella_capture` and `take_capture_handoff` (capture.cc:304) use `width + height + endgame_margin`. `pathing.to_any_altar().at(p)` is already cached and is exact for our own position. The Marcella branch (138) also leaves out the tribute turns that the Prism branch (152) adds. Severity: low (only in the last ~150 rounds on big maps). Effort: small.
7. **Rename `prism_capture_holder` to `sole_capture_holder`** (cross-file: farm.cc, siege.cc, bot_parts.h). It returns Prism, Marcella or Tavi. Effort: trivial.
8. **`holders(G)` ignores the Tribute emblem** (capture.cc:48, `tribute_turns(..., false)`). A team whose holders own Tribute emblems could split big groups fewer ways. This is a heuristic choice and probably deliberate, so it is a note only.
9. **The fix's bound could cover more.** `contesting` / `contest_capture` still contest gem holds whose gems the enemy cannot bank before round 2000: they pay late, or far from an altar. Only the gold tiebreak is at stake then. Severity: endgame only, low. Effort: medium, because it needs the enemy holder's walk to an altar.
