import json,gzip,glob,collections
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    mp=json.load(open('/home/ubuntu/wt/mac13-kronos/replays/.analysis/maps/'+m['mapFile'].split('/')[-1]))
    mono={g['id'] for g in mp['groups'] if 'Monolith' in g['types']}
    if not mono: return ('nomono',)
    names={c['id']:c['name'] for c in m['champions']}
    w=m['result']['winner']; caps=[]
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['k']=='capture' and e['g'] in mono:
            caps.append((e['r'], e['team'], [names[s[0]] for s in e['shares']], sum(s[1] for s in e['shares'])))
    return ('mono', caps, w, m['result']['rounds'])
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=8) if x]
    M=[x for x in R if x[0]=='mono']; print('games',len(R),'mono maps',len(M))
    first=[x for x in M if x[1]]; print('with a mono capture',len(first))
    print('first capturer wins', sum(1 for x in first if x[1][0][1]==x[2])/len(first))
    print('prism among first holders', sum(1 for x in first if 'Prism' in x[1][0][2])/len(first))
    import statistics; print('first capture round median', statistics.median(x[1][0][0] for x in first), 'game len median', statistics.median(x[3] for x in first))
    print('captures per game', statistics.mean(len(x[1]) for x in first))
