"""s1: how much of a solo (S/K) choice's clear other champions dealt, and the clear time with and without help.

    python research/mac13-kronos/s1/clear_help.py [choices.jsonl] [--games N]
"""
import gzip
import json
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AN = ROOT / 'replays' / '.analysis'


def work(item):
    d, chs = item
    m = json.loads((AN / d / 'meta.json').read_text())
    mp = json.loads((AN / 'maps' / f"{m['map']['hash']}.json").read_text())
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    dmg = defaultdict(list)  # group -> [(round, champion, amount)]
    with gzip.open(AN / d / 'events.jsonl.gz', 'rt') as f:
        for line in f:
            e = json.loads(line)
            if e['k'] in ('attack', 'cast') and 'cdmg' in e:
                for camp, amt in e['cdmg']:
                    if camp in camp_group:
                        dmg[camp_group[camp]].append((e['r'], e['a'], amt))
    out = []
    for r in chs:
        lo, hi = r['r0'], r['clear_r']
        mine = other = 0.0
        for rr, a, amt in dmg.get(r['fc_h'], []):
            if lo <= rr <= hi:
                if a == r['cid']:
                    mine += amt
                else:
                    other += amt
        out.append((r['fc_mode'], r['fc_c'], hi - r['arrive'], mine, other, r['outcome'] == 'ours', r['kind']))
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else str(Path(__file__).resolve().parents[3] / 'replays' / 'mac13-kronos-s1-choices.jsonl.gz')
    by = defaultdict(list)
    import gzip
    for l in (gzip.open(path, "rt") if path.endswith(".gz") else open(path)):
        r = json.loads(l)
        if r['fc_mode'] in 'SK' and r['fc_st'] == 0 and r['arrive'] is not None and r['clear_r'] is not None and r['clear_team'] == 0:
            by[r['game']].append(r)
    res = []
    with Pool(24) as p:
        for o in p.imap_unordered(work, list(by.items()), chunksize=8):
            res += o
    tg = 2048
    print(f'solo choices cleared by the team after our arrival: {len(res) / tg:.1f}/tg')
    for label, f in [('alone (others <10%)', lambda x: x[4] < 0.1 * (x[3] + x[4])), ('helped (others >=10%)', lambda x: x[4] >= 0.1 * (x[3] + x[4]))]:
        g = [x for x in res if f(x)]
        n = len(g)
        mean = lambda xs: sum(xs) / len(xs) if xs else float('nan')
        print(f'| {label} | {n / tg:.1f}/tg | clear priced {mean([x[1] for x in g]):.1f} | real {mean([x[2] for x in g]):.1f} '
              f'| others\' damage share {mean([x[4] / max(1, x[3] + x[4]) for x in g]):.2f} | paid {100 * mean([x[5] for x in g]):.0f}% |')
        for k in ('cluster', 'wolf', 'elk', 'golem'):
            gk = [x for x in g if x[6] == k]
            if gk:
                print(f'|   {k} | {len(gk) / tg:.1f}/tg | clear priced {mean([x[1] for x in gk]):.1f} | real {mean([x[2] for x in gk]):.1f} | paid {100 * mean([x[5] for x in gk]):.0f}% |')


if __name__ == '__main__':
    main()
