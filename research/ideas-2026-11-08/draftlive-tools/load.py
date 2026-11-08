"""Rows of a dlive lab: one per game: map, k, side, opp, body, win (ours), margin (gem lead at end/1000), our team, F92 score."""
import json
from pathlib import Path
W = Path('/home/ubuntu/tmp-offload/draftlive')
CH = ["ryth","vesper_vale","vendetta","cassi_and_issac","stellar","prism","marcella","willow","ren","varg","tavi","heart_of_ruin"]
def rows(name, scores=W / 'f92scores.json'):
    D = W / name
    games = json.load(open(D / 'games.json')); lists = json.load(open(D / 'lists.json'))
    S = {m['name']: {tuple(t): s for t, s in m['teams']} for m in json.load(open(scores))}
    res = {}
    for l in open(D / 'batch' / 'results.jsonl'):
        r = json.loads(l); res[r['stem']] = r
    out = {}
    for f in [D / 'batch' / 'outcomes.jsonl']:
        if f.exists():
            for l in open(f):
                o = json.loads(l); out[Path(o['file']).stem] = o
    R = []; bad = 0
    for i, g in enumerate(games):
        st = f'g{i:05d}'; r = res.get(st)
        if not r or 'winner' not in r: continue
        name, k, side, opp, body = g['meta']
        us = 0 if side == 'a' else 1
        team = tuple(lists[name]['teams'][k]) if k >= 0 else tuple(lists[name]['teams'][0])
        o = out.get(st); margin = None
        if o:
            if o.get('draft') and tuple(o['draft'][us]) != team: bad += 1; continue
            fin = o['cp'].get('end') or o['cp'][max(o['cp'], key=lambda x: int(x) if x.isdigit() else -1)]
            mine, theirs = sum(fin[us]), sum(fin[1 - us]); margin = (mine - theirs) / 1000
        R.append(dict(map=name, k=k, side=side, opp=opp, body=body, win=int(r['winner'] == us), margin=margin, team=team,
                      s=S[name][team], picks=lists[name]['picks'], stem=st, rounds=r.get('rounds')))
    if bad: print('DRAFT MISMATCH', bad)
    return R
