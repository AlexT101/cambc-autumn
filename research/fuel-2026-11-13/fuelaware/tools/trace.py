"""trace.py BATCHGLOB...: reads the fuelaware debug trace (mktrace.py) from kept replays' stdout.

Turns are SLOT lines (round, champion); a turn with no TE line ran out of fuel. Prints, a game:
  - static fields built in the turn (d) and in the queue (q), by kind and round, and how often the turn ran out;
  - the fuel tests before a group field's read (FG), by site and outcome;
  - the queue's last stage by round, and when each champion's warm-up first completes;
  - shortcuts on turns that built a field against all turns.
"""
import collections, glob, sys, zipfile
from multiprocessing import Pool

BUCKETS = ((1, 1), (2, 5), (6, 20), (21, 50), (51, 100), (101, 200), (201, 400), (401, 2000))


def bucket(r):
    for lo, hi in BUCKETS:
        if lo <= r <= hi:
            return f'{lo}-{hi}' if lo != hi else str(lo)
    return '?'


def one(f):
    side = 'b' if f.rsplit('.', 1)[0].endswith('-21') else 'a'
    try:
        text = zipfile.ZipFile(f).read(f'team-{side}.stdout').decode('utf-8', 'replace').replace('\x00', '')
    except Exception:
        return None
    turns = {}
    cur = None
    area = groups = None
    for l in text.splitlines():
        try:
            if l.startswith('SLOT '):
                v = l.split()
                cur = (int(v[1]), int(v[2]))
                turns.setdefault(cur, {'f': [], 'g': [], 'te': None, 's': []})
            elif l.startswith('TE '):
                v = l.split()
                k = (int(v[1]), int(v[2]))
                if k in turns:
                    turns[k]['te'] = (int(v[3]), int(v[4]), int(v[5]), int(v[6]))
            elif l.startswith('FLD '):
                v = l.split()
                k = (int(v[1]), int(v[2]))
                if k in turns:
                    turns[k]['f'].append((v[3], int(v[4]), int(v[5]), v[6]))
            elif l.startswith('FG '):
                v = l.split()
                k = (int(v[1]), int(v[2]))
                if k in turns:
                    turns[k]['g'].append((v[3], int(v[4])))
            elif l.startswith('SHORTCUT '):
                v = l.split()
                k = (int(v[1]), int(v[2]))
                if k in turns:
                    turns[k]['s'].append(v[3])
            elif l.startswith('MAPFEAT ') and area is None:
                area = int(l.split()[1])
            elif l.startswith('CREW GROUP g'):
                groups = max(groups or 0, int(l.split()[2][1:]) + 1)
        except (ValueError, IndexError):
            continue
    return turns, area, groups


