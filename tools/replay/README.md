# Replay extraction

Decodes `.repl26a` replays (ladder downloads and local `cambc run` / `run_batched.py` output) with the game's own engine and caches compact per-game tables for offline analysis. Node 22+ (tested on 26), no dependencies.

```
node tools/replay/extract.mjs replays/ladder replays/batch-20261013-185810-654911
node tools/replay/extract.mjs <dirs or .repl26a files...> [--threads N] [--force]
node tools/replay/extract.mjs --update-engine
```

- Inputs are searched recursively. Each distinct replay (by sha256) is decoded once, in parallel worker threads, into `replays/.analysis/<first 16 hex of sha256>/`. Cached games are skipped unless `--force`, the extractor version changes or the engine changes.
- Identical replays do occur: the bots and engine are deterministic, so a rematch on the same map can be byte-identical. All copies are listed in `meta.sources`; `index.json` has one row per source file.
- Exit code 1 if any replay fails to decode or fails a hard validation check.
- `--update-engine` starts `cambc view`, downloads the `v0_0_1-*.wasm` the viewer uses into `engine/`, and rewrites `engine/version.json`. If the snapshot layout changed (`Game_Visualiser_SnapshotSize() != 184696`), loading fails and the decoder in `engine.mjs` has to be re-ported from the viewer's `PanelChrome-*.js` (functions `xr`/`br`/`Sr` and table constant `Q`).
- About 1.1 s per game on one thread (39 s for 532 games on 16). About 100 KB per game (gzipped).

## Files

| File | Contents |
| --- | --- |
| `engine.mjs` | WASM wrapper (`Engine`, `Game`), snapshot decoder (`Snapshot`), static map extraction, enums, `mirror`/`ownFrame` helpers, zip unwrapping for local replays. |
| `extract.mjs` | CLI and per-game extraction (`extractGame`). |
| `engine/v0_0_1.wasm`, `engine/version.json` | Engine copy and its provenance (cambc version, asset name, snapshot size, sha256). |

Output, under `replays/.analysis/`:

| Path | Contents |
| --- | --- |
| `index.json` | `{v, games: [{dir, source, kind, map, mapHash, teams, winner, rounds, gems, ok, copies}]}`, one row per source file. |
| `enums.json` | Name tables for every integer code below. |
| `maps/<hash>.json` | Static map, shared by all games on identical maps. |
| `<dir>/meta.json` | Game summary and validation. |
| `<dir>/events.jsonl.gz` | One JSON event per line. |
| `<dir>/rounds.json.gz` | Per-round state, columnar. |

Python: `json.load(gzip.open(p))` for rounds, `[json.loads(l) for l in gzip.open(p, 'rt')]` for events.

## Conventions

- Positions are `[x, y]` tiles, origin bottom-left (as the rules). `null` when dead.
- Teams: `0` = team A, `1` = team B, `2` = none.
- Champion ids are the engine's global ids (team A's picks first; Cassi before Issac, so a team can have 6 bodies).
- Rounds are play rounds `1..N` (the draft is skipped). `s` is the engine step index (counts every step, including draft and ticks), so it orders events exactly. `t` is the champion-turn index within the round, `-1` for round phases (camp respawns, captures, camp attacks).
- Group and camp ids are the engine's in-game ids (each map camp appears twice, as the canonical camp and its mirror).
- Team B's frame: `mirror(map, x, y)` in `engine.mjs` (`horizontal`: `(W-1-x, y)`, `vertical`: `(x, H-1-y)`, `rotational`: `(W-1-x, H-1-y)`) maps any tile to its symmetric tile and back; apply it to team B positions to compare both teams in team A's frame (`ownFrame(map, team, x, y)`).

## meta.json

