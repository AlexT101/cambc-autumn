import hashlib,json
from pathlib import Path
H=Path('/home/ubuntu/tmp-offload/warding-2026-11-10');M=Path('/home/ubuntu/tmp-offload/mite-r5-fidelity')
mite=[r for r in json.loads((M/'features.json').read_text()) if r['cohort']=='r5']
base=Path('/home/ubuntu/tmp-offload/oppre/replays/others');idx=json.loads(Path('/home/ubuntu/tmp-offload/oppcls/an/index.json').read_text())
lookup={Path(g['source']).stem:g for g in idx['games']};other={}
for line in (base/'list.tsv').open():
 r=line.rstrip('\n').split('\t')
 if 'Ad Astra' not in r[6:8] or r[1]<'2026-11-09' or r[0] not in lookup:continue
 side=0 if r[6]=='Ad Astra' else 1;key=(r[3],side)
 if key not in other or other[key][1]<r[1]:other[key]=r
common=[r for r in mite if (r['map'],r['ms']) in other]
common.sort(key=lambda r:hashlib.sha256((r['map']+r['side']).encode()).hexdigest());chosen=common[:40];jobs=[]
for m in chosen:
 r=other[(m['map'],m['ms'])]
 a=lookup[r[0]];ap=Path('/home/ubuntu/tmp-offload/oppcls/an')/a['dir'];meta=json.loads((ap/'meta.json').read_text());mm=json.loads((Path(m['path'])/'meta.json').read_text());assert meta['map']['hash']==mm['map']['hash']
 for cohort,side,p,mid,created in [('Mite-r5',m['ms'],m['path'],m['match'],'2026-11-10T06'),('Ocean-v105',1-m['ms'],m['path'],m['match'],'2026-11-10T06'),('Ad-Astra',m['ms'],str(ap),r[0],r[1])]:
  jobs.append(dict(cohort=cohort,side=side,path=p,match=mid,map=m['map'],created=created))
(H/'jobs.json').write_text(json.dumps(jobs,indent=1));print(len(common),'common cells;',len(chosen),'selected;',len(jobs),'cohort views')
