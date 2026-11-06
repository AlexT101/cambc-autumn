# Live-ladder scrims (2026-11-06)

Unranked match groups on the live platform against chosen teams, maps and sides, as a testing axis beside local
A/Bs. The user: "I don't care which submission is up or what our rating is ... maximise data we get." Most of the
budget goes on the two strongest teams, Intercontinental Fish and Mite, on a frozen set of maps and sides
([SET.md](SET.md)), so every version of ours is measured on the same games against the same opponent bots.

## Mechanism

- `cambc match-groups create <team id> --maps <five map names or ids> --sides a,b,a,b,a [--source-group <group>]`
  queues one unranked group of five games against that team's live bot (CLI 5.0.0). The five maps must be
  **different** (HTTP 400 otherwise). `--side`/`--sides` choose our side per game. `--source-group` plays the
  opponent's bot from an earlier group instead of its live one (patch notes, CLI 4.0.0): this pins opponent versions.
- Our side plays our **live** submission (`cambc submissions list`: "Live: N"). `cambc submit` puts the team in
  "follow newest ready version" mode, so any submission (ours or another agent's) becomes live once built (~5 min
  queue for v78). `cambc submissions activate N` pins one.
- Results: `cambc match-groups show <group> --json` (each game's map, side, result, end reason, drafts).
  `cambc matches download <match>` gives the bundle (replay.repl26a, team-?.stdout/debug and our `.fuel` profile),
  `cambc matches summary <match>` the binary match summary, which `cambc summary FILE` turns into JSON locally
  (rounds, seed, tributed gems per side, per-champion gold, kills, damage timelines). The web cookie that shows
  submission versions in the API (`~/cambc/web-cookie.txt`) has expired; we record our version at queue time instead.
  big-arm's capture was not needed (the CLI gives everything for our own games) and was not touched.
- Unranked groups do not move the rating. Other teams' scrims against us arrive in the same list (we are side B in
  most of them); they spend their quota, not ours.

## Limits

- **Quota: 50 groups (250 games) in a rolling hour, shared by the team.** `cambc match-groups quota --json` gives
  `limit`, `used` and `resetsAt`; each group frees exactly one hour after it was queued (measured: 23 used fell to 6
  at 05:00:52-05:01:15 as the 04:00:52-04:01:15 groups aged out). `maxRankGap` is null: any team may be challenged.
  `opponentRanks` lists 843 teams.
- The CLI answers rate limits with "retry after N seconds"; the downloads rate-limit bursts (3 s between calls).
- No other documented limits on scrims (docs mirror, patch notes). The job stays well inside: at most 38 groups an
  hour (a reserve of 12 is kept free), one create per 75 s, at most 6 in flight, back-off on every error.
- A group plays in about 2 minutes on the server (five games in parallel), so the quota, not the server, limits us.

## Determinism

**Live games are deterministic.** Repeating the first Fish and Mite groups with the opponent pinned reproduced all
ten games exactly: same result, rounds, tributed gems, kills and match seed. So one round of the set per (our
version, opponent bot) is all the information there is; repeats only cost quota. Differences between our versions
on the set are exact paired flips, not noise; the noise is which maps and sides the set contains.

## Data flow

The job is `tools/ladder_scrims.py` (commands in its docstring). State is append-only jsonl in `data/`:

| file | what |
|---|---|
| `set-v1.json` | the frozen set (core 40 maps, ext 88 maps, platform ids) |
| `tasks.jsonl` | planned groups: our version, opponent, five (map, side) games, pin, priority |
| `events.jsonl` | `created` (group id, live version at queue time, source group, quota used, `is_ref`), `finished`, `dropped` |
| `games.jsonl` | one row per game: version, opponent, map, side, result, end reason, rounds, tributed gems both sides, kills, earned gold, both drafts, seed, engine, group and match ids, replay path |
| `run.log` | the job's log |

Replays and summaries: `replays/ladder-scrims/<group id>/<position>-<map>.{zip,summary.bin}` (gitignored, ~150 KB
a game).

## The job

```
setsid nohup /home/ubuntu/venv/bin/python tools/ladder_scrims.py run >> research/ladder-scrims-2026-11-06/data/run.log 2>&1 < /dev/null &
py tools/ladder_scrims.py status                 # progress, refs, quota, live version
py tools/ladder_scrims.py report --by side,map   # win rates with Wilson 95% CIs
py tools/ladder_scrims.py pair 78 79             # paired flips between two of our versions on the same games
touch research/ladder-scrims-2026-11-06/data/STOP   # stop cleanly (delete the file before restarting)
```

- Resumable: on restart it polls the groups still in flight and queues what is pending. A lock file stops a second
  copy. It exits after 8 errors in a row (back-off 1, 2, 4 ... 30 min); a create the server refuses with HTTP 400
  is dropped and logged instead.
