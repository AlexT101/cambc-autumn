#!/bin/bash
# round_tune.sh ROUND_DIR: one SPSA round as localq's tune rounds (~/tmp-offload/localq/round_tune.sh, tune1) on the
# round's base: tune1's 19 economy and fight knobs (localq mktune.sh), 700 iterations on the round's own 40 fresh
# ladder-v2 suites, scored win .75 / gems .25, against the gate's Fish/Mite bodies at training noise seeds 951-953 (six
# of nine opponents), the base itself, charybdis 519 and ocean 506. The second-half (Polyak) mean, ported into a copy
# of the base, is the candidate; both the tunified bot and the port must replay the base / each other byte-identically
# at 100M on bench.py's sets.
source /home/ubuntu/cambc-autumn/research/ideas-2026-11-12/labs/common.sh
RUN=lab-$ID; S=lab-$ID-start; T=lab-$ID-tune; ITERS=${ITERS:-700}
B=$D/bench; mkdir -p $B
bench_pair() {  # bench_pair BOT1 BOT2 TAG: identical replays at 100M on the default and wide sets
  for s in def wide; do for b in $1 $2; do extra=""; [ $s = wide ] && extra="--set wide"
    python3 tools/fuel/bench.py run $b $extra --out $B/$3-$(basename $b)-$s.json --games $B/g > $B/$3-$(basename $b)-$s.log 2>&1 || return 1
    rm -rf $B/g; done; done
  for s in def wide; do echo "== $s"; python3 tools/fuel/bench.py compare $B/$3-$(basename $1)-$s.json $B/$3-$(basename $2)-$s.json 2>&1 | tail -4; done > $B/$3-compare.txt
  grep -q "identical replays: 16/16" $B/$3-compare.txt && grep -q "identical replays: 52/52" $B/$3-compare.txt
}
mkmaps 40
if [ ! -f $D/setup.done ]; then
  python3 tools/pooled.py 1 -- python3 ~/tmp-offload/localq/bodies.py 951 952 953 > $D/bodies.log 2>&1 || fail BODIES
  ./copybot -f ${BASE#bots/} variants/$S > /dev/null || fail COPYBOT
  bash ~/tmp-offload/localq/mktune.sh variants/$S variants/$T > $D/mktune.log 2>&1 || fail MKTUNE
  bench_pair variants/$S variants/$T setup || fail SETUP-BENCH-NOT-IDENTICAL
  OPPS=$(for k in 951 952 953; do printf "variants/spar-dvn$k-Flp4,variants/spar-dvn$k-Mt3q,"; done)variants/$S,variants/chy-519,variants/oc-dfuel-506
  python3 tools/tune/tune.py init --run $RUN --bot bots/variants/$T --opps $OPPS --pool $(ls -d $D/maps/fresh-* | paste -sd,) \
    --maps 16 --pairs 4 --seed $((SEED % 100000)) --force > $D/init.log 2>&1 || fail INIT
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
  rm -f replays/tune/$RUN/STOP
  python3 tools/tune/tune.py run --run $RUN --hours 200 > $D/tune.out 2>&1 &
  P=$!
  until ! kill -0 $P 2>/dev/null || { [ -f $H ] && [ $(wc -l < $H) -ge $ITERS ]; }; do sleep 60; done
  touch replays/tune/$RUN/STOP; wait $P; ev "tune exit $? at $(wc -l < $H) iterations"
  [ $(wc -l < $H) -ge $ITERS ] || fail TUNE-SHORT
  touch $D/tune.done
fi
if [ ! -f $D/cand.done ]; then
  python3 research/ideas-2026-11-09/spsa87-tools/polyak.py $RUN $D/avg.json > $D/apply.log 2>&1 || fail POLYAK
  python3 tools/tune/tune.py apply --run $RUN --values $D/avg.json --out bots/variants/$T-applied >> $D/apply.log 2>&1 || fail APPLY
  ./copybot -f ${BASE#bots/} $CAND > /dev/null || fail COPYBOT
  python3 research/ideas-2026-11-08/tune3-tools/port_tune.py bots/variants/$T-applied/src/tune.json bots/$CAND > $D/port.log 2>&1 || fail PORT
  bench_pair variants/$T-applied $CAND cand || fail PORT-BENCH-NOT-IDENTICAL
  candidate "SPSA constants ($ITERS iterations, second-half mean): $(tr '\n' ' ' < $D/port.log | cut -c1-600)"
  touch $D/cand.done
fi
