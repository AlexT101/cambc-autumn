import json,gzip,glob,sys,collections,statistics as st
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json')); w=M['result']['winner']
    names={c['id']:c['name'] for c in M['champions']}; team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    st_=[e for e in ev if e['k']=='tribute_start']; en=[e for e in ev if e['k']=='tribute_end']
    if not en: return None
    last=en[-1]
    if last.get('total',0)<1000: return None
    a=last['a']; s=[e for e in st_ if e['a']==a and e['r']<=last['r']][-1]
    i=ri.get(s['r'])
    score=R['gems'][team[a]][i] if i is not None else 0
    big=[e for e in st_ if team[e['a']]==team[a] and e['gems']>=150]
    return dict(who=names[a], start_gems=s['gems'], need=1000-score, dur=s.get('dur'), attempts=len([e for e in big if e['a']==a]))
def main():
    res=[o for o in ProcessPoolExecutor(32).map(one,[x[:-10] for x in glob.glob(A+'/*/meta.json')]) if o]
    print(len(res), collections.Counter(r['who'] for r in res).most_common(4))
    P=[r for r in res if r['who']=='Prism']
    print('Prism winning tributes: start gems median %d, needed median %d, surplus median %d, dur median %s, attempts mean %.1f'%(
        st.median(r['start_gems'] for r in P), st.median(r['need'] for r in P), st.median(r['start_gems']-r['need'] for r in P), st.median(r['dur'] for r in P if r['dur']), st.mean(r['attempts'] for r in P)))
    print('surplus quartiles', st.quantiles([r['start_gems']-r['need'] for r in P],n=4))
if __name__=='__main__': main()
