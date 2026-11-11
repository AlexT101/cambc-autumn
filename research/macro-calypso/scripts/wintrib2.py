import gzip, json, sys, collections
from pathlib import Path
an=Path(sys.argv[1]); c=collections.Counter()
near=collections.Counter()
for d in sorted(p.parent for p in an.glob('*/meta.json')):
    meta=json.loads((d/'meta.json').read_text()); win=meta['result']['winner']; team={x['id']:x['team'] for x in meta['champions']}
    R=json.load(gzip.open(d/'rounds.json.gz')); ch=R['champions']
    ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    for e in ev:
        if e['k']=='tribute_start' and e['gems']>=200:
            t=team[e['a']]; c['start']+=1
            r=e['r']; at=e['at']
            na=sum(1 for o in ch if o['team']==t and o['id']!=e['a'] and o['alive'][r] and o['x'][r] is not None and max(abs(o['x'][r]-at[0]),abs(o['y'][r]-at[1]))<=6)
            ne=sum(1 for o in ch if o['team']!=t and o['alive'][r] and o['x'][r] is not None and max(abs(o['x'][r]-at[0]),abs(o['y'][r]-at[1]))<=10)
            # outcome: find next tribute_end/cancel/death for a
            out='?'
            for f in ev:
                if f['s']<=e['s']: continue
                if f['k']=='tribute_end' and f['a']==e['a']: out='done'; break
                if f['k']=='tribute_cancel' and f['a']==e['a']: out='cancel:'+str(f.get('cause',f.get('why','')))[:10]; break
                if f['k']=='death' and f['v']==e['a']: out='died'; break
            c[out.split(':')[0]]+=1
            near[(min(na,4),min(ne,3),out.split(':')[0])]+=1
print(c)
for k in sorted(near): print(k, near[k])
