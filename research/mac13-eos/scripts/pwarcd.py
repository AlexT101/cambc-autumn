"""Prism duel starts (both Prisms first within 5 after 5+ rounds apart beyond 6): whose stun was ready, whether a
camp cast had spent it, and who died within 15 rounds. Usage: pwarcd.py EXTRACTED_DIR"""
import gzip, json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor


def cheb(c, d, i):
    if c['x'][i] is None or d['x'][i] is None: return 99
    return max(abs(c['x'][i] - d['x'][i]), abs(c['y'][i] - d['y'][i]))


def g(d):
    meta = json.loads((d / 'meta.json').read_text())
    names = {int(c['id']): c['name'] for c in meta['champions']}
    R = json.load(gzip.open(d / 'rounds.json.gz'))
    ch = {int(c['id']): c for c in R['champions']}
    pr = [i for i in ch if names[i] == 'Prism']
    if len(pr) != 2: return []
    deaths = collections.defaultdict(list)
    camp_stun = collections.defaultdict(list)  # prism -> rounds it stunned a camp
    any_stun = collections.defaultdict(list)
    for l in gzip.open(d / 'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'death' and e['v'] in pr: deaths[e['v']].append(e['r'])
        elif e['k'] == 'cast' and e.get('a') in pr and e.get('slot') == 0:
            any_stun[e['a']].append(e['r'])
            if 'camp' in e: camp_stun[e['a']].append(e['r'])
    a, b = pr
    A, B = ch[a], ch[b]
    out = []
    apart = 99
    for i in range(1, len(A['x'])):
        if not (A['alive'][i] and B['alive'][i]):
            apart = 99
            continue
        dd = cheb(A, B, i)
        if dd > 6: apart += 1; continue
        if dd <= 5 and apart >= 5:
            for me, foe in ((a, b), (b, a)):
                M, F = ch[me], ch[foe]
                last = [r for r in any_stun[me] if i - 8 < r <= i]
                out.append(dict(r=i, ratio=F['foc'][i] / max(1, M['foc'][i]), cd=(M['cd0'][i] or 0) > 0, ecd=(F['cd0'][i] or 0) > 0,
                                camp=bool(last) and last[-1] in camp_stun[me], die=any(i <= r <= i + 15 for r in deaths[me]),
                                kill=any(i <= r <= i + 15 for r in deaths[foe])))
        apart = 0
    return out


if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d / 'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: E = [x for r in ex.map(g, dirs, chunksize=4) for x in r]
    E = [e for e in E if e['r'] < 600]
    print('duel starts (each side once)', len(E))
    for lab, f in (('all', lambda e: True), ('ratio<0.8 (we bigger)', lambda e: e['ratio'] < 0.8), ('0.8-1.25', lambda e: 0.8 <= e['ratio'] <= 1.25), ('ratio>1.25 (we smaller)', lambda e: e['ratio'] > 1.25)):
        S = [e for e in E if f(e)]
        print(f'== {lab}: {len(S)}')
        for k, (c, ec) in enumerate(((False, False), (False, True), (True, False), (True, True))):
            s = [e for e in S if e['cd'] == c and e['ecd'] == ec]
            if s: print(f'   our stun {"down" if c else "ready"} theirs {"down" if ec else "ready"}: n {len(s)} we die {100 * sum(e["die"] for e in s) / len(s):.0f}% we kill {100 * sum(e["kill"] for e in s) / len(s):.0f}%  (our stun spent on a camp {100 * sum(e["camp"] for e in s) / len(s):.0f}%)')
