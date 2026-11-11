import gzip, json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def one(d):
    meta=json.loads((d/'meta.json').read_text()); win=meta['result']['winner']
    R=json.load(gzip.open(d/'rounds.json.gz'))
    ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}
    out=[]
    for e in ev:
        if e['k']=='recall_end':
            c=ch[idx[e['a']]]; r=max(0,e['r']-6)
            out.append(dict(w=c['team']==win, hp=c['hp'][r]/c['maxHp'][r], gold=c['gold'][r], gems=c['gems'][r], r=e['r']))
    return out
if __name__=='__main__':
  dirs=sorted(p.parent for p in Path(sys.argv[1]).glob('*/meta.json'))
  with ProcessPoolExecutor(32) as ex: res=[x for r in ex.map(one,dirs) for x in r]
  print(len(res)/len(dirs)/2,'recalls/team-game')
  print('hp buckets', sorted(collections.Counter(round(x['hp'],1) for x in res).items()))
  print('gold buckets', sorted(collections.Counter(min(x['gold']//50*50,500) for x in res).items()))
  print('gems>0', sum(x['gems']>0 for x in res)/len(res), 'mean gems', sum(x['gems'] for x in res)/len(res))
  hi=[x for x in res if x['hp']>0.7]; print('hp>0.7 share', len(hi)/len(res), 'of those gold>=150', sum(x['gold']>=150 for x in hi)/max(1,len(hi)), 'gems>0', sum(x['gems']>0 for x in hi)/max(1,len(hi)))
  full=[x for x in res if x['hp']>=0.95]
  print('full hp', len(full)/len(res), 'gems0', sum(x['gems']==0 for x in full)/len(full), 'gold<30 & gems0', sum(x['gems']==0 and x['gold']<30 for x in full)/len(full))
