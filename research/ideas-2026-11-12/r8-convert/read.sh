#!/bin/bash
# read.sh ARM FIRST N: the pooled fgate reads (fr8 and std) of variants/ARM against variants/rc-524 over finished runs only.
source ~/tmp-offload/r8-convert/env.sh
ARM=$1; FIRST=$2; N=$3
for KIND in fr8 std; do
  EXTRA=""; [ "$KIND" = fr8 ] && EXTRA="--fish-body fr8-g25"
  python3 tools/fgate.py variants/$ARM variants/rc-524 --pool v3 --first-batch $FIRST --max-batches $N --ci 0 --no-run $EXTRA 2>&1 | python3 -c "
import sys,json
for l in sys.stdin:
    if l.startswith('{'):
        r=json.loads(l)
        f=lambda k: ('%+.2f ±%.2f'%tuple(r[k])) if r.get(k) else 'n/a'
        print('$ARM $KIND b$FIRST+%d: fresh %s (Fish %s, Mite %s; one-site %s, multi %s) ladder %s | %d fresh games, cand %.2f%% ref %.2f%%, errors %d, early %d' % (r['batches'], f('fresh'), f('fresh_fish'), f('fresh_mite'), f('fresh_one_site'), f('fresh_multi_site'), f('ladder'), 8*r['fresh_units'], r['cand_win_pct'], r['ref_win_pct'], r['errors'], r['early_losses']))
"
done
