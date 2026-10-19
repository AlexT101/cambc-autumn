# hecate: remaining work

The open items from the 2026-10-18 review of `bots/hecate/src`, in the order to do them. What's done is in git history (f01312a..ed3b2ac), [CHANGES.md](CHANGES.md) item 14 and [EXPERIMENTS.md](../EXPERIMENTS.md). Numbers like 2.8 are the original review's; they match EXPERIMENTS.md.

## How to test
- **No play change** (refactors, fuel savings):
  1. `py tools/fuel/bench.py run <copy> --out a.json`, before and after the change.
  2. `bench.py compare a.json b.json` must show 16/16 identical replays.
- **Fuel gates:** `bench.py run <copy> --fuel 0` counts `SHORTCUT` tags and out-of-fuel turns at the real budget. A removal must not add out-of-fuel turns.
- **Play changes:** copy the bot to `bots/variants/` and run `py run_batched.py variants/<new> variants/<base> --threads 22`, three times: plain, `--gen` and `--central`. That's 390 games; noise is ±2.5 points.
  - Bundle fixes that are clearly correct; test judgement calls alone.
  - Keep a fix that raises the win rate, and a removal that comes out level.
- **Unclear result:** `node tools/replay/extract.mjs replays/<batch>...`, then `py tools/replay/ab_compare.py <variant name> <batch>...`. It compares the two bots within the same games: captures, gems, camp damage, deaths, and time from clear to hold.
- **Bench every helper for fuel.** A shared `Safety::considered()` filter cost 72–102 fuel a turn in WASM even when inlined.
- **Fuel savings stay** (caches, memos, precomputation, work done with spare fuel). Only fuel *gates*, which make a worse choice when fuel is short, are candidates for removal.

## Work list

