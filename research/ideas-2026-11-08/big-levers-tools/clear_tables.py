import pickle,os,collections,numpy as np
C=pickle.load(open(os.path.expanduser('~/tmp-offload/bigl/clears.pkl'),'rb'))
def cls(t):
    if 'Monolith' in t: return 'Monolith'
    if 'Golem' in t: return 'Golem'
    if 'Elk' in t: return 'Elk'
    if 'Wolf' in t: return 'Wolf'
    return 'cluster'
ngames=len(set(c['dir'] for c in C))
print('games',ngames)
for phase,(lo,hi) in (('r<150',(0,150)),('150-500',(150,500)),('500+',(500,3000))):
  print('==',phase)
  for k in ('Wolf','Elk','Golem','Monolith'):
    out=[]
    for who in ('us','them'):
        cs=[c for c in C if cls(c['types'])==k and lo<=c['r0']<hi and c['waker'] is not None and ((c['waker']==c['us'])==(who=='us'))]
        if not cs: continue
        own=[c for c in cs if c['clearer']==c['waker']]; stolen=[c for c in cs if c['clearer'] not in (c['waker'],'slept')]; slept=[c for c in cs if c['clearer']=='slept']
        t=np.median([c['r1']-c['r0'] for c in own]) if own else 0
        # camp damage taken share of the waker team on own clears
        out.append(f"{who}: woke {len(cs)/ngames:.2f}/g own-clear {len(own)/len(cs):.2f} stolen {len(stolen)/len(cs):.3f} slept {len(slept)/len(cs):.2f} median clear {t:.0f}r")
    print(f'{k:9s}',' | '.join(out))
# steals per game in losses vs wins
for res in (False,True):
    cs=[c for c in C if c['win']==res]; n=len(set(c['dir'] for c in cs))
    st_by_them=[c for c in cs if c['waker']==c['us'] and c['clearer'] not in (c['us'],'slept',None)]
    st_by_us=[c for c in cs if c['waker'] is not None and c['waker']!=c['us'] and c['clearer']==c['us']]
    print('W' if res else 'L', f'games {n}: they finish our woken groups {len(st_by_them)/n:.2f}/g ({sum(c["gems"] for c in st_by_them)/n:.0f} gems), we finish theirs {len(st_by_us)/n:.2f}/g ({sum(c["gems"] for c in st_by_us)/n:.0f} gems)')
    st_early=[c for c in st_by_them if c['r0']<150]; su_early=[c for c in st_by_us if c['r0']<150]
    print('   r<150: they finish ours',f'{len(st_early)/n:.2f}/g ({sum(c["gems"] for c in st_early)/n:.0f}g)',' we finish theirs',f'{len(su_early)/n:.2f}/g ({sum(c["gems"] for c in su_early)/n:.0f}g)')
