#!/bin/bash
# tune2.sh: SPSA of c520-ps's 19 lab knobs (localq mktune.sh) against mf-c2 only (current Mite with its retreat rule; mkbody.py static
# members 961-966, noise 0.2), on 40 fresh ladder-v3 suites (mapgen seeds 7932000-7932039), scored win .75 / gems .25,
# as the labs' round_tune.sh. The second-half (Polyak) mean, ported into a copy of c520-ps, is variants/mft2-c520.
# Pauses the labs filler for the SPSA and resumes it after. Resumable through done-files in ~/tmp-offload/mitefit/tune1.
set -o pipefail
R=/home/ubuntu/cambc-autumn; D=/home/ubuntu/tmp-offload/mitefit/tune2; RUN=mft2; ITERS=${ITERS:-600}
cd $R; source /home/ubuntu/venv/bin/activate
ev() { echo "$(date -u '+%F %T') $*" >> $D/events; }
fail() { ev "FAIL $*"; touch $D/FAILED; exit 1; }
BASE=variants/c520-ps; S=mft2-start; T=mft2-tune; CAND=variants/mft2-c520; B=$D/bench; mkdir -p $B
bench_pair() {
  for s in def wide; do for b in $1 $2; do extra=""; [ $s = wide ] && extra="--set wide"
    python3 tools/fuel/bench.py run $b $extra --out $B/$3-$(basename $b)-$s.json --games $B/g > $B/$3-$(basename $b)-$s.log 2>&1 || return 1
    rm -rf $B/g; done; done
  for s in def wide; do echo "== $s"; python3 tools/fuel/bench.py compare $B/$3-$(basename $1)-$s.json $B/$3-$(basename $2)-$s.json 2>&1 | tail -4; done > $B/$3-compare.txt
  grep -q "identical replays: 16/16" $B/$3-compare.txt && grep -q "identical replays: 52/52" $B/$3-compare.txt
}
C2="--set hurt_health_fraction=0.40 --set brake_bag=11 --set hurt_retreat_ratio=0.01 --set home_retreat_ratio=1000"
for s in $(seq 7932000 7932039); do
  [ -f $D/maps/fresh-$s/.done ] && continue
  python3 tools/pooled.py 1 -- node tools/mapgen/mapgen.mjs suite --mix ladder-v3 --seed $s --jobs 1 --out $D/maps/fresh-$s > /dev/null 2>&1 \
    && touch $D/maps/fresh-$s/.done || fail MAPGEN-$s
done
# tune1 first: one SPSA at a time, and it resumes the labs filler on exit.
until [ -f $D/../tune1/DONE ] || [ -f $D/../tune1/FAILED ]; do sleep 60; done
if [ ! -f $D/setup.done ]; then
  for k in 961 962 963 964 965 966; do
    python3 research/ideas-2026-11-12/mitefit/mkbody.py mf-s$k --static $k $C2 -f > /dev/null || fail BODY
  done
  ./copybot -f $BASE variants/$S > /dev/null || fail COPYBOT
  bash ~/tmp-offload/localq/mktune.sh variants/$S variants/$T > $D/mktune.log 2>&1 || fail MKTUNE
  bench_pair variants/$S variants/$T setup || fail SETUP-BENCH-NOT-IDENTICAL
  python3 tools/tune/tune.py init --run $RUN --bot bots/variants/$T --opps $(printf "variants/mf-s%s," 961 962 963 964 965 | sed "s/,$/,variants\/mf-s966/") \
    --pool $(ls -d $D/maps/fresh-* | paste -sd,) --maps 16 --pairs 4 --seed 7932 --force > $D/init.log 2>&1 || fail INIT
  python3 - $RUN <<'PY' || fail CONFIG
import json, sys
p = f'/home/ubuntu/cambc-autumn/replays/tune/{sys.argv[1]}/config.json'; c = json.load(open(p))
c.update(weights={'win': 0.75, 'gems': 0.25, 'gold': 0.0}, a=0.25, A=100, c=0.12)
if 'hit_given_reach' in c['params']: c['params']['hit_given_reach'][0] = 0.21
json.dump(c, open(p, 'w'), indent=1)
PY
  touch $D/setup.done; ev "setup: $(tail -n 1 $D/init.log | cut -c1-200)"
fi
H=replays/tune/$RUN/history.jsonl
if [ ! -f $D/tune.done ]; then
  bash research/ideas-2026-11-12/labs/ctl.sh pause; ev "labs filler paused"
  rm -f replays/tune/$RUN/STOP
  python3 tools/tune/tune.py run --run $RUN --hours 200 > $D/tune.out 2>&1 &
  P=$!
  until ! kill -0 $P 2>/dev/null || { [ -f $H ] && [ $(wc -l < $H) -ge $ITERS ]; }; do sleep 60; done
  touch replays/tune/$RUN/STOP; wait $P; ev "tune exit $? at $(wc -l < $H) iterations"
  bash research/ideas-2026-11-12/labs/ctl.sh resume; ev "labs filler resumed"
  [ $(wc -l < $H) -ge $ITERS ] || fail TUNE-SHORT
  touch $D/tune.done
fi
if [ ! -f $D/cand.done ]; then
  python3 research/ideas-2026-11-09/spsa87-tools/polyak.py $RUN $D/avg.json > $D/apply.log 2>&1 || fail POLYAK
  python3 tools/tune/tune.py apply --run $RUN --values $D/avg.json --out bots/variants/$T-applied >> $D/apply.log 2>&1 || fail APPLY
  ./copybot -f $BASE $CAND > /dev/null || fail COPYBOT
  python3 research/ideas-2026-11-08/tune3-tools/port_tune.py bots/variants/$T-applied/src/tune.json bots/$CAND > $D/port.log 2>&1 || fail PORT
  bench_pair variants/$T-applied $CAND cand || fail PORT-BENCH-NOT-IDENTICAL
  ev "CANDIDATE $CAND: $(tr '\n' ' ' < $D/port.log | cut -c1-600)"
  touch $D/cand.done
fi
touch $D/DONE
