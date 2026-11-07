# Combat lab

2026-11-07. Play very many isolated fights (a few champions, a few to ~30 rounds) to improve ocean's combat
logic, then port what is learned into ocean and judge it with `ab.py` on full games.

## Why a dedicated runner

- The native engine inside cambc (what fastrunner drives) exports only the runner's API: no sandbox, no replay
  loading, no way to copy game state.
- The viewer's WASM build of the same engine (`tools/replay/engine/v3_0_0.wasm`, cambc 5.0.0) exports
  `Game_Sandbox_{Teleport,Damage,Buff,GiveGold,GiveGems,RespawnGroup,CampAttack,CampCast}` and the timeline API, and
  all its state is its linear memory.
- Measured (scratchpad prototype, wasm2c + clang -O2, 2026-11-07):

  | | |
  |---|---|
  | instantiate + load map + draft | 0.5 ms |
  | engine state (100x100 map) | 1.8 MB |
  | snapshot restore (memcpy) | 0.043 ms |
  | engine champion turn of random play | 5.6 us |
  | replay from a snapshot | deterministic (identical memory hash) |

- For comparison, a full ocean champion turn under native fastrunner costs ~29 us (one 840-round game: 10,084
  turns in 0.295 s, 63k fuel a turn on average). The engine is not the bottleneck; the bots are.
- The other route, `fork()` of a fastrunner process at a real frame, costs 32-40 ms a fork at a game's ~600 MB
  resident: 5-10x a rollout. The dedicated runner avoids it.

## Architecture

1. **Engine backend** (in progress): fastrunner with the wasm2c engine in place of cambc's native one
   (`FASTRUNNER_ENGINE=wasm`), bots and import layer unchanged (native mode, exact fuel). Accepted only when full
   games' bundles are byte-identical to the default backend's.
2. **Scenario layer**: a fastrunner subcommand that builds a scenario from a spec (below), snapshots the engine at
   the fight's first round, and plays rollouts from the snapshot with fresh bot instances for the fighters only.
3. **Frame bank**: fight starts taken from games of our own bots (ocean and astraeus variants, own / ladder / test
   drafts; never fish), written as scenario specs.
4. **Lab ocean**: a copy of ocean with a control block the runner reads and writes in the bot's memory (forced
   alternatives, logged candidates, patchable constants). Economy logic is kept by default, so lab behaviour is
   ocean's; a switch can stub it.
5. **Learning**: rollout values of alternatives at a decision (policy improvement over ocean), distilled into C++
   scoring terms; SPSA of combat constants on the lab reward. Judged by `ab.py` (20k games) before shipping.

## Opponents

Only ocean and astraeus variants (frozen copies in `bots/variants/`, baselines), on their own drafts, ladder
drafts or test drafts. Not fish (it plays poorly).

## Scenario setup (how each piece of state is set)

| state | how |
|---|---|
| picks | the runner makes them (`Game_Action_Draft`); draft bots' plans run with the picks substituted, cached per (map, team, picks) and written directly afterwards |
| items | round 1, on spawn: `GiveGold` then `BuyItem` |
| round | idle rounds (no bots run) until the frame's round; cheap, and amortised by the snapshot |
| position | `Sandbox_Teleport` |
| health | `Sandbox_Damage` to the target (read back and corrected: emblems change damage taken) |
| stun, shield, enhanced attack | `Sandbox_Buff(entity, type 1/0/2, turns, amount)` |
| gems, gold | `GiveGems`, `GiveGold` |
| cooldowns | written into engine memory: cooldown of champion c, slot s is the u32 at `base + 72 c + 8 s` (counts down to 0, as the API reads it); `base` moves with the map, so it is found per scenario by one calibration cast in a throwaway copy of the engine and a memory diff |
| camps | `Sandbox_Damage` on camp entities (kind 2), `RespawnGroup` |
| champions outside the fight | left on their spawn, their bots not run |

- Sandbox edits are refused except at an input boundary (a champion's turn, awaiting input: "Sandbox edits require
  an input boundary"). Edits go at the last champion turn of round `round - 1`, then that turn ends unplayed, so
  the round-start phases (camp respawns, captures, camp attacks) follow as in the real game. That champion's turn end
  ticks its cooldowns and buffs, so they are set one higher.
- Measured: 5 shards bought on spawn in round 1 (150 gold given): health 1700 as expected; 300 idle rounds 1.8 ms;
  health set exactly in one corrected step under Durability's -10%.

Not settable yet: tributed gem totals, channels in progress (recall, tribute, teleport), the exact respawn timer of a
dead champion, wards (placeable by the runner as the champion), altar locks.

## Lab ocean: the control block

The lab's ocean is frozen at `bots/baselines/v83` (tracked; ocean at commit 3642f1dff = ladder submission v83,
identical to oc-base17, `test_draft` off; `bots/variants/oc-lab-3642f1d` is the same, untracked), so a teammate's change to `bots/ocean` cannot move it. Lab copies, baselines and the port back
all start from it; anything learned is re-checked against the then-current ocean before shipping.

Hooks go into a copy of ocean made by a script (like `research/diana-2026-11-03/tunify.py`), never into ocean
itself, so ocean's release build is untouched. Economy logic stays on (agreed 2026-11-07): a fighter walking off
to farm is ocean's real disengage.

- A global behind a 16-byte magic, found by the runner in the bot's linear memory (data segments are copied
  verbatim), read and written by the runner between turns: no fuel cost to the bot.
- Out (bot to runner): each decision's branch (strike search, chase, retreat, ...), `want_home`'s verdict and
  `stand_lost_at`'s prediction, the strike search's chosen candidate (end tile, entry, removed set, cast kept or
  spent) with its score parts (hit value, danger, cast price, progress), and how many candidates were priced exactly.
- In (runner to bot): a ban list for the strike search and forced verdicts for `want_home` / chase at a given
  champion turn. The search is branch-and-bound (`plan_strikes` prices end tiles best bound first), so there is no
  ranked list to read; but rollouts are deterministic, so rollout k bans the choices rollouts 1..k-1 made at the same
  decision and the search returns its k-th best. Alternatives come in ocean's own order.

## Scenario spec (JSON, one per line in a `.jsonl`)

```
{
  "id": "frame id (source game + round)",
  "source": {"replay": "...", "round": 312},
  "map": "maps/00ambush.map26a",          // path to the map file
  "picks": [[draft ids, team A, pick order], [team B]],   // enums.draftChampions ids
  "round": 312,                            // the fight starts at the beginning of this round
  "champions": [                           // every body, by engine id
    {"id": 0, "team": 0, "alive": true, "x": 40, "y": 51, "hp": 812.5, "gold": 37, "gems": 12,
     "items": {"<item id>": count}, "cons": [crystal, control ward, lock, scroll],
     "cd": [3, 0], "stun": 0, "shield": {"amount": 0, "turns": 0}, "respawn": 0, "fighter": true}
  ],
  "camps": [{"id": 12, "alive": true, "hp": 900, "awake": false}],   // camps within the fight zone
  "fight": {"zone": [x0, y0, x1, y1], "kind": "1v1|2v1|2v2|...", "initiator": 0}
}
```

State is the end of round `round - 1` as the replay records it (`rounds.json.gz` of `tools/replay/extract.mjs`).
