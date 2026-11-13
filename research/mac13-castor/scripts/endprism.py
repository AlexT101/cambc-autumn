# The winning team's Prism (if it scored the win): its last tribute_start round vs R1000 (score + living bags >= 1000),
# its bag then, the channel length, cancels before it; by bot.
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
    starts=[];cancels=[];deaths=0
    for line in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(line)
        if e.get('a')==p and e['k']=='tribute_start': starts.append(e)
        if e.get('a')==p and e['k']=='tribute_cancel': cancels.append(e)
    if not starts: return None
    last=starts[-1]
    return (g['teams'][w], r1, last['r'], last['gems'], last.get('dur'), len(starts), len(cancels), g['rounds'], [c.get('cause') for c in cancels])
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[s for s in ex.map(one,ds,chunksize=4) if s]
    by=collections.defaultdict(list)
    for s in S: by[s[0]].append(s)
    for b,L in by.items():
        L=[s for s in L if s[1] is not None]
        print(b,len(L),'start-R1000 median',st.median(s[2]-s[1] for s in L),'bag at start median',st.median(s[3] for s in L),
              'dur median',st.median(s[4] for s in L if s[4]),'end-R1000 median',st.median(s[7]-s[1] for s in L),
              'tribute starts mean %.2f cancels mean %.2f'%(st.mean(s[5] for s in L),st.mean(s[6] for s in L)),
              'single-tribute share %.2f'%(sum(s[5]==1 for s in L)/len(L)))
        print('  cancel causes',collections.Counter(c for s in L for c in s[8]).most_common(5))
        print('  start-R1000 quartiles',[sorted(s[2]-s[1] for s in L)[int(q*len(L))] for q in (0.1,0.25,0.5,0.75,0.9)])
