#!/bin/bash
# round_draft.sh ROUND_DIR: a draft-lab refit as draft18 (CHANGES 515, EXPERIMENTS "Draft18 on charybdis") with the
# round's base as the lab player: 1M games on its own 100 fresh ladder-v4 suites (340 maps each), F92 features, draft18's opponents
# (self .2, ocean 506 .2, the gate's Fish/Mite bodies at training noise seed 951 .3 each), draft10-f92's searched
# penalties to start; no mid-run searches (they starved the refits in draft18). The final fit: the lab's own search if
# it ends within 40 min, else draft18's way, a plain fit at the starting penalties in a link lab (LAB-start).
# Candidate: the base with only draft_model.h replaced, if native parity is exact and the first draft turn has no more
# drafts over 10M than the base's.
source /home/ubuntu/cambc-autumn/research/ideas-2026-11-12/labs/common.sh
LAB=lab-$ID; LD=$D/lab; mkdir -p $LD; ln -sfn $LD replays/draftlab/$LAB
mkmaps 100
if [ ! -f $D/init.done ]; then
  python3 - "$LD" "$SRC" "$D" "$SEED" "$(rj base_src_sha256)" <<'PY' || fail CONFIG
import json, sys
ld, base, d, seed, sha = sys.argv[1:]
c = json.load(open('/home/ubuntu/cambc-autumn/replays/draftlab/draft18/config.json'))
for k in ('current_lab', 'link_of'):
    c.pop(k, None)
c.update(seed=int(seed) % 100000, pool=[f'{d}/maps/fresh-*'], holdout=[], search_batches=[], source=base, source_sha=sha,
         current_lab='replays/draftlab/draft18-start',
         opponent_bots={'ocean': 'bots/variants/oc-dfuel-506', 'fish': 'bots/variants/spar-dvn951-Flp4', 'mite': 'bots/variants/spar-dvn951-Mt3q'},
         source_note=f'filler {d.rstrip("/").split("/")[-1]}: {base} as the lab player; draft18 config otherwise; own fresh ladder-v4 pool from seed {seed}')
json.dump(c, open(f'{ld}/config.json', 'w'), indent=1)
PY
  python3 tools/draftlab/lab.py init --lab $LAB > $D/init.log 2>&1 || fail INIT
  touch $D/init.done; ev "init: $(grep -c . $LD/maps.jsonl) maps; $(tail -n 1 $D/init.log | cut -c1-200)"
fi
MODEL=$LAB
if [ ! -f $D/lab.done ]; then
  setsid python3 tools/draftlab/lab.py run --lab $LAB --hours 200 >> $D/run.log 2>&1 &
  P=$!
  until ! kill -0 $P 2>/dev/null || grep -q "final fit with search" $LD/lab.log 2>/dev/null; do sleep 60; done
  for i in $(seq 40); do kill -0 $P 2>/dev/null || break; sleep 60; done
  if kill -0 $P 2>/dev/null; then
    kill -TERM -$P; sleep 10; kill -KILL -$P 2>/dev/null; echo start > $D/model.kind
    ev "final search still running after 40 min: stopped; plain fit in $LAB-start"
  else
    wait $P; rc=$?; [ $rc -eq 0 ] || fail "LAB-RUN exit $rc"; echo searched > $D/model.kind
  fi
  python3 -c "import json;m=json.load(open('$LD/model.json'));assert m['games']>=900000, m['games']" 2>/dev/null \
    || [ "$(cat $D/model.kind)" = start ] || fail LAB-SHORT
  touch $D/lab.done; ev "lab done: $(wc -l < $LD/games.slim.jsonl) games; $(grep '^cv\|^fit' $LD/fit.log | tail -n 2 | tr '\n' ' ' | cut -c1-250)"
fi
if [ "$(cat $D/model.kind)" = start ]; then
  MODEL=$LAB-start
  if [ ! -f $D/start.done ]; then
    mkdir -p $D/start; ln -sfn $D/start replays/draftlab/$MODEL
    for f in games.jsonl games.slim.json games.slim.jsonl ladder.jsonl maps.jsonl prior.json; do ln -sfn $LD/$f $D/start/$f; done
    python3 -c "import json;c=json.load(open('$LD/config.json'));c['link_of']='replays/draftlab/$LAB';json.dump(c,open('$D/start/config.json','w'),indent=1)"
    python3 tools/pooled.py 32 -- node tools/draftlab/model.mjs fit --lab replays/draftlab/$MODEL --threads 32 > $D/start-fit.log 2>&1 || fail START-FIT
    touch $D/start.done; ev "plain fit: $(grep '^fit\|cv' $D/start-fit.log | tail -n 1 | cut -c1-200)"
  fi
fi
if [ ! -f $D/cand.done ]; then
  python3 -c "import json,math;m=json.load(open('replays/draftlab/$MODEL/model.json'));assert all(math.isfinite(x) for p in m['picks'].values() for x in p['theta'])" || fail MODEL-NAN
  ./copybot -f ${BASE#bots/} $CAND > $D/cand.log 2>&1 || fail COPYBOT
  rm -f bots/$CAND/READY
  node tools/draftlab/model.mjs cpp --lab replays/draftlab/$MODEL --out bots/$CAND/src/draft/draft_model.h >> $D/cand.log 2>&1 || fail CPP
  # native.mjs exits 1 on any feature difference, last-digit float ones included (draft19: 121 of 676 maps, teams all
  # equal); what ships is the team, so the gate is the summary line: no key or team mismatch, no C++ failure.
  node tools/draftlab/native.mjs --lab replays/draftlab/$MODEL maps maps $D/maps/fresh-$SEED --src bots/$CAND/src/draft > $D/parity.log 2>&1
  S=$(grep ' maps: .* key mismatches' $D/parity.log | tail -n 1)
  [ -n "$S" ] || fail PARITY-OUTPUT
  echo "$S" | grep -q ' 0 key mismatches' && echo "$S" | grep -q ' 0 team mismatches, 0 C++ failures' || fail "PARITY: $S"
  for b in ${SRC#bots/} $CAND; do
    python3 tools/draftlab/firstturn.py --sample $LD/maps.jsonl --need --bot bots/$b --jobs 8 --name $ID-$(basename $b) > $D/firstturn-$(basename $b).out 2>&1 || fail FIRSTTURN-RUN
  done
  over() { grep -o 'over it: [0-9]*' $D/firstturn-$1.out | grep -o '[0-9]*$' | tail -n 1; }
  ob=$(over $(basename $SRC)); oc=$(over $(basename $CAND))
  [ -n "$oc" ] && [ -n "$ob" ] && [ "$oc" -le "$ob" ] || fail "FIRSTTURN: drafts over 10M cand $oc, base $ob"
  rm -rf bots/variants/firstturn-$ID-*
  candidate "draft model refitted on $BN ($MODEL, $(cat $D/model.kind) fit, $(wc -l < $LD/games.slim.jsonl) games); $(echo "$S" | grep -o '[0-9]* maps: 0 key mismatches')/0 team mismatches; first-turn drafts over 10M: $oc (base $ob)"
  touch $D/cand.done
fi
