# Audit: `bots/astraeus/src/model/crew_work.h`

`earliest_work_delay` gives the first turn on which a claimed-camp crew member can damage the group, so it also counts the turns of work it misses. Its only caller is `work_arrival` in `economy/farm.cc:538-578`, which feeds `crew_work`'s `delayed_damage`, our share of a group shared with allies.

## Changed (commit a4708fce, byte-identical, fuel +0)

- Rewrote the header comment. It now says what the value is (a turn index from the anchor, which also counts the turns of work missed) and what each parameter means; the old comment gave only "optimistic movement envelope".
- Folded `if (kill_resets) dash_ready = 0;` into the `first_dash` max. Added a short comment on the cycle arithmetic, which is the one part that is hard to read.
- Added `static_assert`s that fix the semantics: no dash; arriving by walking before the dash is ready; arriving on the first dash; the second cycle, both before and on its dash turn; and `kill_resets`. I checked each one by hand by counting tiles closed per turn.
- I tried merging the "arrives walking before the dash" branch into `left <= 0` as `std::min(walked, first_dash)`. It is mathematically the same and replays stayed identical, but it cost +4 fuel/turn on the mean (+0.01% total), so I reverted it to the branch.
- Bench (4 maps, `--test-draft`): 8/8 identical replays, total fuel 2211802776 -> 2211802776.

## Considered, not changed

- **The optimistic direction.** An underestimated delay over-credits allies' work and so understates our share. That is a valuation choice, not a bug, and the comment states the bias.
- **`gap <= 0` returns 0 even when `first_turn == 1`.** This is right: the ally is already in reach, so it misses no work this round.
- **Dashing as early as possible.** This is optimal (earliest dashes maximise tiles closed by every turn), so the greedy cycle formula is exact for the model it states.

## Suggestions

1. **Exclusive spells cannot follow a walk, but the caller's reach assumes they can** (`farm.cc:548-551` together with this function). Severity: low; effort: small, in farm.cc.
   - The caller sets `reach` to the max of basic reach and every damage ability's `reach()`, e.g. 5 for Ryth/Prism/Stellar ground spells, 4 for unit spells. Every damage spell is `excludes_walking`, and a dash uses the turn's one cast. So a spell-reached arrival really happens on turn `earliest_work_delay(gap_spell) + 1`, not on the turn the last tile is closed.
   - The result is one turn optimistic whenever the spell, not the basic attack, sets the reach.
   - Exact fix: `min(f(d - basic_reach), f(d - spell_reach) + 1)`, with the `+1` only when `gap_spell > 0`. That is two calls instead of one.
2. **Ranged basic attacks cannot follow a walk** (rules `turn.ranged`). Severity: low; effort: small to medium.
   - Prism, Stellar and Cassi have no attack reset, so their walk-then-attack arrival is really `f(gap) + 1`.
   - Vesper, Tavi and Willow can walk, reset, then attack, but the reset is a cast, so it conflicts with a dash that turn. A ranged dasher (Vesper) can still dash without walking and then attack, closing `dash_steps` that turn rather than `1 + dash_steps`.
   - An exact model needs a "may damage after walking" flag per arrival option. The header's "no cast conflicts" caveat covers this today; it is the same one-turn over-credit as item 1.
3. **`kill_resets` is really "cooldowns unknown"** (`farm.cc:567` passes `cooldowns_uncertain()`, which is true only for an unseen Vendetta). The name and comment fit Vendetta, the only case today. If other champions' unseen cooldowns ever become uncertain, consider renaming it to `dash_maybe_ready`. Cosmetic.
4. **Code duplicated across bots.** The function is copied verbatim into hyperion, hermes, river, river_ac and the baselines. This needs no action for astraeus; it is noted only so that a fix to item 1 or 2 is not expected to propagate.
