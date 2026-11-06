"""Tables for recall-detection-2026-11-06.md from collect.py's counts.json.

py research/recall-detection-2026-11-06/report.py counts.json > tables.md
"""
import json, sys

D = json.load(open(sys.argv[1]))
KEY, T = D['key'], D['thresholds']
XS = [f'{round(t * 100)}%' for t in T]
GROUPS = {'Fish': ['Fish'], 'Mite': ['Mite'], 'ocean (scrims v78-v81)': ['ocean-v78', 'ocean-v79', 'ocean-v80', 'ocean-v81'],
          'astraeus (self-play)': ['astraeus-self'], 'Fish (ladder 10-30)': ['Fish-ladder'],
          'Mite (ladder 10-30)': ['Mite-ladder']}
REAL, FEINT = {'completed', 'kept_int'}, {'feint', 'abandoned'}

rows = []
for k, n in D['counts'].items():
    r = dict(zip(KEY, k.split('|')))
    for f in ('full', 'nw', 'w1b', 'w1seen', 'w1gems', 'w1dist', 'cb', 'cseenb', 'nextkept'):
        r[f] = int(r[f])
    r['n'] = n
    rows.append(r)


def pct(a, b):
    return f'{100 * a / b:.1f}' if b else '-'


def rules(seen):
    """name -> predicate on a row. seen: only windows an enemy saw count."""
    w1 = (lambda r: r['w1seen'] == 1) if seen else (lambda r: r['w1b'] >= 0)
    cb = 'cseenb' if seen else 'cb'
    out = {'(a) any window': lambda r: w1(r) or r[cb] >= 0,
           '(b) first window': w1,
           '(c) 2nd+ window (current)': lambda r: r[cb] >= 0}
    for i, x in enumerate(XS):
        out[f'(d) first window, hp<{x}'] = lambda r, i=i: w1(r) and r['w1b'] <= i
    for i, x in enumerate(XS):
        out[f'(e) 2nd+ window, hp<{x}'] = lambda r, i=i, cb=cb: r[cb] >= 0 and r[cb] <= i
    for i, x in enumerate(XS):
        out[f'(f) (c) or (d) hp<{x}'] = lambda r, i=i, cb=cb: r[cb] >= 0 or (w1(r) and r['w1b'] <= i)
    return out


def table2(rs, seen):
    real = sum(r['n'] for r in rs if r['cls'] in REAL)
    print('| rule | flagged | precision % | recall % | undecided among flagged % | precision % if undecided = real |')
    print('| --- | ---: | ---: | ---: | ---: | ---: |')
    for name, p in rules(seen).items():
        R = sum(r['n'] for r in rs if r['cls'] in REAL and p(r))
        F = sum(r['n'] for r in rs if r['cls'] in FEINT and p(r))
        U = sum(r['n'] for r in rs if r['cls'] == 'undecided' and p(r))
        print(f'| {name} | {R + F + U} | {pct(R, R + F)} | {pct(R, real)} | {pct(U, R + F + U)} | {pct(R + U, R + F + U)} |')
    print()


