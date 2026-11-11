import json,gzip,os,collections
def loadx(ext):
    return json.load(open(ext+'/index.json'))['games']
_mc={}
def load(ext,d):
    d=ext+'/'+d
    meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    mf=os.path.join(ext,'maps',os.path.basename(meta['mapFile']))
    if mf not in _mc: _mc[mf]=json.load(open(mf))
    return meta,R,ev,_mc[mf]
def acct(meta,R,ev,us):
    team={c['id']:c['team'] for c in meta['champions']}
    typ={c['id']:c['name'] for c in meta['champions']}
    A=[collections.Counter(),collections.Counter()]
    for e in ev:
        k=e['k']
        if k=='capture':
            for cid,g,go in e['shares']:
                t=0 if team[cid]==us else 1
                A[t]['cap_gems']+=g; A[t]['cap_gold']+=go
            A[0 if e['team']==us else 1]['caps']+=1
        elif k=='death':
            t=0 if team[e['v']]==us else 1
            A[t]['deaths']+=1; A[t]['died_gems']+=e.get('gems',0)
            if e.get('by') is not None and 'camp' not in e: A[1-t]['kill_gems']+=e.get('gemsTo',0) or 0; A[1-t]['kills']+=1
        elif k=='tribute_end':
            t=0 if team[e['a']]==us else 1
            A[t]['trib']+=1; A[t]['trib_gems']+=e['gems']
    return A,team,typ
def local_games(ext):
    """rows: dir, map, us(team idx of bot0), win"""
    out=[]
    for g in loadx(ext):
        src=g['source']; base=os.path.basename(src)
        us=0 if base.endswith('-12.repl26a') else 1
        out.append(dict(dir=g['dir'],map=g['map'],us=us,win=g['winner']==us,src=src,rounds=g['rounds']))
    return out
