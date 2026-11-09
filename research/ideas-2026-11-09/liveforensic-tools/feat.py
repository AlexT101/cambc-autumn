import os
import gzip, json, pickle, sys, os
from pathlib import Path
from multiprocessing import Pool
G=Path('/home/ubuntu/tmp-offload/handoff/gate'); ROOT=Path('/home/ubuntu/cambc-autumn')
SC=os.path.expanduser('~/tmp-offload/liveforensic/')+''
cells,mc=pickle.load(open(SC+'cells.pkl','rb'))
idx=json.load(open(G/'analysis/index.json'))['games']
by={str((ROOT/g['source']).resolve()):g['dir'] for g in idx}
V=[86,87,88,89,90,91,93,95]
def path(v,k):
    o='inte' if k[2]=='fish' else 'mite'
    return G/'raw'/f'v{v}-r2'/o/f'{k[0]}-{k[1]}.repl26a'
def feat(job):
    v,k=job
    p=str(path(v,k).resolve())
    if p not in by: return (v,k,None)
    d=G/'analysis'/by[p]
    T=0 if k[1]=='a' else 1
    meta=json.load(open(d/'meta.json'))
    team={c['id']:c['team'] for c in meta['champions']}
    rd=json.load(gzip.open(d/'rounds.json.gz'))
    rounds=rd['round']
    def gem_at(t,r):
        i=min(range(len(rounds)),key=lambda i:abs(rounds[i]-r)) if rounds[-1]>=r else len(rounds)-1
        return rd['gems'][t][i]
    f={'rounds':rounds[-1]}
    for r in (200,400,600,800,1000):
        f[f'us{r}']=gem_at(T,r); f[f'op{r}']=gem_at(1-T,r)
    ours=[c for c in rd['champions'] if c['team']==T]
    f['oof']=sum(t==6 for c in ours for t in c['turn'])
    # earned gold at 300/600
    def earned(team_, r):
        i=min(len(rounds)-1, max(0,r-1)); return sum(c['earned'][i] for c in rd['champions'] if c['team']==team_)
    f['gold300us']=earned(T,300); f['gold300op']=earned(1-T,300)
    f['gold600us']=earned(T,600); f['gold600op']=earned(1-T,600)
    ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    cnt={}
    def inc(n,x=1): cnt[n]=cnt.get(n,0)+x
    for e in ev:
        kk=e['k']; r=e['r']; ph='e' if r<600 else 'l'
        a=e.get('a'); mine = team.get(a)==T if a is not None else None
        if kk=='lock_place':
            inc(f"lock_{'us' if e['team']==T else 'op'}_{ph}")
        elif kk=='tribute_blocked':
            inc(f"tblk_{'us' if mine else 'op'}_{ph}")
        elif kk=='tribute_cancel':
            inc(f"tcan_{'us' if mine else 'op'}_{e.get('cause')}_{ph}")
        elif kk=='tribute_end':
            inc(f"trib_{'us' if mine else 'op'}_{ph}"); inc(f"tribg_{'us' if mine else 'op'}_{ph}",e.get('gems',0))
        elif kk=='death':
            vic=team.get(e['v']); inc(f"death_{'us' if vic==T else 'op'}_{ph}"); inc(f"dgems_{'us' if vic==T else 'op'}_{ph}",e.get('gems',0) or 0)
        elif kk=='attack' and e.get('lock'):
            inc(f"lockhit_{'us' if mine else 'op'}_{ph}")
        elif kk=='capture':
            inc(f"cap_{'us' if e['team']==T else 'op'}_{ph}")
        elif kk=='shop' and mine:
            for it,dl in (e.get('items') or {}).items():
                if dl>0: inc('buy_'+it,dl)
        elif kk=='consumable' and mine:
            for it,dl in (e.get('cons') or {}).items():
                if dl>0: inc('cons_'+it+'_'+ph,dl)
    f.update(cnt)
    return (v,k,f)
if __name__=='__main__':
    jobs=[(v,k) for k,c in cells.items() for v in V if v in c]
    with Pool(int(sys.argv[1]) if len(sys.argv)>1 else 8) as P:
        res=P.map(feat,jobs,chunksize=8)
    out={}
    miss=0
    for v,k,f in res:
        if f is None: miss+=1; continue
        out[(v,k)]=f
    print('missing',miss,'ok',len(out))
    pickle.dump(out,open(SC+'feat.pkl','wb'))
