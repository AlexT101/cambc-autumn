import json,gzip,glob,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; WHO=sys.argv[2]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx={g['dir']:g for g in json.load(open(ROOT+'/index.json'))['games']}
def one(d):
    g=idx.get(os.path.basename(d))
    if not g or WHO not in g['teams']: return None
    us=g['teams'].index(WHO); meta=json.load(open(d+'/meta.json'))
    pr={c['id']:c['team'] for c in meta['champions'] if en[c['type']]=='Prism'}
    if us not in pr.values(): return ('we have no Prism', g['winner']==us)
    f=None
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and e['v'] in pr: f=pr[e['v']]; break
    k='our Prism dies first' if f==us else 'theirs dies first' if f is not None else 'no Prism death'
    return (k, g['winner']==us)
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[s for s in ex.map(one,ds,chunksize=4) if s]
    N=collections.Counter(k for k,_ in S); W=collections.Counter(k for k,w in S if w)
    for k in N: print('%-22s %4d games, win %.1f%%'%(k,N[k],100*W[k]/N[k]))
    print('all',len(S),'%.1f'%(100*sum(w for _,w in S)/len(S)))
