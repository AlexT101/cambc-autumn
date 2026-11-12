"""What the Prism's own model said on its last turns before each death (variants/pl-trace, debug builds).

    python3 trace.py EXTROOT/TAG [--dump N]

pl-trace prints, for our Prism off its spawn with a live enemy: at its turn start
  PLS round handle x y health worst lethal open safe least stunned doubled stuns
(worst: Safety::worst_damage at its tile; lethal: Safety::lethal there; open: free steps; safe: those not lethal;
least: the least worst_damage of a step), and at its turn end
  PLE round handle x y health worst lethal decision doubled stuns fuel.
A turn with PLS and no PLE ran out of fuel (or died in its own turn). For each death to champions, T0 is its last
turn, T1 the one before, and so on. Printed: how those turns split by what the model knew.
"""
import collections, gzip, json, os, re, sys, zipfile
from multiprocessing import Pool

ROOT = '/home/ubuntu/cambc-autumn'


def parse(line, p, S, E, D):
    v = line.split()
    if line.startswith('PLS '):
        if int(v[2]) == p: S[int(v[1])] = dict(x=int(v[3]), y=int(v[4]), hp=int(v[5]), worst=int(v[6]), lethal=int(v[7]), open=int(v[8]), safe=int(v[9]), least=int(v[10]), stunned=int(v[11]), doubled=int(v[12]), stuns=int(v[13]))
    elif line.startswith('PLE '):
        if len(v) == 11: v.insert(8, '?')
        if int(v[2]) == p: E[int(v[1])] = dict(x=int(v[3]), y=int(v[4]), hp=int(v[5]), worst=int(v[6]), lethal=int(v[7]), dec=v[8], doubled=int(v[9]), stuns=int(v[10]), fuel=int(v[11]))
    elif line.startswith('D '):
        if len(v) >= 4 and int(v[2]) == p: D[int(v[1])] = v[3]


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        names = [t['name'] for t in meta['teams']]
        us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception as e:
        sys.stderr.write(f'{d}: {e!r}\n')
        return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    prisms = [c for c in team if typ[c] == 'Prism' and team[c] == us]
    if not prisms: return dict(deaths=[], turns=[])
    p = prisms[0]
    S = {}; E = {}; D = {}
    for line in out.replace('\x00', '').splitlines():
        line = line.strip()
        try:
            parse(line, p, S, E, D)
        except (ValueError, IndexError):
            pass
    for line in ():
        if line.startswith('PLS '):
            v = line.split()
            if int(v[2]) == p: S[int(v[1])] = dict(x=int(v[3]), y=int(v[4]), hp=int(v[5]), worst=int(v[6]), lethal=int(v[7]), open=int(v[8]), safe=int(v[9]), least=int(v[10]), stunned=int(v[11]), doubled=int(v[12]), stuns=int(v[13]))
        elif line.startswith('PLE '):
            v = line.split()
            if int(v[2]) == p: E[int(v[1])] = dict(x=int(v[3]), y=int(v[4]), hp=int(v[5]), worst=int(v[6]), lethal=int(v[7]), dec=v[8], doubled=int(v[9]), stuns=int(v[10]), fuel=int(v[11]))
        elif line.startswith('D '):
            v = line.split()
            if len(v) >= 4 and int(v[2]) == p: D[int(v[1])] = v[3]
    deaths = []
    for x in ev:
        if x['k'] == 'death' and x['v'] == p and x.get('by') is not None:
            r = x['r']
            turns = [q for q in sorted(S) if q <= r][-6:][::-1]
            # A death in the Prism's own turn (Ren's reflection) or before it: the last PLS at or before r.
            deaths.append(dict(r=r, gems=x.get('gems', 0), dir=os.path.basename(d), killer=typ.get(x['by']),
                               T=[dict(q=q, s=S[q], e=E.get(q), d=D.get(q)) for q in turns if r - q <= 12]))
    # Every traced turn, for base rates: (end lethal, decision)
    dr = sorted(x['r'] for x in ev if x['k'] == 'death' and x['v'] == p and x.get('by') is not None)
    turns = [(E[q]['lethal'], E[q]['dec'], S[q]['lethal'], S[q]['safe'] > 0, S[q]['stunned'], E[q]['worst'] / max(1, E[q]['hp']), E[q]['stuns'],
              E[q]['doubled'] / max(1, E[q]['hp']), next((r - q for r in dr if r >= q), 999), (E[q]['x'], E[q]['y']) != (S[q]['x'], S[q]['y']),
              S[q]['least'] / max(1, S[q]['hp']) if S[q]['open'] else 9.0, S[q]['worst'] / max(1, S[q]['hp'])) for q in S if q in E]
    return dict(deaths=deaths, turns=turns, nS=len(S), nE=len(E))


