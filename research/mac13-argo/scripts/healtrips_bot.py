"""healtrips.py split by bot (meta.json teams[].name): heal-trip share of alive time r1-600 by champion type
(recalls started under 60% hp, start to the next camp hit), Willow healing done per 100 alive rounds, camp deaths
a game. py healtrips_bot.py EXTRACT_DIR"""
import gzip, json, sys, statistics as st
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = [meta['teams'][t]['name'] for t in (0, 1)]
    C = R['champions']; rid = {r: i for i, r in enumerate(R['round'])}; n = min(len(R['round']), 600)
    mc = {c['id']: c for c in meta['champions']}
    team = {c['id']: c['team'] for c in C}
    hits = defaultdict(list)
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('cdmg') and e['r'] <= 700: hits[e['a']].append(e['r'])
    out = {'trips': [], 'willow': [], 'camp_deaths': {nm: 0 for nm in names}, 'games': names}
    for e in ev:
        if e['k'] == 'death' and not e.get('linked') and (e.get('by') is None or e.get('by') not in team):
            out['camp_deaths'][names[team[e['v']]]] += 1
    for c in C:
        alive = sum(c['alive'][:n]); trips = []; rs = None
        nm = names[c['team']]; ty = mc[c['id']]['name']
        for e in ev:
            if e.get('a') != c['id'] or e['r'] > 600: continue
            if e['k'] == 'recall_start':
                i = rid.get(e['r'] - 1, 0); rs = (e['r'], c['hp'][i] / c['maxHp'][i] if c['maxHp'][i] else 1)
            elif e['k'] == 'recall_end' and rs:
                if rs[1] < 0.6:
                    nxt = next((h for h in hits[c['id']] if h > e['r']), None)
                    trips.append((nxt - rs[0]) if nxt else None)
                rs = None
            elif e['k'] == 'recall_cancel': rs = None
        out['trips'].append((nm, ty, alive, trips))
        if ty == 'Willow':
            out['willow'].append((nm, sum(c['alive']), (mc[c['id']].get('stats') or {}).get('healingDone', 0)))
    return out


if __name__ == '__main__':
    root = Path(sys.argv[1]); dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    agg = defaultdict(lambda: [0, 0, []]); wil = defaultdict(lambda: [0, 0.0, 0]); cd = defaultdict(int); games = defaultdict(int)
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=8):
            if not r: continue
            for nm in r['games']: games[nm] += 1
            for nm, k in r['camp_deaths'].items(): cd[nm] += k
            for nm, ty, alive, trips in r['trips']:
                a = agg[(nm, ty)]; a[0] += alive; a[1] += len(trips); a[2] += [t for t in trips if t is not None]
            for nm, alive, healed in r['willow']:
                w = wil[nm]; w[0] += alive; w[1] += healed; w[2] += 1
    for nm in sorted(games):
        print(f"== {nm}: games {games[nm]} camp deaths/game {cd[nm]/games[nm]:.3f}")
        if nm in wil:
            w = wil[nm]; print(f"   Willow games {w[2]} healing /100 alive rounds {100*w[1]/max(1,w[0]):.0f}")
        for (n2, ty), (alive, k, ts) in sorted(agg.items()):
            if n2 != nm or alive < 2000: continue
            share = (k * (st.mean(ts) if ts else 0)) / alive * 100
            print(f"   {ty:14s} heal recalls /100 alive {100*k/alive:.2f}; median start->hit {st.median(ts) if ts else '-'}; heal-trip share {share:.1f}%")