def main():
    files = sorted(f for g in sys.argv[1:] for f in glob.glob(g + '/*.repl26a'))
    with Pool(24) as p:
        res = [x for x in p.map(one, files, chunksize=8) if x and x[0]]
    G = len(res)
    n_turns = collections.Counter()
    oof = collections.Counter()
    fld = collections.defaultdict(lambda: [0, 0, 0, []])   # (bucket, kind, where) -> n, cost, turn ran out, left
    fg = collections.Counter()
    stage = collections.defaultdict(collections.Counter)
    end_left = collections.defaultdict(list)
    first_done = collections.defaultdict(list)   # stage -> first round reached, per champion
    never = collections.Counter()
    champs = 0
    sc_field = collections.Counter()
    sc_all = collections.Counter()
    t_field = t_all = 0
    oof_field = 0
    heavy = collections.defaultdict(lambda: [0, 0])   # d-build turns by bucket: n, ran out
    for turns, area, groups in res:
        firsts = {}
        handles = set()
        for (r, h), t in turns.items():
            b = bucket(r)
            handles.add(h)
            n_turns[b] += 1
            ran_out = t['te'] is None
            oof[b] += ran_out
            t_all += 1
            for s in set(t['s']):
                sc_all[s] += 1
            built = [x for x in t['f'] if x[3] == 'd' and x[1] > 4000]
            if built and r > 1:
                t_field += 1
                oof_field += ran_out
                heavy[b][0] += 1
                heavy[b][1] += ran_out
                for s in set(t['s']):
                    sc_field[s] += 1
            for kind, cost, left, where in t['f']:
                if cost <= 4000:
                    continue
                e = fld[(b, kind, where)]
                e[0] += 1
                e[1] += cost
                e[2] += ran_out
                e[3].append(left)
            for site, made in t['g']:
                fg[(b, site, made)] += 1
            if t['te']:
                st = t['te'][3]
                stage[b][st] += 1
                end_left[b].append(t['te'][2])
                for s in (4, 6, 7, 9, 10):
                    if st >= s and (h, s) not in firsts:
                        firsts[(h, s)] = r
        champs += len(handles)
        for h in handles:
            for s in (4, 6, 7, 9, 10):
                if (h, s) in firsts:
                    first_done[s].append(firsts[(h, s)])
                else:
                    never[s] += 1
    order = [f'{lo}-{hi}' if lo != hi else str(lo) for lo, hi in BUCKETS]
    print(f'games {G}, champions {champs / G:.2f} a game')
    print('rounds   turns/game  ran out/game  mean fuel left at the turn end')
    for b in order:
        if n_turns[b]:
            L = end_left[b]
            print(f'{b:9s} {n_turns[b] / G:9.1f} {oof[b] / G:9.3f}  {sum(L) / max(1, len(L)):9.0f}')
    print(f'all       {sum(n_turns.values()) / G:9.1f} {sum(oof.values()) / G:9.3f}')
    print('\nstatic fields over 4k (calls a game | mean cost | turn ran out a game | fuel left after p10 p50 | rounds kind where)')
    for (b, kind, where), (n, c, o, left) in sorted(fld.items(), key=lambda kv: (order.index(kv[0][0]), kv[0][2], -kv[1][0])):
        if n / G < 0.02:
            continue
        left.sort()
        print(f'{n / G:8.3f} {c / n:7.0f} {o / G:7.3f}  {left[len(left) // 10]:6d} {left[len(left) // 2]:6d}  {b:8s} {kind:13s} {where}')
    print('\nturns that built a field in decide (rounds 2+): by rounds, a game, ran out')
    for b in order:
        if heavy[b][0]:
            print(f'  {b:8s} {heavy[b][0] / G:7.3f} {heavy[b][1] / G:7.3f} ({100 * heavy[b][1] / heavy[b][0]:.1f}% against {100 * oof[b] / n_turns[b]:.2f}% of all turns)')
    print(f'  total {t_field / G:.3f} a game, ran out {oof_field / G:.3f}')
    print('\nfuel tests before a group field (a game): made 1 = field there, 2 = built now, 0 = cut')
    sites = sorted({k[1] for k in fg})
    for site in sites:
        tot = {m: sum(v for k, v in fg.items() if k[1] == site and k[2] == m) for m in (0, 1, 2)}
        print(f'  {site:6s} there {tot[1] / G:8.3f}  built {tot[2] / G:7.3f}  cut {tot[0] / G:7.3f}   by rounds (cut): '
              + ' '.join(f'{b}:{fg[(b, site, 0)] / G:.3f}' for b in order if fg[(b, site, 0)]))
    print('\nthe queue\'s last stage by rounds (% of finished turns): 0 none, 1 enemy tiles, 2-3 next walk, 4 map, 5 foot, 6 centres, 7 fields, 8 clears, 9 drafted tiles, 10 ring')
    for b in order:
        tot = sum(stage[b].values())
        if tot:
            print(f'  {b:8s} ' + ' '.join(f'{s}:{100 * stage[b][s] / tot:4.1f}' for s in range(11)))
    print('\nfirst round a champion\'s queue reaches a stage: p10 p50 p90 max, never')
    for s in (4, 6, 7, 9, 10):
        L = sorted(first_done[s])
        if L:
            print(f'  stage {s:2d}: {L[len(L) // 10]:4d} {L[len(L) // 2]:4d} {L[9 * len(L) // 10]:4d} {L[-1]:4d}   never {100 * never[s] / champs:.1f}%')
    print('\nshortcuts: % of turns that built a field in decide | % of all turns')
    for s, n in sorted(sc_all.items(), key=lambda kv: -kv[1])[:14]:
        print(f'  {s:28s} {100 * sc_field[s] / max(1, t_field):6.2f}  {100 * n / t_all:6.2f}')


if __name__ == '__main__':
    main()
