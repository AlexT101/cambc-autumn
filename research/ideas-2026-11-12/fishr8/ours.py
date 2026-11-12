"""Our scrims against Fish from big-arm's capture rows, joined to ladder_scrims tasks by group id: version, refset.
    py ours.py [ROWS.tsv.gz]  -> ~/tmp-offload/fishr8/ours.json (match id -> row)"""
import json, os, sys
from meta import rows
D = '/home/ubuntu/cambc-autumn/research/ladder-scrims-2026-11-06/data/'
grp = {}
for l in open(D + 'events.jsonl'):
    e = json.loads(l)
    if e.get('ev') == 'created' and e.get('opp_id') == '1890540d-1ffc-4847-adbf-d0d08772f268':
        grp[e['group']] = e['task']
task = {}
for l in open(D + 'tasks.jsonl'):
    t = json.loads(l); task[t['id']] = t
src = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/tmp-offload/fishr8/rows_recent.tsv.gz')
out = {}
for r in rows(src):
    if r['opp'] != 'stellar best girl' or r['group_id'] not in grp: continue
    t = task.get(grp[r['group_id']], {})
    out[r['match_id']] = dict(match=r['match_id'], task=grp[r['group_id']], version=t.get('version'), refset=t.get('refset'),
                              map=r['map'], side='b' if r['f_side'] == 'a' else 'a', result=('loss' if r['f_win'] else 'win') if r['f_win'] is not None else None,
                              opp_picks=r['f_picks'], our_picks=r['op_picks'], replay=r['replay'], created=r['created_at'], group=r['group_id'])
json.dump(out, open(os.path.expanduser('~/tmp-offload/fishr8/ours.json'), 'w'))
import collections
c = collections.Counter((v['version'], v['refset'], v['result']) for v in out.values())
for k in sorted(c, key=str): print(k, c[k])
print(sum(1 for v in out.values() if v['refset'] == 'r8' and v['replay']), 'r8 with replay')
