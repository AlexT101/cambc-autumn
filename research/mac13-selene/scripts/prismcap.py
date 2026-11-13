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
    names={c['id']:c['name'] for c in meta['champions']}
    team={c['id']:c['team'] for c in meta['champions']}
    cg={c['id']:c['group'] for c in mp['camps']}
    dmg=defaultdict(lambda: defaultdict(float))
    res=Counter()
    for e in ev:
        if e['k'] in ('attack','cast') and e.get('cdmg'):
            for cid,a in e['cdmg']:
                g=cg.get(cid)
                if g is not None: dmg[g][e['a']]+=a
        if e['k']=='capture':
            g=e['g']; holders=[s[0] for s in e['shares']]; gems=sum(s[1] for s in e['shares'])
            d=dmg[g]; tot=sum(d.values()) or 1
            prism_hold=any(names[h]=='Prism' for h in holders)
            if prism_hold:
                pd=sum(v for k,v in d.items() if names[k]=='Prism')/tot
                allyd=sum(v for k,v in d.items() if team[k]==e['team'] and names[k]!='Prism')/tot
                res['prism_caps']+=1; res['prism_gems']+=gems
                if pd>=0.5: res['prism_own_clear_gems']+=gems
                elif allyd>=0.5: res['prism_ally_clear_gems']+=gems
                else: res['prism_other_gems']+=gems
            else:
                res['ally_caps']+=1; res['ally_gems']+=gems
            dmg[g]=defaultdict(float)
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r)
    n=len(dirs)*2
    print({k: round(v/n,1) for k,v in tot.items()}, 'per team-game')
if __name__=='__main__': main()
