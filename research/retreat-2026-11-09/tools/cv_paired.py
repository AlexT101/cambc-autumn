"""cv_metrics.py's metrics paired by game (map and side) between two extracted debug batches: mean B - A, 95% interval.

usage: cv_paired.py EXTRACT_A BOT_A EXTRACT_B BOT_B [--procs N]
"""
import argparse, json, math, os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from cv_metrics import one, LETTERS


def keyed(ex, bot, procs):
    ix = json.load(open(f'{ex}/index.json'))
    games = ix['games']
    out = {}
    with ProcessPoolExecutor(procs) as pool:
        for g, r in zip(games, pool.map(one, [(ex, g, bot) for g in games], chunksize=8)):
            if r: out[os.path.basename(g['source']).split('-', 1)[1]] = r[0]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exa'); ap.add_argument('bota'); ap.add_argument('exb'); ap.add_argument('botb')
    ap.add_argument('--procs', type=int, default=16)
    a = ap.parse_args()
    A, B = keyed(a.exa, a.bota, a.procs), keyed(a.exb, a.botb, a.procs)
    common = sorted(set(A) & set(B))
    keys = ['won', 'kills', 'deaths', 'deaths_champ', 'chaser_deaths', 'chase_eps', 'chase_kill_eps', 'nokill_chase_turns',
            'turns_C', 'turns_F', 'turns_R', 'turns_P', 'turns_X', 'gems600', 'enemy_gems600', 'gold600', 'captures',
            'enemy_captures', 'denials', 'oof_lines']
    print(f'{len(common)} paired games: {a.botb} - {a.bota}')
    for k in keys:
        d = [B[g][k] - A[g][k] for g in common]
        n = len(d); m = sum(d) / n
        sd = math.sqrt(sum((x - m) ** 2 for x in d) / max(1, n - 1))
        base = sum(A[g][k] for g in common) / n
        print(f'  {k:20s} {base:10.2f} -> {base + m:10.2f}   diff {m:+9.3f} +- {1.96 * sd / math.sqrt(n):7.3f}')


if __name__ == '__main__':
    main()
