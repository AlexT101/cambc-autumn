"""Why our clears go uncaptured: joins ck.py episodes with the killer's per-turn D trace (debug builds:
`D round handle branch farm_group claim`). For each non-prompt clear of ours, the killer's branch and claim on its
next turn: kept (claim is the cleared group), moved (another group), or another branch (fight, retreat, bank...).

usage: why.py EXTDIR [--kinds gemcl,goldcl,cl] [--show N]"""
import sys, json, gzip, os, re, zipfile, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import ck
ext = sys.argv[1]
kinds = sys.argv[sys.argv.index('--kinds') + 1].split(',') if '--kinds' in sys.argv else None
show = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 0
tab = collections.Counter(); shown = 0; n = 0
for g in json.load(open(ext + '/index.json'))['games']:
    us = ck.side_of(g['source'], None); n += 1
    with zipfile.ZipFile(g['source']) as z:
        out = z.read(f"team-{'ab'[us]}.stdout").replace(b'\0', b'').decode('utf-8', 'replace')
    D = {}
    for l in out.splitlines():
        if l.startswith('D '):
            p = l.split()
            try: D[(int(p[2]), int(p[1]))] = (p[3], int(p[4]), int(p[5]))
            except (IndexError, ValueError): pass
    handles = sorted({h for h, _ in D})
    d = ext + '/' + g['dir']; meta = json.load(open(d + '/meta.json'))
    ours = [c['id'] for c in meta['champions'] if c['team'] == us]
    name = {c['id']: c['name'] for c in meta['champions']}
    hid = dict(zip(ours, handles)) if len(handles) == len(ours) else {}
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    clears = {(e['g'], e['r']): e.get('by') for e in ev if e['k'] == 'group_clear'}
    xs, _ = ck.game(ext, g, us, 8, None)
    for x in xs:
        if x['by'] != 'us' or x['cls'] == 'prompt' or (kinds and x['kind'] not in kinds): continue
        k = clears[(x['g'], x['clear'])]; h = hid.get(k)
        if h is None: tab['no-trace'] += 1; continue
        at = D.get((h, x['clear'])); nxt = D.get((h, x['clear'] + 1))
        if at is None or nxt is None: tab[(x['cls'], 'dead/oof')] += 1; continue
        br, fg, cl = nxt
        others = [hh for hh in handles if hh != h and D.get((hh, x['clear'] + 1), ('', -1, -1))[2] == x['g']]
        if cl == x['g'] or fg == x['g']: why = f'kept-{br}'
        elif others: why = 'ally-claims'
        elif br in 'FP': why = f'moved-{br}{"-held" if at[0] == "P" else ""}'
        else: why = f'branch-{br}'
        tab[(x['cls'], why)] += 1; tab[('who', name[k], why)] += 1
        tab[('turns', why)] += x['ours'] - x['held']
        prev = D.get((h, x['clear'] - 1))
        if why == 'moved-F': tab[('moved-F prev claim', 'same' if prev and prev[2] == x['g'] else 'other')] += 1
        if show and shown < show and why == 'moved-F':
            shown += 1; print(g['source'], 'g', x['g'], 'r', x['clear'], name[k], 'prev', prev, 'at', at, 'next', nxt, x['cls'], x['ours'], x['held'])
print(n, 'games')
for k, v in sorted(tab.items(), key=lambda kv: (str(kv[0][0]), -kv[1])): print(k, v, f'{v/n:.2f}/game')
