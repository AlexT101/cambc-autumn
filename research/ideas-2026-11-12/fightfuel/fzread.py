"""Reads the fightfuel profile's FZ and SHORTCUT lines from debug replays: python3 fzread.py BATCHGLOB [--who prism|all|other]

Tables: turns by context (enemies in sight), out-of-fuel share and stacks, the scopes' fuel, shortcuts per 1000 turns.
rows(globs) returns the turns for other scripts: dicts with round, handle, prism, dec, seen, near, allies, hp, gems, hit,
start, left_decide, left_queue, oof (stack tuple or None), sc {id: (fuel, calls)}, cuts (set of SHORTCUT names), game.
"""
import collections, glob, sys, zipfile, re, os, pickle, hashlib
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from instr_ids import IDS


def one(f):
    side = 'b' if f.rsplit('.', 1)[0].endswith('-21') else 'a'
    try: text = zipfile.ZipFile(f).read(f'team-{side}.stdout').decode('utf-8', 'replace').replace('\x00', '')
    except Exception: return []
    cuts = collections.defaultdict(set); out = []
    for line in text.splitlines():
        v = line.split()
        if not v: continue
        if v[0] == 'SHORTCUT' and len(v) >= 4:
            try: cuts[(int(v[1]), int(v[2]))].add(v[3])
            except ValueError: pass
        elif v[0] == 'FZ' and len(v) >= 15:
            try:
                r = dict(round=int(v[1]), handle=int(v[2]), prism=bool(int(v[3]) & 256), type=int(v[3]) & 255, dec=v[4], seen=int(v[5]), near=int(v[6]), allies=int(v[7]),
                         hp=int(v[8]), gems=int(v[9]), hit=int(v[10]), start=int(v[11]), left_decide=int(v[12]), left_queue=int(v[13]),
                         oof=None if v[14] == '-' else tuple(int(x) for x in v[14].split('.') if x != 'x'), game=f)
                r['sc'] = {int(a): (int(b), int(c)) for a, b, c in (x.split(':') for x in v[15:])}
                out.append(r)
            except ValueError: pass
    for r in out: r['cuts'] = cuts.get((r['round'], r['handle']), set())
    return out


def rows(globs):
    files = sorted(f for g in globs for f in glob.glob(g + '/*.repl26a'))
    key = hashlib.md5(('|'.join(files)).encode()).hexdigest()[:12]
    cache = f'/tmp/claude-1000/fz-{key}.pkl'
    if os.path.exists(cache): return pickle.load(open(cache, 'rb'))
    with Pool(32) as pool: R = [r for g in pool.map(one, files, chunksize=16) for r in g]
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    pickle.dump(R, open(cache, 'wb'))
    return R


def q(u, p): return u[min(len(u) - 1, int(p * len(u)))] if u else 0


def ctx(r): return 'none' if r['seen'] == 0 else f'{min(r["seen"], 3)}{"+" if r["seen"] >= 3 else ""}'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    who = 'prism'
    seen_min = 1; near_max = 99; decs = None
    for a in sys.argv[1:]:
        if a.startswith('--who='): who = a[6:]
        if a.startswith('--seen='): seen_min = int(a[7:])
        if a.startswith('--near='): near_max = int(a[7:])
        if a.startswith('--dec='): decs = a[6:]
    R = rows(args)
    R = [r for r in R if r['round'] > 2 and r['hp'] >= 0 and (who == 'all' or r['prism'] == (who == 'prism'))]
    games = len({r['game'] for r in R})
    print(f'{len(R)} turns of {who} (alive, round 3 on) in {games} games')
    print('\ncontext (enemies in sight)   turns   OOF%   used before queue: p50 p90 p99   left after decide <10k %   decisions')
    for c in ('none', '1', '2', '3+'):
        S = [r for r in R if ctx(r) == c]
        if not S: continue
        used = sorted(r['start'] - r['left_queue'] for r in S if r['oof'] is None and r['left_queue'])
        low = sum(1 for r in S if r['oof'] is not None or r['left_decide'] < 10000)
        dec = collections.Counter(r['dec'] for r in S)
        print(f'  {c:5s} {len(S):8d}  {100 * sum(1 for r in S if r["oof"] is not None) / len(S):5.2f}  {q(used, .5):6d} {q(used, .9):6d} {q(used, .99):6d}   {100 * low / len(S):5.1f}   '
              + ' '.join(f'{k}{100 * n / len(S):.0f}' for k, n in dec.most_common(8)))
    F = [r for r in R if r['seen'] >= seen_min and r['near'] <= near_max and (decs is None or r['dec'] in decs)]
    if not F: return
    print(f'\nfight turns ({seen_min}+ enemies in sight, nearest within {near_max}, decisions {decs or "any"}): {len(F)}')
    print('scope            share of turns   mean a turn   when called: p50   p90   p99   calls p50 p99')
    tot = collections.Counter(); present = collections.Counter(); vals = collections.defaultdict(list); calls = collections.defaultdict(list)
    for r in F:
        if r['oof'] is not None: continue
        for i, (f, n) in r['sc'].items(): tot[i] += f; present[i] += 1; vals[i].append(f); calls[i].append(n)
    nf = sum(1 for r in F if r['oof'] is None)
    for i in sorted(tot, key=lambda i: -tot[i]):
        u = sorted(vals[i]); cn = sorted(calls[i])
        print(f'  {IDS.get(i, i):15s} {100 * present[i] / nf:6.1f}%   {tot[i] / nf:9.0f}   {q(u, .5):9d} {q(u, .9):6d} {q(u, .99):6d}   {q(cn, .5):4d} {q(cn, .99):4d}')
    print('\nout-of-fuel stacks (fight turns):')
    st = collections.Counter('.'.join(IDS.get(i, str(i)) for i in r['oof']) for r in F if r['oof'] is not None)
    no = sum(st.values())
    for k, n in st.most_common(25): print(f'  {100 * n / max(1, no):5.1f}%  {k}')
    print('\nshortcuts per 1000 turns: fight | no enemy in sight')
    N = [r for r in R if r['seen'] == 0]
    cf = collections.Counter(c for r in F for c in r['cuts']); cn = collections.Counter(c for r in N for c in r['cuts'])
    for k in sorted(set(cf) | set(cn), key=lambda k: -cf[k]): print(f'  {k:28s} {1000 * cf[k] / len(F):7.1f} | {1000 * cn[k] / max(1, len(N)):7.1f}')


if __name__ == '__main__':
    main()
