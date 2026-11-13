import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    cn={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}; rix={r:i for i,r in enumerate(R['round'])}
    out=[]
    for e in ev:
        if e['k']=='death' and cn.get(e['v'])=='Prism' and cn.get(e.get('by'))=='Prism':
            i=rix.get(e['r']-1,0); v=ch[idx[e['v']]]; k=ch[idx[e['by']]]
            ratio=(k['foc'][i] or 1)/(v['foc'][i] or 1)
            # allies within 6 of killer and victim
            def near(c):
                return sum(1 for o in ch if o['team']==c['team'] and o['id']!=c['id'] and o['alive'][i] and o['x'][i] is not None and c['x'][i] is not None and max(abs(o['x'][i]-c['x'][i]),abs(o['y'][i]-c['y'][i]))<=6)
            out.append((ratio, near(k), near(v)))
    return out
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows+=r
    print('prism-on-prism kills',len(rows))
    b=Counter()
    for r,_,_ in rows: b['<0.8' if r<0.8 else '0.8-1.25' if r<=1.25 else '1.25-2' if r<=2 else '>2']+=1
    print('killer/victim focus ratio', dict(b))
    print('support killer-victim', Counter((min(k,3),min(v,3)) for _,k,v in rows).most_common(10))
if __name__=='__main__': main()