def main():
    root = sys.argv[1]
    dump = int(sys.argv[sys.argv.index('--dump') + 1]) if '--dump' in sys.argv else 0
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool:
        G = [g for g in pool.map(one, dirs, chunksize=8) if g]
    D = [d for g in G for d in g['deaths']]
    T = [t for g in G for t in g['turns']]
    print(f'{root}: {len(G)} games, {len(D)} Prism deaths to champions; traced Prism turns {len(T)}')
    el = sum(1 for t in T if t[0])
    print(f'All traced turns: ended on a tile its model calls lethal {el} ({100 * el / max(1, len(T)):.2f}%); of those, began on one {sum(1 for t in T if t[0] and t[2])}, had a non-lethal step {sum(1 for t in T if t[0] and t[3])}, stunned {sum(1 for t in T if t[0] and t[4])}')
    c = collections.Counter(t[1] for t in T if t[0])
    print('  decisions on those turns:', ', '.join(f'{k} {v}' for k, v in c.most_common()))
    def tab(name, key, order):
        g = collections.defaultdict(list)
        for t in T: g[key(t)].append(t)
        nd = sum(1 for t in T if t[8] <= 1)
        print('\n' + name)
        for k in order:
            s = g.get(k)
            if not s: continue
            d1 = sum(1 for t in s if t[8] <= 1); d3 = sum(1 for t in s if t[8] <= 3)
            print(f'  {str(k):16s} {len(s):8d} turns ({100 * len(s) / len(T):6.2f}%)  dead before its next turn {100 * d1 / len(s):6.2f}% = {d1:4d} ({100 * d1 / max(1, nd):4.1f}%)  within 3 rounds {100 * d3 / len(s):6.2f}%')
    cuts = [0.001, 0.25, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.5]
    b = lambda x: next((f'<{c}' for c in cuts if x < c), f'>={cuts[-1]}')
    order = [f'<{c}' for c in cuts] + [f'>={cuts[-1]}']
    tab("Its model's worst damage / health on the tile it ended its turn on", lambda t: b(t[5]), order)
    tab('The same, where a stun reaches that tile', lambda t: b(t[5]) if t[6] else None, order)
    tab('The same, where none does', lambda t: b(t[5]) if not t[6] else None, order)
    tab('Doubled bound / health (each enemy yet to act counted twice)', lambda t: b(t[7]), order)
    tab('Worst / health 0.5-1.0 at the turn end: the least worst / health among its steps at the turn start', lambda t: b(t[10]) if 0.5 <= t[5] < 1.0 and not t[4] else None, order)
    tab('Worst / health 0.5-1.0 at the turn end: by decision', lambda t: t[1] if 0.5 <= t[5] < 1.0 and not t[4] else None, sorted({t[1] for t in T}))
    tab('Worst / health 0.5-1.0 at the turn end: it had moved onto the tile', lambda t: t[9] if 0.5 <= t[5] < 1.0 and not t[4] else None, [False, True])
    lb = lambda x: '<0.25' if x < 0.25 else '<0.5' if x < 0.5 else '<0.75' if x < 0.75 else '<1' if x < 1 else '>=1'
    eb = lambda x: '0.5-0.75' if x < 0.75 else '0.75-1' if x < 1 else '>=1'
    for dec in ('R', 'F'):
        tab(f'{dec} turns ending at worst / health 0.5+: (ended at, moved, least step at the turn start)',
            lambda t: (eb(t[5]), 'moved' if t[9] else 'stayed', lb(t[10])) if t[5] >= 0.5 and t[1] == dec and not t[4] else None,
            [(a, m, c) for a in ('0.5-0.75', '0.75-1', '>=1') for m in ('stayed', 'moved') for c in ('<0.25', '<0.5', '<0.75', '<1', '>=1')])
    tab('R turns: worst / health at the turn START', lambda t: lb(t[11]) if t[1] == 'R' and not t[4] else None, ['<0.25', '<0.5', '<0.75', '<1', '>=1'])
    for k in range(3):
        cat = collections.Counter(); dec = collections.Counter(); n = 0
        for d in D:
            if len(d['T']) <= k: cat['no turn'] += 1; continue
            t = d['T'][k]; s = t['s']; e = t['e']; n += 1
            if s['stunned']: cat['stunned'] += 1
            elif e is None: cat['no turn end (out of fuel, or died in its turn)'] += 1
            elif e['lethal'] and s['safe'] == 0 and (not s['lethal'] or True) and s['open'] == 0: cat['ended lethal: no free step'] += 1
            elif e['lethal'] and s['safe'] == 0: cat['ended lethal: every step lethal'] += 1
            elif e['lethal'] and (e['x'], e['y']) == (s['x'], s['y']): cat['ended lethal: stayed, a non-lethal step was open'] += 1
            elif e['lethal']: cat['ended lethal: stepped onto it, a non-lethal step was open'] += 1
            else: cat['ended on a tile its model calls survivable'] += 1
            if e is not None and e['lethal'] and s['safe'] > 0 and not s['stunned']: dec[e['dec']] += 1
        print(f'\nT{k} (the {"last" if k == 0 else str(k) + " before the last"} turn), {n} deaths with one:')
        for name, v in cat.most_common(): print(f'  {name:62s} {v:5d} ({100 * v / len(D):4.1f}%)')
        if dec: print('  decisions when it ended lethal with a non-lethal step open:', ', '.join(f'{a} {b}' for a, b in dec.most_common()))
        dd = collections.Counter(d['T'][k]['d'] or (d['T'][k]['e'] or {}).get('dec', '?') for d in D if len(d['T']) > k)
        print('  decisions:', ', '.join(f'{a} {b}' for a, b in dd.most_common()))
    # Deaths whose last turn ended on a survivable tile: by how much the model missed.
    miss = [d for d in D if d['T'] and d['T'][0]['e'] and not d['T'][0]['e']['lethal'] and not d['T'][0]['s']['stunned']]
    print(f'\nLast turn ended survivable by the model: {len(miss)}; worst / health there (median) '
          f'{sorted(d["T"][0]["e"]["worst"] / max(1, d["T"][0]["e"]["hp"]) for d in miss)[len(miss) // 2] if miss else 0:.2f}; '
          f'died the same round as that turn {sum(1 for d in miss if d["T"][0]["q"] == d["r"])}, the next {sum(1 for d in miss if d["T"][0]["q"] == d["r"] - 1)}')
    if dump:
        import random
        random.seed(3)
        for d in random.sample(D, min(dump, len(D))):
            print(d['dir'], 'r', d['r'], 'bag', d['gems'], d['killer'])
            for t in d['T']: print('   ', t['q'], t['d'], 'S', t['s'], 'E', t['e'])


if __name__ == '__main__':
    main()
