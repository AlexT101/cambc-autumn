"""Q3 trace: what our home trips are for. Alive turns by branch (TT d), and the reasons recalls were kept
(TE recall keep=1 why, counted once per recall: the turn with left=4 or the first kept turn)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
def one(arg):
    key,g=arg; T=tload(key); br=Counter(); why=Counter(); n=0; last={}
    for (r,c),L in sorted(T['turns'].items()):
        tt=L.get('tt')
        if not tt or tt.get('a')!='1': continue
        n+=1; br[tt.get('d')]+=1
        for e in L['te']:
            if e['k']=='recall' and e.get('keep')=='1':
                if last.get(c)!=r-1: why[e.get('why')]+=1
                last[c]=r
    return dict(br=dict(br),why=dict(why),n=n)
if __name__=='__main__':
    res=pmap(one,trace_keys()); br=Counter(); why=Counter(); n=sum(x['n'] for x in res)
    for x in res: br.update(x['br']); why.update(x['why'])
    print('alive turns by branch:',{k:round(100*v/n,1) for k,v in br.most_common()})
    print('kept recalls by reason (per game):',{k:round(v/len(res),1) for k,v in why.most_common()})
