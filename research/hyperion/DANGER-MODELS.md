# Danger models

The inventory behind TODO 3 (one danger model) and STRIKE-SEARCH phase 5. Each model answers some form of: who can hit
tile p and how hard, do we lose a fight here, do we die here. Costs and shares were measured on main bbf6f05 (CHANGES
1-59) with `tools/fuel/bench.py run hyperion --set wide --test-draft`; "heavy" means turns over 100k at 100M fuel.
Later profiles are in [EXPERIMENTS.md](../EXPERIMENTS.md#fuel); re-profile before relying on a number.

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
| `step_guard` | tiles a step or dash could end on that want_home would flee: Strike bound, Reach exposure, union fight, then fights; built on first need (CHANGES 110) | 19% heavy | decide (twice when the search moved us) |
| `prey` | the best kill whose fight at the enemy's tile is won | 10% heavy | chase, `carry_bag`, `continue_tribute` |
| strike search end tiles | Strike share, exact `blow` (10 queries), `threats_at`, `lethal`, `damage_bound` for shields, removal | 16% heavy | decide, `strike_after` |
| self_abilities, abilities, turn order | own threat depth per landing, the shield's own camp loop, unwidened one-turn reach for casts, `damage_bound` by hand in `offer_escape` | small-3% | dashes, shields, casts, turn order |

## Overlaps to fold

1. **"Who hits p, how hard" has four representations** (Strike, Reach, Threat fields, `enemy_area`), unseen enemies
   get seven treatments, and the Strike-then-Reach gate is written three times (`Safety::blow`, step_guard's bound,
   plan's share).
2. **The same tile is priced in several passes a turn.** Plan's end tiles: exact blows, then `threats_at` (repeating
   the visible blows), then `damage_bound` for the shield, then `lethal`. Turn order: `damage_ceiling` twice,
   `damage_bound`, `threats_at`, all at our tile. step_guard's tiles and the search's end tiles are mostly the same,
   judged by different models.
3. **"Do we lose or die here" has about seven models:** the fight sim (no camps), `stand`, the idle sim, `lethal`,
   the pack zone, `tribute_safe`, `offer_escape`.
4. **The fight memo is shared only by exact key.** prey keys at the enemy's tile and rarely hits.
5. **Camp danger has about nine models:** `find_members`/`camp_damage`, plan's `camp_at`, `wake`/`find_wakers`,
   `threats_near`, `shield_if_needed`'s loop, `min_camp_damage`/`finishing_camp`, `camp_cast keep`/`wake_risk`/
   `landing_wakes`, `CampGroup::threat()`, `access_fire`.
6. **`fight_key` forces the full threat build**, a field for every unseen credible enemy, even when only visible
   enemies can reach the tile.

The byte-identical memos once proposed as first steps save nothing (EXPERIMENTS Fuel): a turn memo for `lethal` sees
0.1 repeated tiles a heavy turn, step_guard repeats 2% of its keys, and the Reach memo has no collisions. The saving
has to come from folding passes (2, 3, 5), not from caching them.
