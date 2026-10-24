# hyperion-v38-trace: trace schema (version 1)

This is v38 (`git archive 5b02a02 bots/hyperion`) plus read-only decision logging. It is run by `tools/replay/harness/trace_batch.py` with the tracer harness (`tools/replay/harness/wrappers/harness_trace.h`). That harness replays the recorder run's fuel view, so the traced bot makes the ladder bot's decisions; every segment's host calls are checked against the recorder's.

Output is our team's stdout, `runs/batch/<key>/trace.stdout.gz`. It holds one record per line, each a tag followed by space-separated `key=value` fields.

## Reading it

- **Line order.** Lines from one champion are in order. Champions' lines interleave by flush, about once per turn, so join on `r` (round) and `c` (champion id = engine handle).
- **Missing fields.** Absent optional fields mean "no" or "none".
- **Number formats.**
  - Positions are `x,y`, with (-1,-1) meaning dead or none.
  - Health, damage and values are rounded floats.
  - `never` in fighter fields is 2147483647.
- **Fight summaries `T`** are `lost:tku:tkt:falls:allies:enemies`:
  - `lost`: 1 if they win when they strike first;
  - `tku`: their turns to kill our side, 0 if not within the horizon;
  - `tkt`: our turns to kill theirs;
  - `falls`: 1 if our own champion falls first, `?` if not asked;
  - `allies`, `enemies`: fighter counts.
- **Trust.** A game's trace explains the ladder game only through `ladder_trusted_through` in its `trace_validation.json`.
  - After that round the recorder run (and so the trace) has diverged from the ladder. The puppet then replays the ladder blindly, so the game is a different one.
  - With `exact_vs_rec` false, the trace is also unverified after `rec_trusted_through`. See "Validation".

## Verbosity

These options are set per game: `trace_batch.py --level N --rounds R0-R1`, passed on to `trace_data.py`. Changing them rebuilds only `rec_data.cpp`.

