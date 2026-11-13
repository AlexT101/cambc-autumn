# Allies' (non-Prism) camp damage r<=LIMIT by what became of the group: captured with the Prism sharing, captured by
# allies only, captured by the enemy, not captured by LIMIT+100. W vs L. Plus Prism damage the same way.
import json,gzip,sys,os,collections
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; LIMIT=int(sys.argv[2]) if len(sys.argv)>2 else 150
def one(d):
    d=os.path.join(ROOT,d)
    try: meta=json.load(open(d+'/meta.json')); ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}; w=meta['result']['winner']
    pending=collections.defaultdict(list)  # camp -> [(team, who, amt)]
    g_of={}; out=collections.Counter()
    def settle(g,fate_by_team):
        for c in [c for c,gg in g_of.items() if gg==g]:
            for t,who,amt in pending.pop(c,[]):
                lab='W' if t==w else 'L'; out[(lab,who,fate_by_team(t))]+=amt
            g_of.pop(c,None)
    for e in ev:
        if e['r']>LIMIT+100: break
        if e['k'] in ('attack','cast') and e.get('cdmg') and e['r']<=LIMIT:
            for camp,amt in e['cdmg']: pending[camp].append((team[e['a']],'Prism' if names[e['a']]=='Prism' else 'ally',amt))
        if e['k']=='camp_death': g_of[e['camp']]=e['g']
        if e['k']=='capture':
            pr=any(names[s[0]]=='Prism' for s in e['shares']); ct=e['team']
            settle(e['g'],lambda t: ('own+Prism' if pr else 'own,no Prism') if t==ct else 'enemy took')
    for c,l in pending.items():
        for t,who,amt in l: out[('W' if t==w else 'L',who,'not captured')]+=amt
    return out
if __name__=='__main__':
    idx=json.load(open(ROOT+'/index.json')); dirs=sorted({g['dir'] for g in idx['games']})
    with ProcessPoolExecutor(32) as ex: res=[x for x in ex.map(one,dirs,chunksize=8) if x]
    T=collections.Counter()
    for r in res: T.update(r)
    for lab in 'WL':
        for who in ('Prism','ally'):
            tot=sum(v for k,v in T.items() if k[0]==lab and k[1]==who)
            print(lab,who,'camp dmg/game %.0f'%(tot/len(res)),{k[2]:round(v/tot,3) for k,v in T.items() if k[0]==lab and k[1]==who})
