"""Victim's decision branch (D lines) on its last 1 and 3 turns before a champion kill, mirror debug batch.
Needs the batch dir (replays with stdout) and its extract dir."""
import json,gzip,glob,os,sys,collections,re,zipfile
from concurrent.futures import ProcessPoolExecutor
B=sys.argv[1]; A=sys.argv[2]
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$',re.M)
CH=json.load(open(A+'/enums.json'))['champions']
idx={}
for g in json.load(open(A+'/index.json'))['games']: idx[os.path.basename(g['source'])]=g['dir']
def one(p):
    d=idx.get(os.path.basename(p))
    if not d: return []
    m=json.load(open(os.path.join(A,d,'meta.json'))); typ={c['id']:CH[c['type']] for c in m['champions']}
    br={}
    z=zipfile.ZipFile(p)
    for n in z.namelist():
        if n.endswith('.stdout'):
            for x in D.finditer(z.read(n)): br[(int(x.group(1)),int(x.group(2)))]=x.group(3).decode()
    # D lines use handle ids; assume handle == engine id
    out=[]
    for l in gzip.open(os.path.join(A,d,'events.jsonl.gz'),'rt'):
        e=json.loads(l)
        if e['k']!='death' or e.get('by') is None or e.get('linked'): continue
        v=e['v']; seq=[br.get((e['r']-k,v)) for k in range(0,11)]
        out.append((typ[v],seq,m["result"]["winner"]==m["champions"][[c["id"] for c in m["champions"]].index(v)]["team"]))
    return out
if __name__=='__main__':
    ps=glob.glob(B+'/*.repl26a')
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ps,chunksize=8) for x in o]
    print('kills',len(S),'with any branch',sum(1 for s in S if any(s[1])))
    for k,lab in ((1,'last turn before death round'),(0,'death round turn')):
        c=collections.Counter(s[1][k] for s in S)
        print(lab,' '.join('%s %.1f%%'%(b,100*v/len(S)) for b,v in c.most_common(10)))
    c=collections.Counter(''.join(x or '.' for x in reversed(s[1][1:])) for s in S)
    print('last 3 turns (oldest first):',' '.join('%s %.1f%%'%(b,100*v/len(S)) for b,v in c.most_common(15)))
    E=[s for s in S if s[1][1]=='E']; print('E deaths: victim team won %.2f'%(sum(1 for s in E if s[2])/len(E)))
    Rr=[s for s in S if s[1][1]=='R']; print('R deaths: victim team won %.2f'%(sum(1 for s in Rr if s[2])/len(Rr)))
    c=collections.Counter(); n=0
    for s in S:
        if s[1][1]=='E': continue
        for b in s[1][1:]:
            if b: c[b]+=1; n+=1
    print('non-E kills, branch share over victim last 10 turns:',' '.join('%s %.1f%%'%(b,100*v/n) for b,v in c.most_common(10)))
