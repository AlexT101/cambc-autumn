#!/usr/bin/env python3
"""plstats.py BATCH... [--bot NAME]: perma-lock debug lines (PL*) of bot 1 (or NAME) per game, from run_batched bundles.

Per game: rounds the gate held (PLG, distinct rounds), locks placed while it held (PLPUT; by a holder or
not), enemy gems in channels those cancelled, holder wait rounds (PLWAIT), seeks, restocks, stun walks,
Tavi sales, out-of-sight lock sightings (PLVISX). Totals, and split by won / lost, with the gate's first
round's lead and bags."""
import collections, json, sys, zipfile
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith('--')]
want = None
if '--bot' in sys.argv: want = sys.argv[sys.argv.index('--bot') + 1]; args.remove(want)
rows = []
for d in map(Path, args):
    res = json.loads((d / 'results.json').read_text())
    bots = [Path(b).name for b in res['bots']]
    me = bots.index(want) if want else 0
    win = {}
    for m in res['matches']:
        win[Path(m.get('replay', '') or '').name] = m.get('winner')
    for b in sorted(d.glob('*.repl26a')):
        order = b.stem.rsplit('-', 1)[1]
        team = 'a' if (order == '12') == (me == 0) else 'b'
        with zipfile.ZipFile(b) as z:
            out = z.read(f'team-{team}.stdout').replace(b'\0', b'').decode('utf-8', 'replace')
        r = collections.Counter(); g_rounds = set(); first = None; wait_rounds = set(); lands = set(); hold_rounds = set()
        for line in out.splitlines():
            f = line.split()
            if not f or not f[0].startswith('PL'): continue
            k = f[0]
            if k == 'PLG':
                g_rounds.add(int(f[1]))
                if len(f) > 7 and int(f[7]) >= 2: hold_rounds.add(int(f[1]))
                if first is None: first = (int(f[1]), int(f[3]), int(f[4]), int(f[5]), int(f[6]))
            elif k == 'PLPUT':
                r['put'] += 1; r['put_holder'] += int(f[5]) >= 0; r['cancelled'] += int(f[4]); r['put_cancel'] += int(f[4]) > 0
            elif k == 'PLWAIT': wait_rounds.add(int(f[1]))
            elif k == 'PLLAND':
                key = (int(f[1]), int(f[3]))
                if key in lands: continue
                lands.add(key); r['land'] += 1; r['land_gems'] += int(f[3]); r['land_unlocked'] += int(f[4]) == 0
            else: r[k] += 1
        r['hold_rounds'] = len(hold_rounds); r['gate_rounds'] = len(g_rounds); r['wait_rounds'] = len(wait_rounds)
        w = win.get(b.name)
        rows.append(dict(game=f'{d.name}/{b.name}', won=None if w is None else w == me, first=first, **r))
keys = ['hold_rounds', 'gate_rounds', 'land', 'land_gems', 'land_unlocked', 'put', 'put_holder', 'put_cancel', 'cancelled', 'wait_rounds', 'PLSEEK', 'PLRESTOCK', 'PLSTUN', 'PLSELL', 'PLVISX']
def summ(rs, label):
    n = len(rs)
    if not n: return
    fired = sum(1 for r in rs if r.get('gate_rounds'))
    print(f'{label}: {n} games, gate fired in {fired} ({100*fired/n:.0f}%); per game: ' + ', '.join(f'{k} {sum(r.get(k,0) for r in rs)/n:.1f}' for k in keys))
summ(rows, 'all')
import math
for lab, sub in (('hold gate fired', [r for r in rows if r.get('hold_rounds')]), ('hold gate never fired', [r for r in rows if not r.get('hold_rounds')])):
    n = sum(1 for r in sub if r['won'] is not None); w = sum(1 for r in sub if r['won'])
    if n: print(f'{lab}: CAND {100*w/n:.1f}% of {n} (+-{196*math.sqrt(.25/n):.1f})')
summ([r for r in rows if r['won']], 'won')
summ([r for r in rows if r['won'] is False], 'lost')
fr = [r for r in rows if r['first']]
if fr:
    import statistics as st
    print('gate first fires: round median', st.median(r['first'][0] for r in fr), '| lead median', st.median(r['first'][1] for r in fr),
          '| max enemy bag median', st.median(r['first'][2] for r in fr), '| enemy tributed median', st.median(r['first'][4] for r in fr))
if '--json' in sys.argv: print(json.dumps(rows))
