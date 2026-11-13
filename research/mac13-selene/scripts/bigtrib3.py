import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    rix={r:i for i,r in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    win=meta['result']['winner']
    res=Counter(); open_={}
    for e in ev:
        if e['k']=='tribute_start' and e['gems']>=200:
            i=rix.get(e['r']); a=e['a']; t=C[a]['team']; p=e['at']
            if i is None: continue
            al=sum(1 for c in R['champions'] if c['team']==t and c['id']!=a and c['alive'][i] and c['x'][i] is not None and max(abs(c['x'][i]-p[0]),abs(c['y'][i]-p[1]))<=4)
            en=sum(1 for c in R['champions'] if c['team']!=t and c['alive'][i] and c['x'][i] is not None and max(abs(c['x'][i]-p[0]),abs(c['y'][i]-p[1]))<=8)
            open_[a]=(min(al,2),min(en,2),int(t==win),e['r'],e['dur'])
        elif e['k'] in ('tribute_end','tribute_cancel') and e['a'] in open_:
            k=open_.pop(e['a']); out='end' if e['k']=='tribute_end' else e.get('cause')
            res[k[:3]+(out,)]+=1; res[('bag',min(e.get('gems',0)//200,4),'W' if k[2] else 'L',out)]+=1; res[('turns',out)]+=e['r']-k[3]; res[('dur',out)]+=k[4]; res[('n',out)]+=1
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r)
    n=len(dirs); print('tributes of 200+ gems: allies<=4 (0/1/2+), enemies<=8 at start (0/1/2+): attempts a game, success %, causes')
    for o in ('end','stun','lock','manual'): print(o,'n/game %.2f mean turns spent %.1f planned %.1f'%(tot[('n',o)]/n,tot[('turns',o)]/max(1,tot[('n',o)]),tot[('dur',o)]/max(1,tot[('n',o)])))
    for b in range(1,5):
        for w in 'WL':
            row={o:tot[('bag',b,w,o)] for o in ('end','stun','lock','manual')}; s_=sum(row.values())
            if s_: print('bag %d-%d'%(200*b,200*b+199),w,'%.2f/game'%(s_/n),'success %.0f%%'%(100*row['end']/s_))
    for al in range(3):
        for en in range(3):
            row={o:sum(v for k,v in tot.items() if len(k)==4 and k[0]==al and k[1]==en and k[3]==o) for o in ('end','stun','lock','manual','death')}
            s=sum(row.values())
            if s: print(al,en,'%.2f'%(s/n),'success %.0f%%'%(100*row['end']/s), {k:'%.0f%%'%(100*v/s) for k,v in row.items() if k!='end'})
if __name__=='__main__': main()
