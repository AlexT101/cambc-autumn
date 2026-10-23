# hyperion: where the fuel goes

The profile behind the 2026-10-22 fuel work: what still holds, and the danger-model inventory for TODO 3. Measured on
main bbf6f05 (CHANGES 1-59, profile) and d59ccf7 (1-67, out-of-fuel anatomy), with `tools/fuel/bench.py run hyperion
--set wide --test-draft` (26 maps, 52 games against hecate) and instrumented copies whose meters sat in `debug_block`.
CHANGES 60-81 have since cut out-of-fuel turns by ~61% and the worst search from 158.6k to 78.2k, so read the shares,
not the counts; re-profile before relying on a number.

## What still holds

- **Every out-of-fuel turn runs out inside `decide`.** World update, comms and turn end never do.
- **Fight maps hold them.** gen-chambers (both seeds), gen-hourglass-102205812 and 00contest held 81% of turns over
  100k: 8-10 champion brawls, largest simulation 4-8 fighters on 86% of heavy turns. By champion: Heart of Ruin, then
  Ren, Varg, Ryth.
- **~50k of fixed work comes before the strike search.** World update ~14k, `want_home` ~19k (`stand` 8.5k, `lethal`
  5.6k over 1.4 calls, `camp_trapped` 3k), `step_guard` ~16k (own code 10.9k: Reach::at looks, bounds, fight keys).
  The search then starts with ~41k (p50) and is where 59% of out-of-fuel turns ran out (66% of those in `grow`), farm
  18%.
- **Gates move fuel, not save it.** At the real budget step-guard and prey-cut-short hold `step_guard` to ~18k and
  `prey` to ~2k on out-of-fuel turns (25k and 16k at 100M); the strike search, ungated, spends what they save and runs
  out. That is why every gate removal raised out-of-fuel turns.
- **Replays run out again.** ~44% of out-of-fuel turns are replays (CHANGES 59), and 80% of re-cut replays run out in
  the same step as the turn they replace, whatever fuel they start with. Cut first-time out-of-fuel turns and their
  replays fall with them (x1.78). Carrying out the abandoned plan instead traded them for stale actions.
