# Rules verification

`../../cambc-rules.yaml` is the source of truth; these probes are how its rules were settled and how to re-check them after an engine update.

## Running a probe

```
cambc run tools/probes/<A> tools/probes/<B> --map <map> --rounds <N> --fuel 50000000 -o <dir>
```

- Pass a large `--fuel`: at the default budget, logging runs out of fuel and shifts timings into the next round.
- Each probe's source header gives its run command and scenario switches; `run.sh` scripts take `<scenario> <map> <rounds>`.
- Logs are the `PROBE` lines in `team-a.stdout` / `team-b.stdout` inside the `.repl26a` zip; strip NULs with `tr -d '\000'` before grepping.
- To compare engine versions, run each probe under each cambc binary: `pip download cambc==X --no-deps` fetches an old wheel, whose `cambc-X.data/scripts/cambc` runs as is (`CAMBC_NO_UPDATE_CHECK=1` silences its upgrade notice).
- Map names need their prefix (`00interlock`); generated maps go by path (`maps/gen/<file>.map26a`). `makemap.mjs` (in `probe-corner`, `probe-denial`) builds custom maps through the engine's map builder.

## Which probe checks what

| YAML | Probes |
|---|---|
| `champions` (stats, abilities, modifiers), `camps.types`, settings, items | `probe-designs` (all designs and the item table from the engine; diff its output across engine versions); `probe-facts` (hyperion's champions.h against the engine); `probe-heart` (Heart of Ruin, draft id 11, drafts and plays) |
| `result.round_limit`, `fuel` | `probe-fuel`, `probe-fuel-b..e`; `probe-firstturn`; `probe-fuel-ops` (fuel per arithmetic instruction: a 64-bit division ~3.5 above a multiply); `probe-fuel-arb` + `probe-fuel-arb-big` (`run.sh`; release, 2026-11-08): an 8 MiB `#embed` table costs no start-up fuel (first turn 189,746 left either way); `memory.grow` of 1 MiB 7; a 64 KiB `memcpy` 1 a byte, a 4-wide v128 copy loop 0.43 a byte (clang turns a plain copy loop into `memcpy`), `memset` 0.2 a byte; 16 byte lookups 112 scalar, 12 by `i8x16.swizzle`; `powf` 54, `sinf` 41, `expf` 28, `logf` 23, `atan2f` 17 a call; `sqrt` and divides ~1 above an add; a non-inlined call ~5; on 100x100 a full distance field 25k and its `export_linear_buffer` 2.5k, the export equal to `sdk_DistanceField_Get` on every tile |
| `map.coordinates`, `map.symmetry` | `probe-introspect` |
| `map.size` (the engine's width and height); the published range, 28x28 (04pinwheel, 04plaza) to 100x100, from the ladder map files (`node tools/mapgen/mapgen.mjs check maps` prints each map's size; 2026-11-05) | `probe-mapsize` (04pinwheel reads 28x28) |
| `map.corners`, diagonal sight | `probe-corner` |
| `draft`, `rounds.champion_order`, `rounds.team_order`, `memory`, dead champions' slots | `probe-order`, `probe-order-b` |
| `memory.replay`: replays record every priority set (raw int32) but neither team's shared or draft bytes (two games differing only in those bytes give byte-identical `replay.repl26a`) | `probe-replay-leak` (00corners, 40 rounds; 2026-11-08) |
| `memory.shared` across a turn that ran out of fuel (its writes show at once; resumed, it reads live bytes); host prices of the shared-memory read and write (9 each) | `probe-suspend-memory` |
| `fuel.exhaustion` while channelling a recall (the bot resumes next round, still recalling) | `probe-suspend-channel` |
| `fuel.end_turn` (ending a turn with under 40 fuel loses the next turn) | `probe-endturn-fuel` |
| `fuel.exhaustion`, where an out-of-fuel turn stops (cambc 5.0.1 against 5.0.0, 2026-11-09): after a host call that spends the fuel (a radius-8 shadow cast, 441, with 95 left), the next raw imports (`round_number`, the move) run next round on 5.0.1 and ran the same turn on 5.0.0; after straight-line guest code spends it (2,050 with 184 left), the next import runs next round on both. Unchanged between the two: `probe-endturn-fuel`'s threshold (`LEFT` 375 loses the next turn, 380 keeps it; the gap is the code before `end_turn`) and every PROBE line of `probe-endturn-fuel`, `-suspend-memory`, `-suspend-channel`, `-fuel`, `-fuel-b` and `-firstturn` | `probe-hostcall-fuel` (`MODE` 0: host call, 1: guest code) |
| `draft.in_play`, `vision.visible_champions`, `vision.unseen_units` | `probe-enemyinfo` |
| `vision.unseen_units`: the raw status of every per-champion import on an enemy out of vision (97 `api_not_in_vision`; identity and ability props readable; gold 105, wards 112), and `champion_at` on an empty tile in vision (98) | `probe-unseen-codes` |
| `vision.visible_champions`, `vision.unseen_units`: a teammate's gold through the raw `sdk_champion_gold`, in vision or out of it (code 0, its exact gold; `gold_count()` refuses non-self only client-side); an enemy's, seen or not, 105 | `probe-ally-gold` (00collision: teammates' 500 reads of Marcella's gold all match her own, 28 out of vision), `probe-ally-gold-b` (both teams meet on a tiny map: 489 reads of enemies in vision, all 105) |
| `turn`, `abilities` (cooldown, excludes walking, reset, dash, targets) | `probe-allowances`, `probe-allowances-b` |
| `abilities.stun`, `combat.kill`, `death`, `recall`, `map.spawn` | `probe-stun`, `probe-stun-b`, `probe-stunstack` |
| `death.respawn`: consumables, shards and gold kept through death | `probe-death-items` |
| `champions.tavi.passive`: sales on spawn only (off spawn: "Selling items requires your team's spawn tiles"); several sales a turn (two types, the same type twice, a count of 2) and a buy after a sale all succeed; shard refunds 30, emblem 150, stats removed; Health bought off spawn raises max only, arrives healed on spawn, and sold lowers health and max by 75 | `probe-tavi-sell` (00packs, 250 rounds; 2026-11-08) |
| `death.dead_turns`, `rounds.champion_order`: a dead champion sets its priority (no error), and from the next round, still dead, moves in its team's order and takes its alternation slot; the priority persists through respawn | `probe-dead-priority`, `probe-dead-priority-b` (00packs, 150 rounds) |
| `recall` with a shield | `probe-shield-recall` |
| `recall.landing`: the spawn tile order, from every side, with tiles occupied, on rotational and horizontal maps | `probe-recall-land` (`makemap.mjs <rot\|rot-nw\|hor>`) |
| `economy.emblems` Durability with a shield (the -10% applies before absorption) | `probe-durability-shield` |
| `camps.wake`, `camps.sleep`, `camps.attack` | `probe-camps`, `probe-camps-b`, `probe-stunwake`, `probe-sleep-range`, `probe-sleep-timing`; ties: `probe-denial` scenario 6 |
| `camps.sleep` for gem and gold clusters: a champion within Chebyshev 3 (straight or diagonal) keeps an awake cluster awake, one at 4 does not; the same alone, in a cluster-only group (gem+gold) and in groups with an elk (an elk held awake at 4 does not keep its gem cluster awake at 4) | `probe-cluster-sleep` (`makemap.mjs`) |
| `camps.state`: a cleared group's `state()` and `capture_state()` with only one of its two camp tiles in vision, and an unseen capturer | `probe-capture-vision` |
| `vision.unseen_units` for camps: nothing about a camp or group with no tile in vision is readable, alive, dead or respawning (97 from per-camp reads and `capture_state`, group state 0, cooldown 106, absent from occupancy boards) | `probe-camp-unseen` (`makemap.mjs`) |
| `abilities.stun` on a camp: the skipped attack, a second stun after it | `probe-campstun` |
| `abilities.stun` on a champion: what observers read before and after the lost turn, a stun on a spent buff | `probe-stunread` |
| `capture`, `gems.tribute`, `economy.gold`, `economy.bonuses` | `probe-capture`, `probe-capture-b`, `probe-reset`, `probe-reset-b`, `probe-denial` (team B: `probe-denial-b`, which run.sh fills); contest: `probe-misc` scenario 2 |
| `economy.bonuses` with Marcella's passive gold (Treasure on her tribute gold) | `probe-marcella-gold` |
| `economy.emblems` (2.0.0; re-run on cambc 5.0.0, Skirmish x1.10): Capture (alone, and joining an ally's capture; `capture_state()` each round), Tribute channel lengths (bags 14/21/28/56), Skirmish and Collectors on basic, unit and ground damage to champions and camps; emblem `passive_magnitude`s | `probe-emblems-v2` (`run.sh <join_delay>`; team B is the no-emblem control) |
| `combat.modifiers`, `altar_locks`, `economy.health_purchase` | `probe-misc`, `probe-misc-b` |
| `rounds.turn_start`, buffs, shields, Marcella, Ren, Prism, Vendetta, Varg passives | `probe-effects`, `probe-effects-b` |
| Varg's splash from a camp target | `probe-varg-splash` |
| Heart of Ruin's landing on unseen enemies | `probe-hor-unseen` |
| `abilities.dash`: paths blocked by visible enemy champions | `probe-dash-enemy` |
| `abilities.dash`: paths blocked by the enemy spawn | `probe-dash-spawn` |
| `abilities.dash`: paths not blocked by an unseen camp (on a bush) | `probe-dash-hidden-camp` |
| `abilities.dash`, `map.corners`: 2-step paths with diagonal steps over holes and altars and through squeezes; `reachable_tiles(S, 2)` agrees | `probe-dash-diagonal` |
| `vision`, `wards`, `teleport_crystal`, `turn.hidden_blocker` | `probe-vision`, `probe-vision-b`, `probe-pathcost`, `ward-hidden`, `probe-wardcd`, `probe-ward-walk`; same-turn ward sight: `probe-ward-sight`; ward sight and bushes, `sdk_ward_vision`, `sdk_wards`: `probe-ward-bush` |
| `vision.shadowcast_radius`: `bitboard::shadow_cast` radius independence (radii 1-8), adjacent clear tiles always in the cast, opaque tiles never, on synthetic boards | `probe-shadowcast` |
| teleporting into a walled altar | `vault` |
| `teleport_crystal.target` onto dead camps' tiles (a cleared group's: lands and captures; a respawning group's: lands); `capture.respawn` with a teleport reserved on the tile (it delays the return) | `probe-teleport-dead-camp` (`makemap.mjs`) |
| `teleport_crystal.target` onto one dead member's tile while the rest of its group lives (lands; the group still reads alive) | `probe-teleport-dead-member` (`makemap.mjs`) |
| `abilities.unit_target` for ally abilities: Willow's heal on an ally in range but unseen (on a bush) is refused, error 30; `heal_amount()` on it throws (97), and on a seen ally reads the health it would restore (its missing health, not 3x Focus) | `probe-willow-heal-vision` (`makemap.mjs`) |
| `abilities.unit_target` with `wards.vision`: Willow's heal on an ally she cannot see from her own tile (on a bush) but sees through her own ward on that bush cluster, placed that turn, is accepted (refused, error 30, just before the ward) | `probe-willow-heal-ward` (`makemap.mjs`) |
| `capture.reward`: the Prospector bonus on a 3-way cluster split, owner lowest id (25% of its share with the remainder: gold 26+2 -> +7, gems 11+2 -> +3) | `probe-prospector-remainder` (`makemap.mjs`) |
| `abilities.stun` with `rounds.turn_end`: a champion stunned on its own spawn heals to full at its lost turn's end, and its cooldowns and stun buff tick on that turn | `probe-stun-spawn-heal` (00elkring) |
| `memory.linear` (the cap), and a bot with 2 MiB more static memory starting | `probe-memory` |
| Bitboard padding (storage bits that are not tiles): what host ops do with it, and that it never reaches the map (facts below) | `probe-padding` (00the-line 33, 01islands 60, 00corners 71, 00ambush 100) |

## Facts outside the rules

- A camp's stun buff (`sdk_camp_buffs`) reads timer 1 from the stun to the camp phase it skips, then timer 0 until the next camp phase: at a turn start, only timer 1 means the next attack is skipped. A stun cast on a timer-0 camp sets 1 and skips the next attack (`probe-campstun`).
- A champion's stun buff (`buff_stun::duration`) reads 1 from the stun until the victim's lost turn ends (observers later in the stunner's round still read 1: it ticks only at the victim's turn end), then 0 until the victim's next turn start, where it expires. So `duration > 0` means the stun will take the victim's next turn, whatever the turn order; a stun cast on a 0 buff sets 1 and takes the next turn (`probe-stunread`; astraeus's `stun_pending`, CHANGES 136). Untested: a stun cast after the victim already acted that round.
- Gold bonuses also apply to Marcella's tribute gold: with a Treasure emblem she gets 2.4 per gem (29 gems: +69.6), and the fraction carries over. The gold is credited when the channel completes, together with the gems, not at its start (`probe-marcella-gold`).
- Errors: a duplicate own pick is error 14; a second pick in one draft turn, or a draft-memory write in play, is error 18; reading an unseen unit's details is error 97; `remaining_channel_time()` while not channelling is error 115; `shadow_cast` from an opaque tile is error 5.
- `is_ready()` reports an attack reset as castable while the attack is unspent, when the cast would fail.
- `bitboard::shadow_cast` with walls and the other bush clusters opaque reproduces engine vision exactly.
- `bitboard::positions()` lists tiles in 8x8 blocks (row order inside each), not row order: a 3x3 spawn on (6..8,6..8) reads (6,6) (7,6) (6,7) (7,7) (8,6) (8,7) (6,8) (7,8) (8,8) (`probe-recall-land`).
- Bitboard raw storage: word `(y / 8) * chunk_stride + x / 8`, bit `(y % 8) * 8 + x % 8`; `chunk_stride` is `chunked_width` rounded up to even (33: 5 -> 6, 71: 9 -> 10, 100: 13 -> 14, 60: 8 -> 8), and there are no rows past `chunked_height`. Distance fields have no stride column: value `(y / 8) * chunked_width + x / 8` chunks of 64. Padding (edge-chunk bits past width/height, plus the stride column) never reaches a map tile through host ops (`probe-padding`):
  - Ops carry padding but never move it onto the map: shifts by 1-9 in every direction (diagonals as two shifts), reflections, `Not`, union, intersection and xor of a padding-only board give no tile. A tile shifted off the map lands in padding but does not come back: the right column shifted right then left is empty. A row or column of walls spanning the map seals it for `distance_field` and `reachable_tiles`, whatever the walls' padding.
  - `count`, `is_empty`, `==` and `positions` ignore padding: a padding-only board is empty and equals an empty one.
  - Padding written: `fill()`, `Not` (the complement of the input's padding: `~empty` has all of it, `~P` of a padding-only P none), shifts (the source's padding moved), and as outputs `reachable_tiles` and `distance_field`'s `visited` (padding not in the walls' padding, independent of the output's prior contents). `clear()`, `shadow_cast`, `draw_chebyshev` and `set` leave none. Distance values in field padding always read `unreachable`.
  - Padding in walls or roots changes nothing on the map: a padding-only roots board reaches no tile.
- Bitboard linear buffers are bit-packed (bit `y*W+x`, least-significant first, `(W*H+7)/8` bytes), though the SDK comment on `import_linear_buffer` says one byte per tile (`probe-shadowcast`).
- Linear memory (local engine, 2026-10-26): `memory.grow` succeeds up to 4096 pages (256 MiB) and fails past it; a grow costs ~8 fuel whatever its size. A bot with a 2 MiB static array starts at 34 pages, and grown memory persists into the next round (`probe-memory`). The server's cap is unverified.
- `fuel_adjust` (debug builds only; `probe-fueladjust`, `probe-fueladjust-b`): a call costs 2.
  - A negative delta charges, but only within the current 100k chunk: a 2x first turn drained in its first chunk reads 100000.
  - A positive delta refunds. `fuel_remaining()` never reads above the budget (on a first turn, 200000 in the first chunk and 100000 in the second), but the excess is real hidden fuel, usable until the turn ends or a drain. With work plus charges every turn at `--fuel 100000000`, instances trap near round 1000 and restart; none do at 100k-30M.
- `distance_field::compute_with_expansion_count(walls, roots, visited, cap)` returns `min(cap, D + 1)`, D the deepest reachable distance: a complete search counts one empty expansion past D, a capped one stops at `cap` without it. So a return below `cap` proves the field complete (D = return - 1), and a return equal to `cap` cannot tell D = cap - 1 or D = cap (complete) from D > cap (cut short); it never exceeds `cap`. Unreached tiles read `unreachable` (one-root, two-root and lone-root strips, D = 0, 5, 12; `probe-field-cap`).
- Costs: `map::camp_groups()` ~28k fuel; a 13-row stat table from `champion_designs` ~2.75k.
- Unreleased content in the engine data: a control ward and a TP scroll (`tp_scroll_time`, retired in the SDK). Neither can be bought.
