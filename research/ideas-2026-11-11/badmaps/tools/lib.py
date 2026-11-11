import json,gzip,os,collections
EXT='/home/ubuntu/tmp-offload/badmaps/ext'
GAMES={r['match']:r for r in json.load(open('/home/ubuntu/tmp-offload/badmaps/an/v115-games.json'))}
for f in ['v113-games.json']:
    p='/home/ubuntu/tmp-offload/badmaps/an/'+f
    if os.path.exists(p):
        for r in json.load(open(p)): GAMES[r['match']]=r
IDX=json.load(open(EXT+'/index.json'))['games']
def find(mp=None,opp=None,side=None,ver=115,result=None):
    out=[]
    for g in IDX:
        m=os.path.basename(g['source']).split('.')[0]; gm=GAMES.get(m)
        if not gm: continue
        if mp and gm['map']!=mp: continue
        if opp and not gm['opp_name'].startswith(opp): continue
        if side and gm['side']!=side: continue
        if ver and gm['version']!=ver: continue
        if result and gm['result']!=result: continue
        out.append((EXT+'/'+g['dir'],gm))
    return out
_mc={}
def load(d,events=True):
    meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')] if events else None
    mf=os.path.join(EXT,meta['mapFile']) if not os.path.isabs(meta['mapFile']) else meta['mapFile']
    if not os.path.exists(mf): mf=os.path.join(d,meta['mapFile'])
    if mf not in _mc: _mc[mf]=json.load(open(mf))
    return meta,R,ev,_mc[mf]
def acct(d,gm):
    """per-team accounting, us=0 them=1"""
    meta,R,ev,mp=load(d)
    us=0 if gm['side']=='a' else 1
    team={c['id']:c['team'] for c in meta['champions']}
    typ={c['id']:c['name'] for c in meta['champions']}
    A=[collections.Counter(),collections.Counter()]
    for e in ev:
        k=e['k']
        if k=='capture':
            for cid,g,go in e['shares']:
                t=0 if team[cid]==us else 1
                A[t]['cap_gems']+=g; A[t]['cap_gold']+=go; 
            A[0 if e['team']==us else 1]['caps']+=1
        elif k=='death':
            t=0 if team[e['v']]==us else 1
            A[t]['deaths']+=1; A[t]['died_gems']+=e.get('gems',0)
            if 'by' in e and e['by'] is not None and 'camp' not in e: A[1-t]['kill_gems']+=e.get('gemsTo',0) or 0; A[1-t]['kills']+=1
            if 'camp' in e: A[t]['camp_deaths']+=1
        elif k=='tribute_end':
            t=0 if team[e['a']]==us else 1
            A[t]['trib']+=1; A[t]['trib_gems']+=e['gems']
        elif k=='tribute_cancel':
            t=0 if team[e['a']]==us else 1
            A[t]['trib_cancel_'+str(e.get('cause'))]+=1
        elif k=='lock_place':
            A[0 if e['team']==us else 1]['locks']+=1
        elif k=='tribute_blocked':
            A[0 if team[e['a']]==us else 1]['trib_blocked']+=1
    return A,meta,R,ev,mp,us,team,typ
