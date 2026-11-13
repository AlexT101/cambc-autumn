#!/bin/bash
# Upload a test bot outside the queue (unmasked) and queue several `cells` steps for it, ahead of the remaining after-queue.
# usage: live_test.sh BOT_DIR "NOTE" WAIT_GATE STEPS.json [--rest]
#   --rest: make this upload REST immediately, while its queued checks run.
#   WAIT_GATE: a sched.log pattern to wait for first (e.g. the previous candidate's "all created"), or "" for none
#   STEPS.json: [[cells_file, step_id, opp, refset, lost_by], ...]
set -u
DIR=$1; NOTE=$2; WAITG=$3; STEPS=$4
BOOK_REST=${5:-}
case "$BOOK_REST" in ""|--rest) ;; *) echo "expected optional --rest"; exit 1;; esac
SUBMIT_ARGS=()
if [ "$BOOK_REST" = --rest ]; then SUBMIT_ARGS+=(--rest); fi
R=/home/ubuntu/cambc-autumn; S=~/tmp-offload/handoff/sched; W=~/tmp-offload/rbook-mask
cd $R
[ ${#NOTE} -le 80 ] || { echo "note over 80 characters"; exit 1; }
[ -z "$WAITG" ] || until grep -qE "$WAITG" $S/sched.log; do sleep 15; done
python3 $W/upload_rest.py build "$DIR" "$NOTE" || exit 1
WS=$(python3 -c "import json;c=json.load(open('$W/prepared.json'));assert not c['masked'];print(c['workspace'])") || { echo "build is masked"; exit 1; }
(cd $WS && rm -f $W/multi-bundle.zip && cambc bundle ocean --output $W/multi-bundle.zip > /dev/null 2>&1)
B=$(stat -c %s $W/multi-bundle.zip); echo "bundle bytes $B"; [ "$B" -lt 5000000 ] || { echo "bundle too big"; exit 1; }
phase() { python3 -c "import json;c=json.load(open('$S/state.json'))['batches']['cur'];print('rest' if c is None else c['phase'])"; }
start_sched() { rm -f $S/STOP; setsid nohup /home/ubuntu/venv/bin/python tools/live_sched.py >> $S/sched.out 2>&1 < /dev/null & sleep 5; }
for try in $(seq 40); do
  until [ "$(phase)" = rest ]; do sleep 10; done
  PID=$(cat $S/sched.lock); touch $S/STOP
  while kill -0 $PID 2>/dev/null; do sleep 2; done
  [ "$(phase)" = rest ] && break
  echo "$(date -u +%T) a batch started before the stop; retrying"; start_sched; sleep 60
done
[ "$(phase)" = rest ] || { echo "never between batches"; start_sched; exit 1; }
echo "$(date -u +%T) scheduler stopped between batches"
python3 $W/upload_rest.py submit "${SUBMIT_ARGS[@]}"; rc=$?
if [ $rc -eq 0 ]; then
python3 - "$STEPS" <<'EOF'
import json, sys
from pathlib import Path
S = Path.home() / 'tmp-offload/handoff/sched'
st = json.loads((S / 'state.json').read_text())
v = st['history'][-1]['version']
f = S / 'after-queue.json'
steps = json.loads(f.read_text())
done = st['batches'].get('after_done', [])
new = []
for spec in json.loads(Path(sys.argv[1]).read_text()):
    cf, sid, opp, rs, src = spec[:5]
    pin = spec[5] if len(spec) > 5 else 'ref'
    assert pin in ('ref', 'none')
    new.append({"id": sid, "kind": "cells", "version": v, "lost_by": src, "opp": opp,
                "refset": rs, "pin": pin, "ahead": True, "cells": json.loads(Path(cf).read_text()),
                "note": f"coordinator 2026-11-13: book coverage check, {opp} pin={pin}; not host strength"})
i = next((k for k, s in enumerate(steps) if s['id'] not in done), len(steps))
steps[i:i] = new
(S / f'after-queue.json.bak-{new[0]["id"]}').write_text(f.read_text())
f.write_text(json.dumps(steps, indent=1) + '\n')
print('queued steps', [s['id'] for s in new], 'for v%d' % v, 'at position', i, [s['id'] for s in steps])
EOF
fi
start_sched; sleep 60
echo "$(date -u +%T) submit rc=$rc"; pgrep -af "live_sched.py|ladder_scrims.py run" | grep -v bash | cut -c1-70
tail -6 $S/sched.log | cut -c1-260
