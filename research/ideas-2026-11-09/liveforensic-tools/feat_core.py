import os
import gzip, json
def features(d,T):
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
    return f
