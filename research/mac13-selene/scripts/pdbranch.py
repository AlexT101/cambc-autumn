import json, gzip, sys, os, re, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
AN='/home/ubuntu/wt/mac13-selene/replays/.analysis'
D_RE=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
        z=zipfile.ZipFile(meta['source'])
    except Exception: return None
    cn={c['id']:c['name'] for c in meta['champions']}
    Dl={}
    for nm in z.namelist():
        if nm.endswith('.stdout'):
            for m in D_RE.finditer(z.read(nm)): Dl[(int(m.group(1)),int(m.group(2)))]=m.group(3).decode()
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}; rix={r:i for i,r in enumerate(R['round'])}
    out=[]
    for e in ev:
        if e['k']=='death' and cn.get(e['v'])=='Prism' and cn.get(e.get('by'))=='Prism':
            v=e['v']; k=e['by']; r=e['r']; i=rix.get(r-1,0)
            fv=ch[idx[v]]['foc'][i]; fk=ch[idx[k]]['foc'][i]
            par = 0.8 <= (fk or 1)/(fv or 1) <= 1.25
            seq=''.join(Dl.get((rr,v),'?') for rr in range(r-3,r+1))
            out.append((par, seq, e.get('gems',0)))
    return out
def main():
    idx=json.load(open(os.path.join(AN,'index.json')))
    dirs=[os.path.join(AN,g['dir']) for g in idx['games'] if 'mirdbg' in g['source']]
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=4):
            if r: rows+=r
    print('prism-on-prism kills', len(rows), 'parity', sum(1 for r in rows if r[0]))
    print('victim last branches (all):', Counter(r[1][-2:] for r in rows).most_common(12))
    print('parity:', Counter(r[1][-2:] for r in rows if r[0]).most_common(10))
    big=[r for r in rows if r[2]>=100]
    print('bag100+:', len(big), Counter(r[1][-2:] for r in big).most_common(10))
if __name__=='__main__': main()