- **Fight simulations:** ~400 fuel a half-turn (282 at 1v1, 634 at 4v4), 5k a sim. Ends: all enemies fall 43%,
  `outlives` 25%, we all fall 21%, horizon 9% (16% on heavy turns; 20-30% of sim fuel, and 37% in a later
  measure). A non-plain act() (shield kits,
  mostly Heart of Ruin's missing-health scaling) is 44% of sim fuel.
- **Farm evaluation loop:** 11% of all fuel, 8.6k a farm turn; touching a group costs ~150-270 even when rejected.
- **Smaller standing costs:** `update_camps` 3k a turn (8k on camp-dense maps, three host calls a visible member);
  `siege_candidate` 2.6k on 55% of turns (`altars_sealed` -> `access_fire`, memoised a round); `set_turn_order` 3%;
  `find_members` 2.4% (memo holds the last tile only); `lethal` 2.2% (82% of turns); `threatened` 1.4% (up to 5 calls a
  turn, not memoised); comms 4.1%.

## Danger models

Each answers some form of: who can hit tile p and how hard, do we lose a fight here, do we die here.

| model | computes | cost | callers |
|---|---|---|---|
| `Strike` / `strike()` | distance table (0-6) of the most damage or stun next turn; ignores walls and sight | memo | everything below; turn_order.cpp keeps a second cache |
| `threat_strike()` | Strike widened when the enemy has two turns before ours | cheap | Safety foes, `threats_near`, `shield_wanted` |
| `Reach` | exact 9x9 placement: walk, dash, sight, Varg splash; 64-entry memo a build | 1.7k a build, ~490 a missed tile | `blow`, step_guard's exposure, plan's exact queries, `approach`, `shield_if_needed` |
| `Threat` / `threats()` | capped distance field per unseen credible enemy | 1.2k a build | `fight_key*`, `worst_damage`, `threatened`, `enemy_area`, `threats_at` |
| `damage_bound` / `damage_ceiling` / `worst_damage` | camp hits plus blows; each treats unseen enemies differently | per enemy | `lethal`, flee and retreat steps, plan `shield_at` and `read_mates`, turn order |
| `lethal(p)` | one-turn kill: ceiling, then bound, then worst | 2.2% | `want_home`, step_guard, plan end tiles at distance 3 |
| `threats_at` | per-enemy blow at p; for unseen enemies a field or a Chebyshev bisection, depending on what ran earlier | | plan, turn order `offer_channel` / `offer_escape` |
| `threatened(p)` | chance of damage before our turn (recall risk) | 1.4% | up to 5 times a turn |
| `find_members`, `camp_damage`, `camp_area` | awake members' hits, cut by nearer champions | 2.4% | `camp_trapped`, `flee_camps`, plan's `camp_at`, `note_upkeep` |
| fight sim (`fight`, `simulate`) | sides alternate 17 own turns; no camp damage; memo of 32 by (enemies hitting p, allies within 4) | 5k a sim | `Safety::stand`, step_guard, prey (up to 8) |
| `turns_to_kill_idle` | we never act; enemies walk in; camps hit | 1.6k, rare | `tribute_safe` |
| pack zone (`outmatched`, `pack_covers`) | subsets of enemies seen this round by health x output | once a round | want_home, prey, routing zones |
| `want_home` | low health, `outmatched`, `camp_trapped`, `lethal`, then `stand` | 21% of heavy-turn fuel | decide, `continue_recall`, `continue_tribute` |
| `step_guard` | tiles a step or dash could end on that want_home would flee: Strike bound, Reach exposure, union fight, then fights | 19% heavy | decide (twice when the search moved us) |
| `prey` | the best kill whose fight at the enemy's tile is won | 10% heavy | chase, `carry_bag`, `continue_tribute` |
| strike search end tiles | Strike share, exact `blow` (10 queries), `threats_at`, `lethal`, `damage_bound` for shields, removal | 16% heavy | decide, `strike_after` |
| self_abilities, abilities, turn order | own threat depth per landing, the shield's own camp loop, unwidened one-turn reach for casts, `damage_bound` by hand in `offer_escape` | small-3% | dashes, shields, casts, turn order |

### Overlaps to fold

1. **"Who hits p, how hard" has four representations** (Strike, Reach, Threat fields, `enemy_area`), unseen enemies
   get seven treatments, and the Strike-then-Reach gate is written three times (`Safety::blow`, step_guard's bound,
   plan's share).
2. **The same tile is priced in several passes a turn.** Plan's end tiles: exact blows, then `threats_at` (repeating
   the visible blows), then `damage_bound` for the shield, then `lethal`. Turn order: `damage_ceiling` twice,
   `damage_bound`, `threats_at`, all at our tile. step_guard's tiles and the search's end tiles are mostly the same,
   judged by different models.
3. **"Do we lose or die here" has about seven models:** the fight sim (no camps), `stand`, the idle sim, `lethal`,
   the pack zone, `tribute_safe`, `offer_escape`.
4. **The fight memo is shared only by exact key.** prey keys at the enemy's tile and rarely hits; step_guard's
   dominance cache is local to one call.
5. **Camp danger has about nine models:** `find_members`/`camp_damage`, plan's `camp_at`, `wake`/`find_wakers`,
   `threats_near`, `shield_if_needed`'s loop, `min_camp_damage`/`finishing_camp`, `camp_cast keep`/`wake_risk`/
   `landing_wakes`, `CampGroup::threat()`, `access_fire`.
6. **`fight_key` forces the full threat build**, a field for every unseen credible enemy, even when only visible
   enemies can reach the tile.

Byte-identical first steps towards one model: a turn memo for `lethal`, step_guard's settled keys and Reach exposures
kept across its two calls, a wider Reach memo.
