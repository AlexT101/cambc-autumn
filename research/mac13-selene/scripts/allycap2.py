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
    ev_by_r={}
    for x in ev: ev_by_r.setdefault(x['r'],[]).append(x)
    for e in ev:
        if e['k']=='capture' and e['team'] in prism:
            holders=[s[0] for s in e['shares']]
            if prism[e['team']] in holders: continue
            gems=sum(s[1] for s in e['shares'])
            if gems==0: continue
            p=ch[idx[prism[e['team']]]]; i=rix.get(e['r'],len(R['round'])-1)
            if not p['alive'][i] or p['x'][i] is None: res.append(('dead',gems)); continue
            t=gc[e['g']]; dd=max(abs(p['x'][i]-t[0]),abs(p['y'][i]-t[1]))
            if dd<=12:
                st='chan%d'%p['chan'][i] if p['chan'][i] in (2,3) else None
                if not st:
                    pos=(p['x'][i],p['y'][i])
                    ingroup=any(pos==tuple(tt) for g2 in mp['groups'] for tt in g2['tiles'])
                    hit=any(x['k'] in('attack','cast') and x.get('a')==p['id'] and x.get('camp') is not None for x in ev_by_r.get(e['r'],[])+ev_by_r.get(e['r']-1,[]))
                    moved = i>0 and (p['x'][i-1],p['y'][i-1])!=pos
                    st='ongrouptile' if ingroup else ('hitcamp' if hit else ('walking' if moved else 'still'))
                res.append((st,gems))
            else: res.append((dd,gems))
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows+=r
    c=Counter(); g=Counter()
    for d,gm in rows:
        b=d if isinstance(d,str) else ('<=20' if d<=20 else '>20')
        c[b]+=1; g[b]+=gm
    print('ally gem captures in Prism games, by Prism distance:', dict(c), 'gems', dict(g))
if __name__=='__main__': main()
