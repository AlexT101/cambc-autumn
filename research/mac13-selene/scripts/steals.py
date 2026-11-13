import json, gzip, sys, os
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    team={c['id']:c['team'] for c in meta['champions']}
    cn={c['id']:c['name'] for c in meta['champions']}
    cg={c['id']:c['group'] for c in mp['camps']}
    dmg=defaultdict(lambda: [0.0,0.0]); last=defaultdict(lambda: None)
    res=Counter(); win=meta['result']['winner']
    for e in ev:
        if e['k'] in ('attack','cast') and e.get('cdmg'):
            for cid,a in e['cdmg']:
                g=cg.get(cid)
                if g is not None: dmg[g][team[e['a']]]+=a
        if e['k']=='camp_death':
            pass
        if e['k']=='capture':
            t=e['team']; g=e['g']; d=dmg[g]; tot=d[0]+d[1]
            gems=sum(s[1] for s in e['shares'])
            if tot>0 and d[1-t]/tot>=0.5:
                res[('stolen_by_winner' if t==win else 'stolen_by_loser')]+=gems
                res['steal_n']+=1
                holders=[cn[s[0]] for s in e['shares']]
                for h in holders: res['thief_'+h]+=1
            dmg[g]=[0.0,0.0]
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r)
    print({k:round(v/len(dirs),2) for k,v in tot.most_common()}, 'per game')
if __name__=='__main__': main()
