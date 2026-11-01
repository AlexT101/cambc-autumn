"""Hold walk-off loops: the same champion walking off the same group's hold on a want_home retreat again within
30 rounds (q1_holdwalk2.json), and how those groups ended (paid to us / them within 60 rounds of the first walk)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
R=json.load(open(CACHE+'/../q1_holdwalk2.json'))
by=defaultdict(list)
for x in R: by[(x['key'],x['c'],x['g'])].append(x)
chains=[]
for k,L in by.items():
    L.sort(key=lambda x:x['r']); cur=[L[0]]
    for x in L[1:]:
        if x['r']-cur[-1]['r']<=30: cur.append(x)
        else: chains.append(cur); cur=[x]
    chains.append(cur)
multi=[c for c in chains if len(c)>=2]
print('walk-off chains',len(chains),'with >=2 walk-offs of one champion from one group within 30 rounds:',len(multi),'walk-offs in them',sum(len(c) for c in multi),'of',len(R))
print('chain length',Counter(len(c) for c in chains))
print('reasons in loops',Counter(x['why'] for c in multi for x in c))
print('loops ended: stolen after the last walk %.2f, leaver died %.2f'%(sum(c[-1]['stolen'] for c in multi)/len(multi),sum(any(x['died'] for x in c) for c in multi)/len(multi)))
print('games with a loop',len({c[0]['key'] for c in multi}),'maps',len({c[0]['map'] for c in multi}))
for c in sorted(multi,key=len,reverse=True)[:10]: print(c[0]['key'],c[0]['name'],'g',c[0]['g'],'rounds',[x['r'] for x in c],[x['why'] for x in c],'left',[x['left'] for x in c],'dmin',[x['dmin'] for x in c])
