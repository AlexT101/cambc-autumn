# Running a draft lab, step by step

How to run the draft lab from scratch, as draft4 was run (2026-11-03: 1.3M games in 1.5 h on the 96-core box).
[README.md](README.md) explains how the lab works; this file is the order of operations. Commands run from the
repository root on the Linux box, `py` = `python3`.

## 1. Settle the decisions with the user first

Ask, and write the answers into the lab's `config.json` (step 6) before `init`. Do not assume last run's.

- **Champion restrictions.** Which champions every team we draft must hold, and which it must never hold. Since
  2026-11-03: always Cassi & Issac, never Stellar (`model.mjs TEAM_LOCK`; a config's `team_lock`, e.g.
  `{"require": ["cassi_and_issac"], "ban": ["stellar"]}`, overrides it). The lock reaches the bot through
  `draft_model.h` (`required`, `banned`), so the C++ needs no change when it moves. Champion names are
  `vehicle.CHAMPS`: ryth, vesper_vale, vendetta, cassi_and_issac, stellar, prism, marcella, willow, ren, varg,
  tavi, heart_of_ruin. Also ask whether opponents' random teams should leave anything out (`explore_exclude`,
  default Stellar).
- **Ladder window** (`patch_since`, ISO time): the opponent prior uses only ranked games from this time on. Ask
  whether it should start at the last balance patch or cover only the last N days. A short window, such as the
  last 3 days, follows a meta shift, for example when one top team starts a draft others copy. It also holds fewer
  games: check the team-games per pick count that `init` prints (draft4 had 3,740 / 4,720 / 12,908 for 3 / 4 / 5
  picks over 3 days). For the last N days, set it to now minus N days, e.g.
  `date -u -d '3 days ago' +%Y-%m-%dT%H:%M`. Step 4's `--since` should be no later than this time.
