# Sourced by a filler round script: round_KIND.sh ROUND_DIR. Steps are resumable through done-files in ROUND_DIR.
set -o pipefail
D=$1; R=/home/ubuntu/cambc-autumn; L=/home/ubuntu/tmp-offload/labs; HERE=$R/research/ideas-2026-11-12/labs
cd $R; source /home/ubuntu/venv/bin/activate
rj() { python3 -c "import json,sys;print(json.load(open('$D/round.json')).get('$1',''))"; }
setj() { python3 -c "import json,sys;p='$D/round.json';j=json.load(open(p));j['$1']=sys.argv[1];json.dump(j,open(p,'w'),indent=1)" "$2"; }
ev() { echo "$(date -u '+%F %T') $*" >> $D/events; }
fail() { ev "FAIL $*"; echo "$*" > $D/fail; exit 1; }
ID=$(rj id); BASE=$(rj base); BN=$(basename $BASE); SEED=$(rj seed)
CAND=variants/lab-$ID-$BN
# The base must be the source the round was created on (a frozen variant: a teammate never edits it).
python3 - "$BASE" "$(rj base_src_sha256)" <<'PY' || fail "BASE-CHANGED: $BASE's src differs from round creation"
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1]) / 'src'
rows = [(str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file()]
assert hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest() == sys.argv[2]
PY
# The labs play and build a private copy of the base: builds in place in a bot that gates use could race theirs.
SRC=bots/variants/labsrc-$ID
if [ ! -f $D/src.done ]; then
  ./copybot -f ${BASE#bots/} ${SRC#bots/} > /dev/null || fail COPYBOT-SRC
  diff -r $BASE/src $SRC/src > /dev/null || fail COPYBOT-SRC-DIFFERS
  touch $D/src.done
fi

# mkmaps N: fresh --mix ladder-v4 suites (coordinator 2026-11-12: lab fits see the ladder's close spawns and open edges) SEED..SEED+N-1 under $D/maps/fresh-{seed}, each generator holding one slot.
mkmaps() {
  [ -f $D/maps.done ] && return 0
  mkdir -p $D/maps
  seq $SEED $((SEED + $1 - 1)) | xargs -P 6 -I{} sh -c \
    '[ -f '$D'/maps/fresh-{}/.done ] || { python3 tools/pooled.py 1 -- node tools/mapgen/mapgen.mjs suite --mix ladder-v4 --seed {} --jobs 1 --out '$D'/maps/fresh-{} > '$D'/maps/gen-{}.log 2>&1 && touch '$D'/maps/fresh-{}/.done; }' \
    || fail MAPGEN
  local n=$(ls $D/maps/*/ | grep -c '\.map26a$')
  [ $(ls -d $D/maps/fresh-*/.done 2>/dev/null | wc -l) -eq $1 ] || fail "MAPGEN: $(ls $D/maps/fresh-*/.done | wc -l) of $1 suites"
  rm -f $D/maps/gen-*.log; touch $D/maps.done; ev "maps: $1 suites from seed $SEED, $n maps"
}

# candidate SUMMARY: the candidate's patch against the base and candidate.json; CAND must exist and build.
candidate() {
  cambc build bots/$CAND > $D/cand-build.log 2>&1 || fail CAND-BUILD
  rm -rf bots/$CAND/.cambc
  echo "lab-$ID: $BASE + filler round $ID ($(rj kind) lab). $1" > bots/$CAND/NOTE
  (cd bots && diff -ruN --exclude=.cambc --exclude=NOTE --exclude=READY --exclude=compile_commands.json ${BASE#bots/}/src $CAND/src) > $D/cand.patch
  mkdir -p $HERE/patches; cp $D/cand.patch $HERE/patches/lab-$ID-$BN.patch
  python3 -c "import json,sys;json.dump({'variant':sys.argv[1],'base':sys.argv[2],'patch':sys.argv[3],'summary':sys.argv[4]},open(sys.argv[5],'w'),indent=1)" \
    "$CAND" "$BASE" "research/ideas-2026-11-12/labs/patches/lab-$ID-$BN.patch" "$1" $D/candidate.json
  ev "CANDIDATE $CAND: $1"
}
none() {
  python3 -c "import json,sys;json.dump({'summary':sys.argv[1]},open(sys.argv[2],'w'),indent=1)" "$1" $D/candidate.json
  ev "NO CANDIDATE: $1"
}
