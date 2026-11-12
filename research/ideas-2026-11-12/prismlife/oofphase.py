"""Where our Prism's out-of-fuel turns ran out (debug builds' OOF lines), near enemies or not: python3 oofphase.py EXTROOT/TAG"""
import collections, gzip, json, os, sys, zipfile
from multiprocessing import Pool
ROOT = '/home/ubuntu/cambc-autumn'


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json'))); R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']
    oof = collections.defaultdict(list); sc = collections.defaultdict(lambda: collections.defaultdict(list)); D = collections.defaultdict(dict)
    for line in out.replace('\x00', '').splitlines():
        v = line.split()
        if len(v) >= 3 and v[0] == 'OOF':
            try: oof[int(v[1])].append(' '.join(v[2:]))
            except ValueError: pass
        elif len(v) >= 4 and v[0] == 'SHORTCUT':
            try: sc[int(v[1])][int(v[2])].append(v[3])
            except ValueError: pass
        elif len(v) >= 4 and v[0] == 'D':
            try: D[int(v[1])][int(v[2])] = v[3]
            except ValueError: pass
    rows = []
    foes = [c for c in ch if team[c] != us]
    for c in ch:
        if team[c] != us: continue
        C = ch[c]
        for i, r in enumerate(rounds):
            if C['turn'][i] != 6: continue
            j = max(0, i - 1)
            me = (C['x'][j], C['y'][j]) if C['alive'][j] and C['x'][j] is not None else None
            near = me is not None and any(ch[e]['alive'][j] and ch[e]['x'][j] is not None and cheb(me, (ch[e]['x'][j], ch[e]['y'][j])) <= 8 for e in foes)
            n_oof = sum(1 for c2 in ch if team[c2] == us and ch[c2]['turn'][i] == 6)
            ph = oof[r][0] if len(oof.get(r, [])) == 1 and n_oof == 1 else '?'
            rows.append((typ[c], near, ph, tuple(sc[r].get(c, [])), D[r].get(c, '.'), D[r - 1].get(c, '.')))
    return rows


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    print(len(R), 'out-of-fuel turns of ours;', sum(1 for r in R if r[0] == 'Prism'), 'the Prism\'s')
    for name, sel in (('Prism near an enemy', lambda r: r[0] == 'Prism' and r[1]), ('Prism, none near', lambda r: r[0] == 'Prism' and not r[1]), ('others near an enemy', lambda r: r[0] != 'Prism' and r[1])):
        S = [r for r in R if sel(r)]
        if not S: continue
        print(f'\n{name}: {len(S)}')
        print('  phase:', ', '.join(f'{a} {100 * b / len(S):.0f}%' for a, b in collections.Counter(r[2] for r in S).most_common(8)))
        c = collections.Counter()
        for r in S: c.update(set(r[3]))
        print('  shortcuts noted that turn:', ', '.join(f'{a} {100 * b / len(S):.0f}%' for a, b in c.most_common(12)))
        print('  decision the turn before:', ', '.join(f'{a} {100 * b / len(S):.0f}%' for a, b in collections.Counter(r[5] for r in S).most_common(8)))
        print('  decision that turn (if it printed):', ', '.join(f'{a} {100 * b / len(S):.0f}%' for a, b in collections.Counter(r[4] for r in S).most_common(8)))
