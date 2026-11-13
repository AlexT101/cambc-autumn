"""Targeted follow-ups on scoreboard.jsonl.gz: early-lead predictiveness, Prism-death timing against the break,
Prism bags in the fight component, win rate by lead bucket.

    py research/mac13-argo/scripts/followups.py [--data FILE]
"""

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median

from findings import boot, q, table, load, parts

ROOT = Path('/home/ubuntu/wt/mac13-argo')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(ROOT / 'research/mac13-argo/data/scoreboard.jsonl.gz'))
    a = ap.parse_args()
    rows = load(a.data)
    N = len(rows)
    P = print

    P('## Which early lead predicts the winner (share of games where W led on it, ties excluded; n = games with a non-tie)')
    def feat(r, side, x, k):
        s = r[side]
        if k == 'wealth':
            return s['at'][str(x)]['wealth']
        if k == 'trib':
            return s['at'][str(x)]['trib']
        if k == 'cap':
            return s['at'][str(x)]['cap']
        if k == 'earned':
            return s['at'][str(x)]['earned']
        if k == 'kills':
            return s['at'][str(x)]['kills']
        if k == 'deaths_neg':
            return -s['at'][str(x)]['deaths']
        if k == 'campdmg':
            return s['at'][str(x)]['campdmg']
        if k == 'prism_bag':
            p = s['prism']
            return None if not p or f'gems{x}' not in p else p[f'gems{x}']
        if k == 'prism_foc':
            p = s['prism']
            return None if not p or f'foc{x}' not in p else p[f'foc{x}']
        if k == 'nonprism_cap':
            return None
    rws = []
    for k in ('wealth', 'cap', 'trib', 'earned', 'campdmg', 'kills', 'deaths_neg', 'prism_bag', 'prism_foc'):
        row = [k]
        for x in (100, 200, 300, 400):
            v = []
            for r in rows:
                if r['n'] < x:
                    continue
                fw, fl = feat(r, 'w', x, k), feat(r, 'l', x, k)
                if fw is None or fl is None or fw == fl:
                    continue
                v.append(1.0 if fw > fl else 0.0)
            lo, hi = boot(v, B=400)
            row.append(f'{100 * mean(v):.0f}% [{100 * lo:.0f}, {100 * hi:.0f}] n={len(v)}' if v else '-')
        rws.append(row)
    P(table(['lead in', 'r100', 'r200', 'r300', 'r400'], rws))
    P('')

    P('## Win rate by collected-gem lead (from either side\'s view)')
    for x in (200, 300, 400, 600):
        b = Counter()
        tot = Counter()
        for r in rows:
            if r['n'] < x:
                continue
            d = r['w']['at'][str(x)]['wealth'] - r['l']['at'][str(x)]['wealth']
            for dd, won in ((d, 1), (-d, 0)):
                k = 'lead<=-100' if dd <= -100 else '-99..-25' if dd <= -25 else '-24..24' if dd < 25 else '25..99' if dd < 100 else '100..199' if dd < 200 else '200+'
                tot[k] += 1
                b[k] += won
        order = ['lead<=-100', '-99..-25', '-24..24', '25..99', '100..199', '200+']
        P(f'r{x}: ' + ', '.join(f'{k}: {100 * b[k] / tot[k]:.0f}% (n={tot[k]})' for k in order if tot[k]))
    P('')

    P('## Prism deaths against the break')
    pr = [r for r in rows if 'Prism' in r['picks']]
    rel = []
    for r in pr:
        b = r['brk']['b0']
        ld = [d for d in r['l']['deaths'] if d['type'] == 'Prism']
        rel.append(ld[0]['r'] - b if ld else None)
    died = [x for x in rel if x is not None]
    P(f'Prism games {len(pr)}; L Prism died {100 * len(died) / len(pr):.0f}%. First L Prism death minus b0: median {median(died):+.0f}, '
      f'IQR {q(died, .25):+.0f}..{q(died, .75):+.0f}; before b0 {100 * mean(x < 0 for x in died):.0f}%, within 0..10 after {100 * mean(0 <= x <= 10 for x in died):.0f}%, '
      f'11..100 after {100 * mean(10 < x <= 100 for x in died):.0f}%, 100+ after {100 * mean(x > 100 for x in died):.0f}%')
    # Prism bags in the fight component
    pb = []
    for r in pr:
        lp = sum(d['bag'] for d in r['l']['deaths'] if d['type'] == 'Prism' and d['killer'] != 'camp')
        wp = sum(d['bag'] for d in r['w']['deaths'] if d['type'] == 'Prism' and d['killer'] != 'camp')
        lo = sum(d['bag'] for d in r['l']['deaths'] if d['type'] != 'Prism' and d['killer'] != 'camp')
        wo = sum(d['bag'] for d in r['w']['deaths'] if d['type'] != 'Prism' and d['killer'] != 'camp')
        pb.append((lp, wp, lo, wo))
    P(f'Bags lost to champions per game, whole game: L Prism {mean(x[0] for x in pb):.0f}, W Prism {mean(x[1] for x in pb):.0f}, '
      f'L others {mean(x[2] for x in pb):.0f}, W others {mean(x[3] for x in pb):.0f}. Share of the kill-gem gap from Prism bags: '
      f'{(mean(x[0] for x in pb) - mean(x[1] for x in pb)) / (mean(x[0] + x[2] for x in pb) - mean(x[1] + x[3] for x in pb)):.2f}')
    # Prism bag at r300/400 as share of team wealth
    for x in (300, 400):
        sh = [(r['w']['prism'][f'gems{x}'] / max(1, r['w']['at'][str(x)]['wealth']), r['l']['prism'][f'gems{x}'] / max(1, r['l']['at'][str(x)]['wealth']))
              for r in pr if r['w']['prism'] and f'gems{x}' in r['w']['prism']]
        P(f'r{x}: Prism bag / team collected gems W {mean(s[0] for s in sh):.2f}, L {mean(s[1] for s in sh):.2f}')
    P('')

    P('## Games where the first kill came late')
    for cut in (300, 500):
        sub = [r for r in rows if (r['first_kill'] or 99999) > cut and r['n'] > cut]
        d = [r['w']['at'][str(cut)]['wealth'] - r['l']['at'][str(cut)]['wealth'] for r in sub]
        P(f'first kill after r{cut}: n={len(sub)} ({100 * len(sub) / N:.0f}%); W ahead at r{cut} {100 * mean(x > 0 for x in d):.0f}%, lead median {median(d):+.0f}, '
          f'IQR {q(d, .25):+.0f}..{q(d, .75):+.0f}')
    P('')

    P('## Bank wins and r2000 games')
    bank = [r for r in rows if r['brk']['b0'] >= r['n']]
    P(f'bank wins {len(bank)}: L carried at end mean {mean(r["l"]["at"][str(r["n"])]["carried"] for r in bank):.0f} (Prism share '
      f'{mean((r["l"]["prism"] or {}).get("gems600", 0) for r in bank if r["l"]["prism"]):.0f} at r600), end round median {median(r["n"] for r in bank):.0f}')
    r2 = [r for r in rows if r['end'] == 'r2000']
    if r2:
        wpc = [sum(1 for x in (r['w']['prism'] or {}).get('trib', []) if x[3].startswith('cancel')) for r in r2]
        P(f'r2000 games {len(r2)}: W Prism tribute cancels per game {mean(wpc):.1f}; team A wins {100 * mean(r["W"] == 0 for r in r2):.0f}%; '
          f'presets {Counter(r["preset"] for r in r2).most_common(6)}')
    # Prism tributes: cancellations by cause per game, W only, excluding r2000 games
    nr2 = [r for r in pr if r['end'] != 'r2000' and r['w']['prism']]
    c = Counter()
    for r in nr2:
        for x in r['w']['prism']['trib']:
            c[x[3]] += 1
    P(f'W Prism tribute outcomes per game, games ending on 1000 gems (n={len(nr2)}): ' + ', '.join(f'{k} {v / len(nr2):.2f}' for k, v in c.most_common()))
    sizes = [x[1] for r in nr2 for x in r['w']['prism']['trib'] if x[3] == 'done']
    P(f'  completed sizes: median {median(sizes):.0f}, IQR {q(sizes, .25):.0f}-{q(sizes, .75):.0f}; final tribute that ended the game was the Prism\'s in '
      f'{100 * mean(bool(r["w"]["prism"]["trib"]) and r["w"]["prism"]["trib"][-1][3] == "done" and r["w"]["prism"]["trib"][-1][5] >= r["n"] - 1 for r in nr2):.0f}%')
    P('')

    P('## Side asymmetry by end type and symmetry')
    for key in ('end', 'sym'):
        g = {}
        for r in rows:
            g.setdefault(r[key], []).append(1.0 if r['W'] == 0 else 0.0)
        P(f'{key}: ' + ', '.join(f'{k} {100 * mean(v):.1f}% [{100 * boot(v, B=400)[0]:.1f}, {100 * boot(v, B=400)[1]:.1f}] n={len(v)}' for k, v in g.items()))
    P('')

    P('## Cleared clusters left unheld: rounds in state "cleared, unclaimed" per capture, by class')
    agg = {}
    for r in rows:
        for c_, s in r['gstats'].items():
            a_ = agg.setdefault(c_, Counter())
            a_.update(s)
    for c_, s in agg.items():
        caps = s.get('caps0', 0) + s.get('caps1', 0)
        if caps:
            P(f'{c_}: idle-cleared rounds per capture {s.get("idle2", 0) / caps:.1f}; untouched-up rounds per capture {s.get("idle1", 0) / caps:.0f}')


if __name__ == '__main__':
    main()
