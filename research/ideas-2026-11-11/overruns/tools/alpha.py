import sys,json,gzip,pickle,collections
def run(pk,tag,maxr=300):
    G=pickle.load(open(pk,'rb')); seen=set(); S=collections.defaultdict(collections.Counter)
    for g in G:
        if g['match'] in seen: continue
        seen.add(g['match']); d0=g['dir']; us=g['us']
        meta=json.load(open(d0+'/meta.json')); team={c['id']:c['team'] for c in meta['champions']}
        mh={c['id']:c['maxHp'] for c in meta['champions']}
        per=collections.defaultdict(lambda:collections.defaultdict(lambda:[set(),0.0]))
        for l in gzip.open(d0+'/events.jsonl.gz','rt'):
            e=json.loads(l)
            if e['r']>maxr: break
            if e['k'] in('attack','cast'):
                for t,dm in e.get('dmg',[]):
                    x=per[e['r']][t]; x[0].add(e['a']); x[1]+=dm
        for side in ('us','them'):
            S[(tag,g['opp'],side)]['games']+=1
        for r,d in per.items():
            for t,(att,dm) in d.items():
                side='them' if team[t]==us else 'us'   # side = the attackers
                s=S[(tag,g['opp'],side)]
                if len(att)>=3: s['a3']+=1
                if len(att)>=4: s['a4']+=1
                if dm>=400: s['d400']+=1
                if dm>=0.5*mh[t]: s['half']+=1
    for k in sorted(S):
        s=S[k]; n=s['games']
        print(k,'per game (r<=%d): rounds with 3+ attackers on one target %.2f, 4+ %.2f, 400+ dmg on one target in a round %.2f, half its base health in a round %.2f'%(maxr,s['a3']/n,s['a4']/n,s['d400']/n,s['half']/n))
run('deaths.pkl','live'); run('deaths_local.pkl','local')