1. **Rare fuel gates (3.1), half done.** Removing all five gates below was level (49.5%), but out-of-fuel turns in `bench.py --fuel 0` rose from 8 to 40 (EXPERIMENTS.md). Removing `step_guard`'s gate is the main cause: restoring it brings the count to 18. So:
   - **keep** `step_guard`'s gate and `Safety::known_fight`;
   - **re-test the other four as one bundle:** `want_home`'s fight-sim gate, chase's crow-flies fallback, `walk_on`'s kept target and `failed_search_pause`. They gave 14–18 out-of-fuel turns against 8, which may be trajectory noise.
     - To tell, bench both bots against a second opponent (`bench.py run ... --fuel 0 --opp nemesis`).
     - Then A/B them as one bundle.

   The code is in `bots/variants/fix-31-sg` (gitignored; rebuild it from the list if it's gone).
   **Keep** `step_towards_funded` (an uncapped route can run out of fuel, which loses the end-of-turn recall, ward and comms) and the fight sim's `fuel_floor` cut.
2. **Fight-sim fixes, one bundle:**
   - 2.8: in `simulate()`, our side isn't checked after our own turn, so a death from Ren's reflect is missed.
   - 2.11: `act()` ignores `arrives_at`, so our stun can hit an enemy that hasn't arrived.
3. **Small removals, one bundle** (keep if level):
   - 4.4: `killable_now`, plus `want_home`'s kill plumbing and `Safety::fight`'s `exclude`. Item 8 was level.
   - 4.6: `keep_walk`'s free-stun logic in `enemy_cast`, replaced by a plain threshold.
   - 4.7: ground casts at unseen enemies (`max_unseen_tiles`).
   - 4.9: the rally bit (`post_rally`, `sight_fight`). No receiver uses it.
   - 4.10: big-group sieges on normal maps (`big_rounds`, `big_respawn_wait`). They lost 39.6%.
4. **Judgement-call fixes, one at a time:**
   - 2.7: when fuel is short and we're unsafe, kite steps towards the group's centre, deeper into reach. Step out of reach instead.
   - 2.9: `emblem_gain_rounds` keeps its +0.15 Jungle term on shared-gem maps, where we never buy Jungle, and prices the Durability step as main-stat growth.
   - 2.10: `siege_candidate()` lets an unready Monolith hide a ready 150+ gem group on normal maps. Skip alive Monoliths unless `map.monolith_only`.
   - 2.11: kite and `contest_capture` disagree on contest timing. Unify them on `enemy_hold_left`, with `contest_capture`'s rule.
5. **The most frequent shortcuts** (`--fuel 0`, 16 games):
   - 3.3: `comms-stale-vision` fired 995 times. `observe()` is skipped when short of fuel or when a teammate posted. Call it from main whenever we moved and are alive.
   - `farm-no-evaluation` fired 255 times. Use cheap steps (`ally_steps`/`dist`) for groups whose field is unaffordable, then delete the mini-farm. Check big maps.
   - `turn-order-sim` and `turn-order` fired 293 and 60 times. Merge into one gate.
6. **Features:**
   - **Home emblem** (recall 5 → 3 turns) as the 2nd or 3rd emblem. Set our own `fast_recall`; only `wants_shop` and farm's heal-trip cost use the fixed recall time.
   - **Walk to lock an altar where a visible enemy is tributing a big bag**, with `Altar::lock_tiles()` as the goals.
   - **`Safety::expected_damage` as a tie-break** in `retreat_step` and `flee_camps`.
7. **Other behaviour changes (3.x), each A/B tested:**
   - 3.2: in `note_sighting`, a teammate's sighting adds the whole enemy spawn, so the enemy stops counting as a threat after about 3 turns.
   - 3.4:
     - Pack-zone ratio `(home || hurt) ? 2.0 : none`.
     - Drop kite's contested branch.
     - Give kite's stations line of sight, as `spell_clear` has.
     - One `run_home()` for `retreat()` and `carry_bag`'s retreat.
     - `recall_outruns` should use `safety.strike_of`.
     - `shield_if_needed` should get `memory.claim`.
   - 3.5:
     - The crew value leaves out `capture_rounds()`.
     - Hits after a walk use `affordable`, not `passing`.
     - Test the spell-clear pricing (`spell_clear_rounds`) both ways.
   - 3.6: `turns_to_kill_idle` should add enemies with `join()`, as `pursuit` does.
   - 4.3: remove the delayed tribute stun (`tribute_to_stun_later`, the D branch, the `hold` parameter). Keep `can_stop_winning_tribute`.
   - 4.8: remove probabilistic `threatened()`. Risky: it gates recalls.
   - 4.11 (Ren's specials): change only on ladder evidence.
8. **Optional refactors, no play change:**
   - One `approach_range(world, g)` for its three copies (`farm_evaluation_reserve`, `walk_range`, `prepare_walk`).
   - Share "gems left per alive ally" between `gold_worth` and `emblem_gain_rounds` as ints, since a float ratio rounds differently.
   - Test `first.is_set(here)` once in kite.
   - Make `enemy_spawn_tiles` a local in `StaticMap::build`.
   - Don't extract `recall_saving`: `remaining_channel_time()` is unsigned.

## Open question
The fuel-only savings cost about 2.5 points over 1,492 games (47.4–47.5% against the same bot without them), although play is identical when fuel is plentiful. So something that runs only when fuel is left over is net harmful. The v17 port was the prime suspect and is gone. Re-test once the gates in items 1 and 5 are settled.

## Don't remove
These have evidence behind them:
- `step_guard`, `pursuit`, `threat_strike`.
- Monolith sieges.
- kite on shared-gem maps.
- `contest_capture`, `camp_trapped`, `finishing_camp`.
- `start_recall`'s pre-start.
- Bush and scouting wards.
- `step_towards_funded`.
- `pick_up` and `spell_clear`.
- The fuel savings: DraftPlan, lineage sharing, `prepare_walk`, the centre warm-up, the memos and caches, static scratch boards.
