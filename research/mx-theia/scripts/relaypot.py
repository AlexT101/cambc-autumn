# Relay potential: for each Prism capture B following a Prism capture A (r<=LIMIT), the rounds from A's payout to B's
# hold start, the Prism's clear rounds at B, and the share of B's camp damage dealt before the Prism's first hit on B.
import json,gzip,sys,os,collections,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; LIMIT=int(sys.argv[2]) if len(sys.argv)>2 else 300
def one(d):
    d=os.path.join(ROOT,d)
    try: meta=json.load(open(d+'/meta.json')); ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    except Exception: return []
    names={c['id']:c['name'] for c in meta['champions']}; P={i for i,n in names.items() if n=='Prism'}
    g_of={}; dmg=collections.defaultdict(list); hold={}; last={}; rows=[]
    for e in ev:
        if e['r']>LIMIT: break
        if e['k'] in ('attack','cast') and e.get('cdmg'):
            for camp,amt in e['cdmg']: dmg[camp].append((e['r'],e['a'],amt))
        if e['k']=='camp_death': g_of[e['camp']]=e['g']
        if e['k']=='capture_hold' and e['team'] in (0,1): hold[(e['g'],e['team'])]=e['r']
        if e['k']=='capture' and e['team'] in (0,1):
            camps=[c for c,g in g_of.items() if g==e['g']]
            for s in e['shares']:
                p=s[0]
                if p not in P: continue
                hs=hold.get((e['g'],e['team']),e['r']-6)
                hits=[x for c in camps for x in dmg.get(c,[])]
                tot=sum(x[2] for x in hits) or 1
                ph=[x[0] for x in hits if x[1]==p]
                if p in last and ph:
                    first=min(ph); pre=sum(x[2] for x in hits if x[0]<first)/tot
                    rows.append(dict(gap=hs-last[p],clear=hs-first,pre=pre))
                elif p in last and not ph:
                    rows.append(dict(gap=hs-last[p],clear=0,pre=1.0))
                last[p]=e['r']
            for c in camps: g_of.pop(c,None); dmg.pop(c,None)
            hold.pop((e['g'],e['team']),None)
    return rows
if __name__=='__main__':
    idx=json.load(open(ROOT+'/index.json')); dirs=sorted({g['dir'] for g in idx['games']})
    with ProcessPoolExecutor(32) as ex: rows=[x for l in ex.map(one,dirs,chunksize=8) for x in l]
    print('consecutive Prism captures',len(rows))
    print('payout->next hold start median %d mean %.1f; Prism first hit->hold start mean %.1f'%(statistics.median(r['gap'] for r in rows),statistics.mean(r['gap'] for r in rows),statistics.mean(r['clear'] for r in rows)))
    print('share of B cleared before the Prism hit it: mean %.2f; fully pre-cleared %.2f; none %.2f'%(statistics.mean(r['pre'] for r in rows),sum(r['pre']>=0.999 for r in rows)/len(rows),sum(r['pre']<=0.001 for r in rows)/len(rows)))
