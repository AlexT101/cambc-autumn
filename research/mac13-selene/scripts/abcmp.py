"""CAND vs REF per game on an extracted A/B batch: usage abcmp.py EXTRACT_DIR CANDNAME"""
import json, gzip, sys, os
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; CAND=sys.argv[2]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    names=[t['name'] for t in meta['teams']]
    if CAND not in names: return None
    ct=names.index(CAND)
    cn={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}; rix={r:i for i,r in enumerate(R['round'])}
    n=len(R['round'])
    out={t:Counter() for t in (0,1)}
    for t in (0,1): out[t]['win']=int(meta['result']['winner']==t); out[t]['games']=1
    prism={c['team']:c['id'] for c in meta['champions'] if c['name']=='Prism'}
    firstp=None
    cg={c['id']:c['group'] for c in mp['camps']}
    dmg=defaultdict(lambda: defaultdict(float))
    for e in ev:
        if e['k']=='death':
            v=e['v']; t=team[v]
            if not e.get('linked'): out[t]['deaths']+=1; out[t]['gems_lost']+=e.get('gems',0)
            if cn[v] in('Cassi','Issac') and not e.get('linked'): out[t]['pair_deaths']+=1
            if cn[v]=='Prism':
                out[t]['prism_deaths']+=1
                if firstp is None and len(prism)==2: firstp=t
        if e['k'] in ('attack','cast') and e.get('cdmg'):
            for cid,a in e['cdmg']:
                g=cg.get(cid)
                if g is not None: dmg[g][e['a']]+=a
        if e['k']=='capture':
            t=e['team']; gems=sum(s[1] for s in e['shares']); out[t]['cap_gems']+=gems
            holders=[s[0] for s in e['shares']]
            if t in prism and prism[t] in holders:
                out[t]['prism_cap_gems']+=gems
                d=dmg[e['g']]; tot=sum(d.values()) or 1
                if sum(v for k,v in d.items() if team[k]==t and cn[k]!='Prism')/tot>=0.5: out[t]['prism_handoff_gems']+=gems
            dmg[e['g']]=defaultdict(float)
    for t in (0,1):
        if t in prism:
            p=ch[idx[prism[t]]]
            for r in (300,500):
                i=rix.get(r)
                if i is not None: out[t][f'prism_bag{r}']=p['gems'][i]; out[t][f'n_bag{r}']=1
            # mean distance to nearest ally while alive
            ds=[];
            for i in range(0,n,5):
                if not p['alive'][i] or p['x'][i] is None: continue
                best=99
                for c in ch:
                    if c['team']==t and c['id']!=p['id'] and c['alive'][i] and c['x'][i] is not None:
                        best=min(best,max(abs(c['x'][i]-p['x'][i]),abs(c['y'][i]-p['y'][i])))
                ds.append(best)
            if ds: out[t]['prism_ally_dist']=sum(ds)/len(ds); out[t]['n_pd']=1; out[t]['prism_isolated']=sum(1 for x in ds if x>6)/len(ds)
        out[t]['earned']=sum(c['earned'][-1] for c in ch if c['team']==t)
        out[t]['tributed']=meta['result']['gems'][t]
    if firstp is not None: out[firstp]['first_prism_death']=1; out[0]['n_fp']=1; out[1]['n_fp']=1
    return out[ct], out[1-ct]
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    C=Counter(); Rf=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: C.update(r[0]); Rf.update(r[1])
    g=C['games']; print('games',g,'cand win',C['win']/g)
    for k in sorted(set(C)|set(Rf)):
        if k.startswith('n_') or k=='games': continue
        den = C['n_bag300'] if k=='prism_bag300' else C['n_bag500'] if k=='prism_bag500' else C['n_pd'] if k in ('prism_ally_dist','prism_isolated') else C['n_fp'] if k=='first_prism_death' else g
        dr = Rf['n_bag300'] if k=='prism_bag300' else Rf['n_bag500'] if k=='prism_bag500' else Rf['n_pd'] if k in ('prism_ally_dist','prism_isolated') else Rf['n_fp'] if k=='first_prism_death' else g
        print(f"{k:20s} cand {C[k]/max(1,den):9.3f}  ref {Rf[k]/max(1,dr):9.3f}")
if __name__=='__main__': main()
