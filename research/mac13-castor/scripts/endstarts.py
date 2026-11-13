# The winning Prism's tribute starts from R1000-150 on (R1000: score + living bags >= 1000): the first one's round
# relative to R1000, how many, turns spent in cancelled channels, enemies within 8 at each start.
import json,gzip,glob,collections,sys,os,statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx={g['dir']:g for g in json.load(open(ROOT+'/index.json'))['games']}
def one(d):
    g=idx.get(os.path.basename(d))
    if not g or g['rounds']>=2000: return None
    meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    w=g['winner']; pr=[c['id'] for c in meta['champions'] if en[c['type']]=='Prism' and c['team']==w]
    if not pr: return None
    p=pr[0]; n=len(R['round']); r1=None
    for i in range(n):
        bag=sum((c['gems'][i] or 0) for c in R['champions'] if c['team']==w and c['alive'][i])
        if R['gems'][w][i]+bag>=1000: r1=R['round'][i]; break
    if r1 is None: return None
    starts=[]; lost=0; op=None
    for line in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(line)
        if e.get('a')!=p or e['r']<r1-150: continue
        if e['k']=='tribute_start': op=e['r']; starts.append(e['r']-r1)
        elif e['k']=='tribute_cancel' and op is not None: lost+=e['r']-op; op=None
    if not starts: return None
    return (g['teams'][w], starts[0], len(starts), lost, g['rounds']-r1)
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[s for s in ex.map(one,ds,chunksize=4) if s]
    for b in sorted(set(s[0] for s in S)):
        L=[s for s in S if s[0]==b]; q=lambda k:[sorted(s[k] for s in L)[int(x*len(L))] for x in (0.1,0.25,0.5,0.75,0.9)]
        print(b,len(L),'first start - R1000',q(1),'starts',q(2),'cancelled channel turns',q(3),'win - R1000',q(4))
