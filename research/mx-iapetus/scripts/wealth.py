import json,gzip,sys
A='replays/.an-mirror/'
def wealth(d, rs=(100,200,300,400,500)):
    R=json.load(gzip.open(A+d+'/rounds.json.gz'))
    m=json.load(open(A+d+'/meta.json'))
    rounds=R['round']; out=[]
    for r in rs:
        if r>rounds[-1]: break
        i=rounds.index(r)
        w=[R['gems'][t][i] for t in (0,1)]
        for c in R['champions']:
            w[c['team']]+=c['gems'][i]
        e=[0,0]
        for c in R['champions']: e[c['team']]+=c['earned'][i]
        out.append((r,w,e))
    return out
for d in sys.argv[1:]:
    print(d, wealth(d))
