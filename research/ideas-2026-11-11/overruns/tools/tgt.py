import sys,json,gzip,pickle,collections
def run(pk,tag,maxr=300):
    G=pickle.load(open(pk,'rb')); seen=set()
    S=collections.defaultdict(collections.Counter); N=collections.Counter(); H=collections.defaultdict(collections.Counter)
    for g in G:
        if g['match'] in seen: continue
        seen.add(g['match']); d0=g['dir']; us=g['us']
        meta=json.load(open(d0+'/meta.json'))
        team={c['id']:c['team'] for c in meta['champions']}; typ={c['id']:c['name'] for c in meta['champions']}
        N[g['opp']]+=1
        for c in meta['champions']:
            S[(tag,g['opp'],'us' if c['team']==us else 'them','present')][c['name']]+=1
        for l in gzip.open(d0+'/events.jsonl.gz','rt'):
            e=json.loads(l)
            if e['r']>maxr: break
            if e['k'] in('attack','cast'):
                for t,dm in e.get('dmg',[]):
                    S[(tag,g['opp'],'us' if team[t]==us else 'them','taken')][typ[t]]+=dm
                    S[(tag,g['opp'],'us' if team[e['a']]==us else 'them','dealt')][typ[e['a']]]+=dm
                for t,h in e.get('heal',[]):
                    S[(tag,g['opp'],'us' if team[t]==us else 'them','healed')][typ[t]]+=h
            if e['k']=='death' and 'camp' not in e and e.get('by') is not None:
                S[(tag,g['opp'],'us' if team[e['v']]==us else 'them','died')][typ[e['v']]]+=1
    for opp in N:
        for side in('us','them'):
            pres=S[(tag,opp,side,'present')]
            print(tag,opp,side,'games',N[opp])
            tot=sum(S[(tag,opp,side,'taken')].values())
            for ty,n in pres.most_common():
                print('   %-14s picked %3d | dmg taken/game %4.0f (share %.2f) | healed %4.0f | died %.2f | dealt %4.0f'%(ty,n,S[(tag,opp,side,'taken')][ty]/n,S[(tag,opp,side,'taken')][ty]/tot,S[(tag,opp,side,'healed')][ty]/n,S[(tag,opp,side,'died')][ty]/n,S[(tag,opp,side,'dealt')][ty]/n))
run('deaths.pkl','live'); run('deaths_local.pkl','local')
