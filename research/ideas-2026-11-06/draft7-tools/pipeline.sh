#!/bin/bash
# pipeline.sh: draft7's remaining steps in one run (2026-11-07, base oc-base11). Log: $D/pipeline.log.
# fits -> suites -> candidates on oc-base11 (+ parity) -> 2x SPRT screens -> held-out 40k -> varied 10k -> panel 20k.
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
D=/home/ubuntu/tmp-offload/draft7; T=research/ideas-2026-11-06/draft7-tools; BASE=variants/oc-base11
export NODE_OPTIONS=--max-old-space-size=98304
log() { echo "$(date '+%F %T') $*" >> $D/pipeline.log; }
ab() { REF=${REF:-$BASE} $T/ab.sh "$@"; }
split() { b=$(ls -d replays/batch-*-ab-$1-* 2>/dev/null | tail -n 1); [ -n "$b" ] && python3 $T/split.py $b >> $D/split-$1.txt 2>&1; }
pct() { python3 -c "import json;d=json.load(open('replays/ab/$1/summary.json'));s=d.get('sprt') or {};print(d['cand_win_pct'], d['games'], s.get('outcome','-'))"; }
log start

# 1. Fits: wait for the F92 search and the pooled fit; refit the pooled lab at F92's searched penalties.
until grep -q FIT-EXIT $D/f92-fit.out; do sleep 60; done
LAM=$(python3 -c "import json;print(json.dumps(json.load(open('replays/draftlab/draft7-f92/model.json'))['lam']))")
log "f92 lam $LAM"
node tools/draftlab/model.mjs fit --lab replays/draftlab/draft7-f92p --lam "$LAM" --threads 32 > $D/f92p-refit.out 2>&1
log "pooled refit exit $?"

# 2. Suites (seeds 590410-19 varied, 590510-29 panel, 590600-39 held out).
node tools/mapgen/mapgen.mjs suite --seed 590600-590639 --out 'maps/suites/fresh/fresh-{seed}' > $D/mapgen-c2.log 2>&1
node tools/mapgen/mapgen.mjs suite --seed 590410-590419 --mix varied --out 'maps/suites/fresh/fresh-{seed}' > $D/mapgen-v2.log 2>&1
node tools/mapgen/mapgen.mjs suite --seed 590510-590529 --out 'maps/suites/fresh/fresh-{seed}' > $D/mapgen-p3.log 2>&1
mk() { name=$1; shift; mkdir -p maps/suites/merged/$name; for s in "$@"; do for f in maps/suites/fresh/fresh-$s/*.map26a; do ln -sf ../../fresh/fresh-$s/$(basename $f) maps/suites/merged/$name/$(basename $f .map26a)-$s.map26a; done; done; log "$name $(ls maps/suites/merged/$name | wc -l) maps"; }
mk d7-held $(seq 590300 590339) $(seq 590600 590639)
mk d7-varied $(seq 590400 590419)
mk d7-panel $(seq 590500 590529)
for f in maps/suites/merged/panel-check-514510/*.map26a; do ln -sf "$(readlink -f $f)" maps/suites/merged/d7-panel/; done
log "d7-panel $(ls maps/suites/merged/d7-panel | wc -l) maps"
node $T/altars.mjs maps/suites/fresh/fresh-5902{0..3}? maps/suites/fresh/fresh-5903{0..3}? maps/suites/fresh/fresh-5904{0,1}? maps/suites/fresh/fresh-5905{0,1,2}? maps/suites/fresh/fresh-5906{0..3}? maps/suites/fresh/fresh-51451? > $D/altars.json

# 3. Candidates on oc-base11.
$T/make_candidate.sh replays/draftlab/draft7-f92 oc-draft7 > $D/cand-oc-draft7.log 2>&1; log "oc-draft7 build $? | $(grep 'team mismatches' $D/cand-oc-draft7.log | tr '\n' ' ')"; log "diff: $(grep -E "differ|Only" $D/cand-oc-draft7.log | tr "\n" " ")"
$T/make_candidate.sh replays/draftlab/draft7-f92p oc-draft7-alt > $D/cand-oc-draft7-alt.log 2>&1; log "oc-draft7-alt build $? | $(grep 'team mismatches' $D/cand-oc-draft7-alt.log | tr '\n' ' ')"
for c in oc-draft7 oc-draft7-alt; do
  if grep 'team mismatches' $D/cand-$c.log | grep -qv ' 0 team mismatches, 0 C++ failures'; then log "PARITY FAIL $c"; exit 1; fi
  [ -f bots/variants/$c/src/draft/draft_model.h ] || { log "NO CANDIDATE $c"; exit 1; }
done
node tools/draftlab/model.mjs teams --lab replays/draftlab/draft7-f92 > $D/teams-draft7-f92.txt 2>/dev/null
node tools/draftlab/model.mjs teams --lab replays/draftlab/draft7-f92p > $D/teams-draft7-f92p.txt 2>/dev/null

# 4. 2x screens, distinct seeds, concurrently; then the two candidates head to head.
ab variants/oc-draft7 s2x-d7 maps/suites/merged/d7-e --fuel 200000 --sprt 0.50,0.51 --sprt-seed 590001 &
ab variants/oc-draft7-alt s2x-d7alt maps/suites/merged/d7-e --fuel 200000 --sprt 0.50,0.51 --sprt-seed 590002 &
wait
REF=variants/oc-draft7 ab variants/oc-draft7-alt s2x-alt-vs-d7 maps/suites/merged/d7-e --fuel 200000 --sprt 0.50,0.51 --sprt-seed 590003
log "2x d7 $(pct s2x-d7) | alt $(pct s2x-d7alt) | alt vs d7 $(pct s2x-alt-vs-d7)"
W=$(python3 - <<'EOF'
import json
r = {k: json.load(open(f'replays/ab/{k}/summary.json')) for k in ('s2x-d7', 's2x-d7alt', 's2x-alt-vs-d7')}
o = lambda k: (r[k].get('sprt') or {}).get('outcome')
alt_better = o('s2x-alt-vs-d7') == 'H1' or (o('s2x-alt-vs-d7') != 'H0' and r['s2x-alt-vs-d7']['cand_win_pct'] > 50 and o('s2x-d7alt') == 'H1')
print('oc-draft7-alt' if alt_better and o('s2x-d7alt') != 'H0' else 'oc-draft7')
EOF
)
log "winner $W"

# 5. Held out, real budget, 40,960 games; varied 10,240.
ab variants/$W held-$W maps/suites/merged/d7-held; split held-$W; log "held $(pct held-$W) | $(cat $D/split-held-$W.txt)"
ab variants/$W var-$W maps/suites/merged/d7-varied; split var-$W; log "varied $(pct var-$W) | $(cat $D/split-var-$W.txt)"

# 6. Panel, 20,480 a member, base and winner.
for b in $BASE variants/$W; do t=$(basename $b)
  for m in variants/astraeus-now-1106 variants/panel-proteus variants/panel-demeter variants/panel-ocean-td baselines/v67; do
    REF=$m ab $b pan-$t-vs-$(basename $m) maps/suites/merged/d7-panel; log "panel $t vs $(basename $m) $(pct pan-$t-vs-$(basename $m))"
  done
done
log PIPELINE-DONE
