# REF's completed winning-size channels (8+ turns) that no CAND body saw: how many had their channeller seen carrying
# a winning bag before, and how long before the channel's start. Args: EXTRACT_DIR (ab.py batch, CAND team A in -12).
import json,gzip,sys,os,collections,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def one(item):
    dn,row=item; d=os.path.join(ROOT,dn); src=row['source']; ci=0 if src.endswith('-12.repl26a') else 1
    meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz')); rd={r:i for i,r in enumerate(R['round'])}
    team={x['id']:x['team'] for x in meta['champions']}; CH={c['id']:c for c in R['champions']}
    ours=[c['id'] for c in R['champions'] if c['team']==ci]
    evs=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    out=[]; open_={}
    for e in evs:
        if e['k']=='tribute_start' and team[e['a']]!=ci:
            i=rd.get(e['r'])
            if i is not None and R['gems'][1-ci][i]+e['gems']>=1000: open_[e['a']]=(e['r'],e['dur'],e['gems'])
        elif e['k'] in ('tribute_end','tribute_cancel') and e['a'] in open_:
            r0,dur,gems=open_.pop(e['a'])
            if e['k']!='tribute_end' or dur<=8: continue
            ch=CH[e['a']]; i0=rd[r0]; i1=rd.get(e['r'],len(R['round'])-1)
            if any(b in (ch['seenBy'][j] or []) for b in ours for j in range(i0,i1+1)): continue
            # last sighting before r0 with a winning bag
            last=None
            for j in range(i0-1,-1,-1):
                if any(b in (ch['seenBy'][j] or []) for b in ours):
                    last=(r0-R['round'][j], ch['gems'][j], R['gems'][1-ci][j]+ch['gems'][j]>=1000); break
            out.append(last)
    return out
if __name__=='__main__':
  idx=json.load(open(ROOT+'/index.json')); rows={}
  for g in idx['games']: rows.setdefault(g['dir'],g)
  with ProcessPoolExecutor(48) as ex: res=[x for r in ex.map(one,list(rows.items()),chunksize=4) for x in r]
  print('never-seen long completions',len(res))
  print('never seen before either',sum(x is None for x in res))
  L=[x for x in res if x]
  print('seen before: winning bag at last sighting',sum(x[2] for x in L),'of',len(L))
  print('rounds since last sighting (winning bag):',sorted(x[0] for x in L if x[2])[:80])
