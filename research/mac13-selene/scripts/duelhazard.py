"""Non-Prism carriers (100+ gems) within 5 of the enemy Prism: P(killed by it within 10), and by window for Prisms."""
import json, gzip, sys, os, math
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def opening(foc, st): return 2.5*foc + 2*st
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    pr={c['team']:c['id'] for c in meta['champions'] if c['name']=='Prism'}
    cn={c['id']:c['name'] for c in meta['champions']}
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}; rounds=R['round']
    kill={}
    for e in ev:
        if e['k']=='death' and e.get('by') in pr.values(): kill.setdefault(e['v'],set()).add(e['r'])
    out=Counter()
    for c in ch:
        t=c['team']
        if (1-t) not in pr: continue
        q=ch[idx[pr[1-t]]]; ks=kill.get(c['id'],set()); isp=cn[c['id']]=='Prism'
        for i,r in enumerate(rounds):
            if not c['alive'][i] or not q['alive'][i] or c['x'][i] is None or q['x'][i] is None: continue
            if max(abs(c['x'][i]-q['x'][i]),abs(c['y'][i]-q['y'][i]))>5: continue
            if isp:
                ours=math.ceil((c['hp'][i]+(c['shield'][i] or 0))/opening(q['foc'][i],q['str'][i]))
                theirs=math.ceil((q['hp'][i]+(q['shield'][i] or 0))/opening(c['foc'][i],c['str'][i]))
                cls='P-lose' if ours<theirs else 'P-flip' if ours==theirs else 'P-win'
            else:
                if c['gems'][i]<100: cls='other-empty'
                else: cls='other-carrier'
            out[(cls,'n')]+=1
            for w in (5,10,20):
                if any(r<k<=r+w for k in ks): out[(cls,w)]+=1
    return out
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x))]
    C=Counter()
    with ProcessPoolExecutor(48) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: C.update(r)
    for cls in ('P-lose','P-flip','P-win','other-carrier','other-empty'):
        n=C[(cls,'n')]
        print(cls, n, ' '.join(f"w{w} {C[(cls,w)]/max(1,n):.4f}" for w in (5,10,20)))
if __name__ == "__main__": main()
