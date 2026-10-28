# Audit: economy/bank.cc (bank)

Line numbers are for `bots/astraeus/src/economy/bank.cc` after the cleanup commit.

## Changed

All in one commit, `astraeus audit (bank): cleanup`. The bench replays are byte-identical (8/8). Total fuel went from 2,211,802,776 to 2,211,690,541 (-0.01%); 3924 turns got cheaper and 409 dearer.

- New `lock_turns(const AltarBelief&)` helper: the turns to break a believed enemy lock, one per hit left. It replaces the same nested ternary in `hop_route` and `bank_gems`.
- `bank_gems`:
  - `any_locked` meant two things: first "some altar is locked or avoided", later "a best altar was chosen". The later uses are now `best >= 0`.
  - The lock-hit test appeared twice (in the pack-zone branch and in the walk branch). It is now one lambda, `lock_hit_ends_turn`.
- `rebuild_altar_access`: the local `walked` shadowed `w.walked`, which means something different. It is renamed `updated` ("`ours` brought up to date without a flood from spawn"). The two overlapping comments about how much the static walk costs are merged and reworded.
- `place_lock`:
  - Added a comment on the pass-1 condition: with no tribute to cancel, it locks only altars on our side.
  - Renamed the lambda `known` to `note_own_lock`.
- `submit_here`: reads the bag once for the `income.tribute_cut` accounting.
- `carry_bag`: uses `my_position()` instead of `cambc::self().position()`, which is the same value through the cached record helper.
- Removed a ladder statistic from `may_chain`'s comment (transient) and the meaningless `// Ours.` header.

## Considered, not changed

- **`own_lock_round[a] >= 0` in `place_lock` (l.33) looks redundant, but it isn't.** `AltarBelief::seen_round` defaults to -1, and without the check an altar never seen would be skipped as "ours".
- **`tribute_ok`'s `turns <= rounds_left` (l.446) looked off by one.** It is exact: a channel of b turn ends started in round r completes at the turn start of round r+b (`rounds.turn_start`), and that must be no later than 2000.
- **`dilate_into` (l.149) duplicates `square_dilate(b, 1, out)` in `model/world.cc:301`.** That function has no declaration in a header, and world.cc comes after bank.cc in `unity.cpp`. Sharing it needs a declaration in `bot_parts.h` or `world.h`, which are other auditors' files. Merging them is a cross-file follow-up and costs a little fuel (a loop instead of unrolled shifts).
- **`altar_here` (l.625) and `tribute_altar` (l.637) are near-duplicates.** One skips enemy-locked altars and the other doesn't. Both are short and clear, so I left them.
- **`take_hop` copies `pathing.teleport_targets()` (l.516).** The API returns the board by value, so a static board here would save nothing.
- **The rebuild logic in `rebuild_altar_access` checks out:**
  - The incremental death update floods from each dead tile beside `ours`. Dead tiles that touch only other dead tiles are reached through those floods, because they are no longer walls.
  - The respawn update tests whether the ring of `ours` tiles around the returning camps is connected. That is sufficient: a path through the returned tiles can be rerouted along the ring.

## Suggestions

1. **`closing` ignores crystal routes (l.420-428). Gap; low severity, small effort.** With no walk from here or from the recall landing (an altar only a crystal reaches), `walk` becomes 0. The bag then reads as "closing" only `walk + recall + crystal` rounds too late. `hop_route(...).steps` (which already includes the recall out) is the exact figure when we carry or can buy a crystal. It would need `hop_route` moved above `closing`.

2. **`bankable_bag`'s pocket test reads the field at `ally_spawn_centre` (l.371). Gap; trivial.** `closing` reads it at `recall_landing(world)`, which is where a recall actually lands. The two should agree, and the landing tile is the exact one.

3. **`tribute_safe` ignores shields (l.94). Gap; Varg and Heart of Ruin only; small.** It compares `memory.damage * window` against `my_health()`. A live shield (Varg's 2.5x Focus, Heart of Ruin's 1.5x) absorbs damage first. Adding the shield value would let them bank in windows they now skip.
   - `turns_to_kill_idle` may already count the shield through `fighter`; I didn't verify that.
   - `Safety::lethal` adds `shield_value(...)` to health the same way, so this is consistent with existing code.

4. **`access_fire` sums every awake member in reach of the tile (l.349). Gap; low.** A monster attacks the nearest champion in its range (`camps.attack`). With an ally standing nearer to the monster, we take less. For a lone banker this is exact; for a crew at an altar it overestimates and can seal altars that are usable.

5. **`access_fire`'s cache is keyed on (round, access version) only (l.310-312). Low.** If our own attack wakes a camp later in the same turn, a later call that turn reads the stale fire. It is harmless today because the callers run before attacks, but it is fragile. Keying on the camps' `version` (`CampBelief::version`) as well would make it exact.

6. **`place_lock` treats each ally separately when testing for a win (l.49). Low.** `ours_wins` checks `score.ally + ally.gems` per ally. Two allies tributing together at one altar, whose combined bags win, still let us cancel them to stop a non-winning enemy tribute. The rule is "worth it only against a win", so summing the allies' bags at the altar is the exact version.

7. **`submit_here` calls `enemy_lock_live` per believed-locked altar in range (l.458). Fuel; small.** That calls `cambc::vision::altar_locks()`: two host calls and two vector allocations (~800 fuel) per call. The raw `sdk_altar_locks` into a static buffer, as `World::update_altars` does, would avoid the allocations. The path is rare.

8. **Recall landing ignores unseen allies (l.116-125). Low.** `recall_landing` skips only allies it can see. An ally on spawn just out of sight (spawns are small, so this is rare) or arriving the same round is not considered. The result only feeds `closing`'s walk estimate, so the impact is at most a step.

9. **Cross-file: `square_dilate` is duplicated by `dilate_into`. Trivial.** Declaring `square_dilate` in a header would let bank.cc drop `dilate_into`. A one-radius special case keeps the unrolled cost.

No fuel gates live in bank.cc. The only fuel-conditioned work related to it is `bot.cc:373`, which warms `flood_altar_walk` when `fuel_ok`. That one is a warm-up, not a worse choice, so it is fine.
