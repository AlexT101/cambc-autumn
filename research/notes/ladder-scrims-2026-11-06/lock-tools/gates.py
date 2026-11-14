#!/usr/bin/env python3
"""gates.py BATCH: from an oc-lock-obs batch (PLG every round: lead, max bag, bag sum, enemy tributed),
how often each perma-lock gate would hold, in what state, and the enemy tributes landing (PLLAND) by gate.
Bot 1 is obs."""
import collections, glob, json, sys, zipfile
from pathlib import Path
d = Path(sys.argv[1]); res = json.loads((d / 'results.json').read_text())
win = {Path(m['replay']).name: m.get('winner') == 0 for m in res['matches'] if m.get('replay')}
G = {
    'lead>=1': lambda l, mb, sb, en: l >= 1,
    'lead>=50': lambda l, mb, sb, en: l >= 50,
    'bag>=100': lambda l, mb, sb, en: mb >= 100,
    'bag>=200': lambda l, mb, sb, en: mb >= 200,
    'bag>=500 (G2)': lambda l, mb, sb, en: mb >= 500,
    'sum>=500 (G2)': lambda l, mb, sb, en: sb >= 500,
    'lead&bag>=100': lambda l, mb, sb, en: l >= 1 and mb >= 100,
    'lead&bag>=200': lambda l, mb, sb, en: l >= 1 and mb >= 200,
    'lead&bag>=500': lambda l, mb, sb, en: l >= 1 and mb >= 500,
    'lead&flip (G3)': lambda l, mb, sb, en: l >= 1 and en + sb > en + l,
    'winbank (G3b)': lambda l, mb, sb, en: en + sb >= 1000,
    'lead&winbank': lambda l, mb, sb, en: l >= 1 and en + sb >= 1000,
}
fire = collections.Counter(); rounds = collections.Counter(); wins = collections.Counter(); first = collections.defaultdict(list)
land = collections.Counter(); land_gems = collections.Counter()
n = 0
for b in sorted(d.glob('*.repl26a')):
    team = 'a' if b.stem.endswith('-12') else 'b'
    out = zipfile.ZipFile(b).read(f'team-{team}.stdout').replace(b'\0', b'').decode('utf-8', 'replace')
    state = {}; lands = {}
    for line in out.splitlines():
        f = line.split()
        if not f: continue
        if f[0] == 'PLG': state[int(f[1])] = tuple(map(int, f[3:7]))
        elif f[0] == 'PLLAND': lands[(int(f[1]), int(f[3]))] = int(f[4])
    n += 1; w = win.get(b.name)
    for g, fn in G.items():
        rs = [r for r, s in state.items() if fn(*s)]
        if rs:
            fire[g] += 1; rounds[g] += len(rs); wins[g] += bool(w); first[g].append(min(rs))
    for (r, gems), locked in lands.items():
        s = state.get(r) or state.get(r - 1)
        if not s: continue
        for g, fn in G.items():
            if fn(*s): land[(g, locked > 0)] += 1; land_gems[(g, locked > 0)] += gems
    land[('all', False)] += len(lands); land_gems[('all', False)] += sum(g for _, g in lands)
import statistics as st
print(f'{n} games (obs = bot 1, side by side), obs won {sum(win.values())}')
print('| gate | games fired | rounds a firing game | first round (median) | obs won when fired | enemy tributes landing while it held: count a game (gems) | of which with our lock believed |')
print('|---|---|---|---|---|---|---|')
for g in G:
    f = fire[g]
    if not f: print(f'| {g} | 0 | | | | | |'); continue
    lc = land[(g, False)] + land[(g, True)]; lg = land_gems[(g, False)] + land_gems[(g, True)]
    print(f'| {g} | {100*f/n:.0f}% | {rounds[g]/f:.0f} | {st.median(first[g]):.0f} | {100*wins[g]/f:.0f}% | {lc/n:.2f} ({lg/n:.0f}) | {land[(g, True)]/n:.2f} ({land_gems[(g, True)]/n:.0f}) |')
print(f'all enemy tributes: {land[("all", False)]/n:.2f} a game ({land_gems[("all", False)]/n:.0f} gems)')