- **Which bot plays** (`init --source REF`, default HEAD): the astraeus commit the vehicles copy. Its draft model
  (`draft_model.h`'s `--lab`) becomes the "current" team source.
- **Budget**: hours (`run --hours`) and whether other jobs (another agent's A/Bs) will share the box. Fair share
  gives the lab weight 2 (`CAMBC_SLOT_WEIGHT`), so others slow but are never starved.
- Defaults that the user confirmed for draft4 and that need no new question unless they ask: separate models
  for 3, 4 and 5 picks (pooled toward a shared fit), no counter-picks (`initial_lam.ctr` 1e9; the C++ refuses
  counters above 1e-3 unless `cpp --counters`), synergy and all 25 map features on.

## 2. Check the box

```
uptime; ps -eo pid,etime,args | grep -E "[a]b.py|[r]un_batched|[l]ab.py|[c]ambc run-batch" | cut -c1-160
tmux ls
```

Know what else is running before starting (another agent's A/B, an old lab in tmux). Tell the user what you found.

## 3. Free disk space

A run needs about 3 KB a game in `games.jsonl` (1.3M games: 3.9 GB, plus a 6x smaller `games.slim.jsonl`) and
~7 GB of replays per 100k-game batch while it is merged (two batches can be on disk at once). Keep 50 GB free.

```
df -h /
du -sh replays/* | sort -rh | head -25
```

The usual space is replay files of finished A/Bs: `*.repl26a` under `replays/batch-<date>-*` (results are kept
in their other files). Before deleting, check nothing running writes there (step 2), and ask the user about
anything that is not from your own runs. On 2026-11-03 this freed ~394 GB:

```
cd replays && find . -maxdepth 2 -path './batch-20261102-*' -name '*.repl26a' -delete; df -h /
```

Old labs' `replays/draftlab/<lab>/batches/` hold only plans and logs once merged; their vehicles in
`bots/variants/dl-<lab>-*` (~160 MB each) can go once the lab is finished.

## 4. Download the top teams' ladder games

The opponent prior is the top teams' drafts in ranked games since `patch_since` (step 1's window), read from
`replays/ladder/*/group.json` (init leaves our team out, `MY_TEAM`). Drafts need no login:

```
py tools/fetch_replays.py --list                       # the ladder now: rank, rating, team id, name
py tools/fetch_replays.py --top 11 --since 2026-10-31 --kind ranked --max-groups 0 --no-replays --threads 8
```

`--top 11` because we are in the top 10. `--max-groups 0` takes every group since `--since`. The website cookie
(`~/cambc/web-cookie.txt` on Linux, `%APPDATA%/cambc/web-cookie.txt` on Windows: the `Cookie:` header of a
logged-in browser session) is read when present and only adds submission versions; replays themselves (without
`--no-replays`) need `cambc login` and `--threads 1`. To show the user what the top teams draft, summarise the
groups per team as in [ladder-drafts-2026-11-03.md](../../research/ladder-drafts-2026-11-03.md).

## 5. Fresh maps and the fast runner

The pool should be suites no A/B or earlier lab has played. List what exists, pick an unused seed range, and
generate it (256 maps a suite):

```
ls -d maps/fresh-* | sed 's#maps/fresh-##' | sort -n | tr '\n' ' '
node tools/mapgen/mapgen.mjs suite --seed 77000-77195 --out 'maps/fresh-{seed}'
```

Then point `lab.py POOL` (or the config's `pool`) at them and record the seeds in its comment, README's Pool and
research/EXPERIMENTS.md. Keep `holdout` (fresh-9300..9379) out of the pool: those judge the result.

The fast runner (once per box; `lab.py` uses it when built and says which runner in `lab.log`):

```
cd tools/fastengine/runner && ./setup_vendor.sh && cargo build --release && cd -
```

## 6. Create the lab and start it

```
mkdir -p replays/draftlab/draft5
cat > replays/draftlab/draft5/config.json <<'EOF'
{"patch_since": "2026-10-31T00:00", "team_lock": {"require": ["cassi_and_issac"], "ban": ["stellar"]}}
EOF
tmux new -d -s draft5 "cd $PWD && python3 tools/draftlab/lab.py init --lab draft5 --source <sha> 2>&1 | tee replays/draftlab/draft5-init.log && python3 tools/draftlab/lab.py run --lab draft5 --hours 1.5 2>&1 | tee replays/draftlab/draft5-run.log; exec bash"
```

`config.json` holds only what differs from `lab.py DEFAULTS`. `init` (~5 min for 50k maps) freezes the bot, measures every pool map's features and writes the prior; check its
last lines: the ladder group count, the team-games per pick count and the source's draft lab. `run` plays
100k-game batches until the deadline, then a final fit with a penalty search (~10-15 min at 1.3M games).

## 7. Watch it

```
py tools/draftlab/lab.py status --lab draft5
tail -f replays/draftlab/draft5/lab.log           # batches, merges, waits
tail replays/draftlab/draft5/fit.log              # fits, searches, cross-validated log loss
```

Healthy: every merge says `0 errors` and a few dozen draft mismatches in 100k (over 2% stops the run), and
`waited N s for batch b+1's preparation` stays under ~1 min. Batch 1 is planned before any game has finished, so
it is sized on a guessed 0.005 s a game (0.03 on stock cambc). The last batches shrink to fit the deadline.
`run` resumes after a crash: start the same
`run` command again. `report.md` is rewritten after each fit.

## 8. After the run

```
node tools/draftlab/model.mjs gain --lab replays/draftlab/draft5      # predicted win %: current draft vs the model's
node tools/draftlab/model.mjs compare --lab replays/draftlab/draft5 --old replays/draftlab/draft3-cheap/model.json
node tools/draftlab/model.mjs cpp --lab replays/draftlab/draft5       # writes bots/astraeus/src/draft/draft_model.h
node tools/draftlab/native.mjs --lab replays/draftlab/draft5 maps maps/suites/legacy/gen# C++ vs JS parity, no games
py tools/draftlab/parity.py --lab replays/draftlab/draft5 maps --jobs 4           # in-game parity
py tools/draftlab/firstturn.py --sample replays/draftlab/draft5/maps.jsonl   # first-turn fuel, if the header names sight_gap or narrow
```

Then A/B the new header against astraeus without it, both on their own drafts (`--no-test-draft`), on holdout
suites no lab or A/B has played, and confirm on a newly generated suite (AGENTS.md). Of the holdout, 9300..9319
judged draft3, 9340..9379 the emblem A/Bs and 9400..9419 confirmed draft3. Judge a draft on at least 20k games
(40 suites of 256 maps, both sides). draft4 was judged on fresh-9320..9339 and fresh-93000..93019 (CHANGES 297);
fresh-93020..93059 (generated 2026-11-03) are unplayed. Generate new suites for the next lab's judging. Check
`ls -d replays/batch-*` for a suite's name before using it:

```
./copybot -r HEAD astraeus variants/astraeus-before      # before the header change is committed
FAST="CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native"
env $FAST python3 tools/ab.py astraeus variants/astraeus-before --no-test-draft --suites $(echo maps/fresh-93{20..39} maps/fresh-930{00..19} | tr ' ' ,)
env $FAST python3 tools/ab.py astraeus variants/astraeus-before --no-test-draft --suites $(echo maps/fresh-930{20..59} | tr ' ' ,)   # confirm
```

Record the run (games, CV log loss, A/B) in research/EXPERIMENTS.md and, if it ships, CHANGES.md and the
README's Deployment section.
