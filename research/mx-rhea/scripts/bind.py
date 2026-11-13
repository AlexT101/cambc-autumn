"""How often a candidate's change binds: pairs each game of CAND vs chy-ref with the mirror's game on the same map and
side (chy-mirror is chy-ref, games are deterministic), finds the first D line (round, champion, branch, farm group,
claim) where the candidate's team differs, and how results flip. Both batches must be debug builds.
Usage: py bind.py MIRROR_BATCH CAND_BATCH"""
import json, sys, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor


def dlines(replay, side):
    z = zipfile.ZipFile(replay)
    s = z.read(f"team-{'ab'[side]}.stdout").decode(errors='replace')
    return [l for l in s.splitlines() if l.startswith('D ')]


def load(batch):
    j = json.load(open(f'{batch}/results.json'))
    out = {}
    for m in j['matches']:
        if m.get('winner') is None: continue
        out[(m['map'].split('/')[-1], tuple(m['order']))] = m
    return out


def pair(args):
    mm, cm, cside = args
    # cside: the candidate's side (0 = team A). The mirror's chy-mirror plays the same code as chy-ref.
    a = dlines(cm['replay'], cside); b = dlines(mm['replay'], cside)
    first = None
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            first = (int(x.split()[1]), y.split()[3], x.split()[3])
            break
    if first is None and len(a) != len(b):
        first = (int((a if len(a) > len(b) else b)[min(len(a), len(b))].split()[1]), 'end', 'end')
    return first


def main():
    mir, cand = load(sys.argv[1]), load(sys.argv[2])
    jobs, meta = [], []
    for (mp, order), cm in cand.items():
        cside = order.index(0)  # bot 0 is CAND in its batch
        mm = mir.get((mp, order))  # same order: chy-mirror (bot 0) on the same side
        if not mm: continue
        base_win = mm['winner'] == 0  # chy-mirror's side won, i.e. chy-ref code on CAND's side
        cand_win = cm['winner'] == 0
        jobs.append((mm, cm, cside)); meta.append((base_win, cand_win, cm['rounds']))
    with ProcessPoolExecutor(32) as ex:
        firsts = list(ex.map(pair, jobs, chunksize=16))
    n = len(jobs)
    same = sum(1 for f in firsts if f is None)
    print(f'{n} paired games; identical decisions all game: {same} ({same/n:.1%})')
    rs = sorted(f[0] for f in firsts if f)
    if rs:
        print('first divergence round p10/p25/p50/p75/p90:', [rs[int(q*(len(rs)-1))] for q in (.1, .25, .5, .75, .9)])
    print('branch at first divergence (ref -> cand):', Counter((f[1], f[2]) for f in firsts if f).most_common(12))
    flips = Counter((b, c) for b, c, _ in meta)
    print(f'results: base win & cand win {flips[(True, True)]}, base win -> cand loss {flips[(True, False)]}, '
          f'base loss -> cand win {flips[(False, True)]}, both lose {flips[(False, False)]}')
    print(f'win rate base {sum(b for b, _, _ in meta)/n:.1%} cand {sum(c for _, c, _ in meta)/n:.1%}')
    for lo, hi in ((0, 100), (100, 200), (200, 400), (400, 800), (800, 10**6)):
        sel = [(m, f) for m, f in zip(meta, firsts) if f and lo <= f[0] < hi]
        if not sel: continue
        d = sum(m[1] for m, _ in sel) - sum(m[0] for m, _ in sel)
        print(f'  diverged r{lo}-{hi}: {len(sel)} games, cand minus base wins {d:+d} ({d/len(sel):+.1%})')


if __name__ == '__main__':
    main()