- `v`, `engine` (version.json), `source`, `sha256`, `sourceKind` (`ladder`, `batch` or `file`), `sources` (every copy: `{source, kind, map, teams, group, matchId, position, problems?}`).
- `map`: `{name, hash, width, height, symmetry}`; `mapFile` is the relative path of the map JSON.
- `teams[0|1]`: ladder `{name, id, ratingBefore}`; batch `{name, bot}` where `bot` is the index into `results.json` `bots` (`-12` files: bot 0 is team A).
- `group`, `matchId`, `position`: ladder group and match.
- `draft`: `{rounds, picks: [[names]...], pickIds}` (ids index `enums.draftChampions`, `-1` = unused round).
- `champions[]`: `{id, team, type, name, draftOrder, maxHp, kills, deaths, assists, earnedGold, gold, gems, stats}` at the end; `stats` is the engine's end-of-game statistics (`Game_Statistics_GetChampion`, identical to the ladder's `group.json`): kills, deaths, assists, earnedGold, spentGold, collectedGems, submittedGems, championDamageDone/Taken, monsterDamageDone/Taken, healingDone, shieldingDone, itemsBought (pairs), consumablesBought.
- `result`: `{winner (0/1), outcome (engine: 1 = A, 2 = B), rounds, gems: [A, B], steps}`.
- `faults`: first two bytes of the engine summary, believed to be per-team bot faults (always 0 so far; unverified).
- `validation`: `{ok, hard[], soft[]}`. Hard: final round, tributed gems, winner and each champion's type, kills, deaths, assists, earned gold and engine statistics against `group.json` (or round and winner against `results.json`), plus derived death events against the engine's death counts. Soft (informational): derived kills, tributes, damage and gold against the engine statistics.
- `counts`: events per kind; `ms`: extraction time.

## maps/&lt;hash&gt;.json

`{hash, width, height, symmetry, champsPerTeam, spawn: [A, B] ({minX, minY, maxX, maxY}, inclusive), walls, holes, bushes, altars (tile lists), camps, groups}`

- `camps[i]`: `{id, type (Wolf, Elk, Gem cluster, Gold cluster, Monolith), x, y, group, hp}`.
- `groups[g]`: `{id, camps (camp ids), tiles (capture tiles), types, gems, gold, respawn (group reward and respawn rounds), mirror (symmetric group id), side (0/1: nearer team A/B spawn, -1 equidistant)}`.

## events.jsonl.gz

Every event has `s`, `r`, `t`, `k` (kind). `a` is the acting champion. Damage lists are `[[id, amount]]`, amounts after shields (hp lost plus shield absorbed). Events of one step are written in this order: the action, channel ends, deaths, camp deaths, group changes.

