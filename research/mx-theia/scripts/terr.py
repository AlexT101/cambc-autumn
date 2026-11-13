# Territory/economy profile of a batch's games, winners vs losers (or by team name).
# usage: py terr.py ANALYSIS_DIR [BATCH_NAME_FILTER [CAND_TEAM_NAME]]  (with a cand name: CAND vs REF, else winner vs loser)
import json,gzip,glob,collections,sys,os,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx=json.load(open(ROOT+'/index.json'))
filt=sys.argv[2] if len(sys.argv)>2 else None
teams_by_dir={}
for g in idx['games']:
    if filt and filt not in g['source']: continue
    teams_by_dir[g['dir']]=g['teams']
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    try:
        meta=json.load(open(d+'/meta.json'))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(d+'/rounds.json.gz'))
        ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    except Exception as e:
        return None
    tn=teams_by_dir.get(os.path.basename(d))
    groups={g['id']:g for g in mp['groups']}
    camps={c['id']:c for c in mp['camps']}
    win=meta['result']['winner']
    out={}
    for team in (0,1):
        o=collections.Counter()
        o['win']=int(win==team)
        o['rounds']=meta['result']['rounds']
        out[team]=o
    # captures
    for e in ev:
        if e['k']=='capture':
            g=groups.get(e['g']); team=e['team']
            if g is None or team not in (0,1): continue
            side=g['side']; rel='mid' if side==-1 else ('own' if side==team else 'enemy')
            gems=sum(s[1] for s in e['shares']); gold=sum(s[2] for s in e['shares'])
            w='early' if e['r']<=300 else 'late'
            o=out[team]
            o[f'cap_{rel}']+=1; o[f'capgems_{rel}']+=gems
            o[f'cap_{rel}_{w}']+=1; o[f'capgems_{rel}_{w}']+=gems
            o['capgems']+=gems; o['capgold']+=gold; o['caps']+=1
            o['holders']+=len(e['shares'])
            types=set(g['types'])
            key='mono' if 'Monolith' in types else 'golem' if 'Golem' in types else 'elk' if 'Elk' in types else 'wolf' if 'Wolf' in types else 'cluster'
            o[f'capgems_{key}']+=gems; o[f'cap_{key}']+=1
        elif e['k']=='death':
            v=e['v']
            # team of victim
        elif e['k'] in ('attack','cast') and e.get('camp') is not None:
            pass
    # per-champion
    champs=meta['champions']
    team_of={c['id']:c['team'] for c in champs}
    for c in champs:
        o=out[c['team']]
        o['deaths']+=c['deaths']; o['kills']+=c['kills']
        o['gold']+=c['earnedGold']
        o[f'gold_{en[c["type"]]}']+=c['earnedGold']
    for e in ev:
        if e['k']=='death':
            o=out[team_of[e['v']]]
            o['gems_lost']+=e.get('gems',0) or 0
            if e.get('camp') is not None: o['camp_deaths']+=1
            if e['r']<=300: o['deaths_early']+=1
    # dispersion: mean over rounds of mean pairwise dist among alive bodies, and nearest ally dist
    CH=R['champions']
    n=len(R['round'])
    for team in (0,1):
        idxs=[i for i,c in enumerate(CH) if c['team']==team]
        tot=0;cnt=0;near_tot=0;ncnt=0;alone=0
        for i in range(0,min(n,600),5):
            pos=[(CH[k]['x'][i],CH[k]['y'][i]) for k in idxs if CH[k]['alive'][i] and CH[k]['x'][i] is not None]
            if len(pos)<2: continue
            for a in range(len(pos)):
                dm=min(cheb(pos[a],pos[b]) for b in range(len(pos)) if b!=a)
                near_tot+=dm; ncnt+=1
                alone+= dm>8
        o=out[team]
        o['near_ally']=near_tot/max(1,ncnt); o['alone_frac']=alone/max(1,ncnt)
        for RR in (150,300,600):
            if n>=RR:
                i=RR-1; tg=R['gems'][team][i]+sum((CH[k]['gems'][i] or 0) for k in idxs)
                o[f'tot{RR}']=tg
    return {'teams':tn,'o':out,'npicks':len(champs)//2}
if __name__=='__main__':
    ds=[os.path.join(ROOT,d) for d in teams_by_dir]
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,ds,chunksize=4) if r]
    W=collections.defaultdict(list); L=collections.defaultdict(list)
    bybot = len(sys.argv)>3
    for r in res:
        for team in (0,1):
            o=r['o'][team]
            if bybot: dst=W if r['teams'][team]==sys.argv[3] else L
            else: dst=W if o['win'] else L
            for k in set(list(r['o'][0].keys())+list(r['o'][1].keys())):
                dst[k].append(o.get(k,0))
    print('games',len(res))
    for k in sorted(set(W)|set(L)):
        w=statistics.mean(W[k]) if W[k] else 0; l=statistics.mean(L[k]) if L[k] else 0
        print(f'{k:24s} {"C" if bybot else "W"} {w:9.2f}  {"R" if bybot else "L"} {l:9.2f}  d {w-l:+8.2f}')
