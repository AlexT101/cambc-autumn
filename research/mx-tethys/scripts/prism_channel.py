"""Prism tribute channels (bag >= MINBAG): outcome (completed / cancelled / died), allies and enemies within 8 of the
Prism over the channel, and the game result.

    py research/mx-tethys/scripts/prism_channel.py ANALYSIS_ROOT BATCH_NAME [MAX] [--minbag N]
"""
import gzip, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
MINBAG = int(sys.argv[sys.argv.index('--minbag') + 1]) if '--minbag' in sys.argv else 100


def one(dd):
    try:
        m = json.loads((dd / 'meta.json').read_text())
        R = json.load(gzip.open(dd / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    rix = {r: i for i, r in enumerate(R['round'])}
    C = {c['id']: c for c in R['champions']}
    out = []
    for k, e in enumerate(ev):
        if e['k'] != 'tribute_start' or names.get(e['a']) != 'Prism' or e['gems'] < MINBAG: continue
        a = e['a']; t = team[a]
        end = None
        for f in ev[k + 1:]:
            if f.get('a') == a and f['k'] in ('tribute_end', 'tribute_cancel'): end = f; break
            if f['k'] == 'tribute_start' and f.get('a') == a: end = dict(f, k='tribute_cancel', cause='self'); break
            if f['k'] == 'death' and f.get('v') == a: end = f; break
        if end is None: continue
        outcome = {'tribute_end': 'done', 'tribute_cancel': 'cancel-' + str(end.get('cause')), 'death': 'died'}[end['k']]
        na = ne = n = 0; ne_max = 0
        for r in range(e['r'], end['r'] + 1):
            i = rix.get(r)
            if i is None: continue
            p = (C[a]['x'][i], C[a]['y'][i])
            if p[0] is None: continue
            ca = ce = 0
            for c in R['champions']:
                if c['id'] == a or not c['alive'][i] or c['x'][i] is None: continue
                if cheb(p, (c['x'][i], c['y'][i])) <= 8:
                    if team[c['id']] == t: ca += 1
                    else: ce += 1
            na += ca; ne += ce; n += 1; ne_max = max(ne_max, ce)
        won_game = m['result']['winner'] == t
        winning = e['gems'] + (m['result'].get('scores') or [0, 0])[t] >= 1000 if m['result'].get('scores') else None
        out.append({'outcome': outcome, 'gems': e['gems'], 'r': e['r'], 'len': end['r'] - e['r'], 'na': na / max(1, n),
                    'ne': ne / max(1, n), 'nemax': ne_max, 'won': won_game})
    return out


def main():
    root = Path(sys.argv[1]); bname = sys.argv[2]
    mx = int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else 10**9
    dirs = []
    for dd in sorted(root.iterdir()):
        mf = dd / 'meta.json'
        if mf.exists() and bname in (json.loads(mf.read_text()).get('source') or ''): dirs.append(dd)
        if len(dirs) >= mx: break
    rows = []; games = 0
    with ProcessPoolExecutor(40) as ex:
        for x in ex.map(one, dirs, chunksize=4):
            if x is not None: games += 1; rows += x
    print(f'games {games}; Prism channels with bag >= {MINBAG}: {len(rows)} ({len(rows) / max(1, games):.2f} a game)')
    for o in sorted(set(x['outcome'] for x in rows)):
        s = [x for x in rows if x['outcome'] == o]
        if not s: continue
        f = lambda k: sum(x[k] for x in s) / len(s)
        print(f"{o:7s} {len(s) / len(rows) * 100:5.1f}%  bag {f('gems'):6.0f}  rounds {f('len'):5.1f}  allies<=8 {f('na'):.2f}  "
              f"enemies<=8 {f('ne'):.2f}  max enemies {f('nemax'):.2f}  team won {sum(x['won'] for x in s) / len(s) * 100:.0f}%")
    for side in (True, False):
        s = [x for x in rows if x['won'] == side]
        if not s: continue
        print(('W' if side else 'L'), f"channels/game {len(s) / games:.2f}, rounds in channels/game {sum(x['len'] for x in s) / games:.1f}, "
              f"rounds in not-done channels/game {sum(x['len'] for x in s if x['outcome'] != 'done') / games:.1f}, done {sum(x['outcome'] == 'done' for x in s) / len(s) * 100:.0f}%")
    by = defaultdict(Counter)
    for x in rows:
        b = 0 if x['nemax'] == 0 else 1 if x['nemax'] == 1 else 2
        by[b][x['outcome']] += 1
    for b in sorted(by):
        tot = sum(by[b].values())
        print(f"max enemies within 8 {['0', '1', '2+'][b]}: {tot} channels, " + ', '.join(f'{k} {v / tot * 100:.0f}%' for k, v in by[b].items()))
    by = defaultdict(Counter)
    for x in rows:
        if x['nemax'] == 0: continue
        b = min(3, round(x['na']))
        by[b][x['outcome']] += 1
    for b in sorted(by):
        tot = sum(by[b].values())
        print(f"contested, mean allies within 8 ~{b}: {tot} channels, " + ', '.join(f'{k} {v / tot * 100:.0f}%' for k, v in by[b].items()))


if __name__ == '__main__':
    main()
