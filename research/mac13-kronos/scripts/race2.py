import json,gzip,glob,collections,statistics,zipfile
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    w=m['result']['winner']; T=len(o['round']); L=1-w; sc=o['gems']
    def bags(team,r): return sum(c['gems'][r] for c in o['champions'] if c['team']==team and c['alive'][r])
    R0=next((r for r in range(T) if sc[L][r]+bags(L,r)>=1000),None)
    if R0 is None: return None
    out={}
    z=zipfile.ZipFile('/home/ubuntu/wt/mac13-kronos/'+m['source'])
    for team in (L,w):
        pid=[c['id'] for c in o['champions'] if c['team']==team and names[c['id']]=='Prism']
        if not pid: continue
        pid=pid[0]
        txt=z.read('team-%s.stdout'%('ab'[team])).decode('latin1')
        cnt=collections.Counter()
        for line in txt.splitlines():
            if line.startswith('D '):
                p=line.split()
                if len(p)>=4 and int(p[2])==pid and int(p[1])>=R0: cnt[p[3]]+=1
        out['LW'[team!=L]]=cnt
    # events: tributes by each team after R0
    ev=collections.Counter()
    team={c['id']:c['team'] for c in m['champions']}
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['r']<R0: continue
        if e['k'] in('tribute_start','tribute_cancel','tribute_end'):
            ev[('L' if team[e['a']]==L else 'W', names[e['a']]=='Prism', e['k'], e.get('cause',''))]+=1
    return (T-R0, out, ev, sc[L][R0]+bags(L,R0) - (sc[w][R0]+bags(w,R0)))
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=4) if x]
    print('games',len(R))
    for side in 'LW':
        tot=collections.Counter()
        for x in R:
            if side in x[1]: tot.update(x[1][side])
        s=sum(tot.values()); print(side,'prism branch shares after R0', {k:round(v/s,3) for k,v in tot.most_common(12)})
    ev=collections.Counter()
    for x in R: ev.update(x[2])
    for k,v in sorted(ev.items(),key=str): print(k, round(v/len(R),2))
    print('lead at R0 (loser total - winner total) median', statistics.median(x[3] for x in R))
