import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); us=r['us']; team={c['id']:c['team'] for c in m['champions']}
    o=Counter(); 
    for e in events(d):
        if e['k']=='capture':
            s='us' if e['team']==us else 'them'
            o[s+'_cap']+=sum(x[1] for x in e['shares'])
        elif e['k']=='death' and e.get('linked') is None:
            s='us' if team[e['v']]==us else 'them'
            o[s+'_lost']+=e['gems']
            if e.get('by') is not None: o[('them' if s=='us' else 'us')+'_killgems']+=e.get('gemsTo',0)
            else: o[s+'_lostcamp']+=e['gems']
        elif e['k']=='tribute_end':
            s='us' if team[e['a']]==us else 'them'; o[s+'_trib']+=e['gems']
    return r['opp'],r['won'],o
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,games()))
    for key in ['Fish','Mite','UoS','PBG','ALL']:
        for won in (False,True):
            X=[o for (op,w,o) in res if (op==key or key=='ALL') and w==won]
            n=len(X); f=lambda k: sum(x[k] for x in X)/n
            print('%-4s %s n=%3d  cap %4.0f/%4.0f  killgems %4.0f/%4.0f  lostOnDeath %4.0f/%4.0f  trib %4.0f/%4.0f'%(key,'W' if won else 'L',n,f('us_cap'),f('them_cap'),f('us_killgems'),f('them_killgems'),f('us_lost'),f('them_lost'),f('us_trib'),f('them_trib')))
