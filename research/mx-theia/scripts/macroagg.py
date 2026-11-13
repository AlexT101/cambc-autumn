# analysis.macro metrics averaged winner vs loser (or CAND vs REF) over N games of an extract dir.
import os,sys,json,statistics,collections
sys.path.insert(0,'/home/ubuntu/wt/mx-theia/tools/replay')
os.environ['CAMBC_ANALYSIS']=sys.argv[1]
from analysis import Game, macro
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; N=int(sys.argv[2]); CAND=sys.argv[3] if len(sys.argv)>3 else None
idx=json.load(open(ROOT+'/index.json'))
dirs=sorted(set(g['dir'] for g in idx['games']))[:N]
def one(d):
    try:
        g=Game(d); o=macro.extract(g); S=o['sides']
        out=[]
        for t in (0,1):
            k=(g.names[t]==CAND) if CAND else (t==g.winner)
            out.append((k,{m:S[t][m] for m in macro.METRICS}))
        return out
    except Exception as e: return None
if __name__=='__main__':
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,dirs) if r]
    A=collections.defaultdict(lambda:collections.defaultdict(list))
    for r in res:
        for k,m in r:
            for kk,v in m.items():
                if isinstance(v,(int,float)) and v is not None: A[k][kk].append(v)
    print('games',len(res))
    for m in macro.METRICS:
        a=A[True][m]; b=A[False][m]
        if a and b: print(f'{m:16s} {statistics.mean(a):9.3f} {statistics.mean(b):9.3f}  ({macro.METRICS[m][0][:80]})')
