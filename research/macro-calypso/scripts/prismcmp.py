import gzip, json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def one(d):
    meta=json.loads((d/'meta.json').read_text())
    tn=[t.get('name') for t in meta['teams']]
    names={x['id']:x['name'] for x in meta['champions']}; team={x['id']:x['team'] for x in meta['champions']}
    win=meta['result']['winner']
    R=json.load(gzip.open(d/'rounds.json.gz')); ch=R['champions']
    out=collections.Counter()
    for t in (0,1):
        out[(tn[t],'games')]+=1; out[(tn[t],'wins')]+= win==t
    pr={c['team']:c for c in ch if names[c['id']]=='Prism'}
    for t,c in pr.items():
        for r in (300,500):
            if r<len(c['gems']): out[(tn[t],f'prism_gems{r}')]+= c['gems'][r] if c['alive'][r] else 0; out[(tn[t],f'prism_n{r}')]+=1
    first=None
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and 'linked' not in e:
            t=team[e['v']]
            out[(tn[t],'deaths')]+=1; out[(tn[t],'gems_lost')]+=e['gems']
            if names[e['v']]=='Prism':
                out[(tn[t],'prism_deaths')]+=1
                if e['gems']>=50:
                    out[(tn[t],'prism_big_deaths')]+=1
                    if first is None: first=t; out[(tn[t],'first_big_prism_death')]+=1; out[(tn[t],'first_and_won')]+= win==t
        if e['k']=='tribute_end' and e['gems']>=200: out[(tn[team[e['a']]],'big_tributes')]+=1
        if e['k']=='tribute_start' and e['gems']>=200: out[(tn[team[e['a']]],'big_trib_starts')]+=1
    return out
if __name__=='__main__':
    an=Path(sys.argv[1]); dirs=sorted(p.parent for p in an.glob('*/meta.json'))
    tot=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one,dirs): tot+=o
    teams=sorted({k[0] for k in tot})
    keys=sorted({k[1] for k in tot})
    for k in keys: print(f'{k:24s}', '  '.join(f'{t}:{tot[(t,k)]}' for t in teams))
