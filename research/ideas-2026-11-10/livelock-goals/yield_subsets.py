"""Describe capture-yield reversals by the gate's structural altar-site classes."""
import collections,json,re,zipfile
from pathlib import Path
root=Path('/home/ubuntu/tmp-offload/livelock-goals')
features={d['name'].replace('_','-'):d['f'] for d in map(json.loads,Path('/home/ubuntu/tmp-offload/diverse/fresh/feat-v2.jsonl').read_text().splitlines())}
yre=re.compile(r'LGY (\d+) (\d+) g(-?\d+) farm(-?\d+) claim(-?\d+) from(-?\d+),(-?\d+) to(-?\d+),(-?\d+)')
dre=re.compile(r'LGD (\d+) (\d+) (.) farm(-?\d+) claim(-?\d+) from(-?\d+),(-?\d+) to(-?\d+),(-?\d+)')
result={}
for run in ['captrace','yieldtrace']:
    totals=collections.defaultdict(collections.Counter)
    for m in json.loads((root/run/'results.json').read_text())['matches']:
        f=features[Path(m['map']).stem.replace('_','-')]
        cls='one_site' if f['altars']==1 or (f['altars']==2 and (f['altar_centre'] or 0)<.06) else 'multi_site'
        c=totals[cls];c['games']+=1;c['rounds']+=m['rounds']
        with zipfile.ZipFile(m['replay']) as z:
            t=z.read('team-'+('a' if m['order'][0]==0 else 'b')+'.stdout').decode(errors='replace')
        ds={(int(a[0]),int(a[1])):a for a in dre.findall(t)}
        for a in yre.findall(t):
            rr,i,g,farm,claim,*pos=map(int,a);c['yields']+=1
            c['other_goal']+=farm>=0 and farm!=g and claim!=g
            nxt=ds.get((rr+1,i))
            c['immediate_back']+=bool(nxt and list(map(int,nxt[-2:]))==pos[:2])
    result[run]={k:dict(v) for k,v in totals.items()}
print(json.dumps(result,indent=2))
(root/'yield-subsets.json').write_text(json.dumps(result,indent=2))
