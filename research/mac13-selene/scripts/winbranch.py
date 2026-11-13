import zipfile, re, sys, os, json, gzip
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
A='replays/.analysis'
def one(g):
    try:
        d=os.path.join(A,g['dir']) if not os.path.isabs(g['dir']) else g['dir']
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz'))); meta=json.load(open(os.path.join(d,'meta.json')))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        z=zipfile.ZipFile(g['source'])
    except Exception as e: return None
    rix={r:i for i,r in enumerate(R['round'])}; n=len(R['round'])
    team={c['id']:c['team'] for c in R['champions']}
    dead=[[0]*n,[0]*n]
    for c in R['champions']:
        for i,a in enumerate(c['alive']):
            if not a: dead[c['team']][i]+=1
    pos={c['id']:(c['x'],c['y']) for c in R['champions']}
    sp=mp['spawn']; W=mp['width']; H=mp['height']
    def cen(s): return ((s['minX']+s['maxX'])/2,(s['minY']+s['maxY'])/2)
    sc=[cen(sp[0]),cen(sp[1])]
    c=Counter()
    for nm in z.namelist():
        if not nm.endswith('.stdout'): continue
        for m in D.finditer(z.read(nm)):
            r=int(m.group(1)); cid=int(m.group(2)); b=m.group(3).decode(); i=rix.get(r)
            if i is None or cid not in team: continue
            t=team[cid]; k=min(3,dead[1-t][i])
            x,y=pos[cid][0][i],pos[cid][1][i]
            if x is None: continue
            do=max(abs(x-sc[t][0]),abs(y-sc[t][1])); de=max(abs(x-sc[1-t][0]),abs(y-sc[1-t][1]))
            zone='own' if de/(do+de+1e-9)>0.6 else 'enemy' if de/(do+de+1e-9)<0.4 else 'mid'
            c[(k,b)]+=1; c[(k,'zone_'+zone)]+=1; c[(k,'ALL')]+=1
    return c
if __name__=='__main__':
    idx=json.load(open(A+'/index.json'))
    gs=[g for g in idx['games'] if 'mirdbg' in g['source']]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for c in ex.map(one,gs,chunksize=4):
            if c: tot.update(c)
    bs=[b for b,_ in Counter({b:n for (k,b),n in tot.items() if k==0}).most_common(14)]
    print('k', *bs)
    for k in range(4):
        a=tot[(k,'ALL')] or 1
        print(k, a, *('%.1f'%(100*tot[(k,b)]/a) for b in bs))
