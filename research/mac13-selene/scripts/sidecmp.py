import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; REF=sys.argv[2] if len(sys.argv)>2 else 'chy-ref'
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    names=[t['name'] for t in meta['teams']]
    if names[0] in ('A',) or names[0]==names[1]:
        src=meta['source'].replace('.repl26a','')
        side={0:'cand',1:'ref'} if src.endswith('-12') else {0:'ref',1:'cand'}
    else:
        side={0:'ref' if names[0]==REF else 'cand',1:'ref' if names[1]==REF else 'cand'}
    if side[0]==side[1]: return None
    G={g['id']:g for g in mp['groups']}; tm={c['id']:c['team'] for c in meta['champions']}
    res=Counter()
    for t in (0,1): res[(side[t],'win')]+=int(meta['result']['winner']==t); res[(side[t],'games')]+=1; res[(side[t],'trib')]+=meta['result']['gems'][t]
    for e in ev:
        if e['k']=='capture':
            t=e['team']; sd=G[e['g']]['side']; z='own' if sd==t else 'enemy' if sd in (0,1) else 'mid'
            res[(side[t],'cap_'+z)]+=sum(s[1] for s in e['shares'])
        if e['k']=='death':
            v=e['v']; res[(side[tm[v]],'deaths')]+=1; res[(side[tm[v]],'bag_lost')]+=e['gems']
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=4):
            if r: tot.update(r)
    for s in ('cand','ref'):
        n=tot[(s,'games')] or 1
        print(s, 'games',n,'win %.1f'%(100*tot[(s,'win')]/n), *('%s %.0f'%(k,tot[(s,k)]/n) for k in ('trib','cap_own','cap_mid','cap_enemy','deaths','bag_lost')))
if __name__=='__main__': main()
