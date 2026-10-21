# Rules verification

`../cambc-rules.yaml` is the source of truth; these probes are how its rules were settled and how to re-check them after an engine update.

## Running a probe

```
cambc run rules-verification/probes/<A> rules-verification/probes/<B> --map <map> --rounds <N> --fuel 50000000 -o <dir>
```

- Pass a large `--fuel`: at the default budget, logging runs out of fuel and shifts timings into the next round.
- Each probe's source header gives its run command and scenario switches; `run.sh` scripts take `<scenario> <map> <rounds>`.
- Logs are the `PROBE` lines in `team-a.stdout` / `team-b.stdout` inside the `.repl26a` zip; strip NULs with `tr -d '\000'` before grepping.
- Map names need their prefix (`00interlock`); generated maps go by path (`maps/gen/<file>.map26a`). `makemap.mjs` (in `probe-corner`, `probe-denial`) builds custom maps through the engine's map builder.

## Which probe checks what

| YAML | Probes |
|---|---|
| `champions` (stats, abilities, modifiers), `camps.types`, settings, items | `probe-designs` (all designs from the engine); `probe-facts` (hecate's champions.h against the engine) |
| `result.round_limit`, `fuel` | `probe-fuel`, `probe-fuel-b..e`; `probe-firstturn` |
| `map.coordinates`, `map.symmetry` | `probe-introspect` |
| `map.corners`, diagonal sight | `probe-corner` |
| `draft`, `rounds.champion_order`, `rounds.team_order`, `memory`, dead champions' slots | `probe-order`, `probe-order-b` |
| `draft.in_play`, `vision.visible_champions`, `vision.unseen_units` | `probe-enemyinfo` |
| `turn`, `abilities` (cooldown, excludes walking, reset, dash, targets) | `probe-allowances`, `probe-allowances-b` |
| `abilities.stun`, `combat.kill`, `death`, `recall`, `map.spawn` | `probe-stun`, `probe-stun-b`, `probe-stunstack` |
| `recall` with a shield | `probe-shield-recall` |
| `camps.wake`, `camps.sleep`, `camps.attack` | `probe-camps`, `probe-camps-b`, `probe-stunwake`, `probe-sleep-range`; ties: `probe-denial` scenario 6 |
| `capture`, `gems.tribute`, `economy.gold`, `economy.bonuses` | `probe-capture`, `probe-capture-b`, `probe-reset`, `probe-reset-b`, `probe-denial`; contest: `probe-misc` scenario 2 |
| `combat.modifiers`, `altar_locks`, `economy.health_purchase` | `probe-misc`, `probe-misc-b` |
| `rounds.turn_start`, buffs, shields, Marcella, Ren, Prism, Vendetta, Varg passives | `probe-effects`, `probe-effects-b` |
| Varg's splash from a camp target | `probe-varg-splash` |
| Heart of Ruin's landing on unseen enemies | `probe-hor-unseen` |
| `vision`, `wards`, `teleport_crystal`, `turn.hidden_blocker` | `probe-vision`, `probe-vision-b`, `probe-pathcost`, `ward-hidden`, `probe-wardcd`, `probe-ward-walk` |
| teleporting into a walled altar | `vault` |

## Facts outside the rules

- Errors: a duplicate own pick is error 14; a second pick in one draft turn, or a draft-memory write in play, is error 18; reading an unseen unit's details is error 97; `remaining_channel_time()` while not channelling is error 115; `shadow_cast` from an opaque tile is error 5.
- `is_ready()` reports an attack reset as castable while the attack is unspent, when the cast would fail.
- `bitboard::shadow_cast` with walls and the other bush clusters opaque reproduces engine vision exactly.
- Costs: `map::camp_groups()` ~28k fuel; a 13-row stat table from `champion_designs` ~2.75k.
- Unreleased content in the engine data: a control ward and a TP scroll (`tp_scroll_time`, retired in the SDK). Neither can be bought.