| `k` | Fields |
| --- | --- |
| `move` | `a, f, to` (a walk; dashes are `cast` and recall arrival is `recall_end`) |
| `blocked` | `a, f, to`: walk onto a tile holding an unseen unit |
| `attack` | `a, f, to`, target `tgt` (champion) / `camp` / `lock: 1` (altar), `hits` (lock hits remaining after), `dmg`, `cdmg` (camps), `refl` + `reflBy` (damage reflected to the attacker by Ren), `heal`, `shield`, `stun` (ids newly stunned) |
| `cast` | as `attack` plus `slot`, `ab` (ability type name), `moved` (new position after a dash); `f` is the caster's tile, `to` the target tile |
| `camp_attack` | `camp, g, tgt, dmg`; `xdmg` other champions hit; `refl` `[[camp, amount]]` Ren's reflection |
| `death` | `v` victim, `at`, `gems` (bag at death), `hp` (before the step), `by` killer id or `camp`, `gold` and `gemsTo` (killer's gain), `assists`, `cause` (step kind), `linked` (set on the Cassi/Issac body that died because its partner did; its value is the partner) |
| `respawn` | `a, at` |
| `shop`, `sell`, `consumable` | `a, gold` (change), `items` / `cons` (`{name: delta}`; emblem combines show as -5 shards +1 emblem), `to` (consumable target) |
| `ward` | `a, to` |
| `recall_start` | `a, gems, at` |
| `recall_end` | `a, gems, f, to` |
| `recall_cancel`, `tribute_cancel`, `teleport_cancel` | `a, gems, cause` (`damage`, `stun`, `death`, `manual`, `lock`, or a step kind), `left` (channel turns left) |
| `tribute_start` | `a, altar, gems, dur` (channel turn ends), `at` |
| `tribute_end` | `a, gems, total` (team total after) |
| `tribute_blocked` | `a, altar, gems`: submit at an enemy-locked altar (counts as a lock hit) |
| `lock_place` | `a, team, to` |
| `lock_destroyed` | `team, at` (detected at the next lock read: lock attacks, tributes, lock placements and round ends) |
| `teleport_start`, `teleport_end` | `a, f?, to` |
| `camp_death` | `camp, g, by` |
| `group_clear` | `g, by`: last monster died |
| `capture_hold` | `g, team, timer`: a team started holding the empty group (paid when the timer runs out) |
| `capture_reset` | `g, team, left, contested`: progress lost the moment the tiles become empty (or `contested` by both teams), usually mid-turn; the next `capture_hold` restarts the timer |
| `capture_flip` | `g, team, from` |
| `capture` | `g, team, shares: [[id, gems, gold]]` |
| `group_respawn` | `g` |
| `group_wake`, `group_sleep` | `g`, `by` (wake) |
| `resign`, `sandbox`, `other_dmg` | rare; `other_dmg` holds hp loss outside attacks and casts (none seen so far) |

## rounds.json.gz

State at the end of each round (read at the first step of the next round; the last entry is the final state).

- `round[i]`: round number; every per-round array below is indexed by `i`.
- `gems: [A[], B[]]`: tributed gems.
- `champions[]` (same order as `meta.champions`), `{id, team}` plus arrays: `x, y, hp, maxHp, alive (0/1), respawn` (rounds left while dead), `gold` (floor), `earned` (lifetime gold), `gems` (carried), `chan` (`enums.channels`: 1 recall, 2 tribute, 3 teleport), `chanT` (turns left), `cd0, cd1` (cooldowns), `str, foc` (effective Strength and Focus), `shield` (shield amount), `stun` (stun turns), `items` (flat `[itemId, count, ...]`, `enums.items`), `cons` (`[teleport crystal, control ward, altar lock, TP scroll]` carried), `kills, deaths, assists, prio` (priority), `ward` (`[charges, recharge]` or null), and:
  - `turn`: what the champion did with its turn this round: 0 no turn, 1 acted, 2 idle (alive, nothing done), 3 channelling, 4 dead, 5 stunned, 6 fuel exhausted (turn rollover).
  - `sees`: enemy champion ids this champion could see (its own view and ward, as its bot sees it) at the start of its turn this round.
  - `seenBy`: enemy champion ids that saw this champion at the start of their turns this round (empty = unseen by the enemy team).
- `groups`: change rows `[round, group, state, team, timer, respawn, awake, hp]` (`groupCols`), written only when a group's row changes, so forward-fill per group. `state` indexes `enums.groupStates` (1 monsters up, 2 cleared and claimable, 3 respawning); `team`/`timer` capture holder and rounds left; `respawn` rounds until respawn; `awake` -1 no living monster, 0 asleep, 1 awake; `hp` living monsters' total.
- `wards[i]`: `[[owner, team, x, y, disabled]]`; `controlWards[i]`: `[[owner, team, x, y, timer]]`; `locks[i]`: `[[team, x, y, hitsLeft]]`.

## How values are derived

The walker reads the omniscient (observer) snapshot after every engine step and diffs consecutive snapshots: damage is hp (plus shield) lost by enemy units during the actor's attack or cast; kills are attributed from the engine's kill counters; captures from group state changes; tributes and recalls from the champion's channel. Vision reads the snapshot once per champion turn from that champion's perspective (`known & 1` on enemy entries), which is exactly the engine's fog of war.

Derived damage agrees with the engine's statistics to within 2% for all but 5 champions in 532 games; those differ by about 100 when both Cassi and Issac take damage in the step that kills them, where the split between the two bodies is a guess. Engine statistics are only available at the end of a replay, so per-step damage comes from the diff.

## Analysis (analyze.py)

Offline reports over the extracted tables: Markdown plus CSVs, no viewer. Python 3.14, standard library only.

```
py tools/replay/analyze.py                                    # ladder (replays/ladder), default reports
py tools/replay/analyze.py replays/batch-X --vs replays/ladder --team aphelios   # adds the gap report
py tools/replay/analyze.py [SOURCES...] [--vs SOURCES...] [--team NAME] [--map NAME] [--since ISO] [--out DIR] [--reports tempo,fights,audits,draft,economy,camps,gap,sensitivity] [--threads N]
```

- SOURCES and `--vs` are replay dirs or files (or analysis dir names), resolved through `index.json`; run `extract.mjs` on them first. Copies count once.
- `--team` keeps that team's side of each game (and only its games); `--map` filters games; `--since 2026-10-13T22:00` keeps ladder groups created from then on. Bots change version during the competition and replays carry no version (`group.json` `submissionId`/`version` are null), so use `--since` to look at current bots.
- Output: `replays/.analysis/reports/<timestamp>/` with `<report>.md`, `<report>-<table>.csv` and `summary.md` (highlights from each report). Every flagged item cites `<game dir> r<round>`.
- Runtime on 16 processes: about 12 s for the 514 ladder games (4 s extraction, the rest mostly the fight-model bootstrap); `sensitivity` adds about 30 s.
- Constants (fight radius and gap, sight window, bag and bank thresholds, lead buckets, early window, bootstrap size) are in `analysis/params.py`; `sensitivity` reruns the headline numbers at the lower and upper values listed there.

Statistics:

- Games are not independent (a ladder group is five games of the same two bots, bots are deterministic, teams meet repeatedly). CIs are 95% cluster bootstraps (1000 resamples, fixed seed) over match groups: a ladder group is one cluster, a local batch map pair is one cluster. `c=` is the number of clusters.
- Winner-vs-loser comparisons are pooled ("winners"/"losers" are the sides that won or lost their game) or paired within a game ("same game"). They partly reflect winning (reverse causality); the audits report also compares rounds 1-150 behaviour within the same gem-lead bucket at round 150.
- Fights are judged by net swing: gems taken from kills - own bags lost (kills and camp deaths) + 0.25 x kill gold. Predictors use start-of-fight state only, univariately and in a ridge logistic regression on standardized differences with cluster-bootstrap CIs.

| Report | Contents |
| --- | --- |
| `tempo` | Game length; opening routes (groups cleared in rounds 1-150, own frame); first clear/capture/tribute; gems per 100 rounds, tributed vs carried over time; win rate by tributed-gem lead at rounds 100/200/300/500; gold earned/spent/banked; shard build order by champion and opening family by team. |
| `fights` | Engagements (champion damage instances sharing a champion within 3 rounds and 16 tiles, or within 1 round and 8 tiles; clusters over 25 rounds split at quiet rounds) with start state, kills, bags lost, net swing, location, initiator; predictors and the logistic model; death risk per 1000 champion-rounds by gem bucket and recent enemy sight, with ASCII heatmaps per map; time, unseen share, tribute and ward heatmaps; altar usage; bushes. |
| `audits` | Suspicious decisions ranked by team, with mean opponent rating, opponents' win rate and the rate against top teams only: large-bag deaths (with recall/altar plausibility), camp deaths and lost gems, camp damage ratio, dead time, recall/tribute cancels by cause, capture resets (walked off, contested, died) and stolen groups, idle turns, unspent gold, casts that hit nothing, out-of-fuel turns; plus the early-window, lead-conditioned comparison. With `--vs`, rankings include the comparison teams. |
| `draft` | Pick and non-mirror win rates (overall and per map), compositions, top teams' usage, per-champion engine statistics per 100 rounds. |
| `economy` | Rounds 1-300 economy of the focus team against its opponents and the --vs sets (all, winners, top 10 by win rate, their wins, low camp-ratio winners): camp DPS per map/preset and champion, camp damage taken/dealt by group type, victim activity and attackers, against the basic-attack minimum; time budget; capture sharing, bags, altar-trip overhead, captured-gem mix; shard mix; recalls and the recall-loop check (must stay 0). Cached in `replays/.analysis/cache/economy/`. The ladder only plays its 9 maps, so judge generated maps against `opponents`. |
| `camps` | Static camp-group values for each map in the sources (from the extracted map files): hp, Strength, gems, gold, respawn, walk from spawn and from the altar, clear time and minimum damage for the Strengths in `params.py` (`camp_strength`), gems per 1k hp, per effort and per farm-and-tribute cycle. |
| `gap` | Only with `--team` and `--vs`: every per-side metric (tempo, fights, audits, economy) for the focus team against the comparison set and its game winners, per map and pooled, ranked by a robust z score; opponent-dependent metrics are flagged. |
| `sensitivity` | Opt-in: headline numbers at a lower and higher value of each key constant. |

Conventions: positions and camp groups are in each team's own frame (team B mirrored onto A); group labels are `<types>(x,y)<o|m|e>` (W wolf, E elk, G gem, $ gold, M monolith; own/middle/enemy half).

For ad-hoc scripts, `tools/replay/analysis/data.py` has the loaders: `resolve(sources)` gives analysis dirs, `Game(dir)` exposes `meta`, `map` (`Map`: `own(team, p)`, `own_group(team, g)`, `group_label`, `cell_of`, altars, bushes), lazily loaded `events` and `rounds`, `ch(id)` (per-round arrays), `champ_damage`, `camp_damage`, `deaths` and `seen_recently`. Each report module's `extract(game, params)` returns its per-game features. Run with `sys.path.insert(0, 'tools/replay')` and `from analysis import Game, resolve`.
