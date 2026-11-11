import json,gzip,glob,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json'))
    w=M['result']['winner']
    names={c['id']:c['name'] for c in M['champions']}
    team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    ri={r:i for i,r in enumerate(R['round'])}
    P={t:[c for c in R['champions'] if c['team']==t and names[c['id']]=='Prism'] for t in (0,1)}
    if not P[0] or not P[1]: return None
    out={}
    for rr in (100,150,200,300,400):
        i=ri.get(rr)
        if i is None: return None
        f=[P[t][0]['foc'][i] for t in (0,1)]
        g=[P[t][0]['gems'][i] for t in (0,1)]
        # team carried by others
        oth=[sum(c['gems'][i] for c in R['champions'] if c['team']==t and names[c['id']]!='Prism') for t in (0,1)]
        sc=R['gems'][0][i] if False else None
        out[rr]=(f[w]/max(f[1-w],1), g[w]-g[1-w], oth[w]-oth[1-w], f[w], f[1-w])
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    res=[]
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one,dirs):
            if o: res.append(o)
    print(len(res),'prism-both games')
    import statistics as st
    for rr in (100,150,200,300,400):
        rat=[o[rr][0] for o in res]
        print(rr,'winner/loser focus median %.2f'%st.median(rat), 'P(winner ahead) %.2f'%(sum(x>1 for x in rat)/len(rat)),
              'bag diff med %.0f'%st.median(o[rr][1] for o in res), 'others diff %.1f'%st.mean(o[rr][2] for o in res),
              'focus W %.0f L %.0f'%(st.mean(o[rr][3] for o in res), st.mean(o[rr][4] for o in res)))
if __name__=='__main__': main()
