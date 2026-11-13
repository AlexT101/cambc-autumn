import json, gzip, sys, os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
T=(50,100,150,200,300)
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
    except Exception: return None
    win=meta['result']['winner']; cn={c['id']:c['name'] for c in meta['champions']}
    out=[]
    for c in R['champions']:
        if cn[c['id']]!='Prism': continue
        w=int(c['team']==win)
        out.append((w,[c['gems'][t-1] if t-1<len(c['gems']) else None for t in T],[c['foc'][t-1] if t-1<len(c['foc']) else None for t in T]))
    # team possession
    return out
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows+=r
    for w in (1,0):
        v=[x for x in rows if x[0]==w]
        print('W' if w else 'L', len(v), 'bag', ['%.0f'%(sum(x[1][i] for x in v if x[1][i] is not None)/max(1,sum(1 for x in v if x[1][i] is not None))) for i in range(len(T))],
              'focus', ['%.0f'%(sum(x[2][i] for x in v if x[2][i] is not None)/max(1,sum(1 for x in v if x[2][i] is not None))) for i in range(len(T))])
if __name__=='__main__': main()
