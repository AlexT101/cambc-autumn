import json, gzip, os, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT = r'C:\Users\alext\Github\cambc-autumn\replays\.analysis'
def game(d):
    try:
        m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
        R = json.load(gzip.open(os.path.join(ROOT, d, 'rounds.json.gz')))
    except Exception: return None
    out = []
    rounds = m['result']['rounds']
    for t in (0, 1):
        champs = [ (i,c) for i,c in enumerate(m['champions']) if c['team'] == t]
        picks = len(m['draft']['picks'][t])
        bodies = len(champs)
        gems = m['result']['gems'][t]
        # champion-rounds alive & off-spawn-ish: alive rounds
        alive = sum(sum(R['champions'][i]['alive']) for i,_ in champs)
        dead = sum(len(R['champions'][i]['alive']) - sum(R['champions'][i]['alive']) for i,_ in champs)
        deaths = sum(c['deaths'] for _,c in champs)
        earned = sum(R['champions'][i]['earned'][-1] for i,_ in champs)
        # collected gems (captures + kills) from rounds: not available directly; use tributed
        out.append(dict(team=m['teams'][t]['name'], won=m['result']['winner']==t, rounds=rounds, picks=picks, bodies=bodies,
                        gems=gems, alive=alive, dead=dead, deaths=deaths, earned=earned, map=m['map']['name']))
    return out
if __name__ == '__main__':
    idxj = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))
    dirs = sorted({g['dir'] for g in idxj['games'] if g['kind'] == 'ladder' and g['ok'] and '20261016' <= g['source'].split('/')[2][:8]})
    rows = []
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(game, dirs, chunksize=8):
            if r: rows += r
    json.dump(rows, open('rates.json', 'w'))
    tops=['Intercontinental Fish','Mite','Sneaky Bush Campers','Univardisty of Shingtonwash','Nyxius','procless','PTN Hyperion']
    def summ(rs, label):
        if not rs: return
        rho = sum(r['gems'] for r in rs) / sum(r['rounds']*r['picks'] for r in rs)
        rho_alive = sum(r['gems'] for r in rs) / max(1,sum(r['alive'] for r in rs))
        dr = sum(r['deaths'] for r in rs) / sum(r['rounds']*r['picks'] for r in rs) * 1000
        deadshare = sum(r['dead'] for r in rs) / max(1,sum(r['dead']+r['alive'] for r in rs))
        gold = sum(r['earned'] for r in rs) / sum(r['rounds']*r['picks'] for r in rs)
        print(f'{label[:24]:24s} games {len(rs):5d} win {sum(r["won"] for r in rs)/len(rs):.2f} rounds {st.mean(r["rounds"] for r in rs):6.0f} gems/pick-round {rho:.3f} gems/body-alive-round {rho_alive:.3f} deaths/1k pick-rounds {dr:.2f} dead-share {deadshare:.3f} gold/pick-round {gold:.3f}')
    summ(rows, 'ALL')
    for t in tops: summ([r for r in rows if r['team']==t], t)
