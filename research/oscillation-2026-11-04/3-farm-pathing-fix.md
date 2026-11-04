# Stream 3 (farm pricing and pathing accuracy): fix notes

Branch `osc/3-farm-pathing` (worktree `/home/ubuntu/wt/osc-3-farm-pathing`), from 088bf3f4. Line numbers are
`bots/astraeus/src` at 088bf3f4.

## Plan

The stream's pathologies share one cause: farm chooses and prices a group with one model of the walk and then
walks with another. Pricing reads static steps (centre fields, static walls); the walk routes around live camps and
units under a cap of static + 16. When they disagree, the walk fails, nothing reaches pricing, and the same target is
chosen again next turn. The fix makes the walk's own live-camp search the record pricing reads.

1. **Live-walk records (B 3, ≈40-90k turns).** `Pathing::search_approach` (the approach field: from a group's
   attack tiles, around static walls and live camps, searched out to our tile) already is "the route the walk will
   take" over terrain and camps. Today a failed search is thrown away (so it is repeated every turn: `act()` and
   `prepare_next_turn` search the farm choice's approach each turn, uncached when it fails) and its cap is static +
   16, so a long detour reads as no way at all.
   - Keep every search as a record: its labels, the layers it ran and whether it ran dry. A tile it labels has its
     exact live walk; an unlabelled tile is at least that many layers away (labels are complete below the last
     layer), and unreachable if the search ran dry (the goals' region holds no other tile). That is position
     independent, so it holds as we walk away. Validity is the existing `same_labels` test (camp changes off the
     labels and away from the group's goals change no label, and so no lower bound either).
   - The search's cap becomes static + `wide_detour` (6 x 16, the wider search `step_field` already uses), so a
     detour is told apart from a seal.
   - A record that already answers for our tile (labelled; or unlabelled with the search dry or past the cap a new
     search would use) is not searched again: `approach()` / `prepare_approach()` return null without the search.
   - `Pathing::live_steps(group, range)`: the record's answer (exact, a lower bound, unreachable, or -1 for none).
   - Farm pricing: a walked group's steps are max(static steps, live_steps); a sealed group is skipped. The walk's
     cap (best_steps + 16) then covers the live route, so the walk and the price agree.
   - Farm's failed walk falls back to `walk_on` for every champion, not only dashers (`!walked && dasher`, farm.cc
     1915, 1978): its approach search makes the record, and it descends the live field when there is one.
     `walk_on` no longer descends the static centre field when the live search found no way (it only walked into
     the seal); short of fuel it still does.
   - Callers affected: every `approach()` user (farm `walk_on`, `act()`, `prepare_next_turn`, siege far walk,
     support work route, plan `goal_field`): they get fields past the old cap and no repeated failed searches.
   - Fuel: a sealed group costs one search to its cap (≤ a full flood), then nothing until camps change near it;
     pricing reads one slot per walked group.
2. **Groups priced one turn and skipped the next (C 1).** A cleared group the enemy holds (`CampBelief::holder ==
   enemy`) pays them at `payout_round()` and then respawns: farm priced it as free gems with no clear, and skipped
   it the turn after (respawning, `max_wait`). Skip it as `ally_holding` groups are; a contest is
   `contest_capture`'s (branch X), which runs before farm.
3. **Pending tribute (B 6, real part).** `gems_short` takes an ally's tribute channel as landed. A channel far from
   its end (b = 136 turns in the adgato example, cancelled again and again) priced every group at 0 for hundreds of
   rounds. Count a channel only within `tribute_window` turns of its end; before that its gems may not land.
4. **Allies in a neck (B 4).** `step_towards_funded` (siege, kite, fight) gets `step_route`'s `make_way` on a
   failed route. Siege's repeat of a failed engaged walk is stream 4's (siege.cc): noted below.
5. **Respawn held back by our own champions (B 5).** Farm leaves a due respawning group's camp tile (round start
   would find us on it) instead of staying there to attack or wait, not only when it prices nothing.

Not planned here: guard-vs-goal walls (C 4) and guard/want_home semantics (stream 2), travel_dash (stream 1),
siege/kite (stream 4).

## What changed

Final commit **25e10cc** on `osc/3-farm-pathing` (five commits over 088bf3f4; bot copy `bots/variants/osc3-25e10cc`).
The plan above held except where the A/Bs said otherwise (see "Iterations").

- **Approach records** (`model/pathing.{h,cc}`). `search_approach` keeps every search in its slot, failures
  included, with `layers` and `dry`. The cap is unchanged: static steps + `max_detour`, the farm walk's own cap.
  `labels_hold` is the old validity test, cached per slot at the `live_flips` it failed at. `approach_known` means a
  new search would tell nothing new; `approach()`, `prepare_approach()` and `approach_cost()` skip such a search.
  `live_steps(group, range)` reads the record:
  - the exact steps, if it labelled us;
  - a lower bound (the layers it ran);
  - `unreachable` if it ran dry, or if a search from here would run no farther than it did;
  - -1 if there is no record.

  The fuel estimates for an approach search now price the layers it really runs (`static_field_cost_estimate(steps
  + max_detour)`), not the static steps.