for g, teams in GROUPS.items():
    rs = [r for r in rows if r['team'] in teams]
    if not rs:
        continue
    ng = sum(D['games'].get(t, 0) for t in teams)
    dates = sorted({d for t in teams for d in D['dates'].get(t, [])})
    S = lambda f: sum(r['n'] for r in rs if f(r))
    tot = S(lambda r: r['cls'] != 'open')
    print(f'## {g}\n\n{ng} games ({", ".join(dates)}); Home emblem on {pct(S(lambda r: r["full"] == 3), S(lambda r: True))}% of recalls.\n')
    print('**1. Counts** (open at game end left out)\n')
    print('| class | recalls | % | per game |')
    print('| --- | ---: | ---: | ---: |')
    line = lambda name, n: print(f'| {name} | {n} | {pct(n, tot)} | {n / ng:.1f} |')
    line('started', tot)
    comp = S(lambda r: r['cls'] == 'completed'); ki = S(lambda r: r['cls'] == 'kept_int')
    line('**real** (completed + kept then interrupted)', comp + ki)
    line('&nbsp; completed', comp)
    for c in ('damage', 'stun', 'death', 'other'):
        n = S(lambda r: r['cls'] == 'kept_int' and r['cause'] == c)
        if n: line(f'&nbsp; kept, then {c}', n)
    line('**feint** (cancelled by hand at its first own turn)', S(lambda r: r['cls'] == 'feint'))
    line('abandoned (kept a turn or more, then cancelled by hand)', S(lambda r: r['cls'] == 'abandoned'))
    und = S(lambda r: r['cls'] == 'undecided')
    line('**undecided** (interrupted before its first own turn)', und)
    for c in ('damage', 'stun', 'death', 'other'):
        n = S(lambda r: r['cls'] == 'undecided' and r['cause'] == c)
        if n: line(f'&nbsp; {c}', n)
    line('&nbsp; of which no round-end window (interrupted the round it started)', S(lambda r: r['cls'] == 'undecided' and r['nw'] == 0))
    nk = S(lambda r: r['cls'] == 'undecided' and r['nextkept'] == 1); nn = S(lambda r: r['cls'] == 'undecided' and r['nextkept'] >= 0)
    print(f'\nUndecided recalls followed within 2 rounds by a recall the champion kept: {pct(nk, nn)}% (of {nn} followed by any recall).')
    for i in (2, 5):
        dr = S(lambda r: r['cls'] in REAL | FEINT and r['w1b'] >= 0 and r['w1b'] <= i)
        rr = S(lambda r: r['cls'] in REAL and r['w1b'] >= 0 and r['w1b'] <= i)
        ud = S(lambda r: r['cls'] == 'undecided' and r['w1b'] >= 0 and r['w1b'] <= i)
        print(f'Decided recalls with first-window hp<{XS[i]}: {pct(rr, dr)}% real; undecided ones with that health: {ud}.')
    print('\n**2. Rules, every window** (precision: real / (real + feint + abandoned), undecided left out)\n')
    table2(rs, False)
    if g not in ('astraeus (self-play)',):
        print('**2s. Rules, only windows an enemy saw** (seen by an enemy champion in that round or the next)\n')
        table2(rs, True)
    real = [r for r in rs if r['cls'] in REAL]
    NR = sum(r['n'] for r in real)
    miss = sum(r['n'] for r in real if r['cb'] < 0)
    late = sum(r['n'] for r in real if r['cb'] >= 0 and r['w1b'] >= 0)
    print(f'**3. Real recalls against rule (c)**: {NR} real; (c) misses {miss} ({pct(miss, NR)}%: kept at the first own turn, '
          f'interrupted before the second round end); reads {late} ({pct(late, NR)}%) one window late.\n')
    print('| X | missed, caught by (d) | late, caught a window earlier by (d) | extra feints flagged by (d) | extra undecided flagged by (d) |')
    print('| --- | ---: | ---: | ---: | ---: |')
    for i, x in enumerate(XS):
        a = sum(r['n'] for r in real if r['cb'] < 0 and 0 <= r['w1b'] <= i)
        b = sum(r['n'] for r in real if r['cb'] >= 0 and 0 <= r['w1b'] <= i)
        f = S(lambda r: r['cls'] in FEINT and r['cb'] < 0 and 0 <= r['w1b'] <= i)
        u = S(lambda r: r['cls'] == 'undecided' and 0 <= r['w1b'] <= i)
        print(f'| {x} | {a} / {miss} | {b} / {late} | {f} | {u} |')
    print()
    # Gems and spawn distance in the first window, decided recalls only.
    print('**First-window gems and distance** (decided recalls: % real)\n')
    print('| | 0 gems | 1-9 | 10+ | on spawn | 1-5 tiles | 6+ |')
    print('| --- | ---: | ---: | ---: | ---: | ---: | ---: |')
    cells = []
    for f, v in [('w1gems', 0), ('w1gems', 1), ('w1gems', 2), ('w1dist', 0), ('w1dist', 1), ('w1dist', 2)]:
        rr = S(lambda r: r['cls'] in REAL and r[f] == v); dd = S(lambda r: r['cls'] in REAL | FEINT and r[f] == v)
        cells.append(f'{pct(rr, dd)} ({dd})')
    print('| real % (n) | ' + ' | '.join(cells) + ' |\n')
