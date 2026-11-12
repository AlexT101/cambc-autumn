#!/bin/bash
# round_emb.sh ROUND_DIR: emblem lab round 5's edit lab (tools/emblab README "Round 5", EXPERIMENTS "Emblem lab round
# 5") on the round's base: the same library (331 edits, rebuilt on the base), screen (six rank cuts) and replication
# (the 20 survivors on new games to n_eff 150k each), against a second lab team (0.5) and the gate's Fish and Mite
# bodies at noise seeds 952 and 953 by default (~/tmp-offload/labs/EMB_OPPONENTS.json overrides). Round 5's calibration is replaced by one warm batch at equal
# shares. Candidate: the replicated edits at +0.25 points and z >= 2 (round 5's shipped set: one past z 2.5 and the
# three near-misses at z 2.0-2.3 all held in A/Bs), greedily without conflicts, as a plain bot (edits.py table).
source /home/ubuntu/cambc-autumn/research/ideas-2026-11-12/labs/common.sh
LAB=lab-$ID; LD=$D/lab; mkdir -p $LD; ln -sfn $LD replays/emblab/$LAB
E="python3 tools/emblab/elab.py"
mkmaps 200
if [ ! -f $D/setup.done ]; then
  # Opponents: $L/EMB_OPPONENTS.json ({"opponents": shares, "opponent_bots": dirs}) when present, frozen into the round.
  [ -f $D/opponents.json ] || { [ -f $L/EMB_OPPONENTS.json ] && cp $L/EMB_OPPONENTS.json $D/opponents.json; }
  python3 tools/emblab/edits.py build --base $SRC --out $LD/edits.json --r4 --structural > $D/edits.log 2>&1 || fail EDITS
  python3 - "$LD" "$SRC" "$D" "$SEED" <<'PY' || fail CONFIG
import json, os, sys
ld, base, d, seed = sys.argv[1:]
opp = {"opponents": {"self": 0.5, "fish": 0.25, "mite": 0.25},
       "opponent_bots": {"fish": ["bots/variants/spar-dvn952-Flp4", "bots/variants/spar-dvn953-Flp4"],
                         "mite": ["bots/variants/spar-dvn952-Mt3q", "bots/variants/spar-dvn953-Mt3q"]}}
if os.path.exists(f"{d}/opponents.json"):
    opp = {k: v for k, v in json.load(open(f"{d}/opponents.json")).items() if k in ("opponents", "opponent_bots")}
assert all(os.path.isdir(b) for bots in opp["opponent_bots"].values() for b in bots), opp
json.dump({"seed": int(seed) % 100000, "source": base, "registry": f"{ld}/edits.json", **opp,
           "pool": [f"{d}/maps/fresh-*"], "auto": None, "none_share": 0.08, "solo_share": 0.12}, open(f"{ld}/config.json", "w"), indent=1)
PY
  ev "opponents: $(python3 -c "import json;c=json.load(open('$LD/config.json'));print(c['opponents'], c['opponent_bots'])")"
  $E init --lab $LAB > $D/init.log 2>&1 || fail INIT
  $E drafts --lab $LAB > $D/drafts.log 2>&1 || fail DRAFTS
  touch $D/setup.done; ev "setup: $(tail -n 1 $D/edits.log); $(tail -n 1 $D/init.log | cut -c1-200); $(tail -n 1 $D/drafts.log | cut -c1-160)"
fi
if [ ! -f $D/check.done ]; then
  # The vehicle must play exactly as plain bots at unlimited fuel: unedited, with a table edit and with a flag edit.
  FLAG=$(python3 -c "import json;r=json.load(open('$LD/edits.json'));print(next(e['name'] for e in r['edits'] if e['tier']=='structural'))")
  $E check --lab $LAB --games 48 --fuel 100000000 --edits row-off-ryth "$FLAG" > $D/check.log 2>&1 || fail CHECK-RUN
  python3 - $D/check.log <<'PY' || fail "CHECK: vehicle differs from plain bots ($(tail -n 3 $D/check.log | tr '\n' ' '))"
import re, sys
rows = [l for l in open(sys.argv[1]) if 'vehicle = reference bot on' in l]
assert len(rows) == 3, rows
for l in rows:
    a, n = map(int, re.search(r'reference bot on (\d+) of (\d+)', l).groups())
    assert a == n, l
PY
  rm -rf $LD/check; touch $D/check.done; ev "check: $(grep -c 'reference bot on' $D/check.log) vehicles identical to plain bots at 100M"
fi
if [ ! -f $D/warm.done ]; then
  python3 -c "import json;r=json.load(open('$LD/edits.json'));json.dump({'label':'warm','active':{str(e['id']):1 for e in r['edits']}},open('$LD/alloc.json','w'))"
  $E run --lab $LAB --games 80000 --batches 1 >> $LD/run.out 2>&1 || fail WARM
  touch $D/warm.done; ev "warm batch: $(grep 'merged' $LD/lab.log | tail -n 1 | cut -c1-200)"