- **Farm prices the walk** (`economy/farm.cc`).
  - A walked group's steps are max(static, live). A group no walk within the walk's cap reaches is skipped, so price
    and walk now agree on what is reachable.
  - `walk_on` no longer descends the static centre field when the live search found no way: that only walked into
    the seal. Short of fuel it still does.
  - Every champion's failed walk falls back to `walk_on`, not only dashers'. This is the cleared-best walk and the
    final walk, and it no longer runs twice in the unfunded branch.
  - `recall_farm` is kept for picks priced by live steps (it was lost whenever the record raised them).
- **Enemy holds** (C 1). Farm skips a cleared group the enemy holds, as it skips an ally-held one.
- **Long ally tributes** (B 6). Farm prices with `gems_short(world, tribute_window)`: a capture is worth something
  only in the worlds where the allies' long tributes get cancelled. Bank (`winning_bag`), capture and camps keep the
  full count.
  - A first version changed `gems_short` itself. Bank then chained farm beside a 1,124-gem ally tribute, which the
    auditor also flagged in `race_left` and `win_lands`.
- **Funded walks make way** (B 4). `step_towards_funded` calls `make_way` after a failed route, as `step_route` does.
- **Due respawns** (B 5).
  - Farm leaves the camp tile of a group due to respawn at the next round start, and a ranged champion does not fire
    from one.
  - A waiter next to an ally boxed in on such a tile (no free exit but our tile) steps aside (`step_aside`).

### Iterations (A/B on `maps/osc-fix-10k`, 10,240 games each vs astraeus-088bf3f, both on their own drafts)

| version | win % (95% CI) | OOF turns CAND / REF |
|---|---|---|
| 2cce5b3: records with a wide cap (static + 96), three repricing passes | 49.0 (48.0-49.9) | 96,792 / 59,217 |
| fe0f856: auditor fixes; in-loop probes of each leader replace the passes | 48.7 (47.8-49.7) | 73,523 / 57,245 |
| fe0f856 with no live pricing or probes (noA) | 49.2 | 57,540 / 57,557 |
| fe0f856 with no probes (noP) | 49.5 (48.5-50.4) | 58,512 / 58,029 |
| noP, cap back to static + 16 (noW) | 50.5 (49.5-51.5) | 61,660 / 57,319 |
| noP, static centre descent restored in walk_on (noS) | 49.5 | 58,548 / 58,076 |
| noP, cleared-best walk_on only for dashers (noK) | 49.4 | 58,684 / 58,317 |
| fe0f856 without the enemy-hold skip / farm-only window / funded make_way / due-respawn leave | 48.5 / 48.8 / 48.7 / 48.4 | ~73k / ~57k |
| fe0f856 with the final walk_on fallback only for dashers (noF) | 47.5 (46.5-48.5) | 73,532 / 56,731 |
| **25e10cc (= noW, dead code removed)** | **50.5 (49.5-51.4)** | **59,957 / 57,685** |

- Searching the pick's walk while pricing costs fuel: about 15k more OOF turns, plus about 0.8 points from the
  changed picks. Whether done as repricing passes or as in-loop probes, it lost.
- Without it, pricing reads only the records the walk, `act()` and `prepare_next_turn` make anyway. A group found
  closed is dropped the turn after its walk first searches it: 03fan cycles a few turns through its sealed groups,
  then stops, because the records persist.
- The wide cap (a detour up to 96 priced and walked) lost about 1 point against treating "no way within the walk's
  cap" as closed. Long live detours go round camps that change: walking them loses to farming elsewhere.

## Auditor

A read-only subagent reviewed 2f1256d..2cce5b3. Findings and responses:

1. **A lower-bound record could stall the walk forever** (priced at `layers`, never searched again, and the route
   fails at its cap). Fixed: when no search from here would run past the record, `live_steps` says `unreachable`.
2. **A live-sealed group skips the hop and recall pricing.** Not changed. A live seal is around the group or around
   us; hops serve statically separate regions, and a recall-out from a live seal is rare. Left open.
3. **`recall_farm` was lost when live steps raised the price.** Fixed.
4. **A repricing pass could end worse than the first under `room()`** (a fuel gate). Moot: the passes are gone.
5. **verify's searches are fuel-gated; it verified four candidates.** Moot: the passes and probes are gone.
6. **The widened cap wasn't in the cost estimates.** Fixed: the estimate is at the real cap, and the cap is back to
   static + 16.
7. **`labels_hold` had no cache.** Fixed: a failure is cached per slot and flip count.
8. **walk_on ran twice in the unfunded branch,** and the fallback for walkers costs a step_field search. Fixed the
   double call. The fallback stays: removing it cost 1.2 points (noF).
