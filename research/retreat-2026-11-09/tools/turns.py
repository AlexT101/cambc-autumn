import json, gzip, sys, zipfile
sys.path.insert(0, __import__('os').path.dirname(__file__))
import retreat_audit as ra
ex = 'replays/retreat-analysis'
src, c, ra0, ra1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
g = [x for x in json.load(open(f'{ex}/index.json'))['games'] if x['source'] == src][0]
meta = json.load(open(f"{ex}/{g['dir']}/meta.json")); team_of = {x['id']: x['team'] for x in meta['champions']}; type_of = {x['id']: x['type'] for x in meta['champions']}
R = json.load(gzip.open(f"{ex}/{g['dir']}/rounds.json.gz")); ridx = {x: i for i, x in enumerate(R['round'])}; ch = {x['id']: x for x in R['champions']}
ev = [json.loads(l) for l in gzip.open(f"{ex}/{g['dir']}/events.jsonl.gz", 'rt')]
t = team_of[c]
decs = {tt: ra.load_stdout_decisions(src, 'ab'[tt]) for tt in (0, 1)}
for r in range(ra0, ra1 + 1):
    i = ridx[r]
    me = (ch[c]['x'][i], ch[c]['y'][i])
    line = f"r{r} {decs[t].get((r, c), '?')} {ra.NAMES[type_of[c]]}@{me} hp {ch[c]['hp'][i]:.0f} cd {ch[c]['cd0'][i]},{ch[c]['cd1'][i]} stun {ch[c]['stun'][i]} |"
    for f in ch:
        if ch[f]['alive'][i] and ch[f]['x'][i] is not None and ch[f]['x'][i] >= 0:
            q = (ch[f]['x'][i], ch[f]['y'][i]); d = max(abs(q[0] - me[0]), abs(q[1] - me[1])) if me[0] is not None else 99
            if d <= 8 and f != c: line += f" {'E' if team_of[f] != t else 'a'}:{ra.NAMES[type_of[f]]}{q}d{d} {decs[team_of[f]].get((r, f), '?')}"
    print(line)
    for e in ev:
        if e['r'] == r and (e.get('a') == c or any(v == c for v, _ in (e.get('dmg') or []))) and e['k'] not in ('recall_start', 'recall_cancel'):
            print('     ', {k: e[k] for k in e if k in ('k', 'a', 'f', 'to', 'tgt', 'dmg', 'ab', 'moved', 'stun')})