- It never switches the submission: a task runs only while its version is live, so a submission switch pauses the
  other version's tasks. Our version is recorded at queue time (the `live` field); if anyone switches the live
  submission while groups are in flight, those groups' version is uncertain (check the times in `events.jsonl`
  against `cambc submissions list`).
- **A/B between our versions:** submit (or activate) version N, then `plan --version N --sets core --opps fish,mite
  --priority 100` (priority >= 100 may use the reserve) and `--sets ext`. Each version's core takes ~25 minutes of
  quota, core + ext ~3 hours. Then `pair OLD N`. Alternating submissions works because tasks wait for their version.

## Throughput and plan

- Measured: 34 groups (170 games) from 04:54 to 05:51, i.e. **~36 groups = 180 games an hour, ~4,300 games a day**
  while tasks are pending. The cap is the job's reserve (38 of 50 per rolling hour) and its 75 s pace; a group's
  collection (10 downloads) takes ~1 minute. The other 12 groups an hour stay free for a new version's
  `--priority 100` tasks or other agents.
- v78's plan (154 groups): core vs Fish and Mite (done), the determinism repeats (done), calibration core one side
  per map vs Vvvvv and Ad Astra (priority 40), ext vs Fish and Mite (30), calibration vs NEETCoders (20), then the
  other side of core vs Vvvvv, Ad Astra and NEETCoders (10). At ~36 an hour it ends about 09:15 UTC; the job then
  idles and checks for new tasks every 5 minutes.

## Opponents (2026-11-06 05:00 UTC)

Ladder ratings at 05:00; champion shares from each team's last 40 ranked games; we were #3-4 at ~2560.

| # | team | rating | record | last 40 | champions (share of games) | commonest team |
|---|---|---|---|---|---|---|
| 1 | Intercontinental Fish | 2722 | 2406-732 | 29-11 | C&I 97%, HoR 92%, Marcella 75%, Vendetta 72%, Willow 60%, Vesper 35% | C&I + HoR + Marcella + Vendetta + Willow |
| 2 | Mite | 2710 | 2073-1256 | 27-13 | C&I 97%, Vendetta 92%, HoR 87%, Vesper 82%, Tavi 67%, Marcella 17% | C&I + HoR + Tavi + Vendetta + Vesper |
| 4 | Vvvvv @ 2FA (Univardisty) | 2570 | 1785-1537 | 27-13 | HoR 100%, Varg 72%, Ryth 70%, Marcella 67%, C&I 45%, Willow 42% | C&I + HoR + Ryth + Varg + Willow |
| 5 | Ad Astra | 2502 | 1527-1416 | 19-21 | Vesper 100%, HoR 95%, Marcella 80%, Ren 52%, C&I 37%, Willow 30% | HoR + Marcella + Ren + Vesper + Willow |
| 6 | BattleCats | 2474 | 1449-1425 | 16-24 | Marcella 97%, HoR 90%, Vendetta 82%, Ryth 55%, Varg 47%, Prism 35% | HoR + Marcella + Ryth + Varg + Vendetta |
| 7 | NEETCoders | 2460 | 1651-1696 | 10-30 | HoR 90%, Vendetta 90%, Vesper 77%, Marcella 77%, Ryth 37%, C&I 27% | HoR + Marcella + Ryth + Vendetta + Vesper |
| 8 | test4 | 2440 | 1096-1117 | 17-23 | Marcella 100%, C&I 100%, HoR 82%, Willow 82%, Vesper 75% | C&I + HoR + Marcella + Vesper + Willow |
| 9 | subscribe to caterpillow | 2439 | 1147-1091 | 20-20 | HoR, Vendetta, Marcella 100%, Vesper 87%, C&I 70% | C&I + HoR + Marcella + Vendetta + Vesper |
| 10 | print dont int | 2425 | 1528-1579 | 21-19 | HoR, Marcella 100%, Willow 75%, Vendetta 75%, Ryth 52% | HoR + Marcella + Ryth + Vendetta + Willow |
| 11 | Trzy Kwaterki | 2409 | 1671-1685 | 18-22 | Marcella, Vesper 100%, HoR 97%, Vendetta 62%, Ryth 42% | HoR + Marcella + Ryth + Vendetta + Vesper |
| 12 | Nyx | 2389 | 1648-1599 | 20-20 | Vesper, HoR, Vendetta 100%, Marcella 80%, C&I 40% | C&I + HoR + Marcella + Vendetta + Vesper |
| 13 | Sponge (Albert and Bob) | 2382 | 1539-1537 | 23-17 | HoR, Vesper, Marcella 100%, Ryth 80%, C&I 57% | C&I + HoR + Marcella + Ryth + Vesper |
| 14 | T1 | 2376 | 1620-1649 | 18-22 | Vesper, HoR 100%, Marcella 95%, Vendetta 57%, Willow 32% | HoR + Marcella + Vendetta + Vesper + Willow |
| 15 | policy wonk | 2358 | 1222-1236 | 23-17 | HoR 100%, Marcella 87%, Vendetta 57%, Tavi 52%, Ren 50% | HoR + Marcella + Ren + Tavi + Willow |
| 16 | Supaswag | 2347 | 1282-1239 | 18-22 | Marcella, Vendetta, Vesper 100%, Willow 67%, HoR 57% | HoR + Marcella + Vendetta + Vesper + Willow |
| 17 | Team Kungarna | 2338 | 1687-1615 | 20-20 | Marcella 100%, HoR 97%, Ryth 72%, Vendetta 65%, Prism 52% | HoR + Marcella + Prism + Ryth + Vendetta |
| 18 | German Empire | 2336 | 1617-1552 | 21-19 | Vesper 100%, Marcella 85%, Vendetta 77%, Tavi 75%, HoR 65% | HoR + Marcella + Tavi + Vendetta + Vesper |
| 19 | Nanyang Technological University | 2326 | 1705-1618 | 21-19 | Vesper, HoR, C&I 100%, Vendetta 82%, Marcella 37% | C&I + HoR + Marcella + Vendetta + Vesper |
| 20 | Noobot | 2317 | 1322-1262 | 20-20 | Marcella, Vesper, Ryth 100%, Willow 92%, HoR 65% | HoR + Marcella + Ryth + Vesper + Willow |

