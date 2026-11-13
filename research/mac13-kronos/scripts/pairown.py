# Pair deaths on own ground (side fraction < 0.4), r<=500: killer, fallen body, partner distance, warning.
import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}; tm={c['id']:c['team'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz')); C={c['id']:c for c in o['champions']}
    sp={}
    for c in o['champions']: sp.setdefault(c['team'],(c['x'][0],c['y'][0]))
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz')]
    out=[]; done=set()
    for i,e in enumerate(ev):
        if e['r']>500: break
        if e['k']!='death' or names[e['v']] not in('Cassi','Issac') or (e['r'],tm[e['v']]) in done: continue
        v=e['v']; t=tm[v]; a,b=sp[t],sp[1-t]; p=e['at']
        da=max(abs(p[0]-a[0]),abs(p[1]-a[1])); db=max(abs(p[0]-b[0]),abs(p[1]-b[1]))
        if da/max(1,da+db)>=0.4: continue
        done.add((e['r'],t))
        k=e.get('by'); kn=names.get(k,'camp') if isinstance(k,int) and k in tm and tm[k]!=t else 'camp'
        # fallen body: last damaging event on either
        pair=[c for c in m['champions'] if c['team']==t and c['name'] in('Cassi','Issac')]
        ids=[c['id'] for c in pair]; fallen='?'
        for q in reversed(ev[max(0,i-60):i]):
            tg=q.get('tgt')
            if q.get('dmg') is not None and tg in ids: fallen=names[tg]; break
        r=e['r']; pc=[C[x] for x in ids]
        dist=None
        if all(c['x'][r-1] is not None for c in pc): dist=max(abs(pc[0]['x'][r-1]-pc[1]['x'][r-1]),abs(pc[0]['y'][r-1]-pc[1]['y'][r-1]))
        fid=[x for x in ids if names[x]==fallen]
        warn=None; hp5=None
        if fid and isinstance(k,int) and k in C:
            fc=C[fid[0]]; warn=any(k in (fc['sees'][rr] or []) for rr in range(max(0,r-6),r-1))
            hp5=fc['hp'][r-5]/max(1,fc['maxHp'][r-5]) if fc['hp'][r-5] is not None else None
        out.append((kn,fallen,dist,warn,hp5,r))
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for r in p.map(one,fs,chunksize=4) if r for x in r]
    print('own-ground pair deaths r<=500',len(R))
    print('killer',collections.Counter(x[0] for x in R).most_common(8))
    print('fallen',collections.Counter(x[1] for x in R))
    print('partner dist',collections.Counter(min(x[2],12) if x[2] is not None else None for x in R).most_common())
    print('fallen saw killer 2-6 rounds before',collections.Counter(x[3] for x in R))
    h=[x[4] for x in R if x[4] is not None]; print('fallen hp fraction 5 rounds before quartiles',sorted(h)[len(h)//4::len(h)//4])
    print('rounds quartiles',sorted(x[5] for x in R)[len(R)//4::len(R)//4])
