"""Print one Fish actor's turns over a round window from the engage rows (ENGAGE.md), one line a turn.

  python3 tools/fish/engage_show.py COHORT SHA16 ACTOR R0 R1 [--all]   (--all: every Fish actor)

Columns: round, actor, type, tile -> end tile, hp%, gems, gold, priority level L written (or start),
visible enemies (type@distance hp%, '*' recalling, 'T' tribute), allies in sight (type@d), memory of
unseen enemies (type@d age), actions (h=hit champion, c=camp, R=recall kept/started, X=cancel,
D=dash, S=submit, $=shop).
"""
import argparse
import gzip
import json
from pathlib import Path

NAMES = ['Ryth', 'Ves', 'Vend', 'Cassi', 'Issac', 'Stel', 'Prism', 'Marc', 'Wil', 'Ren', 'Varg', 'Tavi', 'HoR']


def load(cohort, game):
    with gzip.open(Path('replays/fish-engage') / f'{cohort}-rows-v1.jsonl.gz', 'rt') as f:
        for line in f:
            if line[:200].find(f'"game":"{game}"') >= 0:
                return json.loads(line)
    raise SystemExit('game not found')


def line(aid, r):
    x, y = r.get('x'), r.get('y')
    if not x:
        return f"r{r['r']:4d} a{aid:<2} dead"
    E = ' '.join(f"{NAMES[e['type']]}@{e['d']}:{100 * e['hp'] / e['mhp']:.0f}{'*' if e['ch'] == 1 else 'T' if e['ch'] == 2 else ''}"
                 for e in x['E'])
    A = ' '.join(f"{NAMES[a['type']]}@{a['d']}" for a in x['A'])
    M = ' '.join(f"{NAMES[m['type']]}@{m['d']}~{r['r'] - m['r']}" for m in x['M'] if m.get('alive'))
    acts = ''
    end = '?'
    L = x['Lstart']
    if y:
        acts = ('h' if y['hitc'] else '') + ('c' if y['camp'] else '') + ('D' if y['dash'] else '') + \
               ('X' if y['cancel'] else '') + ('R' if y['recall'] else '') + ('S' if y['submit'] else '') + ('$' if y['shop'] else '')
        end = f"({y['ex']},{y['ey']})"
        if y['L'] is not None:
            L = f"{y['L']}w"
    return (f"r{r['r']:4d} a{aid:<2} {NAMES[x['type']]:5} ({x['x']},{x['y']})->{end:9} hp{100 * x['hp'] / x['mhp']:3.0f} g{x['gems']:<3} "
            f"$ {x['gold']:<4} hw{x['hw']:<3} L{L!s:5} ch{x['ch']}{x['ct']} | E[{E}] A[{A}] M[{M}] {acts}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cohort'); p.add_argument('game'); p.add_argument('actor', type=int)
    p.add_argument('r0', type=int); p.add_argument('r1', type=int)
    p.add_argument('--all', action='store_true')
    a = p.parse_args()
    g = load(a.cohort, a.game)
    ids = sorted(int(k) for k in g['actors']) if a.all else [a.actor]
    out = []
    for i in ids:
        for r in g['actors'][str(i)]:
            if a.r0 <= r['r'] <= a.r1:
                out.append((r['r'], i, line(i, r)))
    print(g['map'], 'side', g['side'], 'roster', [(c['id'], NAMES[c['type']], c['team']) for c in g['roster']])
    for _, _, s in sorted(out):
        print(s)


if __name__ == '__main__':
    main()