The map pool is the 128 published maps for everyone (ranked groups draw from it); there is no per-team pool.
Fish and Mite over their last 100 ranked games (01:30-04:40 UTC): Fish 72-28, Mite 75-25. Our ranked record against
them over 01:40-04:50 (live v75, "stellar best girl (troll bot)"): Fish 3-12, Mite 4-16.

## Submissions

- **v78** = `bots/ocean` = `bots/variants/oc-retest-clean` (HER: CHANGES 419-421 on oc-base4, which has 416 and 422;
  `test_draft` off), source tree hash 662c6f649702 (sha256 of the sorted src file hashes), repo HEAD fbfb51d8,
  submitted 04:46 UTC, live 04:51. Before it, v75 ("stellar best girl (troll bot)") was live, not v77.

## Results: v78 (HER) on the core set (2026-11-06 04:54-05:51 UTC)

160 games, both sides of 40 maps against each of Fish and Mite, opponents pinned to refs r1 (Fish `01a1af35`, Mite
`01a1af36`). Wilson 95% CIs. Live with `py tools/ladder_scrims.py report --by side,picks,map`.

| opponent | all | side A | side B | 3 picks | 4 picks | 5 picks |
|---|---|---|---|---|---|---|
| Intercontinental Fish | **40-40, 50.0% (39.3-60.7)** | 21-19 | 19-21 | 11-7 | 7-11 | 22-22 |
| Mite | **47-33, 58.8% (47.8-68.9)** | 24-16 | 23-17 | 10-8 | 9-9 | 28-16 |

By map style (both sides): one-altar maps Fish 18/28, Mite 17/28; multi-altar Fish 22/52, Mite 30/52; Monolith maps
Fish 16/26, Mite 19/26, others 24/54 and 28/54; maps of 70x70 or more Fish 6/16, Mite 12/16. Lost on both sides to
both: 00lanes, 00quarry, 02the_pack. Won on both sides against both: 03the_front, 03one_gem, 03twisty,
00breadcrumbs. 92% of games end on 1000 gems; the rest on the round-2000 tiebreak, which we won 7 of 8.

**Against local predictions** (`compare_local.py`; local = v78's frozen copy `variants/oc-retest-clean` on the 128
ladder maps, both sides, own drafts, fast runner; on these same 80 map-sides):

| local opponent | local, all 256 | local, these 80 | live Fish | live Mite |
|---|---|---|---|---|
| `variants/astraeus-now-1106` | 56.2% | 57.5% | 50.0% | 58.8% |
| `variants/panel-proteus` | 62.9% | 68.8% | | |
| `variants/panel-demeter` | 66.8% | 66.2% | | |
| `variants/astraeus-now-1105` | 62.9% | | | |
| `variants/panel-ocean-td` (ladder compositions) | 84.0% | 80.0% | | |

- Mite plays HER about as well as astraeus-now-1106 does (58.8% live against 57.5% local); Fish ~7 points better
  (50.0%). Both are far stronger than the rest of the panel (proteus, demeter, ocean-td read 66-80% on the same
  games): the panel overrates us against the top two by 8-30 points. astraeus-now-1106 is the only panel member
  near their level.
- Per-map agreement with local is nil: the correlation of per-map scores (wins over the two sides) between live and
  local-vs-astraeus-now-1106 is +0.12 (Fish) and +0.16 (Mite), and -0.2 to +0.2 for the other panel members. Local
  map-level weak spots do not predict live ones (each cell is only two games, so this is weak evidence).
- For contrast, our ranked record against them 01:40-04:50 UTC with v75 (the "troll" bot) live: Fish 3-12, Mite 4-16.
