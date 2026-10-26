# Rules verification

`../../cambc-rules.yaml` is the source of truth; these probes are how its rules were settled and how to re-check them after an engine update.

## Running a probe

```
cambc run tools/probes/<A> tools/probes/<B> --map <map> --rounds <N> --fuel 50000000 -o <dir>
```

- Pass a large `--fuel`: at the default budget, logging runs out of fuel and shifts timings into the next round.
- Each probe's source header gives its run command and scenario switches; `run.sh` scripts take `<scenario> <map> <rounds>`.
- Logs are the `PROBE` lines in `team-a.stdout` / `team-b.stdout` inside the `.repl26a` zip; strip NULs with `tr -d '\000'` before grepping.
- Map names need their prefix (`00interlock`); generated maps go by path (`maps/gen/<file>.map26a`). `makemap.mjs` (in `probe-corner`, `probe-denial`) builds custom maps through the engine's map builder.

## Which probe checks what

| YAML | Probes |
|---|---|
| `champions` (stats, abilities, modifiers), `camps.types`, settings, items | `probe-designs` (all designs from the engine); `probe-facts` (hyperion's champions.h against the engine); `probe-heart` (Heart of Ruin, draft id 11, drafts and plays) |
| `result.round_limit`, `fuel` | `probe-fuel`, `probe-fuel-b..e`; `probe-firstturn`; `probe-fuel-ops` (fuel per arithmetic instruction: a 64-bit division ~3.5 above a multiply) |
| `map.coordinates`, `map.symmetry` | `probe-introspect` |
| `map.corners`, diagonal sight | `probe-corner` |
| `draft`, `rounds.champion_order`, `rounds.team_order`, `memory`, dead champions' slots | `probe-order`, `probe-order-b` |
| `memory.shared` across a turn that ran out of fuel (its writes show at once; resumed, it reads live bytes); host prices of the shared-memory read and write (9 each) | `probe-suspend-memory` |
| `fuel.exhaustion` while channelling a recall (the bot resumes next round, still recalling) | `probe-suspend-channel` |
| `fuel.end_turn` (ending a turn with under 40 fuel loses the next turn) | `probe-endturn-fuel` |
| `draft.in_play`, `vision.visible_champions`, `vision.unseen_units` | `probe-enemyinfo` |
| `turn`, `abilities` (cooldown, excludes walking, reset, dash, targets) | `probe-allowances`, `probe-allowances-b` |
| `abilities.stun`, `combat.kill`, `death`, `recall`, `map.spawn` | `probe-stun`, `probe-stun-b`, `probe-stunstack` |
| `death.respawn`: consumables, shards and gold kept through death | `probe-death-items` |
| `recall` with a shield | `probe-shield-recall` |
| `economy.emblems` Durability with a shield (the -10% applies before absorption) | `probe-durability-shield` |
| `camps.wake`, `camps.sleep`, `camps.attack` | `probe-camps`, `probe-camps-b`, `probe-stunwake`, `probe-sleep-range`, `probe-sleep-timing`; ties: `probe-denial` scenario 6 |
| `abilities.stun` on a camp: the skipped attack, a second stun after it | `probe-campstun` |
| `abilities.stun` on a champion: what observers read before and after the lost turn, a stun on a spent buff | `probe-stunread` |
| `capture`, `gems.tribute`, `economy.gold`, `economy.bonuses` | `probe-capture`, `probe-capture-b`, `probe-reset`, `probe-reset-b`, `probe-denial` (team B: `probe-denial-b`, which run.sh fills); contest: `probe-misc` scenario 2 |
| `economy.bonuses` with Marcella's passive gold (Treasure on her tribute gold) | `probe-marcella-gold` |
| `economy.emblems` (2.0.0): Capture (alone, and joining an ally's capture; `capture_state()` each round), Tribute channel lengths (bags 14/21/28/56), Skirmish and Collectors on basic, unit and ground damage to champions and camps; emblem `passive_magnitude`s | `probe-emblems-v2` (`run.sh <join_delay>`; team B is the no-emblem control) |
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

## Facts outside the rules

- A camp's stun buff (`sdk_camp_buffs`) reads timer 1 from the stun to the camp phase it skips, then timer 0 until the next camp phase: at a turn start, only timer 1 means the next attack is skipped. A stun cast on a timer-0 camp sets 1 and skips the next attack (`probe-campstun`).
- A champion's stun buff (`buff_stun::duration`) reads 1 from the stun until the victim's lost turn ends (observers later in the stunner's round still read 1: it ticks only at the victim's turn end), then 0 until the victim's next turn start, where it expires. So `duration > 0` means the stun will take the victim's next turn, whatever the turn order; a stun cast on a 0 buff sets 1 and takes the next turn (`probe-stunread`; astraeus's `stun_pending`, CHANGES 136). Untested: a stun cast after the victim already acted that round.
- Gold bonuses also apply to Marcella's tribute gold: with a Treasure emblem she gets 2.4 per gem (29 gems: +69.6), and the fraction carries over. The gold is credited when the channel completes, together with the gems, not at its start (`probe-marcella-gold`).
- Errors: a duplicate own pick is error 14; a second pick in one draft turn, or a draft-memory write in play, is error 18; reading an unseen unit's details is error 97; `remaining_channel_time()` while not channelling is error 115; `shadow_cast` from an opaque tile is error 5.
- `is_ready()` reports an attack reset as castable while the attack is unspent, when the cast would fail.
- `bitboard::shadow_cast` with walls and the other bush clusters opaque reproduces engine vision exactly.
- Bitboard linear buffers are bit-packed (bit `y*W+x`, least-significant first, `(W*H+7)/8` bytes), though the SDK comment on `import_linear_buffer` says one byte per tile (`probe-shadowcast`).
- `fuel_adjust` (debug builds only; `probe-fueladjust`, `probe-fueladjust-b`): a call costs 2.
  - A negative delta charges, but only within the current 100k chunk: a 2x first turn drained in its first chunk reads 100000.
  - A positive delta refunds. `fuel_remaining()` never reads above the budget (on a first turn, 200000 in the first chunk and 100000 in the second), but the excess is real hidden fuel, usable until the turn ends or a drain. With work plus charges every turn at `--fuel 100000000`, instances trap near round 1000 and restart; none do at 100k-30M.
- Costs: `map::camp_groups()` ~28k fuel; a 13-row stat table from `champion_designs` ~2.75k.
- Unreleased content in the engine data: a control ward and a TP scroll (`tp_scroll_time`, retired in the SDK). Neither can be bought.
