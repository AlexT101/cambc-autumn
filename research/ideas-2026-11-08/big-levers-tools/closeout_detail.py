# After our crossing of 1000 owned: per carrier (bag >= 30 at crossing) the first 80 rounds: tribute starts/ends/
# cancels (cause), deaths, rounds spent within 1 of an altar, and whether an enemy champion was within 6.
import json,gzip,os,sys,pickle,collections,numpy as np
ana=os.environ.get('ANA',os.path.expanduser('~/tmp-offload/bigl/ana'))
C=pickle.load(open(sys.argv[1],'rb'))
sel=[c for c in C if c['ours']]
agg=collections.defaultdict(collections.Counter)
for c in sel:
    key='blown' if not c['won'] else 'closed'
    d=ana+'/'+c['dir']; meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    mp=json.load(open(ana+'/maps/'+os.path.basename(meta['mapFile']))); alt=mp['altars']
    r0=c['r0']; i0=R['round'].index(r0)
    us=None
    # identify our team as the team whose own crossed at r0 (closeout row has trib/car of 'ours')
    tri=np.array(R['gems'])
    car=np.zeros((2,len(R['round'])))
    for ch in R['champions']: car[ch['team']]+=np.array(ch['gems'])
    us=0 if abs(tri[0][i0]+car[0][i0]-c['trib']-c['car'])<1e-6 else 1
    agg[key]['n']+=1
    carriers=[ch for ch in R['champions'] if ch['team']==us and ch['alive'][i0] and ch['gems'][i0]>=30]
    agg[key]['carriers']+=len(carriers)
    for ch in carriers:
        near=0; enemy=0; chan=0; dead=0
        for i in range(i0,min(i0+80,len(R['round']))):
            if not ch['alive'][i]: dead=1; break
            x,y=ch['x'][i],ch['y'][i]
            if min(max(abs(x-a[0]),abs(y-a[1])) for a in alt)<=1: near+=1
            if ch['chan'][i]==2: chan+=1
            if any(o['team']!=us and o['alive'][i] and o['x'][i] is not None and max(abs(o['x'][i]-x),abs(o['y'][i]-y))<=6 for o in R['champions']): enemy+=1
        agg[key]['rounds_near_altar']+=near; agg[key]['rounds_channelling']+=chan; agg[key]['rounds_enemy_within6']+=enemy; agg[key]['died_within80']+=dead
        agg[key]['bag']+=ch['gems'][i0]
        alt_d=min(max(abs(ch['x'][i0]-a[0]),abs(ch['y'][i0]-a[1])) for a in alt); agg[key]['altar_dist']+=alt_d
    # enemy carried/trib at crossing
    agg[key]['opp_need']+=1000-c['opp_trib']
for k,v in agg.items():
    n=v['n']; nc=v['carriers']
    print(k,f"n={n} carriers/g {nc/n:.2f}, per carrier: bag {v['bag']/nc:.0f}, altar dist {v['altar_dist']/nc:.1f}, of next 80 rounds: near altar {v['rounds_near_altar']/nc:.1f}, channelling {v['rounds_channelling']/nc:.1f}, enemy within 6 {v['rounds_enemy_within6']/nc:.1f}, died {v['died_within80']/nc:.2f}; opp needed {v['opp_need']/n:.0f} to win")
