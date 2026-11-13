import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}
    team={c['id']:c['team'] for c in meta['champions']}
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}
    rix={r:i for i,r in enumerate(R['round'])}
    gc={g['id']:g['tiles'][0] for g in mp['groups']}
    prism={c['team']:c['id'] for c in meta['champions'] if c['name']=='Prism'}
    res=[]
    for e in ev:
        if e['k']=='capture' and e['team'] in prism:
            holders=[s[0] for s in e['shares']]
            if prism[e['team']] in holders: continue
            gems=sum(s[1] for s in e['shares'])
            if gems==0: continue
            p=ch[idx[prism[e['team']]]]; i=rix.get(e['r'],len(R['round'])-1)
            if not p['alive'][i] or p['x'][i] is None: res.append(('dead',gems)); continue
            t=gc[e['g']]; dd=max(abs(p['x'][i]-t[0]),abs(p['y'][i]-t[1]))
            res.append((dd,gems))
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows+=r
    c=Counter(); g=Counter()
    for d,gm in rows:
        b='dead' if d=='dead' else ('<=6' if d<=6 else '<=12' if d<=12 else '<=20' if d<=20 else '>20')
        c[b]+=1; g[b]+=gm
    print('ally gem captures in Prism games, by Prism distance:', dict(c), 'gems', dict(g))
if __name__=='__main__': main()
