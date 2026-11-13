# Kept/broken hub promises by Prism state, distance, timing (debug study extract; reads HUB lines from the replays' stdout).
# usage: hubdiag.py EXTRACT_DIR (run from the worktree root)
import gzip, json, sys, re, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0,'research/mx-phoebe/scripts')
HUB = re.compile(rb'HUB (\d+) (\d+) g(\d+) at (\d+) (\d+) mode (\S) gems (\d+) prem (\S+) eta (-?\d+) task (-?\d+) alive (\d) state (\d) finish (-?\d+)')
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    d=Path(d)
    try:
        meta=json.loads((d/'meta.json').read_text()); mp=json.loads((d/meta['mapFile']).resolve().read_text())
        R=json.load(gzip.open(d/'rounds.json.gz')); ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
        z=zipfile.ZipFile(meta['source'])
    except Exception: return None
    typ={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    idx={c['id']:i for i,c in enumerate(R['champions'])}
    by_tile={tuple(t):g['id'] for g in mp['groups'] for t in g['tiles']}
    tiles={g['id']:g['tiles'] for g in mp['groups']}
    caps=[e for e in ev if e['k']=='capture']
    out=Counter()
    for side,name in ((0,'team-a.stdout'),(1,'team-b.stdout')):
        if meta['teams'][side]['name']!='phb-hub': continue
        pr=[c for c in typ if typ[c]=='Prism' and team[c]==side]
        if not pr: continue
        p=pr[0]; pc=R['champions'][idx[p]]
        seen=set()
        for m in HUB.finditer(z.read(name)):
            r=int(m[1]); gid=by_tile.get((int(m[4]),int(m[5]))); eta=int(m[9]); mode=m[6].decode()
            cap=next((e for e in caps if e['g']==gid and r<=e['r']<=r+80 and e['team']==side),None)
            if not cap or (gid,cap['r']) in seen: continue
            seen.add((gid,cap['r']))
            gems=sum(x[1] for x in cap['shares']); pg=sum(x[1] for x in cap['shares'] if x[0]==p)
            kept=pg*2>=gems
            ix=min(cap['r'],len(pc['alive']))-1
            dd=min(cheb((pc['x'][ix],pc['y'][ix]),t) for t in tiles[gid]) if pc['alive'][ix] else -1
            b='dead' if dd<0 else '0' if dd==0 else '1-3' if dd<=3 else '4-6' if dd<=6 else '7-10' if dd<=10 else '11+'
            lag=cap['r']-r
            lb='<10' if lag<10 else '10-20' if lag<20 else '20-40' if lag<40 else '40+'
            k='K' if kept else 'B'
            out[(k,'dist',b)]+=1; out[(k,'lag',lb)]+=1; out[(k,'mode',mode)]+=1
            out[(k,'eta','<=5' if eta<=5 else '6-15' if eta<=15 else '16+')]+=1
            ix0=min(r,len(pc['alive']))-1
            d0=min(cheb((pc['x'][ix0],pc['y'][ix0]),t) for t in tiles[gid]) if pc['alive'][ix0] else -1
            out[(k,'d0','dead' if d0<0 else '0-5' if d0<=5 else '6-10' if d0<=10 else '11-20' if d0<=20 else '21+')]+=1
            out[(k,'lagxd0',f"{lb}|{'<=10' if 0<=d0<=10 else '>10'}")]+=1
            cr=cap['r']
            pev=[e for e in ev if cr-6<=e['r']<cr and (e.get('a')==p or e.get('v')==p)]
            pcap=any(e['k']=='capture' and e['g']!=gid and any(x[0]==p for x in e['shares']) for e in ev if cr-3<=e['r']<=cr+6)
            kinds=set()
            for e in pev:
                if e['k'] in ('recall_start','recall_end','tribute_start','shop'): 
                    if e['k']=='recall_start' and not any(f['k']=='recall_cancel' and f.get('a')==p and f['r']<=e['r']+1 for f in ev if e['r']<=f['r']<=e['r']+1): kinds.add('recall')
                    elif e['k']!='recall_start': kinds.add('home/bank')
                if e['k']=='attack' and 'camp' in e: kinds.add('campfight')
                if e['k']=='attack' and 'camp' not in e: kinds.add('champfight')
                if e['k']=='cast' and e.get('ab') not in ('Dash',): kinds.add('cast')
                if e['k']=='death': kinds.add('died')
            st='died' if 'died' in kinds else 'champfight' if 'champfight' in kinds else 'recall' if 'recall' in kinds or 'home/bank' in kinds else 'othercap' if pcap else 'campfight' if 'campfight' in kinds or 'cast' in kinds else 'idle/walk'
            out[(k,'pstate',st)]+=1
            t=int(m[10]); out[(k,'task',('live' if m[11]==b'1' else 'clr')+('<=10' if t<=10 else '11-25' if t<=25 else '26+'))]+=1
            fin=int(m[13]); dlt=t-fin
            out[(k,'free-fin','<-10' if dlt<-10 else '-10..-1' if dlt<0 else '0..5' if dlt<=5 else '>5')]+=1
            out[(k,'margin',str(min(6,fin+5-int(m[9]))))]+=1
            out[(k,'gstate','alive' if m[12]==b'0' else 'cleared' if m[12]==b'1' else 'resp')]+=1
            ph='r1-150' if r<=150 else 'r151-300' if r<=300 else 'r301+'
            out[(k,'ph',ph)]+=1
    return out
if __name__=='__main__':
    dirs=[str(p.parent) for p in Path(sys.argv[1]).glob('*/meta.json')]
    tot=Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one,dirs,chunksize=8):
            if r: tot.update(r)
    for cat in ['dist','lag','mode','eta','ph','d0','lagxd0','pstate','task','gstate','free-fin','margin']:
        keys=sorted(set(k[2] for k in tot if k[1]==cat))
        print(cat, '  '.join(f"{v}: K{tot[('K',cat,v)]} B{tot[('B',cat,v)]} ({tot[('K',cat,v)]/max(1,tot[('K',cat,v)]+tot[('B',cat,v)]):.0%})" for v in keys))
