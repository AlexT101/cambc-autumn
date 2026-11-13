# How games end: final round, outcome, the winner's tributes (count, size, by Prism or not), the winning tribute,
# tribute cancels (cause), locks placed, the loser's tributed total and its Prism's bag at the end.
import json,gzip,sys,os,collections,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    res=meta['result']; w=res['winner']
    trib=[(e['r'],e['a'],e['gems'],team[e['a']]) for e in ev if e['k']=='tribute_end']
    canc=[(e.get('cause'),e['gems'],team[e['a']]) for e in ev if e['k']=='tribute_cancel']
    locks=collections.Counter(team.get(e['a'],e.get('team')) for e in ev if e['k']=='lock_place')
    starts=[(e['r'],e['a'],e['gems'],e['dur']) for e in ev if e['k']=='tribute_start']
    return dict(rounds=res['rounds'],outcome=res['outcome'],gems=res['gems'],w=w,trib=trib,canc=canc,locks=locks,names=names,starts=starts)
def main():
    idx=json.load(open(ROOT+'/index.json')); dirs=sorted({g['dir'] for g in idx['games']})
    with ProcessPoolExecutor(32) as ex: G=[x for x in ex.map(one,dirs,chunksize=8) if x]
    print('games',len(G),'outcome',collections.Counter(g['outcome'] for g in G))
    print('end round buckets',sorted(collections.Counter(min(g['rounds'],2000)//200*200 for g in G).items()))
    print('loser tributed at end: median',statistics.median(g['gems'][1-g['w']] for g in G),'buckets',sorted(collections.Counter(g['gems'][1-g['w']]//200*200 for g in G).items()))
    for lab,side in (('W',0),('L',1)):
        tt=[t for g in G for t in g['trib'] if (t[3]==g['w'])==(side==0)]
        pr=[t for t in tt if G and True]
        byp=collections.Counter(); size=collections.Counter()
        for g in G:
            for t in g['trib']:
                if (t[3]==g['w'])!=(side==0): continue
                byp[g['names'][t[1]]]+=t[2]
        tot=sum(byp.values())
        print(lab,'tributes/game %.1f gems/game %.0f'%(len(tt)/len(G),tot/len(G)),{k:round(v/tot,3) for k,v in byp.most_common(6)})
        print('  tribute size buckets',sorted(collections.Counter(min(t[2],600)//50*50 for t in tt).items()))
    fin=[]
    for g in G:
        wt=[t for t in g['trib'] if t[3]==g['w']]
        if g['outcome']==1 and wt: fin.append((wt[-1][2],g['names'][wt[-1][1]],len(wt)))
    print('winning tribute (outcome 1): size median',statistics.median(f[0] for f in fin) if fin else None,'by',collections.Counter(f[1] for f in fin).most_common(4),'tributes before it median',statistics.median(f[2] for f in fin) if fin else None)
    print('share of gems scored by the final tribute: %.2f'%(statistics.mean(f[0]/1000 for f in fin)))
    c=collections.Counter((x[0],'W' if x[2]==g['w'] else 'L') for g in G for x in g['canc']); print('cancels',c)
    print('cancelled gems W %.0f L %.0f per game'%(sum(x[1] for g in G for x in g['canc'] if x[2]==g['w'])/len(G),sum(x[1] for g in G for x in g['canc'] if x[2]!=g['w'])/len(G)))
    print('locks placed W %.2f L %.2f per game'%(sum(g['locks'].get(g['w'],0) for g in G)/len(G),sum(g['locks'].get(1-g['w'],0) for g in G)/len(G)))
if __name__=='__main__': main()
