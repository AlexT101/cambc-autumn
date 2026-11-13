"""Brief C mechanism: per team-game, CAND (--by-bot) vs the other team, from an extract.mjs --out DIR.

    python3 stakes.py EXTRACT_DIR --by-bot NAME

Deaths a game by victim type (C&I once a pair), Prism first death (rate, by r400, median round), kills made,
gems taken by kills, gems captured (capture shares), win rate.
"""
import argparse, gzip, json, statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def one(args):
    d, by_bot = args
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = [t['name'] for t in meta['teams']]
    if names[0] == names[1] or by_bot not in names:
        return None
    focus = names.index(by_bot)
    typ = {c['id']: c['name'] for c in meta['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    out = {0: Counter(), 1: Counter()}
    prism_first = {0: None, 1: None}
    for t in (0, 1):
        out[t]['games'] = 1
        out[t]['win'] = 1 if meta['result']['winner'] == t else 0
        out[t]['has_prism'] = 1 if any(typ[i] == 'Prism' and team[i] == t for i in typ) else 0
        out[t]['has_ci'] = 1 if any(typ[i] == 'Cassi' and team[i] == t for i in typ) else 0
    for e in ev:
        k = e['k']
        if k == 'death' and not e.get('linked'):
            v = e['v']; t = team[v]; ty = typ[v]; ty = 'C&I' if ty in ('Cassi', 'Issac') else ty
            out[t]['deaths'] += 1
            out[t]['d_' + ty] += 1
            if e['r'] <= 400: out[t]['deaths_r400'] += 1
            if e.get('by') in typ:
                out[1 - t]['kills'] += 1
                out[1 - t]['kill_gems'] += e.get('gemsTo', 0) or 0
                if typ[e['by']] == 'Prism': out[t]['d_by_prism'] += 1
            out[t]['gems_lost_death'] += e.get('gems', 0) or 0
            if ty == 'Prism' and prism_first[t] is None: prism_first[t] = e['r']
        elif k == 'death' and e.get('linked'):
            out[team[e['v']]]['gems_lost_death'] += e.get('gems', 0) or 0
        elif k == 'capture':
            for cid, gems, gold in e.get('shares', []):
                out[team[cid]]['captured'] += gems
    res = {}
    for t in (0, 1):
        o = dict(out[t])
        o['prism_first'] = prism_first[t]
        res['focus' if t == focus else 'other'] = o
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir'); ap.add_argument('--by-bot', required=True)
    a = ap.parse_args()
    dirs = [p.parent for p in Path(a.dir).rglob('meta.json')]
    tot = {'focus': Counter(), 'other': Counter()}
    firsts = {'focus': [], 'other': []}
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(one, [(str(d), a.by_bot) for d in dirs], chunksize=16):
            if not r: continue
            for side in ('focus', 'other'):
                o = r[side]
                for k, v in o.items():
                    if k != 'prism_first' and v is not None: tot[side][k] += v
                if o['has_prism']:
                    tot[side]['prism_games'] += 1
                    if o['prism_first'] is not None:
                        tot[side]['prism_died'] += 1
                        firsts[side].append(o['prism_first'])
                        if o['prism_first'] <= 400: tot[side]['prism_died_r400'] += 1
    keys = sorted(set(tot['focus']) | set(tot['other']))
    print(f"{'metric':22s} {a.by_bot:>12s} {'other':>12s}")
    for side in ('focus',):
        pass
    for k in keys:
        if k in ('games', 'prism_games', 'prism_died', 'prism_died_r400', 'has_prism', 'has_ci'): continue
        vals = []
        for side in ('focus', 'other'):
            g = max(1, tot[side]['games'])
            denom = max(1, tot[side]['has_ci']) if k == 'd_C&I' else g
            vals.append(tot[side][k] / denom)
        print(f"{k:22s} {vals[0]:12.3f} {vals[1]:12.3f}")
    for side in ('focus', 'other'):
        pg = max(1, tot[side]['prism_games'])
        med = statistics.median(firsts[side]) if firsts[side] else float('nan')
        print(f"{side}: games {tot[side]['games']}, Prism games {tot[side]['prism_games']}, Prism died {tot[side]['prism_died'] / pg:.3f}"
              f" (by r400 {tot[side]['prism_died_r400'] / pg:.3f}), first-death median r{med:.0f}; C&I games {tot[side]['has_ci']}"
              " (d_C&I is per C&I game)")


if __name__ == '__main__':
    main()
