# REF's winning-size channels cancelled by CAND's stun or lock (an ab.py debug batch; CAND team A in -12): the share of
# the channel run at the cancel, split by whether CAND's denial made it (a DENY ... made- line by the actor that round)
# or another path did (the strike search's stun, place_lock at turn end). Args: EXTRACT_DIR [REPO].
import json,gzip,sys,os,re,zipfile,collections,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; REPO=sys.argv[2] if len(sys.argv)>2 else '/home/ubuntu/wt/mx-theia'
MADE=re.compile(rb'^[\s\0]*DENY (\d+) (\d+) .* made-(\w+)\s*$',re.M)
def one(item):
    dn,row=item; d=os.path.join(ROOT,dn); src=row['source']; ci=0 if src.endswith('-12.repl26a') else 1
    meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz')); rd={r:i for i,r in enumerate(R['round'])}
    team={x['id']:x['team'] for x in meta['champions']}
    out=zipfile.ZipFile(os.path.join(REPO,src)).read('team-a.stdout' if ci==0 else 'team-b.stdout')
    made={(int(m.group(1)),int(m.group(2))) for m in MADE.finditer(out)}
    evs=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    open_={}; res=[]; last_actor={}
    for e in evs:
        if e['k']=='cast' and team.get(e['a'])==ci and e.get('stun'):
            for v in e['stun']: last_actor[(v,e['r'])]=e['a']
        if e['k']=='attack' and team.get(e['a'])==ci and e.get('stun'):
            for v in e['stun']: last_actor[(v,e['r'])]=e['a']
        if e['k']=='lock_place' and team.get(e['a'])==ci: last_actor[('lock',tuple(e['to']),e['r'])]=e['a']
        if e['k']=='tribute_start' and team[e['a']]!=ci:
            i=rd.get(e['r'])
            if i is not None and R['gems'][1-ci][i]+e['gems']>=1000: open_[e['a']]=(e['r'],e['dur'],tuple(e['altar']))
        elif e['k'] in ('tribute_end','tribute_cancel') and e['a'] in open_:
            r0,dur,alt=open_.pop(e['a'])
            if e['k']!='tribute_cancel' or e.get('cause') not in ('stun','lock') or dur<=8: continue
            actor=last_actor.get((e['a'],e['r'])) if e['cause']=='stun' else last_actor.get(('lock',alt,e['r']))
            share=min(1,(e['r']-r0)/max(1,dur))
            res.append((e['cause'], actor is not None and (e['r'],actor) in made, share))
    return res
if __name__=='__main__':
    idx=json.load(open(ROOT+'/index.json')); rows={}
    for g in idx['games']: rows.setdefault(g['dir'],g)
    with ProcessPoolExecutor(48) as ex: res=[x for r in ex.map(one,list(rows.items()),chunksize=4) for x in r]
    C=collections.defaultdict(list)
    for c,m,s in res: C[(c,'denial' if m else 'other path')].append(s)
    for k,v in sorted(C.items()): print(k,len(v),'mean share %.2f'%statistics.mean(v),'share<0.5: %d'%sum(x<0.5 for x in v))
