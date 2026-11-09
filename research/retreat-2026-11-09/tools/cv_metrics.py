"""Per team-game metrics of one bot in extracted debug batches (D trace lines needed), for the chase verdict A/Bs.

usage: cv_metrics.py EXTRACT_DIR BOT [EXTRACT_DIR BOT ...] [--procs N]

kills: enemy champions killed by the bot's team (a linked pair once); deaths: the bot's champions (to champions, to
camps); chaser deaths: deaths within 3 rounds of the champion's C (chase) decision; turns by decision letter (C chase,
F farm, A attack, R retreat, X contest, P hold, G siege, B bank); chase episodes as chasecf (runs of C, gaps <= 2;
a kill by the chaser, or by a teammate within 4 of it, up to the end + 2) and their no-kill turns; tributed gems and
lifetime gold earned at round 600 (the last round if earlier); captures by each side; denials (enemy holds reset);
OOF trace lines. Mean per team-game with a 95% normal interval of the mean.
"""
import argparse, gzip, json, math, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

LETTERS = 'CFARXPGBTHSUW'


def one(args):
    ex, g, bot = args
    try:
        meta = json.load(open(f"{ex}/{g['dir']}/meta.json"))
        R = json.load(gzip.open(f"{ex}/{g['dir']}/rounds.json.gz"))
        ev = [json.loads(l) for l in gzip.open(f"{ex}/{g['dir']}/events.jsonl.gz", 'rt')]
        z = zipfile.ZipFile(g['source'])
    except Exception:
        return []
    team_of = {c['id']: c['team'] for c in meta['champions']}
    ridx = {r: i for i, r in enumerate(R['round'])}
    chi = {c['id']: c for c in R['champions']}
    outs = []
    for t in (0, 1):
        if g['teams'][t] != bot: continue
        C = Counter()
        lines = z.read(f"team-{'ab'[t]}.stdout").decode(errors='replace').replace('\x00', '').splitlines()
        dec = {}
        for l in lines:
            if l.startswith('OOF'): C['oof_lines'] += 1
            p = l.split()
            if len(p) >= 4 and p[0] == 'D':
                try: dec[(int(p[1]), int(p[2]))] = p[3]
                except ValueError: pass
        for d in dec.values():
            if d in LETTERS: C['turns_' + d] += 1
        deaths = [e for e in ev if e['k'] == 'death']
        linked_second = {(e['r'], e['linked']) for e in deaths if e.get('linked') is not None}
        kills = []
        for e in deaths:
            v = e['v']
            if team_of.get(v) == t:
                C['deaths'] += 1
                C['deaths_champ' if e.get('by') is not None else 'deaths_camp'] += 1
                if any(dec.get((r, v)) == 'C' for r in range(e['r'] - 3, e['r'] + 1)): C['chaser_deaths'] += 1
            elif e.get('by') is not None and team_of.get(e['by']) == t and (e['r'], v) not in linked_second:
                C['kills'] += 1
                kills.append(e)
        # chase episodes (chasecf)
        for i in [c for c in chi if team_of[c] == t]:
            rs = sorted(r for (r, j), d in dec.items() if j == i and d == 'C')
            eps = []
            for r in rs:
                if eps and r - eps[-1][-1] <= 2: eps[-1].append(r)
                else: eps.append([r])
            for ep in eps:
                r0, r1 = ep[0], ep[-1]
                def near(e):
                    if e['by'] == i: return True
                    kk = ridx.get(e['r'] - 1)
                    if kk is None or not chi[i]['alive'][kk] or not e.get('at'): return False
                    return max(abs(chi[i]['x'][kk] - e['at'][0]), abs(chi[i]['y'][kk] - e['at'][1])) <= 4
                kill = any(r0 <= e['r'] <= r1 + 2 and near(e) for e in kills)
                C['chase_eps'] += 1
                C['chase_kill_eps'] += kill
                if not kill: C['nokill_chase_turns'] += len(ep)
        k600 = ridx.get(600, len(R['round']) - 1)
        C['gems600'] = R['gems'][t][k600]
        C['gold600'] = sum(chi[c]['earned'][k600] for c in chi if team_of[c] == t)
        C['enemy_gems600'] = R['gems'][1 - t][k600]
        for e in ev:
            if e['k'] == 'capture': C['captures' if e['team'] == t else 'enemy_captures'] += 1
            elif e['k'] == 'capture_reset' and e['team'] != t: C['denials'] += 1
        C['won'] = 1 if g.get('winner') == t else 0
        outs.append(C)
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pairs', nargs='+')
    ap.add_argument('--procs', type=int, default=16)
    a = ap.parse_args()
    cols = []
    for ex, bot in zip(a.pairs[::2], a.pairs[1::2]):
        ix = json.load(open(f'{ex}/index.json'))
        rows = []
        with ProcessPoolExecutor(a.procs) as pool:
            for r in pool.map(one, [(ex, g, bot) for g in ix['games']], chunksize=8): rows.extend(r)
        cols.append((bot, rows))
    keys = ['won', 'kills', 'deaths', 'deaths_champ', 'deaths_camp', 'chaser_deaths', 'chase_eps', 'chase_kill_eps',
            'nokill_chase_turns'] + ['turns_' + l for l in LETTERS] + ['gems600', 'enemy_gems600', 'gold600', 'captures',
            'enemy_captures', 'denials', 'oof_lines']
    print(f"{'metric':20s} " + ' '.join(f'{b + f" (n={len(r)})":>26s}' for b, r in cols))
    for k in keys:
        cells = []
        for b, rows in cols:
            xs = [r[k] for r in rows]
            n = len(xs)
            m = sum(xs) / n
            sd = math.sqrt(sum((x - m) ** 2 for x in xs) / max(1, n - 1))
            cells.append(f'{m:12.3f} +-{1.96 * sd / math.sqrt(n):9.3f}')
        print(f'{k:20s} ' + ' '.join(f'{c:>26s}' for c in cells))


if __name__ == '__main__':
    main()
