"""Prism deaths by champions: killer type, bag moved, round; and the game result for the victim's team."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json')); w=m['result']['winner']
    typ={c['id']:CH[c['type']] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and typ[e['v']]=='Prism' and e.get('by') is not None:
            out.append((typ.get(e['by'],'?'),e.get('gems',0),e['r'],w==team[e['v']]))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    print('Prism kills',len(S),'per game %.2f'%(len(S)/len(ds)))
    c=collections.Counter(s[0] for s in S); g=collections.Counter()
    for s in S: g[s[0]]+=s[1]
    for k,v in c.most_common(): print('  %-14s %5d kills, gems moved %6d (%.0f a kill)'%(k,v,g[k],g[k]/v))
    big=[s for s in S if s[1]>=100]; print('bag>=100:',len(big),'victim team won %.0f%%'%(100*sum(s[3] for s in big)/max(1,len(big))))
    print('  killers of big bags',collections.Counter(s[0] for s in big).most_common(6))
