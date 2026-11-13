"""Findings A-G from scoreboard.jsonl.gz (scoreboard.py's rows). Prints Markdown tables to stdout.

    py research/mac13-argo/scripts/findings.py [--data FILE] > out.md
"""

import argparse
import gzip
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

ROOT = Path('/home/ubuntu/wt/mac13-argo')
GCLS = ['wolf', 'wolf_cl', 'elk', 'golem', 'gem_cl', 'gold_cl', 'mixed_cl', 'monolith']
ZONES = ['own', 'mid', 'enemy']
LAB = ['walk', 'walk_bag', 'camp', 'hold', 'tribute', 'recall', 'fight', 'wait_camp', 'wait_altar', 'spawn', 'idle', 'lost', 'dead']


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo = math.floor(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def boot(xs, f=mean, B=500, seed=1):
    if len(xs) < 5:
        return (None, None)
    rnd = random.Random(seed)
    n = len(xs)
    st = sorted(f([xs[rnd.randrange(n)] for _ in range(n)]) for _ in range(B))
    return st[int(0.025 * B)], st[int(0.975 * B) - 1]


def f1(x, d=1):
    return '-' if x is None else f'{x:.{d}f}'


def ci(xs, d=1, f=mean):
    if not xs:
        return '-'
    lo, hi = boot(xs, f)
    return f'{f1(f(xs), d)} [{f1(lo, d)}, {f1(hi, d)}]'


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    for r in rows:
        out.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    return '\n'.join(out)


def load(p):
    rows = [json.loads(l) for l in gzip.open(p, 'rt')]
    idx = json.loads((ROOT / 'maps/suites/mac13/ana/index.json').read_text())['maps']
    meta = {m['file'][:-len('.map26a')]: m for m in idx}
    for r in rows:
        nm = r['map']
        kind, rest = nm.split('-', 1)
        preset = rest.rsplit('-', 1)[0]
        r['kind'] = 'mutation' if kind == 'mut' else 'generated'
        r['preset'] = preset if kind == 'gen' else 'mut'
        r['mut'] = preset if kind == 'mut' else None
        a = r['area']
        r['sizec'] = 'S(<1600)' if a < 1600 else 'M(1600-3000)' if a < 3000 else 'L(3000+)'
        r['idx'] = meta.get(nm)
    return rows


def at(side, r, key):
    return side['at'][str(r)][key]


def parts(row, a, b):
    """W minus L component change over (a, b] from the 'at' marks: farm by class / zone, fight, camp."""
    w, l = row['w']['at'], row['l']['at']
    def d(side, k):
        return side[str(b)][k] - (side[str(a)][k] if a > 0 else 0)
    o = {'farm': d(w, 'cap') - d(l, 'cap'),
         'fight': (d(w, 'kg') - d(w, 'lostc')) - (d(l, 'kg') - d(l, 'lostc')),
         'camp': d(l, 'lostm') - d(w, 'lostm')}
    for c in GCLS:
        o['cap_' + c] = d(w, 'cap_' + c) - d(l, 'cap_' + c)
    for z in ZONES:
        o['cap_' + z] = d(w, 'cap_' + z) - d(l, 'cap_' + z)
    o['wealth'] = d(w, 'wealth') - d(l, 'wealth')
    o['bank'] = w[str(b)]['carried'] - l[str(b)]['carried']
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(ROOT / 'research/mac13-argo/data/scoreboard.jsonl.gz'))
    a = ap.parse_args()
    rows = load(a.data)
    N = len(rows)
    P = print
    P(f'# Scoreboard findings ({N} distinct games)\n')

    # ---------------------------------------------------------------- outcome
    P('## Outcome')
    ends = Counter(r['end'] for r in rows)
    P(f'end types: {dict(ends)}; identity failures (wealth != cap+kill-lost): {sum(1 for r in rows if r["ident_bad"])} games; '
      f'mirror drafts: {sum(r["mirror_draft"] for r in rows)}/{N}')
    ns = [r['n'] for r in rows]
    P(f'end round median {median(ns)} (IQR {q(ns, .25):.0f}-{q(ns, .75):.0f}); W tributed median {median(r["gems"][r["W"]] for r in rows)}, '
      f'L tributed median {median(r["gems"][1 - r["W"]] for r in rows)} (IQR {q([r["gems"][1 - r["W"]] for r in rows], .25):.0f}-{q([r["gems"][1 - r["W"]] for r in rows], .75):.0f})')
    P('')
    # time series
    P('### Collected (tributed + carried) / tributed / capture / kill gems at round X (games still running at X; final value otherwise)')
    cps = [100, 200, 300, 400, 500, 600, 800, 1000]
    tr = []
    for x in cps:
        live = [r for r in rows if r['n'] >= x]
        def m(side, k):
            return mean(r[side]['at'][str(x)][k] for r in rows)
        tr.append([x, len(live), f'{m("w", "wealth"):.0f} / {m("l", "wealth"):.0f}', f'{m("w", "trib"):.0f} / {m("l", "trib"):.0f}',
                   f'{m("w", "cap"):.0f} / {m("l", "cap"):.0f}', f'{m("w", "kg"):.0f} / {m("l", "kg"):.0f}',
                   f'{m("w", "lostm"):.0f} / {m("l", "lostm"):.0f}',
                   f'{mean(r["w"]["at"][str(x)]["wealth"] - r["l"]["at"][str(x)]["wealth"] for r in live):+.0f}' if live else '-',
                   f'{100 * mean(r["w"]["at"][str(x)]["wealth"] > r["l"]["at"][str(x)]["wealth"] for r in live):.0f}%' if live else '-'])
    P(table(['round', 'live', 'collected W/L', 'tributed W/L', 'capture W/L', 'kill gems W/L', 'lost to camps W/L', 'W-L collected (live)', 'W ahead (live)'], tr))
    P('')

    # ---------------------------------------------------------------- A. the break
    P('## A. The break')
    b0 = [r['brk']['b0'] for r in rows]
    b0s = [r['brk']['b0s'] for r in rows]
    b100 = [r['brk']['b100'] for r in rows]
    bank = [r for r in rows if r['brk']['b0'] >= r['n']]
    P(f'b0 = last round W\'s collected lead was <= 0 (lead > 0 for good after it). median {median(b0)}, IQR {q(b0, .25):.0f}-{q(b0, .75):.0f}, '
      f'p10 {q(b0, .1):.0f}, p90 {q(b0, .9):.0f}. As a share of game length: median {median(r["brk"]["b0"] / r["n"] for r in rows):.2f}.')
    P(f'strict (last round lead < 0): median {median(b0s)}; W never behind (strict) in {100 * mean(x == 0 for x in b0s):.1f}%.')
    P(f'b100 = last round lead <= 100: median {median(b100)}, IQR {q(b100, .25):.0f}-{q(b100, .75):.0f}.')
    P(f'"bank" wins (W ended with collected <= L: won by tributing, not by wealth): {len(bank)} ({100 * len(bank) / N:.1f}%).')
    P(f'L\'s largest lead: median {median(r["brk"]["l_lead_max"] for r in rows)} gems, at median r{median(r["brk"]["l_lead_max_r"] for r in rows)}; '
      f'L led by 50+ at some point in {100 * mean(r["brk"]["l_lead_max"] >= 50 for r in rows):.0f}%, 100+ in {100 * mean(r["brk"]["l_lead_max"] >= 100 for r in rows):.0f}%.')
    hist = Counter(min(x // 100, 10) for x in b0)
    P('b0 histogram (per 100 rounds): ' + ', '.join(f'{k * 100}-{k * 100 + 99 if k < 10 else "+"}: {hist[k]}' for k in sorted(hist)))
    P('')

    def brk_by(key, minn=20):
        g = defaultdict(list)
        for r in rows:
            g[r[key]].append(r)
        out = []
        for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])):
            if len(v) < minn:
                continue
            bb = [r['brk']['b0'] for r in v]
            out.append([k, len(v), f'{median(bb):.0f}', f'{q(bb, .25):.0f}-{q(bb, .75):.0f}', f'{median(r["brk"]["b100"] for r in v):.0f}',
                        f'{median(r["n"] for r in v):.0f}', f'{median(r["brk"]["b0"] / r["n"] for r in v):.2f}'])
        return out
    for key in ('sizec', 'npick', 'kind'):
        P(table([key, 'n', 'b0 median', 'b0 IQR', 'b100 median', 'end median', 'b0/end'], brk_by(key)))
        P('')

    # ---------------------------------------------------------------- B. components
    P('## B. What builds the margin (W minus L, gems; mean [95% bootstrap CI], median)')
    P('farm = capture gems; fight = (kill gems taken - own bags lost to champions), W minus L (= 2x the kill-gem gap); '
      'camp = L\'s bags lost to camps minus W\'s. They sum to the change in the collected-gem lead. bank = W minus L carried (untributed) at the window end.')
    wins = {
        'pre (1..b0)': lambda r: (0, r['brk']['b0']),
        'surge (b0..b100)': lambda r: (r['brk']['b0'], r['brk']['b100']),
        'first 100 after b0': lambda r: (r['brk']['b0'], min(r['n'], r['brk']['b0'] + 100)),
        'post (b100..end)': lambda r: (r['brk']['b100'], r['n']),
        'r1-300': lambda r: (0, 300 if r['n'] >= 300 else r['n']),
        'r1-600': lambda r: (0, 600 if r['n'] >= 600 else r['n']),
        'whole game': lambda r: (0, r['n']),
    }
    keys = ['wealth', 'farm', 'fight', 'camp', 'bank'] + ['cap_' + z for z in ZONES] + ['cap_' + c for c in GCLS]
    res = {}
    for nm, fn in wins.items():
        ps = []
        for r in rows:
            aa, bb = fn(r)
            if nm == 'surge (b0..b100)' and bb <= aa:
                continue
            if str(aa) not in r['w']['at'] and aa != 0:
                continue
            ps.append(parts(r, aa, bb))
        res[nm] = ps
    rws = []
    for k in keys:
        rw = [k]
        for nm in wins:
            xs = [p[k] for p in res[nm]]
            rw.append(f'{mean(xs):+.1f}' if k not in ('farm', 'fight', 'wealth') else ci(xs) + f'; med {median(xs):+.0f}')
        rws.append(rw)
    rws.append(['n'] + [len(res[nm]) for nm in wins])
    P(table(['component'] + list(wins), rws))
    P('')
    # dominant component per game in the surge and first 100 after
    for nm in ('surge (b0..b100)', 'first 100 after b0', 'whole game'):
        dom = Counter(max(('farm', 'fight', 'camp'), key=lambda k: p[k]) for p in res[nm])
        P(f'{nm}: largest W component per game: ' + ', '.join(f'{k} {100 * v / len(res[nm]):.0f}%' for k, v in dom.most_common()))
    # surge: farm share of the gain
    xs = [p for p in res['first 100 after b0']]
    P(f'first 100 rounds after b0: lead gain mean {mean(p["wealth"] for p in xs):+.1f}; farm {mean(p["farm"] for p in xs):+.1f}, '
      f'fight {mean(p["fight"] for p in xs):+.1f}, camp {mean(p["camp"] for p in xs):+.1f}; '
      f'games where |fight| > |farm|: {100 * mean(abs(p["fight"]) > abs(p["farm"]) for p in xs):.0f}%')
    P('')
    # kill swing at the break: did L lose a big bag within +-10 rounds of b0?
    trig = []
    for r in rows:
        b = r['brk']['b0']
        big = max((d['bag'] for d in r['l']['deaths'] if abs(d['r'] - b) <= 10), default=0)
        trig.append(big)
    P(f'L death within 10 rounds of b0: {100 * mean(any(abs(d["r"] - r["brk"]["b0"]) <= 10 for d in r["l"]["deaths"]) for r in rows):.0f}% of games; '
      f'with a bag >= 50: {100 * mean(x >= 50 for x in trig):.0f}%, >= 100: {100 * mean(x >= 100 for x in trig):.0f}%')
    pd = []
    for r in rows:
        b = r['brk']['b0']
        pdl = [d for d in r['l']['deaths'] if d['type'] == 'Prism' and abs(d['r'] - b) <= 10]
        pd.append(bool(pdl))
    P(f'L Prism died within 10 rounds of b0: {100 * mean(pd):.0f}% (Prism drafted in {100 * mean("Prism" in r["picks"] for r in rows):.0f}% of games)')
    P('')

    # ---------------------------------------------------------------- C. subsets
    P('## C. Subsets that isolate farming from the Prism duel')

    def prism_dead_before(r, side, rr):
        return any(d['type'] == 'Prism' and d['r'] <= rr for d in r[side]['deaths'])
    hasp = [r for r in rows if 'Prism' in r['picks']]
    sub = {
        'all': rows,
        'Prism drafted, no Prism death before b0': [r for r in hasp if not prism_dead_before(r, 'w', r['brk']['b0']) and not prism_dead_before(r, 'l', r['brk']['b0'])],
        'Prism drafted, a Prism died before b0': [r for r in hasp if prism_dead_before(r, 'w', r['brk']['b0']) or prism_dead_before(r, 'l', r['brk']['b0'])],
        'no Prism drafted': [r for r in rows if 'Prism' not in r['picks']],
        'no kill before r300': [r for r in rows if r['first_kill'] is None or r['first_kill'] > 300],
    }
    rws = []
    for nm, rs in sub.items():
        if not rs:
            continue
        pre = [parts(r, 0, r['brk']['b0']) for r in rs]
        f100 = [parts(r, r['brk']['b0'], min(r['n'], r['brk']['b0'] + 100)) for r in rs]
        whole = [parts(r, 0, r['n']) for r in rs]
        rws.append([nm, len(rs), f'{median(r["brk"]["b0"] for r in rs):.0f}',
                    f'{mean(p["farm"] for p in pre):+.0f} / {mean(p["fight"] for p in pre):+.0f} / {mean(p["camp"] for p in pre):+.0f}',
                    f'{mean(p["farm"] for p in f100):+.0f} / {mean(p["fight"] for p in f100):+.0f} / {mean(p["camp"] for p in f100):+.0f}',
                    f'{mean(p["farm"] for p in whole):+.0f} / {mean(p["fight"] for p in whole):+.0f} / {mean(p["camp"] for p in whole):+.0f} / {mean(p["bank"] for p in whole):+.0f}'])
    P(table(['subset', 'n', 'b0 med', 'pre: farm/fight/camp', 'b0+100: farm/fight/camp', 'whole: farm/fight/camp/bank'], rws))
    P('')

    # ---------------------------------------------------------------- D. standardised W-L differences
    P('## D. W vs L behaviour, standardised (paired: mean W-L / sd of W-L; P(W>L) excludes ties)')

    def feats():
        def one(s, sa):
            tot = sum(s['L_' + k] for k in LAB if 'L_' + k in s) or 1
            alive = s['alive'] or 1
            o = {f'lab_{k}': s.get('L_' + k, 0) / tot for k in LAB}
            o['lab_walk_all'] = o['lab_walk'] + o['lab_walk_bag']
            o['lab_work'] = o['lab_camp'] + o['lab_hold'] + o['lab_tribute']
            o['campdmg_per_alive'] = s['campdmg'] / alive
            o['cap_per_100alive'] = 100 * s['cap'] / alive
            for z in ZONES:
                o[f'idle_{z}'] = s[f'idle_{z}'] / s[f'up_{z}'] if s[f'up_{z}'] else None
                o[f'idlev_{z}_per100'] = 100 * s[f'idlev_{z}'] / s['rounds']
            o['raids'] = s['raid_n']
            o['own_lost'] = s['lost_own_n']
            o['steals'] = s['steal_n']
            o['nn'] = s['nn'] / s['nn_n'] if s['nn_n'] else None
            o['clus'] = s['clus'] / s['clus_n'] if s['clus_n'] else None
            o['kills'] = s['kills']
            o['deaths'] = s['deaths']
            o['camp_deaths'] = s['cdeaths']
            if sa is not None:
                o['gold_earned'] = sa['earned']
                o['gold_spent'] = sa['spent']
                o['gold_bank'] = sa['bank']
            return o
        return one
    def dz_table(name, getter):
        acc = defaultdict(list)
        cnt = 0
        for r in rows:
            g = getter(r)
            if g is None:
                continue
            sw, sl, aw, al = g
            fw = feats()
            ow, ol = fw(sw, aw), fw(sl, al)
            cnt += 1
            for k in ow:
                if ow[k] is not None and ol[k] is not None:
                    acc[k].append((ow[k], ol[k]))
        out = []
        for k, v in acc.items():
            ds = [x - y for x, y in v]
            sd = pstdev(ds)
            dz = mean(ds) / sd if sd > 0 else 0
            nt = [d for d in ds if d != 0]
            gt = mean(d > 0 for d in nt) if nt else None
            out.append((abs(dz), [k, f'{mean(x for x, _ in v):.3g}', f'{mean(y for _, y in v):.3g}', f'{mean(ds):+.3g}', f'{dz:+.2f}',
                                  f1(100 * gt if gt is not None else None, 0) + '%', len(v)]))
        out.sort(key=lambda x: -x[0])
        P(f'### {name} ({cnt} games)')
        P(table(['feature', 'W', 'L', 'W-L', 'dz', 'P(W>L)', 'n'], [x[1] for x in out]))
        P('')
    dz_table('Rounds 1-150 (before most breaks)', lambda r: (r['w']['win']['p1'], r['l']['win']['p1'], r['w']['at']['150'], r['l']['at']['150']))
    dz_table('Pre-break window 1..b0, games with b0 >= 100',
             lambda r: (r['w']['win']['pre'], r['l']['win']['pre'], r['w']['at'][str(r['brk']['b0'])], r['l']['at'][str(r['brk']['b0'])])
             if r['brk']['b0'] >= 100 and r['brk']['b0'] < r['n'] else None)
    dz_table('First 100 rounds after b0',
             lambda r: (r['w']['win']['brk100'], r['l']['win']['brk100'], None, None) if r['w']['win']['brk100'] and r['brk']['b0'] < r['n'] - 20 else None)

    noP = [r for r in rows if 'Prism' in r['picks'] and not any(d['type'] == 'Prism' and d['r'] <= r['brk']['b0'] for side in ('w', 'l') for d in r[side]['deaths'])]
    nok = [r for r in rows if (r['first_kill'] is None or r['first_kill'] > 300) and r['n'] > 300]
    P('## C (detail). Subsets')
    for nm, rs in (('no Prism death before b0', noP), ('no kill before r300', nok)):
        live = [r for r in rs if r['n'] > 300]
        d3 = [r['w']['at']['300']['wealth'] - r['l']['at']['300']['wealth'] for r in live]
        P(f'{nm}: n={len(rs)}; W ahead at r300 in {100 * mean(x > 0 for x in d3):.0f}% (lead mean {mean(d3):+.0f}, median {median(d3):+.0f}); '
          f'b0 median {median(r["brk"]["b0"] for r in rs):.0f}; L\'s Prism died (ever) in '
          f'{100 * mean(any(d["type"] == "Prism" for d in r["l"]["deaths"]) for r in rs):.0f}% / W\'s Prism ever died {100 * mean(any(d["type"] == "Prism" for d in r["w"]["deaths"]) for r in rs):.0f}%')
        p3 = [parts(r, 0, 300) for r in live]
        P('  r1-300 W-L: ' + ', '.join(f'{k} {mean(p[k] for p in p3):+.1f}' for k in ['wealth', 'farm', 'fight', 'camp'] + ['cap_' + z for z in ZONES] + ['cap_' + c for c in GCLS]))
    rows_bak = rows
    rows = nok
    dz_table('No kill before r300: rounds 1-300', lambda r: (r['w']['win']['r1_300'], r['l']['win']['r1_300'], r['w']['at']['300'], r['l']['at']['300']))
    rows = noP
    dz_table('No Prism death before b0: pre-break window, b0 >= 100',
             lambda r: (r['w']['win']['pre'], r['l']['win']['pre'], r['w']['at'][str(r['brk']['b0'])], r['l']['at'][str(r['brk']['b0'])])
             if r['brk']['b0'] >= 100 and r['brk']['b0'] < r['n'] else None)
    rows = rows_bak

    # ---------------------------------------------------------------- labour per phase
    P('## Labour by phase (share of champion-rounds, W / L)')
    rws = []
    for ph in ('p1', 'p2', 'p3'):
        live = [r for r in rows if r['w']['win'][ph] and r['w']['win'][ph]['rounds'] >= 50]
        def sh(side, k):
            return 100 * mean(r[side]['win'][ph]['L_' + k] / sum(r[side]['win'][ph]['L_' + c] for c in LAB) for r in live)
        rws.append([ph + f' (n={len(live)})'] + [f'{sh("w", k):.1f} / {sh("l", k):.1f}' for k in LAB]
                   + [f'{mean(r["w"]["win"][ph]["campdmg"] / max(1, r["w"]["win"][ph]["alive"]) for r in live):.1f} / {mean(r["l"]["win"][ph]["campdmg"] / max(1, r["l"]["win"][ph]["alive"]) for r in live):.1f}'])
    P(table(['phase'] + LAB + ['camp dmg / alive rd'], rws))
    P('')

    # ---------------------------------------------------------------- supply
    P('## Supply left up and unworked (share of up group-rounds with no camp hit and no capture hold, by zone relative to the team)')
    rws = []
    for ph in ('p1', 'p2', 'p3', 'pre', 'game'):
        live = [r for r in rows if r['w']['win'][ph] and r['w']['win'][ph]['rounds'] >= 50]
        row_ = [ph + f' (n={len(live)})']
        for z in ZONES:
            def s_(side):
                num = sum(r[side]['win'][ph][f'idle_{z}'] for r in live)
                den = sum(r[side]['win'][ph][f'up_{z}'] for r in live)
                return 100 * num / den if den else 0
            row_.append(f'{s_("w"):.0f} / {s_("l"):.0f}')
        row_.append(f'{mean(r["w"]["win"][ph]["raid_n"] for r in live):.1f} / {mean(r["l"]["win"][ph]["raid_n"] for r in live):.1f}')
        row_.append(f'{mean(r["w"]["win"][ph]["raid_g"] for r in live):.0f} / {mean(r["l"]["win"][ph]["raid_g"] for r in live):.0f}')
        row_.append(f'{mean(r["w"]["win"][ph]["steal_n"] for r in live):.1f} / {mean(r["l"]["win"][ph]["steal_n"] for r in live):.1f}')
        rws.append(row_)
    P(table(['window', 'own idle W/L', 'mid idle W/L', 'enemy idle W/L', 'raids (enemy-half captures) W/L', 'raid gems W/L', 'steals (captured a group the other team cleared) W/L'], rws))
    P('')
    P('### Group classes: supply and use (whole game, both teams)')
    agg = defaultdict(Counter)
    for r in rows:
        for c, s in r['gstats'].items():
            agg[c].update(s)
    ncls = Counter()
    capg = defaultdict(lambda: [0, 0])
    for r in rows:
        for c in GCLS:
            if r['gstats'][c].get('groups'):
                ncls[c] += 1
            capg[c][0] += r['w']['at'][str(r['n'])]['cap_' + c]
            capg[c][1] += r['l']['at'][str(r['n'])]['cap_' + c]
    rws = []
    for c in GCLS:
        s = agg[c]
        if not s.get('rounds'):
            continue
        rws.append([c, ncls[c], s['groups'], f'{100 * s["up"] / s["rounds"]:.0f}%', f'{100 * s.get("idle1", 0) / s["up"]:.0f}%',
                    f'{100 * s.get("idle2", 0) / s["up"]:.0f}%', f'{1000 * (s["caps0"] + s["caps1"]) / s["rounds"]:.1f}',
                    f'{capg[c][0] / N:.0f} / {capg[c][1] / N:.0f}', f'{100 * (capg[c][0] + capg[c][1]) / sum(sum(v) for v in capg.values()):.0f}%'])
    P(table(['class', 'games with it', 'groups', 'up share', 'up: untouched (monsters alive)', 'up: cleared, unheld', 'captures per 1000 group-rounds', 'capture gems/game W / L', 'share of all capture gems'], rws))
    P('')

    # ---------------------------------------------------------------- cohesion
    P('## Cohesion by phase (W / L)')
    rws = []
    for ph in ('p1', 'p2', 'p3', 'pre'):
        live = [r for r in rows if r['w']['win'][ph] and r['w']['win'][ph]['rounds'] >= 50 and r['w']['win'][ph]['nn_n'] and r['l']['win'][ph]['nn_n']]
        nn = [(r['w']['win'][ph]['nn'] / r['w']['win'][ph]['nn_n'], r['l']['win'][ph]['nn'] / r['l']['win'][ph]['nn_n']) for r in live]
        cl = [(r['w']['win'][ph]['clus'] / max(1, r['w']['win'][ph]['clus_n']), r['l']['win'][ph]['clus'] / max(1, r['l']['win'][ph]['clus_n'])) for r in live]
        rws.append([ph, len(live), f'{mean(x for x, _ in nn):.2f} / {mean(y for _, y in nn):.2f}', ci([x - y for x, y in nn], 2),
                    f'{100 * mean(x for x, _ in cl):.1f} / {100 * mean(y for _, y in cl):.1f}', ci([100 * (x - y) for x, y in cl], 2)])
    P(table(['window', 'n', 'nearest ally (field bodies) W / L', 'W-L', 'largest cluster share % W / L', 'W-L (pt)'], rws))
    P('')

    # ---------------------------------------------------------------- gold and items
    P('## Gold (team totals, W / L, games running at X)')
    rws = []
    for x in (150, 300, 600):
        live = [r for r in rows if r['n'] >= x]
        rws.append([f'r{x}', len(live)] + [f'{mean(r["w"]["at"][str(x)][k] for r in live):.0f} / {mean(r["l"]["at"][str(x)][k] for r in live):.0f}' for k in ('earned', 'spent', 'bank', 'cap_gold')])
    rws.append(['end', N] + [f'{mean(r["w"]["at"][str(r["n"])][k] for r in rows):.0f} / {mean(r["l"]["at"][str(r["n"])][k] for r in rows):.0f}' for k in ('earned', 'spent', 'bank', 'cap_gold')])
    P(table(['round', 'n', 'earned', 'spent', 'unspent', 'capture gold'], rws))
    P('')
    P('### Shard-equivalents (emblem = 5, Greed = 25) and emblems per champion type, W / L')
    rws = []
    for x in ('300', '600'):
        acc = defaultdict(lambda: [[], [], [], []])
        for r in rows:
            if x not in r['w']['items']:
                continue
            for nm, s in r['w']['items'][x].items():
                acc[nm][0].append(s['eq'])
                acc[nm][2].append(s['em'])
            for nm, s in r['l']['items'][x].items():
                acc[nm][1].append(s['eq'])
                acc[nm][3].append(s['em'])
        for nm, v in sorted(acc.items(), key=lambda kv: -len(kv[1][0])):
            if len(v[0]) < 30:
                continue
            rws.append([f'r{x}', nm, len(v[0]), f'{mean(v[0]):.1f} / {mean(v[1]):.1f}', f'{mean(v[2]):.2f} / {mean(v[3]):.2f}'])
    P(table(['round', 'champion', 'n', 'shard-eq W / L', 'emblems W / L'], rws))
    P('')

    # ---------------------------------------------------------------- deaths
    P('## Deaths per game by victim type (W / L)')
    acc = defaultdict(lambda: {'w': [], 'l': [], 'nw': 0, 'nl': 0})
    for r in rows:
        tps = set(r['w']['types'])
        for nm in tps:
            acc[nm]['nw'] += 1
        for side in ('w', 'l'):
            for d in r[side]['deaths']:
                acc[d['type']][side].append(d)
    rws = []
    for nm, v in sorted(acc.items(), key=lambda kv: -kv[1]['nw']):
        if v['nw'] < 30:
            continue
        def st(ds, nn):
            if not ds:
                return '0'
            return (f'{len(ds) / nn:.2f} / r{median(d["r"] for d in ds):.0f} / bag {mean(d["bag"] for d in ds):.0f} / camp {100 * mean(d["killer"] == "camp" for d in ds):.0f}% / '
                    f'outn {100 * mean(d["outn"] for d in ds if d["killer"] != "camp") if any(d["killer"] != "camp" for d in ds) else 0:.0f}% / '
                    f'byPrism {100 * mean(d["killer"] == "Prism" for d in ds):.0f}%')
        rws.append([nm, v['nw'], st(v['w'], v['nw']), st(v['l'], v['nw'])])
    P(table(['victim', 'games', 'W: deaths/game / median round / mean bag / by camp / outnumbered (champ kills) / by Prism', 'L: same'], rws))
    P('')
    # bag lost by time
    P('Gems lost at own deaths per game, by phase (W / L): ' + ', '.join(
        f'{nm} {mean(sum(d["bag"] for d in r["w"]["deaths"] if lo <= d["r"] <= hi) for r in rows):.0f} / {mean(sum(d["bag"] for d in r["l"]["deaths"] if lo <= d["r"] <= hi) for r in rows):.0f}'
        for nm, lo, hi in (('r1-150', 1, 150), ('151-400', 151, 400), ('401-800', 401, 800), ('801+', 801, 99999))))
    P('')

    # ---------------------------------------------------------------- Prism
    P('## Prism (games with Prism drafted)')
    pr = [r for r in rows if r['w']['prism'] and r['l']['prism']]
    rws = []
    for x in (200, 300, 400, 600):
        live = [r for r in pr if f'foc{x}' in r['w']['prism']]
        rws.append([f'r{x}', len(live), f'{mean(r["w"]["prism"][f"foc{x}"] for r in live):.0f} / {mean(r["l"]["prism"][f"foc{x}"] for r in live):.0f}',
                    f'{mean(r["w"]["prism"][f"gems{x}"] for r in live):.0f} / {mean(r["l"]["prism"][f"gems{x}"] for r in live):.0f}',
                    f'{median(r["w"]["prism"][f"gems{x}"] for r in live):.0f} / {median(r["l"]["prism"][f"gems{x}"] for r in live):.0f}'])
    P(table(['round', 'n', 'Focus mean W / L', 'carried gems mean W / L', 'carried median W / L'], rws))
    fdw = [r['w']['prism']['first_death'] for r in pr]
    fdl = [r['l']['prism']['first_death'] for r in pr]
    P(f'\nn={len(pr)}. Prism never died: W {100 * mean(x is None for x in fdw):.0f}%, L {100 * mean(x is None for x in fdl):.0f}%. '
      f'First death round median (when it died): W {median(x for x in fdw if x) if any(fdw) else "-"}, L {median(x for x in fdl if x) if any(fdl) else "-"}. '
      f'First Prism death was L\'s in {100 * mean((l or 99999) < (w or 99999) for w, l in zip(fdw, fdl) if (w or l)):.0f}% of games where one died.')
    for side in ('w', 'l'):
        tt = [x for r in pr for x in r[side]['prism']['trib']]
        done = [x for x in tt if x[3] == 'done']
        canc = [x for x in tt if x[3].startswith('cancel')]
        causes = Counter(x[3] for x in canc)
        P(f'{side.upper()} Prism tributes/game {len(tt) / len(pr):.1f}: completed {len(done) / len(pr):.1f} (mean size {mean(x[1] for x in done) if done else 0:.0f}, median {median(x[1] for x in done) if done else 0:.0f}), '
          f'cancelled {len(canc) / len(pr):.1f} (mean bag {mean(x[1] for x in canc) if canc else 0:.0f}; ' + ', '.join(f'{k[7:]} {v}' for k, v in causes.most_common(4)) + ')'
          f'; gems scored by Prism / team tributed: {sum(x[4] or 0 for x in done) / max(1, sum(r["gems"][r[side]["team"]] for r in pr)):.2f}')
    P('')
    # team tributes
    for side in ('w', 'l'):
        tt = [x for r in rows for x in r[side]['trib']]
        P(f'{side.upper()} all tributes/game {len(tt) / N:.1f}, completed {sum(x[2] == "done" for x in tt) / N:.1f}, cancelled {sum(x[2].startswith("cancel") for x in tt) / N:.1f}')
    P('')

    # ---------------------------------------------------------------- E. map classes
    P('## E. Map classes (preset; mutations pooled)')
    g = defaultdict(list)
    for r in rows:
        g[r['preset']].append(r)
    rws = []
    for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])):
        ps = [parts(r, 0, r['n']) for r in v]
        f100 = [parts(r, r['brk']['b0'], min(r['n'], r['brk']['b0'] + 100)) for r in v]
        dom = Counter(max(('farm', 'fight', 'camp'), key=lambda kk: p[kk]) for p in ps)
        fightdec = mean(abs(p['fight']) > abs(p['farm']) for p in ps)
        rws.append([k, len(v), f'{median(r["brk"]["b0"] for r in v):.0f}', f'{median(r["n"] for r in v):.0f}',
                    f'{mean(p["farm"] for p in ps):+.0f}', f'{mean(p["fight"] for p in ps):+.0f}', f'{mean(p["camp"] for p in ps):+.0f}',
                    f'{mean(p["bank"] for p in ps):+.0f}',
                    f'{mean(p["farm"] for p in f100):+.0f} / {mean(p["fight"] for p in f100):+.0f}',
                    dom.most_common(1)[0][0], f'{100 * fightdec:.0f}%', f'{100 * mean(r["W"] == 0 for r in v):.0f}%',
                    f'{100 * mean(r["end"] == "r2000" for r in v):.0f}%'])
    P(table(['preset', 'n', 'b0 med', 'end med', 'farm', 'fight', 'camp', 'bank', 'b0+100 farm/fight', 'dominant', '|fight|>|farm|', 'team A wins', 'to r2000'], rws))
    P('')
    mut = defaultdict(list)
    for r in rows:
        if r['mut']:
            mut[r['mut']].append(r)
    P(f'Mutations: {sum(len(v) for v in mut.values())} games over {len(mut)} bases.')
    P('')

    # ---------------------------------------------------------------- F. side asymmetry
    P('## F. Side asymmetry (team A moves first on odd rounds; identical bots)')
    aw = [r['W'] == 0 for r in rows]
    lo, hi = boot([float(x) for x in aw], B=1000)
    P(f'team A wins {100 * mean(aw):.1f}% [{100 * lo:.1f}, {100 * hi:.1f}] of {N} distinct games.')
    for key in ('sizec', 'npick', 'sym', 'kind'):
        gg = defaultdict(list)
        for r in rows:
            gg[r[key]].append(r['W'] == 0)
        P(f'- by {key}: ' + ', '.join(f'{k} {100 * mean(v):.1f}% (n={len(v)})' for k, v in sorted(gg.items(), key=lambda kv: str(kv[0]))))
    P('')

    # ---------------------------------------------------------------- G. champion farming
    P('## G. Champion types: farming and fighting (per 1000 alive rounds, whole game, both teams pooled)')
    acc = defaultdict(Counter)
    for r in rows:
        for side in ('w', 'l'):
            for nm, s in r[side]['types'].items():
                a_ = acc[nm]
                a_['alive'] += s['alive']
                a_['cap'] += s['cap']
                a_['campdmg'] += s['campdmg']
                a_['kills'] += s['kills']
                a_['deaths'] += s['deaths']
                a_['cdeaths'] += s['cdeaths']
                a_['n'] += 1
                for k, v in s['lab'].items():
                    a_['L_' + k] += v
    rws = []
    for nm, a_ in sorted(acc.items(), key=lambda kv: -kv[1]['n']):
        if a_['n'] < 60:
            continue
        al = a_['alive'] or 1
        tot = sum(v for k, v in a_.items() if k.startswith('L_'))
        rws.append([nm, a_['n'] // 2, f'{1000 * a_["cap"] / al:.0f}', f'{a_["campdmg"] / al:.1f}', f'{1000 * a_["kills"] / al:.2f}',
                    f'{1000 * a_["deaths"] / al:.2f}', f'{1000 * a_["cdeaths"] / al:.2f}',
                    f'{100 * (a_["L_walk"] + a_["L_walk_bag"]) / tot:.0f}%', f'{100 * a_["L_camp"] / tot:.0f}%', f'{100 * a_["L_hold"] / tot:.0f}%',
                    f'{100 * a_["L_tribute"] / tot:.0f}%', f'{100 * (a_["L_wait_camp"] + a_["L_idle"] + a_["L_spawn"] + a_["L_wait_altar"]) / tot:.0f}%', f'{100 * a_["L_dead"] / tot:.0f}%'])
    P(table(['champion', 'games', 'capture gems', 'camp dmg / alive rd', 'kills', 'deaths', 'camp deaths', 'walk', 'camp', 'hold', 'tribute', 'wait+idle+spawn', 'dead'], rws))
    P('')
    # r2000 games
    r2 = [r for r in rows if r['end'] == 'r2000']
    if r2:
        P(f'Games to r2000: {len(r2)}; W carried at end mean {mean(r["w"]["at"][str(r["n"])]["carried"] for r in r2):.0f}, '
          f'L {mean(r["l"]["at"][str(r["n"])]["carried"] for r in r2):.0f}; tributed W {mean(r["gems"][r["W"]] for r in r2):.0f}, L {mean(r["gems"][1 - r["W"]] for r in r2):.0f}')
    big = [(r['w']['at'][str(r['n'])]['carried'] + r['l']['at'][str(r['n'])]['carried'], r) for r in rows]
    P(f'Gems still carried at the end (both teams): mean {mean(b for b, _ in big):.0f}, games with 300+: {sum(b >= 300 for b, _ in big)}')


if __name__ == '__main__':
    main()
