"""Read livefork_run.py outputs: fidelity, noise, cold-start bias and A/B power of forked live Mite games.

    python3 forkstats.py LIVE_DIR [--local LOCAL_DIR] [--json OUT]

Outcome per arm = our result from the fork: 1 win, 0 loss, 0.5 unfinished. SEs are clustered by game (forks of one game
share its map and history).
"""
import argparse, json, math
from collections import defaultdict
import numpy as np


def load(d):
    games, arms = {}, defaultdict(dict)
    for l in open(f'{d}/out.jsonl'):
        r = json.loads(l)
        if r['type'] == 'game':
            games[r['id']] = r
        else:
            arms[(r['game'], r['fork'])][r['label']] = r
    return games, arms


def ours_of(g):
    return g.get('ours')


def outcome(a, ours):
    if 'winner' not in a or a.get('error'):
        return None
    if not a.get('finished'):
        return 0.5
    w = a['winner']
    return 0.5 if w is None else float(w == ours)


def clustered(pairs):
    """pairs: list of (cluster, value). Mean and cluster-robust SE."""
    if not pairs:
        return float('nan'), float('nan'), 0
    v = np.array([x for _, x in pairs], float)
    m = v.mean()
    by = defaultdict(float)
    for c, x in pairs:
        by[c] += x - m
    n = len(v)
    se = math.sqrt(sum(s * s for s in by.values())) / n
    return m, se, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('live')
    ap.add_argument('--local')
    ap.add_argument('--json')
    a = ap.parse_args()
    rep = {}
    games, arms = load(a.live)
    # game lines lack 'ours': take it from the games files
    ours = {}
    import glob
    for f in glob.glob(f'{a.live}/games-*.jsonl'):
        for l in open(f):
            g = json.loads(l)
            ours[g['id']] = (g['ours'], g['live'])
    errs = [g for g in games.values() if g.get('error') or g.get('fork_errors')]
    print(f'live: {len(games)} games, {len(arms)} forks, {len(errs)} games with errors')
    # main line = live?
    ok = 0
    for gid, g in games.items():
        o, live = ours[gid]
        if g.get('trib') and live['result']:
            s = live['result'].split('-')
            ok += int(g['trib'][o]) == int(float(s[0])) and int(g['trib'][1 - o]) == int(float(s[1]))
    print(f'main line reproduces the live score: {ok}/{len(games)}')
    rounds = sorted({k[1] for k in arms})
    present = {lb for al in arms.values() for lb in al}
    labels = [lb for lb in ['puppet', 'body1', 'body2', 'cold+body1', 'life+body1', '519+body1', 'life+body2', '519+body2'] if lb in present]
    res = defaultdict(list)  # (label, round) -> [(game, outcome)]
    rows = []
    for (gid, r), al in arms.items():
        o = ours[gid][0]
        out = {lb: outcome(al[lb], o) for lb in labels if lb in al}
        if any(v is None for v in out.values()) or len(out) < len(labels):
            continue
        rows.append((gid, r, out, al))
    notes = sum(1 for _, _, _, al in rows for x in al.values() if x.get('notes'))
    print(f'complete forks {len(rows)}; arm rows with DRAFT-/PLAN- notes {notes}')
    tab = {}
    print('\nby fork round: mean our win from the fork (cluster SE), agreement rates')
    hdr = f'{"round":>5} {"n":>5} ' + ' '.join(f'{lb:>11s}' for lb in labels[:4]) + '   agree(b1,live) agree(b1,b2) agree(cold,b1)'
    print(hdr)
    for R in rounds + ['all']:
        sel = [x for x in rows if R == 'all' or x[1] == R]
        if not sel:
            continue
        cells = []
        for lb in (labels + ['-'] * 4)[:4]:
            if lb == '-':
                cells.append('-'); continue
            m, se, n = clustered([(g, out[lb]) for g, _, out, _ in sel])
            cells.append(f'{m * 100:5.1f}±{se * 100:3.1f}')
        ag = lambda x, y: np.mean([out[x] == out[y] for _, _, out, _ in sel]) if x in labels and y in labels else float('nan')
        print(f'{str(R):>5} {len(sel):5d} ' + ' '.join(f'{c:>11s}' for c in cells) +
              f'   {ag("body1", "puppet") * 100:6.1f}%        {ag("body1", "body2") * 100:6.1f}%      {ag("cold+body1", "body1") * 100:6.1f}%')
        d = {}
        for lb in labels:
            m, se, n = clustered([(g, out[lb]) for g, _, out, _ in sel])
            d[lb] = [m, se, n]
        d['agree_b1_live'] = ag('body1', 'puppet'); d['agree_b1_b2'] = ag('body1', 'body2'); d['agree_cold_b1'] = ag('cold+body1', 'body1')
        # paired contrasts
        for name, x, y in [('body_minus_live', [b for b in ['body1', 'body2'] if b in labels], ['puppet'] * len([b for b in ['body1', 'body2'] if b in labels])),
                           ('cold_minus_warm', ['cold+body1'], ['body1']), ('life_minus_519', ['life+body1', 'life+body2'], ['519+body1', '519+body2'])]:
            if not all(v in labels for v in x + y):
                continue
            pairs = [(g, np.mean([out[p] - out[q] for p, q in zip(x, y)])) for g, _, out, _ in sel]
            m, se, n = clustered(pairs)
            sd = float(np.std([v for _, v in pairs]))
            d[name] = [m, se, n, sd]
        tab[str(R)] = d
    print('\npaired contrasts (points of our win rate, cluster SE; sd of the per-fork difference)')
    for name in ['body_minus_live', 'cold_minus_warm', 'life_minus_519']:
        if name not in tab.get('all', {}):
            continue
        print(f'  {name}: ' + '  '.join(f'r{R} {tab[str(R)][name][0] * 100:+.2f}±{tab[str(R)][name][1] * 100:.2f} (sd {tab[str(R)][name][3] * 100:.0f})'
                                        for R in rounds + ['all'] if str(R) in tab))
    # how many forks are 'live' (outcome flips between body seeds or between life and 519)
    for R in rounds:
        sel = [x for x in rows if x[1] == R]
        flip = np.mean([out['life+body1'] != out['519+body1'] or out['life+body2'] != out['519+body2'] for _, _, out, _ in sel])
        print(f'  r{R}: share of forks where life and 519 differ in outcome under either body seed: {flip * 100:.1f}%')
    cpu = [x['cpu_ms'] for _, _, _, al in rows for x in al.values()]
    gcpu = [g['cpu_ms'] - g['arm_cpu_ms'] for g in games.values() if 'cpu_ms' in g]
    print(f'\nCPU: arm mean {np.mean(cpu):.0f} ms (median {np.median(cpu):.0f}); main line + drafts per game {np.mean(gcpu):.0f} ms')
    rep['live'] = {'games': len(games), 'forks': len(rows), 'main_ok': ok, 'table': tab, 'arm_cpu_ms': float(np.mean(cpu)),
                   'game_cpu_ms': float(np.mean(gcpu))}
    if a.local:
        lg, la = load(a.local)
        lours = {}
        for f in glob.glob(f'{a.local}/games-*.jsonl'):
            for l in open(f):
                g = json.loads(l)
                lours[g['id']] = (g['ours'], g['live'])
        lrows = []
        for (gid, r), al in la.items():
            o = lours[gid][0]
            out = {lb: outcome(al[lb], o) for lb in ['warm', 'cold-same', 'cold-other'] if lb in al}
            if len(out) == 3 and all(v is not None for v in out.values()):
                lrows.append((gid, r, out))
        print(f'\nlocal (our live build vs the body from round 1): {len(lg)} games, {len(lrows)} forks')
        mw = clustered([(g, float(x['winner'] == lours[g][0]) if x.get('winner') is not None else 0.5) for g, x in lg.items() if 'winner' in x])
        livew = np.mean([float(lours[g][1]['result'].split('-')[0]) > float(lours[g][1]['result'].split('-')[1]) for g in lg])
        print(f'  full game vs the body: our win {mw[0] * 100:.1f}±{mw[1] * 100:.1f} of {mw[2]}; the same maps/sides live vs Mite: {livew * 100:.1f}')
        lt = {}
        for R in sorted({x[1] for x in lrows}) + ['all']:
            sel = [x for x in lrows if R == 'all' or x[1] == R]
            d = {}
            for name, x, y in [('cold_same_minus_warm', 'cold-same', 'warm'), ('cold_other_minus_warm', 'cold-other', 'warm')]:
                m, se, n = clustered([(g, out[x] - out[y]) for g, _, out in sel])
                d[name] = [m, se, n]
            d['warm'] = clustered([(g, out['warm']) for g, _, out in sel])
            d['agree_same_warm'] = float(np.mean([out['cold-same'] == out['warm'] for _, _, out in sel]))
            d['agree_other_warm'] = float(np.mean([out['cold-other'] == out['warm'] for _, _, out in sel]))
            lt[str(R)] = d
            print(f'  r{R}: n {len(sel)}, warm {d["warm"][0] * 100:.1f}; cold-same - warm {d["cold_same_minus_warm"][0] * 100:+.2f}±{d["cold_same_minus_warm"][1] * 100:.2f}, '
                  f'cold-other - warm {d["cold_other_minus_warm"][0] * 100:+.2f}±{d["cold_other_minus_warm"][1] * 100:.2f}; '
                  f'agree same {d["agree_same_warm"] * 100:.1f}% other {d["agree_other_warm"] * 100:.1f}%')
        rep['local'] = {'games': len(lg), 'forks': len(lrows), 'full_game_win': mw, 'live_win_same_maps': float(livew), 'table': lt}
    if a.json:
        json.dump(rep, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
