import json,gzip,glob,collections,sys,os,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx=json.load(open(ROOT+'/index.json'))
teams_by_dir={g['dir']:g['teams'] for g in idx['games']}
def one(d):
    meta=json.load(open(d+'/meta.json')); tn=teams_by_dir.get(os.path.basename(d)) or [t.get('name') for t in meta['teams']]
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    out={}
    pr={c['id']:c['team'] for c in meta['champions'] if en[c['type']]=='Prism'}
    if len(pr)!=2 or len(set(pr.values()))!=2: return None
    first=next((e for e in ev if e['k']=='death' and e['v'] in pr),None)
    for team in (0,1):
        name=tn[team]; o={}
        for RR in (200,300,400):
            if len(R['round'])<RR: continue
            i=RR-1; tot=R['gems'][team][i]; p=0; f=0
            for ci,c in enumerate(R['champions']):
                if c['team']!=team: continue
                g=c['gems'][i] or 0; tot+=g
                if c['id'] in pr: p=g; f=c['foc'][i]
            o[RR]=(tot,p,f)
        o['win']=meta['result']['winner']==team
        o['first_prism_death']= first is not None and pr[first['v']]==team
        o['prism_killed_other']= first is not None and pr[first['v']]!=team
        out[name]=o
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: res=[r for r in ex.map(one,ds,chunksize=4) if r]
    A=collections.defaultdict(lambda:collections.defaultdict(list))
    for r in res:
        for n,o in r.items():
            for RR in (200,300,400):
                if RR in o: A[n][f'tot{RR}'].append(o[RR][0]); A[n][f'prism{RR}'].append(o[RR][1]); A[n][f'foc{RR}'].append(o[RR][2]); A[n][f'share{RR}'].append(o[RR][1]/max(1,o[RR][0]))
            A[n]['win'].append(o['win']); A[n]['firstdeath'].append(o['first_prism_death'])
    for n,d in A.items():
        print(n, ' '.join(f"{k}={statistics.mean(v):.3f}" if 'share' in k or k in('win','firstdeath') else f"{k}={statistics.mean(v):.0f}" for k,v in d.items()), 'n',len(d['win']))
