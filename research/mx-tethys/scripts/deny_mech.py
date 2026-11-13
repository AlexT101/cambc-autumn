"""CAND vs REF mechanism counts for an A/B batch: capture gems by ground (own / mid / enemy, Chebyshev share to the two
spawns, from the capturing team's side) and phase; both Prisms' Focus ratio CAND/REF at r150 and r250 (both alive) with
the CAND win rate by ratio bucket; champion-killed deaths a game by side (Prism deaths apart) and gems lost dying.
CAND is bot 1: team A in `-12` replays, team B in `-21`.

    py research/mx-tethys/scripts/deny_mech.py ANALYSIS_ROOT BATCH_NAME [MAX]
"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
PHASES = ('r1-150', 'r151-300', 'r301-600', 'r601+')


def one(dd):
    try:
        m = json.loads((dd / 'meta.json').read_text())
        mp = json.loads((dd / m['mapFile']).resolve().read_text())
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
        R = json.load(gzip.open(dd / 'rounds.json.gz'))
    except Exception:
        return None
    src = m.get('source') or ''
    cand = 0 if src.endswith('-12.repl26a') else 1 if src.endswith('-21.repl26a') else None
    if cand is None: return None
    side = lambda t: 'C' if t == cand else 'R'
    sp = mp['spawn']
    cen = lambda s: ((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2)
    gc = {}
    for gi, g in enumerate(mp['groups']):
        tiles = g.get('tiles') or g.get('camps') or []
        pts = []
        for t in tiles:
            if isinstance(t, dict): pts.append((t.get('x'), t.get('y')))
            elif isinstance(t, (list, tuple)): pts.append(tuple(t[:2]))
            elif isinstance(t, int) and t < len(mp['camps']):
                c = mp['camps'][t]; pts.append((c['x'], c['y']) if isinstance(c, dict) else tuple(c[:2]))
        if not pts: continue
        gc[gi] = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    out = defaultdict(float)
    w = m['result']['winner']
    out['games'] = 1
    out['C_win'] = 1.0 if w == cand else 0.0
    names = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    for e in ev:
        if e['k'] == 'capture' and e['g'] in gc:
            t = e['team']; p = gc[e['g']]
            da, de = cheb(p, cen(sp[t])), cheb(p, cen(sp[1 - t]))
            s = da / max(1e-9, da + de)
            ground = 'own' if s < 0.4 else 'enemy' if s > 0.6 else 'mid'
            ph = PHASES[0] if e['r'] <= 150 else PHASES[1] if e['r'] <= 300 else PHASES[2] if e['r'] <= 600 else PHASES[3]
            out[('cap', side(t), ground, ph)] += sum(x[1] for x in e['shares'])
        elif e['k'] == 'death' and e.get('v') in names:
            v = e['v']; s = side(team[v])
            if e.get('by') in names:
                out[('death', s)] += 1
                if names[v] == 'Prism': out[('pdeath', s)] += 1
                out[('lost', s)] += e.get('gems') or 0
            else:
                out[('campdeath', s)] += 1
    pr = {team[i]: i for i in names if names[i] == 'Prism'}
    if len(pr) == 2:
        rix = {r: i for i, r in enumerate(R['round'])}
        C = {c['id']: c for c in R['champions']}
        for RR in (150, 250):
            i = rix.get(RR)
            if i is None: continue
            if any(e['k'] == 'death' and e.get('v') in pr.values() and e['r'] <= RR for e in ev): continue
            fc, fr = C[pr[cand]]['foc'][i] or 0, C[pr[1 - cand]]['foc'][i] or 0
            out[('focus', RR)] = fc / max(1.0, fr)
    return dict(out)


def main():
    root = Path(sys.argv[1]); bname = sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
    dirs = []
    for dd in sorted(root.iterdir()):
        mf = dd / 'meta.json'
        if mf.exists() and bname in (json.loads(mf.read_text()).get('source') or ''): dirs.append(dd)
        if len(dirs) >= mx: break
    tot = defaultdict(float); ratios = {150: [], 250: []}
    with ProcessPoolExecutor(40) as ex:
        for x in ex.map(one, dirs, chunksize=4):
            if not x: continue
            for k, v in x.items():
                if isinstance(k, tuple) and k[0] == 'focus': ratios[k[1]].append((v, x['C_win']))
                else: tot[k] += v
    n = tot['games']
    print(f"games {n:.0f}, CAND win {tot['C_win'] / n * 100:.1f}% (capture gems a game, CAND / REF)")
    for ph in PHASES:
        print(ph, '  '.join(f"{g}: {tot[('cap', 'C', g, ph)] / n:6.1f} / {tot[('cap', 'R', g, ph)] / n:6.1f}" for g in ('own', 'mid', 'enemy')))
    for s, lab in (('C', 'CAND'), ('R', 'REF')):
        print(f"{lab}: champion-killed deaths {tot[('death', s)] / n:.2f} a game, Prism {tot[('pdeath', s)] / n:.3f}, camp deaths "
              f"{tot[('campdeath', s)] / n:.3f}, gems lost dying {tot[('lost', s)] / n:.1f}")
    for RR in (150, 250):
        rs = ratios[RR]
        if not rs: continue
        rs.sort()
        med = rs[len(rs) // 2][0]
        b = defaultdict(lambda: [0, 0.0])
        for r, wn in rs:
            k = '<0.63' if r < 1 / 1.6 else '0.63-0.91' if r < 1 / 1.1 else '0.91-1.1' if r <= 1.1 else '1.1-1.6' if r <= 1.6 else '1.6+'
            b[k][0] += 1; b[k][1] += wn
        mean_log = sum(__import__('math').log(max(1e-6, r)) for r, _ in rs) / len(rs)
        print(f"r{RR} both Prisms alive: {len(rs)} games, CAND/REF Focus median {med:.3f}, geo-mean {__import__('math').exp(mean_log):.3f}; "
              + ', '.join(f"{k} {b[k][0]} ({b[k][1] / b[k][0] * 100:.0f}% CAND wins)" for k in ('<0.63', '0.63-0.91', '0.91-1.1', '1.1-1.6', '1.6+') if b[k][0]))


if __name__ == '__main__':
    main()
