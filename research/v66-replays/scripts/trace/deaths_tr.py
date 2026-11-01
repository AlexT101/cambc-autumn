import sys; sys.path.insert(0,sys.argv[1]); sys.path.insert(0,sys.argv[1]+'/../extract')
from tlib import *
import common as C
from concurrent.futures import ProcessPoolExecutor
MAN={}
for g in json.load(open('replays/v66/manifest.json'))['games']:
    MAN[g['replay']]=g['group'][:8]+'-'+str(g['position'])
G={g['source']:g for g in C.games(distinct=False)}
def one(src):
    key=MAN.get(src); g=G[src]
    if not key: return []
    vf=f'{ROOT}/{key}/trace_validation.json'
    if not os.path.exists(vf): return []
    v=json.load(open(vf)); trust=v.get('ladder_trusted_through') or 0
    m=C.meta(g['dir']); team={c['id']:c['team'] for c in m['champions']}; NM={c['id']:c['name'] for c in m['champions']}
    ev=C.events(g['dir'])
    T,TV=load(key); out=[]
    # damage events to victim per (r) for killing window
    for e in ev:
        if e['k']!='death' or team[e['v']]!=g['us'] or e.get('linked') is not None: continue
        if e['r']>trust: continue
        vic=e['v']
        # last TT of victim with a=1 at or before death round (if its turn in death round came before death, includes it)
        cand=[(r,L['TT'][0]) for (r,c),L in T.items() if c==vic and L['TT'] and L['TT'][0].get('a')=='1' and r<=e['r']]
        if not cand: continue
        r0,tt=max(cand,key=lambda x:x[0])
        # damage received after that turn until death
        dmg=0.0; srcs=Counter()
        for x in ev:
            if x['r']<r0 or x['r']>e['r']: continue
            if x['k'] in('attack','cast'):
                for vv,a in (x.get('dmg') or []):
                    if vv==vic: dmg+=a; srcs[NM[x['a']]+':'+(x.get('ab') or 'atk')]+=a
            if x['k']=='camp_attack' and x.get('tgt')==vic: dmg+=x['dmg']; srcs['camp']+=x['dmg']
        L=T[(r0,vic)]
        home=[h for h in L['TE'] if h.get('k')=='home']
        out.append(dict(key=key,src=src,opp=g['opp'],r=e['r'],r0=r0,victim=NM[vic],killer=NM.get(e.get('by'),'camp'),gems=e['gems'],
            d=tt.get('d'),hp=float(tt.get('hp',0)),hq=float(tt.get('hq',0)),ls=tt.get('ls'),le=tt.get('le'),fs=tt.get('fs'),fe=tt.get('fe'),ts=tt.get('ts'),
            p=tt.get('p'),q=tt.get('q'),home=(home[-1].get('v'),home[-1].get('why')) if home else None,window_dmg=dmg,srcs=dict(srcs),
            sites=[a.get('s') for a in L['TA'] if a['a'] not in('recall','set_priority','cancel_channel')]))
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,list(G)) for x in o]
    json.dump(res,open(sys.argv[1]+'/deaths_tr.json','w'))
    print(len(res))
