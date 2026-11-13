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
    cn={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    cg={c['id']:c['group'] for c in mp['camps']}
    gt={g['id']:('mono' if 'Monolith' in g['types'] else 'golem' if 'Golem' in g['types'] else 'elk' if 'Elk' in g['types'] else 'wolf' if 'Wolf' in g['types'] else 'gems' if 'Gem cluster' in g['types'] else 'gold') for g in mp['groups']}
    dmg=defaultdict(lambda: defaultdict(float)); res=Counter()
    for e in ev:
        if e['k'] in ('attack','cast') and e.get('cdmg'):
            for cid,a in e['cdmg']:
                g=cg.get(cid)
                if g is not None: dmg[g][e['a']]+=a
        if e['k']=='capture':
            g=e['g']; d=dmg[g]; tot=sum(d.values()) or 1; gems=sum(s[1] for s in e['shares'])
            holders=[cn[s[0]] for s in e['shares']]
            pd=sum(v for k,v in d.items() if cn[k]=='Prism' and team[k]==e['team'])/tot
            who='prism_holds' if 'Prism' in holders else 'ally_holds'
            clr='prism_cleared' if pd>=0.5 else 'ally_cleared'
            res[(who,clr,gt[g],'gems')]+=gems; res[(who,clr,gt[g],'n')]+=1
            dmg[g]=defaultdict(float)
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r)
    n=2*len(dirs)
    keys=sorted(set(k[:3] for k in tot))
    for k in keys: print(k, 'n %.2f gems %.1f'%(tot[k+('n',)]/n, tot[k+('gems',)]/n))
if __name__=='__main__': main()
