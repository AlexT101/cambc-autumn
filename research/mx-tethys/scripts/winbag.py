"""Games where a team's tributed score plus its carried gems (all bodies) first reached 1000: when, which team won,
and how the game ended after. Also the round each team's carried+tributed first reached 1000 by Prism alone.

    py research/mx-tethys/scripts/winbag.py ANALYSIS_ROOT BATCH_NAME [MAX]
"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def one(dd):
    try:
        m = json.loads((dd / 'meta.json').read_text())
        R = json.load(gzip.open(dd / 'rounds.json.gz'))
    except Exception:
        return None
    names = {c['id']: c['name'] for c in m['champions']}
    rounds = R['round']; sc = R['gems']  # tributed per team per round
    first = [None, None]; firstp = [None, None]; info = [None, None]
    for i, r in enumerate(rounds):
        for t in (0, 1):
            tot = sc[t][i]
            carried = sum((c['gems'][i] or 0) for c in R['champions'] if c['team'] == t and c['alive'][i])
            pr = sum((c['gems'][i] or 0) for c in R['champions'] if c['team'] == t and c['alive'][i] and names[c['id']] == 'Prism')
            if first[t] is None and tot + carried >= 1000:
                first[t] = r
                info[t] = {'need': 1000 - tot, 'prism': pr, 'others': carried - pr,
                           'maxbag': max([(c['gems'][i] or 0) for c in R['champions'] if c['team'] == t and c['alive'][i]] + [0])}
            if firstp[t] is None and tot + pr >= 1000: firstp[t] = r
    deaths = [[e['r'], e['v'], e.get('gems') or 0] for e in (json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')) if e['k'] == 'death']
    team = {c['id']: c['team'] for c in m['champions']}
    lost_after = [sum(g for r, v, g in deaths if team.get(v) == t and first[t] is not None and r >= first[t]) for t in (0, 1)]
    prism_died_after = [any(names.get(v) == 'Prism' and team.get(v) == t and first[t] is not None and r >= first[t] for r, v, g in deaths) for t in (0, 1)]
    return {'info': info, 'lost_after': lost_after, 'pda': prism_died_after, 'first': first, 'firstp': firstp, 'winner': m['result']['winner'], 'end': rounds[-1]}


def main():
    root = Path(sys.argv[1]); bname = sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
    dirs = []
    for dd in sorted(root.iterdir()):
        mf = dd / 'meta.json'
        if mf.exists() and bname in (json.loads(mf.read_text()).get('source') or ''): dirs.append(dd)
        if len(dirs) >= mx: break
    rows = []
    with ProcessPoolExecutor(40) as ex:
        for x in ex.map(one, dirs, chunksize=4):
            if x: rows.append(x)
    n = len(rows); print('games', n)
    c = Counter()
    lag = []; lagw = []
    for x in rows:
        f = x['first']
        reached = [t for t in (0, 1) if f[t] is not None]
        if not reached: c['nobody reached'] += 1; continue
        t = min(reached, key=lambda t: f[t])
        won = x['winner'] == t
        c['first to reach won' if won else 'first to reach LOST'] += 1
        (lagw if won else lag).append(x['end'] - f[t])
        I = x['info'][t]
        key = 'W' if won else 'L'
        c[key + ' n'] += 1; c[key + ' need'] += I['need']; c[key + ' prism'] += I['prism']; c[key + ' others'] += I['others']
        c[key + ' one bag covers need'] += I['maxbag'] >= I['need']; c[key + ' prism bag covers'] += I['prism'] >= I['need']
        c[key + ' gems lost dying after'] += x['lost_after'][t]; c[key + ' Prism died after'] += x['pda'][t]
        fp = x['firstp']
        if fp[t] is not None and fp[t] <= f[t] + 1: c['reached through Prism bag'] += 1
    for k in ('first to reach won', 'first to reach LOST', 'reached through Prism bag', 'nobody reached'):
        print(f'{k}: {c[k]} ({c[k] / n * 100:.1f}%)')
    for key in 'WL':
        k = c[key + ' n'] or 1
        print(key, {a: round(c[key + ' ' + a] / k, 2) for a in ('need', 'prism', 'others', 'one bag covers need', 'prism bag covers', 'gems lost dying after', 'Prism died after')})
    import statistics
    if lagw: print('median rounds reaching->end won', statistics.median(lagw))
    if lagw: print('rounds from reaching to end, won: mean', sum(lagw) / len(lagw))
    if lag: print('rounds from reaching to end, lost: mean', sum(lag) / len(lag))


if __name__ == '__main__':
    main()
