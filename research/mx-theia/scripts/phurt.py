# Share of the Prism's alive rounds (r<=LIMIT, off spawn) in the hurt band [0.109, 0.453) of max health, with the
# bag carried then; and how long such a stretch lasts.
import json,gzip,sys,os,collections,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; LIMIT=int(sys.argv[2]) if len(sys.argv)>2 else 600
def one(d):
    d=os.path.join(ROOT,d)
    try: meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; out=collections.Counter(); runs=[]
    for c in R['champions']:
        if names[c['id']]!='Prism': continue
        run=0
        for t,r in enumerate(R['round']):
            if r>LIMIT: break
            if not c['alive'][t]: continue
            f=c['hp'][t]/c['maxHp'][t]; out['alive']+=1
            if 0.109<=f<0.453: out['hurt']+=1; out['hurt_gems']+=c['gems'][t]; run+=1
            else:
                if run: runs.append(run)
                run=0
            out['gems']+=c['gems'][t]
    out['runs']=len(runs); out['runlen']=sum(runs)
    return out
if __name__=='__main__':
    idx=json.load(open(ROOT+'/index.json')); dirs=sorted({g['dir'] for g in idx['games']})
    with ProcessPoolExecutor(32) as ex: res=[x for x in ex.map(one,dirs,chunksize=8) if x]
    T=collections.Counter()
    for r in res: T.update(r)
    print('Prism alive rounds in hurt band %.3f; mean bag then %.0f vs overall %.0f; stretches/game %.1f mean length %.1f'%(T['hurt']/T['alive'],T['hurt_gems']/max(1,T['hurt']),T['gems']/T['alive'],T['runs']/len(res),T['runlen']/max(1,T['runs'])))
