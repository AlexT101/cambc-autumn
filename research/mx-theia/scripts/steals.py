# Captures where the other team dealt part of the group's damage since its last respawn: gems "stolen" (weighted
# by the other team's damage share), by group side (from the capturer's view) and round window. Per team (W/L or names).
import json,gzip,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; CAND=sys.argv[2] if len(sys.argv)>2 else None
idx=json.load(open(ROOT+'/index.json'))
rows={}
for g in idx['games']: rows.setdefault(g['dir'],g)
def one(item):
    dname,row=item; d=os.path.join(ROOT,dname)
    try:
        meta=json.load(open(d+'/meta.json')); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    except Exception: return None
    team_of={c['id']:c['team'] for c in meta['champions']}
    camp_g={c['id']:c['group'] for c in mp['camps']}
    groups={g['id']:g for g in mp['groups']}
    dmg=collections.defaultdict(lambda:[0.0,0.0])
    win=meta['result']['winner']
    def key(team): return (row['teams'][team]==CAND) if CAND else (team==win)
    out=collections.Counter()
    for e in ev:
        k=e['k']
        if k in ('attack','cast') and e.get('cdmg'):
            for c,amt in e['cdmg']:
                g=camp_g.get(c)
                if g is not None: dmg[g][team_of[e['a']]]+=amt
        elif k=='group_respawn':
            dmg[e['g']]=[0.0,0.0]
        elif k=='capture':
            g=e['g']; t=e['team']
            if t not in (0,1): continue
            gem=sum(s[1] for s in e['shares'])
            dd=dmg[g]; tot=dd[0]+dd[1]
            share_other=dd[1-t]/tot if tot>0 else 0
            G=groups.get(g); side=G['side'] if G else -1
            rel='mid' if side==-1 else 'own' if side==t else 'enemy'
            out[(key(t),'cap_gems')]+=gem
            out[(key(t),'stole_gems')]+=gem*share_other     # capturer took other's work
            out[(key(1-t),'lost_gems')]+=gem*share_other     # victim's lost work
            out[(key(1-t),f'lost_{"own" if rel=="enemy" else "enemy" if rel=="own" else "mid"}')]+=gem*share_other
            if share_other>0.5: out[(key(t),'steals_n')]+=1
            dmg[g]=[0.0,0.0]
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,list(rows.items()),chunksize=4) if r]
    T=collections.Counter()
    for r in res: T.update(r)
    n=len(res)
    for side in (True,False):
        lab=('CAND' if side else 'REF') if CAND else ('W' if side else 'L')
        print(lab, {k[1]:round(v/n,1) for k,v in sorted(T.items()) if k[0]==side})
