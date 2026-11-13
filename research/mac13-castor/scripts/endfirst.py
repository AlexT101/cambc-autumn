# Who reaches score + living bags >= 1000 first, and does it win; by bot and by whether it has a Prism; and the
# cancelled-channel turns its Prism spent after R1000.
import json,gzip,glob,collections,sys,os,statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx={g['dir']:g for g in json.load(open(ROOT+'/index.json'))['games']}
def one(d):
    g=idx.get(os.path.basename(d))
    if not g: return None
    meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    n=len(R['round']); r1=[None,None]
    for t in (0,1):
        for i in range(n):
            bag=sum((c['gems'][i] or 0) for c in R['champions'] if c['team']==t and c['alive'][i])
            if R['gems'][t][i]+bag>=1000: r1[t]=R['round'][i]; break
    if r1[0] is None and r1[1] is None: return None
    f=0 if r1[1] is None or (r1[0] is not None and r1[0]<r1[1]) else 1
    hasp=any(en[c['type']]=='Prism' and c['team']==f for c in meta['champions'])
    pid=[c['id'] for c in meta['champions'] if en[c['type']]=='Prism' and c['team']==f]
    lost=0; stuns=locks=manual=0
    if pid:
        for line in gzip.open(d+'/events.jsonl.gz','rt'):
            e=json.loads(line)
            if e['k']=='tribute_cancel' and e.get('a')==pid[0] and e['r']>=r1[f]-60:
                lost+= (e.get('left') is not None) and 1
                c=e.get('cause'); stuns+=c=='stun'; locks+=c=='lock'; manual+=c=='manual'
    other=r1[1-f]
    return (g['teams'][f], hasp, g['winner']==f, r1[f], other, stuns, locks, manual, g['rounds'])
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[s for s in ex.map(one,ds,chunksize=4) if s]
    for b in sorted(set(s[0] for s in S)):
        for hp in (True,False):
            L=[s for s in S if s[0]==b and s[1]==hp]
            if not L: continue
            print(b,'Prism' if hp else 'noPrism','first-to-1000 games',len(L),'win %.1f'%(100*sum(s[2] for s in L)/len(L)),
                  'stun %.2f lock %.2f manual %.2f cancels a game near the end'%(st.mean(s[5] for s in L),st.mean(s[6] for s in L),st.mean(s[7] for s in L)))
            Lw=[s for s in L if s[2]]; Ll=[s for s in L if not s[2]]
            if Ll: print('   lost after first: stun %.2f lock %.2f manual %.2f'%(st.mean(s[5] for s in Ll),st.mean(s[6] for s in Ll),st.mean(s[7] for s in Ll)))
