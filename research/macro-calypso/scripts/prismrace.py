import gzip, json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def one(d):
    meta=json.loads((d/'meta.json').read_text()); win=meta['result']['winner']
    R=json.load(gzip.open(d/'rounds.json.gz')); ch=R['champions']
    enums=json.load(open(d.parent/'enums.json'))
    names=enums['champions']
    pr=[c for c in ch if 'Prism' in str(c.get('type', ''))]
    return (win, ch, R['gems'])
def main():
    an=Path(sys.argv[1]); enums=json.load(open(an/'enums.json'))
    dirs=sorted(p.parent for p in an.glob('*/meta.json'))
    res=collections.Counter(); n=0
    for d in dirs:
        meta=json.loads((d/'meta.json').read_text()); win=meta['result']['winner']
        R=json.load(gzip.open(d/'rounds.json.gz')); ch=R['champions']
        if n==0: print(ch[0].get('type'), [k for k in meta.keys()]); 
        n+=1
        picks=meta.get('picks') or meta.get('teams')
        pr={}
        names={c['id']:c['name'] for c in meta['champions']}
        for c in ch:
            if names.get(c['id'])=='Prism': pr[c['team']]=c
        if len(pr)<2: res['noprism-mirror']+=1; continue
        for r in (200,300,400,500):
            if r>=len(R['round']): continue
            g0=pr[0]['gems'][r] if pr[0]['alive'][r] else 0; g1=pr[1]['gems'][r] if pr[1]['alive'][r] else 0
            if g0==g1: continue
            big=0 if g0>g1 else 1
            res[(r,'bigger prism wins')]+= (big==win); res[(r,'n')]+=1
    for k,v in sorted(res.items(), key=str): print(k,v)
main()
