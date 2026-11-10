import json, sys, collections, statistics
rows = json.load(open(sys.argv[1]))
chain = [0,1,2,3,4,20,21,22,23,24,25,5,6,28,29,30,7,8,9,31,32,33,34,35,36,37,10,11,38,39,40,41,42,43,44,45,46,47,26,27,12,13,14]
lab = {1:'world',2:'comms recv',3:'pre-act',4:'act approach',20:'comeback',21:'channels',22:'ward/reveal',23:'shop',24:'can_act+bush_threat',25:'game_ender',5:'support/mend calc',6:'want_home',28:'fixc_commit+support_work',29:'strike_possible',30:'local_support..heal/shield',7:'guard_steps',8:'capture checks+strikes',9:'post-search guard+guard_work',31:'(nothing)',32:'sealed_in+wake_ring',33:'wants_shop',34:'guard_turn',35:'chase_with_guard',36:'contest_capture',37:'kite/siege',10:'willow_follow',11:'farm call',38:'pick_up',39:'bag,gems_short,open_plan',40:'recall_line..crew_proposed',41:'ally claims..',42:'attack_in_range,holding,mirror',43:'walk_on setup,centre_steps',44:'contexts,struck check',45:'recall_out,trips',46:'struggling..partners',47:'lambdas,first',26:'order(nearest_groups)',27:'-',12:'loop setup',13:'LOOP',14:'postloop'}
def segs(r):
    v=r['v']; out={}; lastv=v[0]
    for i in chain[1:]:
        if v[i]==0: continue
        out[i]=lastv-v[i]; lastv=v[i]
    return out
def pct(xs,q):
    xs=sorted(xs); return xs[min(len(xs)-1,int(q*len(xs)))] if xs else 0
late=[r for r in rows if r['round0']>1 and r['round0']==r['round1']]
cut=[r for r in late if r['k']<r['ev']]; unc=[r for r in late if r['k']>=r['ev']]
print(len(late), len(cut), len(unc))
for nm,S in (('cut',cut),('uncut(1/8 sample)',unc)):
    acc=collections.defaultdict(list)
    for r in S:
        s=segs(r)
        for i in chain[1:]: acc[i].append(s.get(i,0))
    print('==',nm)
    for i in chain[1:]:
        xs=acc[i]
        print(f'{lab[i]:32s} mean {statistics.mean(xs):7.0f} p50 {pct(xs,.5):6d} p90 {pct(xs,.9):6d} p99 {pct(xs,.99):6d}')
print('cut: enemies visible', sum(1 for r in cut if r['ne']>0)/len(cut), 'within 8', sum(1 for r in cut if r['nd']<=8)/len(cut))
print('unc: enemies visible', sum(1 for r in unc if r['ne']>0)/len(unc), 'within 8', sum(1 for r in unc if r['nd']<=8)/len(unc))
