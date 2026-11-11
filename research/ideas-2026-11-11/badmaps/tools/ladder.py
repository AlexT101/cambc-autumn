import numpy as np, json, collections, sys, pickle, datetime
base='/home/ubuntu/tmp-offload/badmaps/archive'
days=['2026-11-05','2026-11-06','2026-11-07','2026-11-08','2026-11-09','2026-11-10','2026-11-11']
OUR='547efb5b-57e5-4355-8501-3b331f506d62'
rows=[]
for d in days:
    m=json.load(open(f'{base}/{d}/meta.json'))
    teams=m['teams']; ours=[i for i,t in enumerate(teams) if t['id']==OUR]
    if not ours: continue
    o=ours[0]
    st=np.load(f'{base}/{d}/s_team.npy').reshape(-1,2)
    kind=np.load(f'{base}/{d}/g_kind.npy'); mh=np.load(f'{base}/{d}/g_map_hash.npy'); w=np.load(f'{base}/{d}/g_winner.npy')
    cr=np.load(f'{base}/{d}/g_created.npy'); mt=np.load(f'{base}/{d}/matches.npy')
    ga=np.load(f'{base}/{d}/g_gems_a.npy'); gb=np.load(f'{base}/{d}/g_gems_b.npy'); rd=np.load(f'{base}/{d}/g_rounds.npy')
    idx=np.where((st[:,0]==o)|(st[:,1]==o))[0]
    for i in idx:
        side=0 if st[i,0]==o else 1
        opp=teams[st[i,1-side]]['name']
        rows.append(dict(day=d,t=float(cr[i]),kind=m['kinds'][kind[i]],map=m['maps'][mh[i]]['name'],side='ab'[side],win=int(w[i]==side),winner=int(w[i]),opp=opp,match=mt[i].decode(),gems=(float(ga[i]),float(gb[i])),rounds=int(rd[i])))
pickle.dump(rows,open('/home/ubuntu/tmp-offload/badmaps/an/ourgames.pkl','wb'))
print(len(rows), collections.Counter((r['day'],r['kind']) for r in rows))
print(collections.Counter(r['winner'] for r in rows))