fi
if [ ! -f $D/screen.done ]; then
  if [ ! -f $LD/stage.json ]; then
    python3 - "$LD" <<'PY' || fail SCREEN-SETUP
import json, sys
ld = sys.argv[1]
c = json.load(open(f'{ld}/config.json')); c['auto'] = []; json.dump(c, open(f'{ld}/config.json', 'w'), indent=1)
n = len(json.load(open(f'{ld}/edits.json'))['edits'])
keep = [round(n * k / 330) for k in (250, 180, 120, 75, 45)] + [20]
json.dump({"stages": [[t, k] for t, k in zip((6000, 12000, 20000, 32000, 48000, 80000), keep)], "stage": 0,
           "alive": list(range(1, n + 1)), "history": [], "capacity": 330000}, open(f'{ld}/stage.json', 'w'))
PY
    python3 tools/emblab/efit.py step --lab $LAB >> $D/efit.log 2>&1 || fail SCREEN-STEP
  fi
  rm -f $LD/stop
  until [ -f $LD/stop ]; do $E run --lab $LAB --games 80000 --batches 80 >> $LD/run.out 2>&1 || fail SCREEN-RUN; done
  python3 -c "import json;s=json.load(open('$LD/stage.json'));assert s['stage']>=len(s['stages']),s['stage']" || fail "SCREEN-STOPPED: $(cat $LD/stop)"
  cp $LD/stage.json $LD/stage-screen.json; touch $D/screen.done; ev "screen: $(tail -n 1 $D/efit.log | cut -c1-200); $(grep 'efit step' $LD/lab.log | tail -n 1 | cut -c1-250)"
fi
if [ ! -f $D/repl.done ]; then
  if [ ! -f $D/repl.start ]; then
    python3 - "$LD" <<'PY' > $D/repl.start || fail REPL-SETUP
import json, sys
from pathlib import Path
L = Path(sys.argv[1]); st = json.loads((L / 'stage-screen.json').read_text())
first = len(sorted((L / 'batches').glob('b[0-9][0-9][0-9]')))
json.dump({"stages": [[150000, len(st['alive'])]], "stage": 0, "alive": st['alive'], "from": first, "history": [], "capacity": 330000}, open(L / 'stage.json', 'w'))
print(first)
PY
    python3 tools/emblab/efit.py step --lab $LAB >> $D/efit.log 2>&1 || fail REPL-STEP
  fi
  rm -f $LD/stop
  until [ -f $LD/stop ]; do $E run --lab $LAB --games 80000 --batches 40 >> $LD/run.out 2>&1 || fail REPL-RUN; done
  touch $D/repl.done; ev "replication: $(grep 'efit step' $LD/lab.log | tail -n 1 | cut -c1-250)"
fi
if [ ! -f $D/cand.done ]; then
  FROM=$(cat $D/repl.start)
  python3 tools/emblab/efit.py fit --lab $LAB --from $FROM --json $D/repl.json > $D/repl-fit.log 2>&1 || fail REPL-FIT
  python3 tools/emblab/efit.py fit --lab $LAB --from $FROM --by opp > $D/repl-fit-opp.log 2>&1
  SEL=$(python3 - "$LD" "$D" <<'PY'
import json, sys
sys.path.insert(0, 'tools/emblab')
import edits as ed
ld, d = sys.argv[1:]
reg = ed.load(f'{ld}/edits.json'); by = {e['id']: e for e in reg['edits']}
alive = set(json.load(open(f'{ld}/stage.json'))['alive'])
rows = [r for r in json.load(open(f'{d}/repl.json')) if r['id'] in alive and by[r['id']]['tier'] != 'placebo']
rows.sort(key=lambda r: -r['pts'])
chosen = []
for r in rows:
    if r['pts'] >= 0.25 and r['z'] >= 2.0 and not any(ed.conflicts(by[r['id']], by[c['id']]) for c in chosen):
        chosen.append(r)
top = '; '.join(f"{r['name']} {r['pts']:+.2f} z{r['z']:.1f}" for r in rows[:6])
json.dump({'chosen': [r['id'] for r in chosen], 'rows': rows}, open(f'{d}/selection.json', 'w'), indent=1)
print(' '.join(str(r['id']) for r in chosen) + '\t' + ', '.join(f"{r['name']} {r['pts']:+.2f} z{r['z']:.1f}" for r in chosen) + '\t' + top)
PY
) || fail SELECT
  IDS=$(echo "$SEL" | cut -f1); WHAT=$(echo "$SEL" | cut -f2); TOP=$(echo "$SEL" | cut -f3)
  GAMES=$(wc -l < $LD/games.jsonl)
  if [ -z "$IDS" ]; then
    none "no replicated edit at +0.25 and z>=2 ($GAMES lab games); top: $TOP"
  else
    python3 tools/emblab/edits.py table --registry $LD/edits.json --base $SRC --out bots/$CAND $IDS > $D/table.log 2>&1 || fail TABLE
    candidate "emblem edits $WHAT (replication on new games; lab estimates, not A/Bs; $GAMES lab games)"
  fi
  touch $D/cand.done
fi
