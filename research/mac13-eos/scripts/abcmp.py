"""CAND vs REF per game from an extracted A/B batch: deaths by type, kills, capture gems, gold earned, camp damage,
time dead, by team name. py abcmp.py EXTRACT_DIR CANDNAME"""
import gzip,json,sys,collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
CAND=sys.argv[2]
def g(d):
    meta=json.loads((d/'meta.json').read_text())
    tn=[t['name'] for t in meta['teams']]
    if CAND not in tn: return None
    ci=tn.index(CAND); w=meta['result']['winner']
    out={'win':w==ci,'rounds':meta['result']['rounds']}
    for side,ti in (('C',ci),('R',1-ci)):
        cs=[c for c in meta['champions'] if int(c['team'])==ti]
        out[side]=dict(deaths=sum(c['stats']['deaths'] for c in cs),
            pairdeaths=sum(c['stats']['deaths'] for c in cs if c['name']=='Cassi'),
            prismdeaths=sum(c['stats']['deaths'] for c in cs if c['name']=='Prism'),
            kills=sum(c['stats']['kills'] for c in cs),
            gems=sum(c['stats']['collectedGems'] for c in cs),
            gold=sum(c['stats']['earnedGold'] for c in cs),
            camp=sum(c['stats']['monsterDamageDone'] for c in cs),
            paircamp=sum(c['stats']['monsterDamageDone'] for c in cs if c['name'] in ('Cassi','Issac')),
            tributed=meta['result']['gems'][ti])
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: res=[r for r in ex.map(g,dirs,chunksize=8) if r]
    n=len(res); print('games',n,'cand win',round(sum(r['win'] for r in res)/n,3))
    for k in res[0]['C']:
        c=sum(r['C'][k] for r in res)/n; rr=sum(r['R'][k] for r in res)/n
        print(f'{k:12s} cand {c:9.1f} ref {rr:9.1f} diff {c-rr:+.1f}')
