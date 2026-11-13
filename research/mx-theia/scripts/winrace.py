# CAND vs REF (CANDNAME '-12': an ab.py batch, CAND is team A in '-12' replays and B in '-21'): who first starts a winning-size tribute (score + bag >= 1000) and who wins then; tribute cancels by
# cause against each side, and the share of the channel run before a cancel. Args: ANALYSIS_DIR CANDNAME.
import json,gzip,sys,os,collections,statistics
ROOT=sys.argv[1]; CAND=sys.argv[2]
idx=json.load(open(ROOT+'/index.json')); rows={}
for g in idx['games']: rows.setdefault(g['dir'],g)
dirs=sorted(rows)
c=collections.Counter(); share=collections.defaultdict(list)
for dn in dirs:
    d=os.path.join(ROOT,dn); meta=json.load(open(d+'/meta.json')); team={x['id']:x['team'] for x in meta['champions']}
    names=[t['name'] for t in meta['teams']]; ci=names.index(CAND) if CAND in names else None
    if ci is None and CAND=='-12': src=rows[dn]['source']; ci=0 if src.endswith('-12.repl26a') else 1 if src.endswith('-21.repl26a') else None
    if ci is None: continue
    w=meta['result']['winner']; R=json.load(gzip.open(d+'/rounds.json.gz')); rd={r:i for i,r in enumerate(R['round'])}
    first=None; start={}
    c['games']+=1; c['cand_won']+=w==ci
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='tribute_start':
            t=team[e['a']]; i=rd.get(e['r']); start[e['a']]=(e['r'],e['dur'])
            if i is not None and first is None and R['gems'][t][i]+e['gems']>=1000: first=t
        if e['k']=='tribute_cancel' and e['a'] in start and e['gems']>=100:
            side='CAND' if team[e['a']]==ci else 'REF'; r0,dur=start[e['a']]
            c[(side,'cancel',e.get('cause'))]+=1; share[(side,e.get('cause'))].append(min(1,(e['r']-r0)/max(1,dur)))
        if e['k']=='tribute_end' and e['gems']>=100: c[('CAND' if team[e['a']]==ci else 'REF','done100')]+=1
    if first is None: c['no_winning_start']+=1; c['nws_cand_won']+=w==ci
    elif first==ci: c['cand_first']+=1; c['cand_first_won']+=w==ci
    else: c['ref_first']+=1; c['ref_first_cand_won']+=w==ci
n=c['games']; print('games',n,'CAND win %.3f'%(c['cand_won']/n))
print('CAND first to a winning start: %d, CAND wins %.3f | REF first: %d, CAND wins %.3f | none: %d, CAND wins %.3f'%(c['cand_first'],c['cand_first_won']/max(1,c['cand_first']),c['ref_first'],c['ref_first_cand_won']/max(1,c['ref_first']),c['no_winning_start'],c['nws_cand_won']/max(1,c['no_winning_start'])))
for side in ('CAND','REF'):
    print(side,'100+ tributes done/game %.2f'%(c[(side,'done100')]/n),'cancels/game',{k[2]:round(v/n,2) for k,v in c.items() if isinstance(k,tuple) and k[0]==side and k[1]=='cancel'},'run share',{k[1]:round(statistics.mean(v),2) for k,v in share.items() if k[0]==side})
