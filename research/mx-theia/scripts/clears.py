# Who clears the groups each team captures (camp damage by champion type, r<=LIMIT), split by whether the Prism
# took a share; clear duration (first hit to group_clear) and wait from clear to hold start. W vs L.
import json,gzip,sys,os,collections,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; LIMIT=int(sys.argv[2]) if len(sys.argv)>2 else 600
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    w=meta['result']['winner']; out=collections.Counter()
    dmg=collections.defaultdict(collections.Counter); first={}; clear={}; hold={}
    gid_of_camp={}
    for e in ev:
        if e['r']>LIMIT: break
        if e['k'] in ('attack','cast') and e.get('cdmg'):
            for camp,amt in e['cdmg']:
                dmg[camp][e['a']]+=amt
        if e['k']=='camp_death': gid_of_camp[e['camp']]=e['g']
        if e['k']=='group_clear': clear[e['g']]=e['r']
        if e['k']=='capture_hold' and e['team'] in (0,1): hold.setdefault((e['g'],e['team']),e['r'])
        if e['k']=='capture' and e['team'] in (0,1):
            g=e['g']; t=e['team']; lab='W' if t==w else 'L'
            camps=[c for c,gg in gid_of_camp.items() if gg==g]
            tot=collections.Counter()
            for c in camps: tot.update(dmg.pop(c,{}))
            for c in camps: gid_of_camp.pop(c,None)
            gems=sum(s[1] for s in e['shares'])
            pshare=any(names[s[0]]=='Prism' for s in e['shares'])
            k='P' if pshare else 'o'
            out[(lab,k,'n')]+=1; out[(lab,k,'gems')]+=gems
            T=sum(v for a,v in tot.items() if team.get(a)==t) or 1
            for a,v in tot.items():
                if team.get(a)==t: out[(lab,k,'dmg',names[a] if names[a]=='Prism' else 'ally')]+=v/T
            if g in clear and (g,t) in hold: out[(lab,k,'wait')]+=max(0,hold[(g,t)]-clear[g]); out[(lab,k,'waitn')]+=1
            hold.pop((g,t),None)
    return out
def main():
    idx=json.load(open(ROOT+'/index.json')); dirs=sorted({g['dir'] for g in idx['games']})
    with ProcessPoolExecutor(32) as ex: res=[x for x in ex.map(one,dirs,chunksize=8) if x]
    T=collections.Counter()
    for r in res: T.update(r)
    n=len(res)
    for lab in 'WL':
        for k in 'Po':
            N=T[(lab,k,'n')] or 1
            print(lab,'Prism-share' if k=='P' else 'no-Prism','captures/game %.1f gems/game %.0f'%(N/n,T[(lab,k,'gems')]/n),'clear dmg share Prism %.2f allies %.2f'%(T[(lab,k,'dmg','Prism')]/N,T[(lab,k,'dmg','ally')]/N),'clear->hold wait %.1f'%(T[(lab,k,'wait')]/max(1,T[(lab,k,'waitn')])))
if __name__=='__main__': main()
