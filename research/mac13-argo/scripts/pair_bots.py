"""pair.py's Cassi & Issac measures split by bot in an A/B batch's extract: distance apart shares (r1-800, both alive),
combined camp damage a round by distance, pair deaths a game. Team A's bot is from the replay name's -12/-21 (as
extract.mjs's batch context: -12 puts results.json's bots[0] on team A). py pair_bots.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def band(d): return '0-2' if d <= 2 else '3-5' if d <= 5 else '6-10' if d <= 10 else '11+'


def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    teams = meta.get('teams') or []
    if len(teams) < 2 or 'bot' not in teams[0]: return None
    C = R['champions']; idx = {c['id']: i for i, c in enumerate(C)}
    w = meta['result']['winner']
    team_keys = sorted({c['team'] for c in C}, key=str)
    pairs = {}
    for c in meta['champions']:
        if c['name'] in ('Cassi', 'Issac'): pairs.setdefault(c['team'], {})[c['name']] = c['id']
    campdmg = Counter()
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            v = e['cdmg']; campdmg[(e['a'], e['r'])] += sum(x[1] for x in v) if isinstance(v, list) else v
    out = {}
    for t, p in pairs.items():
        if len(p) < 2: continue
        side = team_keys.index(t) if t in team_keys else 0
        bot = teams[side]['bot']
        o = out.setdefault(bot, {'dist': Counter(), 'dmg': Counter(), 'deaths': 0, 'games': 1, 'won': int(t == w)})
        a, b = C[idx[p['Cassi']]], C[idx[p['Issac']]]
        for i in range(min(len(R['round']), 800)):
            if a['alive'][i] and b['alive'][i] and a['x'][i] is not None and b['x'][i] is not None:
                k = band(cheb((a['x'][i], a['y'][i]), (b['x'][i], b['y'][i])))
                o['dist'][k] += 1
                r = R['round'][i]
                o['dmg'][k] += campdmg[(p['Cassi'], r)] + campdmg[(p['Issac'], r)]
        o['deaths'] += sum(1 for e in ev if e['k'] == 'death' and e['v'] in (p['Cassi'], p['Issac']) and not e.get('linked'))
    return out


if __name__ == '__main__':
    root = Path(sys.argv[1]); dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    names = {0: 'cand', 1: 'ref'}
    T = {}
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, dirs, chunksize=16):
            for bot, x in (o or {}).items():
                t = T.setdefault(bot, {'dist': Counter(), 'dmg': Counter(), 'deaths': 0, 'games': 0, 'won': 0})
                t['dist'].update(x['dist']); t['dmg'].update(x['dmg'])
                for k in ('deaths', 'games', 'won'): t[k] += x[k]
    for bot in sorted(T):
        t = T[bot]; tot = sum(t['dist'].values()) or 1; all_dmg = sum(t['dmg'].values())
        print(f"{names.get(bot, bot)}: games {t['games']} won {t['won']} pair deaths/game {t['deaths'] / max(1, t['games']):.2f} "
              f"camp dmg/rd (both alive) {all_dmg / tot:.1f}")
        print('   ', {k: f"{100 * t['dist'][k] / tot:.0f}% dmg/rd {t['dmg'][k] / max(1, t['dist'][k]):.1f}" for k in ('0-2', '3-5', '6-10', '11+')})