9. **`make_way` in `step_towards_funded` has a weak fuel check,** and the chase back-off is a behaviour change.
   Kept; the noD ablation was neutral (48.7 vs 48.7).

The auditor's remaining-disagreement notes are under Open issues.

## Episodes

Stalled turns: all walks failed and the champion did not move, our side, from the original phase-1 trace game to
a rerun with the final trace build. The games diverge after the change, so read these as before/after of the same
start.

| example | before | after | note |
|---|---|---|---|
| 072-00vault | 6,989 | 95 | won at r276 (was a 2000-round loss) |
| 328-gen-three-lane | 1,174 | 40 | |
| 301-gen-labyrinth | 1,306 | 376 | three champions on group 5's tiles blocked its respawn: fixed by the step-aside |
| 376-gen-topo-necks | 1,081 | 551 | |
| 139-03fan (h8 Prism) | 1,024 | 170 | |
| 170-adgato | 371 | 203 | won at r693 (was a loss) |
| 479-mut-corridors | 184 | 50 | |
| 100-gen-classic | 82 | 54 | |
| 240-gen-huge-shared | 147 | 147 | |
| 121-02stalactites | 47 | 106 | won at r512 (was a loss). One intermediate build had a banker standing 1,600 turns beside an enemy-held altar (bank/guard, not farm) |

## Detector

1,024 games (gen + fresh vs baselines/v69), `replays/osc/osc3-c` vs `replays/osc/before-v69`:

| kind | episodes | turns | change |
|---|---|---|---|
| retreatchurn | 7864 → 7747 | 442,919 → 428,136 | -3.3% |
| claimflip | 8811 → 9200 | 410,005 → 430,687 | +5.0% |
| goalflip | 11968 → 12069 | 251,809 → 253,719 | +0.8% |
| branchflip | 11277 → 11059 | 178,457 → 173,351 | -2.9% |
| stuck_idle | 2100 → 1844 | 79,162 → 64,740 | -18.2% (farm: 55.6k → 43.6k) |
| wander | 2050 → 2008 | 60,482 → 59,756 | -1.2% |
| stuck_fail | 3944 → 2731 | 58,375 → 40,573 | -30.5% (farm: 44.2k → 29.7k) |
| pingpong, jitter, preyflip | | | ±0.2% |

- This stream's kinds shrink: farm stuck_fail by a third, farm stuck_idle by a fifth.
- claimflip grows 5%. The growth is spread thinly over many signatures: 536 games up, 444 down. The largest, in
  mut-vault, is a Willow cycling X/F/R/h on a contested capture: contest/retreat, not farm pricing.
- An intermediate build (2cce5b3) showed bank-only goal flips up 3.1k turns. They come from bank's chain test: farm
  is chained on one tile and not the tile next to it (`may_chain`'s credible-enemy test, or `closing`), so a
  carrier steps back and forth. That is pre-existing, with 8.3k turns before. It is not counted in the final build's
  table above.

## A/B

- **`maps/osc-fix-10k`:** 25e10cc vs astraeus-088bf3f, 10,240 games, `--no-test-draft`: **50.5% (95% CI 49.5-51.4)**.
  - Out-of-fuel turns: CAND 59,957 in 6,493 games, REF 57,685 in 6,246 games (+3.9%).
- **Fresh confirmation suite** `maps/osc3-confirm` (mapgen seeds 3391-3410, 5,120 maps, used by no other A/B), 10,240
  games: **49.9% (49.0-50.9)**.
  - Out-of-fuel turns: CAND 64,262, REF 59,002 (+8.9%).
- Neutral on win rate. Out-of-fuel turns are +4-9%. They come with the records at the narrow cap: the same code with
  the wide cap was +0.9%, but lost a point.

## Open issues

- **OOF +4-9%** with the narrow-cap records. Unmeasured guess: a record that did not reach us goes stale as we move
  away (the needed cap grows by a step), so each failing search is redone. A fuel census of 25e10cc would settle it.
- **For stream 4 (siege.cc ~333/340):** an engaged siege repeats a failed funded walk every turn. It should hand the
  group back to farm after its walk fails, which now prices it from the record.
- **Bank's chain test flips by tile** (`may_chain` / `closing` vs the chained farm's walk; above). The chained farm's
  walk should keep to tiles where the chain test still holds.
- **The step-aside can still cycle** when the boxed-in ally is in another branch and never leaves.
- **A live-sealed group is not priced by recall-out or hop** (auditor 2).
- **Static steps go to the centre, live steps to attack tiles.** A detour shorter than the range plus the centre's
  offset never shows in the price; this errs conservative.
- **The other early returns don't apply the due-respawn leave:** `spell_clear`, `cast_at_camp_on_approach` and
  `!tiles`.
- **Not done:** C 7 (yield_capture's `value_holder` vs farm's `ally_holding`), and C 2/4/6/10 pathing flips beyond
  what the records change.
- **02stalactites (one build):** a banker stood ~1,600 turns at an enemy-occupied altar (bank/guard, streams 1/2).
