import collections,gzip,json,os,sys
from multiprocessing import Pool
from pathlib import Path
R=Path('/home/ubuntu/cambc-autumn');H=Path('/home/ubuntu/tmp-offload/warding-2026-11-10')
from timing import run as timing

def one(job):
 row=timing(job);p=Path(job['path']);m=json.loads((p/'meta.json').read_text());mp=json.loads((p/m['mapFile']).resolve().read_text());bush={tuple(t) for t in mp['bushes']};camp={(c['x'],c['y']) for c in mp['camps']};rd=json.load(gzip.open(p/'rounds.json.gz','rt'))
 row['counts']['bush_wards']=sum(tuple(w['to']) in bush for w in row['wards']);row['counts']['camp_wards']=sum(tuple(w['to']) in camp for w in row['wards']);row['counts']['alive_rounds']=sum(sum(c['alive']) for c in rd['champions'] if c['team']==job['side']);return row

if __name__=='__main__':
 jobs=[]
 for p in sorted((H/'adastra-current-analysis').glob('*/meta.json')):
  m=json.loads(p.read_text());assert m['validation']['ok'],p
  side=next(i for i,t in enumerate(m['teams']) if t['name']=='Ad Astra');src=(R/m['source']).resolve();g=json.loads((src.parent/'group.json').read_text());position=int(src.name.split('-')[0]);match=next(v for v in g['matches'] if v['position']==position)
  jobs.append(dict(cohort='Ad-Astra-20261110',side=side,path=str(p.parent),match=match['id'],map=m['map']['name'],created=g['group']['createdAt'],opponent=m['teams'][1-side]['name']))
 assert len(jobs)==40
 (H/'current-adastra-jobs.json').write_text(json.dumps(jobs,indent=1))
 with Pool(int(os.environ.get('OMP_NUM_THREADS','2'))) as pool:out=list(pool.imap(one,jobs))
 (H/'current-adastra-timing.json').write_text(json.dumps(out));c=collections.Counter()
 for row in out:c.update(row['counts'])
 print(dict(c));print('interval',min(j['created'] for j in jobs),max(j['created'] for j in jobs));print('opponents',dict(collections.Counter(j['opponent'] for j in jobs)))