| level | prints |
|---|---|
| 0 | TV, TT, TA, harness lines |
| 1 (default) | + TB (enemies), TE, TS |
| 2 | + within rounds R0..R1: TB for allies, TF (every fight query), TQ (every threat value), TE `sides` (each simulation's fighters), `cast_cand`, `farm_cand` |

## Volume

| sample | raw | gzip |
|---|---|---|
| Per round (6 games, 9,937 rounds, level 1) | 4.6 KB | 0.46 KB |
| A 528-round game | 3.2 MB | 0.32 MB |
| All 390 games (about 443k rounds) | about 2.0 GB | about 0.2 GB |

Level 2 over a 120-round window adds about 0.5 MB to a game. Run with `--log-limit` raised (the runner passes 1 GiB).

## Lines

### TV: once per champion instance

`TV v=1 bot=hyperion-v38-trace game=<key> c=<id> t=<type> team=<a|b> lvl=<level> win=<R0>-<R1>`

Types are `ryth vesper vendetta cassi issac stellar prism marcella willow ren varg tavi hor`.

### TT: one per champion turn

Printed at the end of `play_turn`, also for a turn abandoned by an exception (`ok=0`, for example a stale turn after running out of fuel). A turn the bot skips before `play_turn` (a stale world update) has none. The ladder's per-turn fuel use (`.fuel`) and the harness's `@o` lines locate those turns.

| field | meaning |
|---|---|
| `r` `c` `t` | round, champion id, type |
| `a` | alive at turn start |
| `p` / `q` | position at turn start / end |
| `hp` / `hq` / `mh` | health at start / end, max health at start |
| `sh=s,e` | shield at start, end (only if any) |
| `g` / `gq` | gems carried at start / end |
| `au` | gold at end (floor) |
| `d` | the turn's branch (`decision` in bot.cpp), see below |
| `dmg` | health lost since the end of our previous turn: what the enemies and camps actually dealt |
| `fg` / `cl` | farm group / claimed group at end (group index, -1 none) |
| `sg` `bk` `cr` | siege, banking (bag headed for an altar), crew (joining an ally's claim) |
| `wa=a:since` | waiting at altar `a` for a safe tribute since that round |
| `st` | stunned at turn start |
| `ch=k:n` / `chq=k:n` | channel at start / end: `rec`, `trib` or `tp`, with turn ends left. A `rec` at start is usually the recall started at the previous turn end, see TA. |
| `cd=a,b` / `cq=a,b` | ability cooldowns (rounds until castable) of slots 0,1 at start / end |
| `wd` | our latest ward |
| `bu` / `vis` | in a bush at start / tiles in this turn's vision (own sight and ward) |
| `fu` | the last `fuel_remaining()` value the bot read this turn: the ladder value, from the recording |
| `nf=a/b` | fight results recorded this turn (distinct kind, tile, key) / simulations actually run |
| `fs` / `fe` | fight sim at the start / end tile as the bot evaluated it (`T`); `none` = no threat reaches the tile; `?` = not evaluated |
| `ls` / `le` | `lethal()` at start / end tile: worst-case damage before our next turn (every credible threat at full damage plus camps); -1 means the cheap bound already proved it below our health |
| `cs` / `ce` | camp damage per camp phase at start / end tile (worst case) |
| `ts` | `threatened()` at start: 1 if the chance of damage before our next turn is at least `recall_risk` |
| `ok=0` | the turn did not complete |
| `mm=n` | harness mismatches so far (never seen in a validated game) |

Prediction versus outcome: `fe`/`le` of turn r, against `dmg` of the champion's next TT, and the replay's damage events.

`d` codes:

| code | branch | code | branch |
|---|---|---|---|
| `-` | none (dead, teleporting, cannot act) | `T` / `t` | tribute kept / cancelled |
| `C` | chase | `K` / `k` | recall kept / cancelled |
| `A` | the strike search attacked | `H` | healing on spawn |
| `R` | retreat | `S` | shopping trip |
| `F` | farm | `P` | holding or contesting a capture |
| `B` | bank (walk to or tribute at an altar) | `Q` | capture recall |
| `W` | wait at an altar | `G` | siege or kite of a big group |
| `X` | contest a capture | `E` | stop a game-ending enemy |

### TB: belief about each enemy, at turn start

Printed after the world update and comms merge: what this turn's decisions used. These are this champion's own beliefs, since vision is per champion.

`TB r c s=e i=<enemy index> h=<handle> t=<type> al=<alive> ...`

| field | meaning |
|---|---|
| `rsp=a-b` | dead: its respawn window |
| `v` | visible now |
| `p` / `pr` / `src` | last known or assumed position, the round of that fix, and its source: `s` seen, `c` comms (a teammate), `i` inferred (spawn, recall arrival), `n` none |
| `hp=h/m` | health as last read / max |
| `sh` | its shield, if any |
| `gm` | gems as last seen |
| `ch=k:end` | believed channel and its end round |
| `rr=a,b` | earliest round each ability slot can be cast (exact while visible, projected through fog) |
| `act` | had acted this round when last read |
| `rsp=now` | respawned this round |
| `tr` | tracked while unseen: `possible` holds every tile it could be on |
| `np` | number of possible tiles (unseen and tracked) |
| `fx` / `tsf` | round of the last exact fix / turns since |
| `bu` | `p` is a bush tile |

Ward and bush blindness: compare TB with the replay's true positions; `v=0` with the truth inside our vision square means bush or wall occlusion. With level 2, `s=a` lines give the same for allies.

### TA: every action call (written by the harness)

`TA r c a=<import> x=<int args> rc=<engine return code, 0 ok> ok=<result through the out-parameter, -1 if none> s=<site>`

| import | `x` |
|---|---|
| `move_to_with_result` | `x,y` |
| `attack` | `kind,target`: kind 1 champion handle, 2 camp handle, 6 altar lock |
| `cast_with_result` | `slot,kind,handle,x,y`: kind 0 = ground or self, then x,y; 1 champion; 2 camp |
| `place_ward_with_result` | `x,y` |
| `submit_gems` | `x,y` (altar) |
| `use_consumable_with_result` | `id,x,y`: lock or crystal |
| `recall`, `cancel_channel` | none |
| `buy_item` | `item,count` |
| `buy_consumable` | `id` |
| `set_priority` | `p` |

`ok=0` with `rc=0` is a hidden blocker: the action failed and revealed the tile.

`s` is the innermost decision site (`TRACE_SITE`) active at the call, the reason code:
- `plan` / `plan_after`: the strike search's plan (TS);
- `farm`, `chase`, `retreat`, `retreat_step`, `flee_camps`, `step_safely`, `carry`, `siege`, `kite`, `contest`, `hold`, `pick_up`, `spell_clear`, `capture_handoff`, `yield_capture`, `hop`;
- `submit` (tribute start), `tribute_keep` and `recall_keep` (their cancels), `recall_start` (the recall started every turn end and cancelled next turn unless wanted);
- `cast_enemies`, `cast_camp`, `cast_camp_approach`;
- `reset_enemy`, `reset_camp`;
- `dash_towards`, `dash_across`, `dash_attack`, `dash_away`;
- `heal`, `shield`, `attack_enemy`, `attack_camp`, `strike_enemy`;
- `ward`, `lock`, `buy`, `buy_lock`, `buy_crystal`, `priority`, `game_ender`, `break_lock`, `act`, `decide`.

### TS: the strike search (plan.cpp), when it ran

`TS r c here=x,y n=<end tiles> pr=<priced> q=<threat queries> cap=<capped> ch=x,y tot raw gain rm kl kp seq done fail alt kill stun`

| field | meaning |
|---|---|
| `ch` | the chosen end tile |
| `tot` | its score in enemy health points: hits' worth plus the goal's progress less the expected damage (`hit_given_reach` × blows) and camps |
| `raw` | the chosen leaf's value before damage |
| `gain` | the goal-walk progress |
| `rm` | plan.cpp's `removed`: hex mask of enemy indices the plan takes out of the end tile's danger, killed (with a Cassi/Issac partner) or stunned with only one turn before ours |
| `kl` | the part of `rm` actually killed (trace-only, from the leaf's dead units) |
| `kp` | cast kept for a shield |
| `seq` | the actions, `\|`-separated: `w` walk, `a` attack, `r` reset, `d` dash, `s<slot>` spell, `h` heal, `sh` shield. Target `:e<handle>` (enemy), `:g<group>.<member>` (camp), `:a<handle>` (ally); tile `@x,y`. |
| `done` / `fail` | actions carried out / plan aborted (a refused action with no alternative) |
| `alt` | up to 3 next-best end tiles, `x,y:total:rm:kl:exact` |
| `kill` | per enemy (handle) that some plan kills: the best such plan's value before damage, and its end tile |
| `stun` | the same for plans that remove the enemy by a stun without killing it |

An enemy in `kill` but not in the chosen `kl` is a kill that was considered and rejected; compare its value with `tot`. `raw`+`gain` is on the same scale.

### TE: decision events

`TE r c k=<kind> ...`

| kind | fields |
|---|---|
| `decide` | `strikes` (an enemy in strike reach), `mend` (healing on spawn), `leave` (want_home said retreat) |
| `home` | want_home: `v` (retreat?); `why` = `low` (health), `outmatched` (a pack zone), `camp` (camps would trap us), `stand_lost` / `stand_falls` / `stand_ok` (the stand fight `t`, with `lethal`, `pursued`, `linked`) |
| `tribute` | continue_tribute: `keep`; `why` = `safe`, `unhurt` (kept), or `hurt` / `home` / `fight` (cancelled); `left` = turn ends left |
| `recall` | continue_recall kept: `why` = `home`, `capture`, `bank`, `shop`, `siege_heal`, `pocket`. `keep=0 why=home_unsafe`: wanted home but cancelled (threatened, a safe tribute here, or enemies would catch it). Other cancels are the routine every-turn one: TA `cancel_channel s=recall_keep`. |
| `carry` | carry_bag: `safe` (tribute safe now), `close` (endgame closing) |
| `prey` | chase candidates, best first: `handle:cost:health` (cost = turns per gem of the kill) |
| `prey_fight` | each candidate's chase fight: `e`, `key` (bits: allies low 16, enemies high 16), `delayed`, `t`, `take` (chased) |
| `ender` | an enemy whose tribute or bag would end the game: `e`, `ch`, `gm` |
| `farm` | farm's choice: `best` group and value `v`, `steps`, `risky`/`rv` (best group too damaging alone), `shared`/`sv`, `help`, `evaluated`, `bank`, `altar_v` |
| `cast` | cast_at_enemies' chosen cast: `slot`, value `v`, `walk` (the walk value it must beat), target `e` or `tile`, `dash` |
| `comms_rx` | merged from a teammate: `what=sight e p at hp` (health share), or `what=capture g respawn` |
| `comms_tx` | what our shared-memory slots hold after posting: `claim`, `bag`, `sight` (enemy index) |
| `sides` (level 2) | each simulated fight's fighters, `us=` and `them=`, each `health/max/shield/strength/arrives_at/ready0,ready1`, plus `first` (`t` they strike first), `camp` (damage per their turn), `self` (our fighter's index) |
| `cast_cand` (level 2) | each unit-target cast candidate: `slot e v thr free hp` |
| `farm_cand` (level 2) | each group farm weighed: `g v steps dmg spare worth cycle` |

### TF, TQ (level 2)

- `TF r c k=<f fight | c chase | s stand> p=x,y key=<hex> new=<1 simulated now, 0 memo> t=<T>`: every fight result.
- `TQ r c q=<lethal|threat|camp|idle> p=x,y v=<value>`: every threat value the bot computed. `idle` is turns for the visible enemies and camps to kill us while we channel.

### Harness lines (`@`)

| line | meaning |
|---|---|
| `@v me seg round calls hash` | each segment (one turn of the instance; `me` -1 is the draft bot) with its host-call count and hash, checked against the recorder's `@y` |
| `@o me seg idx round` | an out-of-fuel point reproduced: the turn ran out before host call `idx` and resumed in `round` |
| `@! fuel me seg idx round` | a fuel read the recording has no value for: divergence |
| `@! yield me seg round calls hash rround rcalls rhash` | a segment whose calls differ from the recorder's |
| `@! round me seg idx now expected` / `@! oof ...` | an unrecorded round change, or a rollover that did not land as recorded |
| `@! tail me seg round` | the instance's final segment, which the game ended in: it has no `@y` to check its calls against (its fuel reads still are). Expected once per instance at game end; not counted as a mismatch. |
| `@! inst me game` | no recorder data for this instance |

### Other lines

- v38's own debug output, unchanged: `D` (round, id, decision, farm group, claim), `SLOT`, `SRCH`, `SRCH-REFUSED`, `SRCH-PASS`, `CHASE-AVAIL`, `FCDELAY`, `FCWINDOW`, `FCPARTNER`, `FPARTIAL`, `FSEED`, `SHORTCUT <round> <id> <what>` (a fuel shortcut taken), `REVEAL`, `DASH-FOLLOW`, `WARM`, `HOPS`, `OOF`, and its checks (`*-MISMATCH`, `REACH-BOUND`).
- Release prints: `rN turn ran out of fuel, finished in rM`, and phase errors.

## Validation

`trace_validation.json` per game, and `runs/batch/trace_validation.json` for all:

| field | meaning |
|---|---|
| `exact_vs_rec` | the trace run's inputs (rollovers included), round-start hashes and result equal the recorder run's, and every segment's host-call count and hash equals the recorder's (`segments_equal` of `segments`) |
| `exact_vs_ladder` | the same against the ladder replay's decoded inputs |
| `ladder_trusted_through` | the last round shared with the ladder, from the recorder's fidelity |
| `rec_trusted_through` | the round before the first mismatch, if not exact |
| `forced_oof` / `rec_oof` | out-of-fuel points reproduced / recorded |
| `rec_x` / `rec_x_first_round` | the recorder's `@x` points (it ran out at its own wrapper's entry check, where the unwrapped bot would not have): the recorder's game is only loosely the ladder's from there, which `ladder_trusted_through` measures |

## Read-only rules followed by the instrumentation

- **Prints.** All output is printed inside `debug_block` with printf.
- **Host calls.** Host calls in debug blocks are not counted or virtualised (the ws SDK's `cambc_debug_depth`). The harness queries the round (`bc_round_number`, which clears the engine's last error) only after a counted call that returned 0, as the recorder does. The trace reads the engine raw into its own buffers, never through the bot's static-scratch helpers (`my_record()` and the like).
- **No stateful evaluators.** It never calls the bot's stateful evaluators: Safety memoises fights and measures their fuel, so a debug call would change later fuel estimates. Values are captured where the bot computes them.
- **Rewritten branches.** Short-circuit conditions logged by reason were split into equivalent sequential `if`s, with the same evaluation order. Multi-return functions (`stand`, `chase_trade`) are wrapped in an immediately invoked lambda.
- **Outside debug blocks.** The only additions outside debug blocks are `TRACE_SITE` scope guards and the TT guard in `play_turn`. They write trace-only globals and make no host calls.
- **Evidence.** The call-hash check is the proof: see `trace_validation.json` per game.

## v47 (`trace-bot-v47`)

`tools/replay/harness/trace-bot-v47/src` is v47 (`git archive f7d54e9e bots/astraeus`: hyperion's machinery plus the Willow layer) with this instrumentation ported, under the same rules. Its lines are the ones above, with these differences:
- `TV bot=astraeus-v47-trace`.
- `TE k=decide` adds `work` (Willow at work: a capture, contest, bank or shop, which skips the strike search).
- `TE k=home why=willow_threat`: Willow, holding no fight, goes home from a likely hit.
- `TE k=support` (Prism and Willow, after `decide`): `local=1` (local_support took the turn), `heal_step=1` (Willow's independent heal step took it), or `local=0 mate retreat` (neither; `retreat=1` sends it to retreat after a heal).
- Decision sites `local_support`, `willow_bank_heal`, `willow_heal_step`.
