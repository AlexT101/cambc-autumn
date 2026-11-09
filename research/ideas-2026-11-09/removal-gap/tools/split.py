import sys,re
lines=open('full.diff').read().split('\n')
files=[];cur=None
for i,l in enumerate(lines,1):
    if l.startswith('diff '): cur={'head':[l],'hunks':[]};files.append(cur)
    elif l.startswith('--- ') or l.startswith('+++ '):
        if cur['hunks']: cur['hunks'][-1][1].append(l)
        else: cur['head'].append(l)
    elif l.startswith('@@'): cur['hunks'].append((i,[l]))
    elif cur and cur['hunks'] and l!='' or (cur and cur['hunks'] and l==''):
        cur['hunks'][-1][1].append(l)
common={14,340,348,355}
arms={'467':{290,300,303,306},'468':{20,29},'470':{229},'471':{35,337,352},
'lock':{4,53,142},'deny':{6,149},'b1':{231,278,283},'gf':{41,47,50,311,318,321,324,329,331},
'b5':{178},'b3w':{195,200,203},'c1':{186,189}}
allh={h for f in files for h,_ in f['hunks']}
used=set().union(*arms.values())|common
print('unassigned',allh-used)
for a,hs in arms.items():
    out=[]
    for f in files:
        sel=[b for h,b in f['hunks'] if h in hs|common]
        if not sel: continue
        out+=f['head']
        for b in sel:
            while b and b[-1]=='': b=b[:-1]
            out+=b
    open(f'arm-{a}.patch','w').write('\n'.join(out)+'\n')
