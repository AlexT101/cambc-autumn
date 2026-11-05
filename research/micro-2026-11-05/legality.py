"""Turns that break the one-walk / one-attack (+resets) / one-cast budget, or act while dead: engine-exploit scan.

    python3 -I research/micro-2026-11-05/legality.py DIR
"""
import collections, glob, gzip, json, multiprocessing as mp, sys


def f(p):
    d = json.load(gzip.open(p)); roster = {c['id']: c for c in d['roster']}
    C = collections.Counter(); ex = []
    cur, L = None, []
    def flush():
        if not L: return
        t = d['teams'][roster[cur[1]]['team']]
        mv = sum(a['k'] == 4 for a in L); at = sum(a['k'] == 5 for a in L)
        casts = [a for a in L if a['k'] == 6]; resets = sum(a.get('ab') == 1 for a in casts)
        dead_act = [a for a in L if a['k'] in (4, 5, 6, 11, 12, 14, 15, 20, 21) and not a['b'][5]] if all(len(a['b']) > 5 for a in L if a['k'] not in (8, 9)) else []
        C[(t, 'turns')] += 1
        for tag, bad in (('walks>1', mv > 1), ('attacks>1+resets', at > 1 + resets), ('casts>1', len(casts) > 1), ('acted_dead', bool(dead_act))):
            if bad:
                C[(t, tag)] += 1
                if len(ex) < 4: ex.append((t, tag, d['key'], cur[0], CHN[roster[cur[1]]['type']], [(a['k'], a.get('ab')) for a in L if a['k'] != 8]))
    for a in d['acts']:
        k = (a['r'], a['a'])
        if k != cur:
            flush(); cur, L = k, []
        L.append(a)
    flush()
    return C, ex


CHN = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
if __name__ == '__main__':
    C = collections.Counter(); E = []
    with mp.Pool(24) as pool:
        for c, e in pool.imap_unordered(f, sorted(glob.glob(sys.argv[1] + '/*.json.gz')), chunksize=16):
            C.update(c); E.extend(e)
    for k, v in sorted(C.items()):
        if k[1] != 'turns': print(k, v, f"/ {C[(k[0], 'turns')]} turns")
    print('turns scanned', sum(v for k, v in C.items() if k[1] == 'turns'))
    for e in E[:20]: print(e)
