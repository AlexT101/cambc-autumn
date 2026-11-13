"""Writes rbuild.py's --extra list for other teams' wins: "REPLAY OUR_SIDE KEY MAP" a line.

    py extra.py CLASS[,CLASS...] OUT.tsv [--cells uncovered|all] [--per-cell N]
CLASS: exact, prefix1.., blind, or forced (every class but exact). Reads cells.py's cands.json and the replays on disk
(~/tmp-offload/fwin/dl, ~/tmp-offload/rbook-foreign/dl). Keys are MAP-SIDE-v900-TEAM-MATCH12 for exact entries (v901
for forced ones: rbuild --force-versions 901), so the book's tools read the cell from them as from our own."""
import argparse, json, os, re
from pathlib import Path

HOME = Path.home() / 'tmp-offload'
DIRS = [HOME / 'rbook-foreign/dl', HOME / 'fwin/dl']


def replay(match):
    for d in DIRS:
        if (d / f'{match}.zip').exists():
            return d / f'{match}.zip'
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('classes')
    ap.add_argument('out')
    ap.add_argument('--cells', default='uncovered')
    ap.add_argument('--per-cell', type=int, default=3)
    ap.add_argument('--cands', default=str(HOME / 'rbook-foreign/cands.json'))
    a = ap.parse_args()
    C = json.load(open(a.cands))
    skip = {tuple(x) for x in C['book']} | {tuple(x) for x in C['left']} if a.cells == 'uncovered' else set()
    want = set(a.classes.split(','))
    n = 0
    with open(a.out, 'w') as f:
        for cell, games in sorted(C['cands'].items()):
            m, s = cell.split(':')
            if (m, s) in skip:
                continue
            k = 0
            for g in games:
                forced = g['klass'] != 'exact'
                if not (g['klass'] in want or (forced and 'forced' in want)) or k >= a.per_cell:
                    continue
                z = replay(g['match'])
                if not z:
                    continue
                team = re.sub(r'[^a-z0-9]', '', g['opp'].lower())[:8]
                f.write(f"{z} {s} {m}-{s}-v{901 if forced else 900}-{team}-{g['match'][-12:]} {m}\n")
                k += 1
                n += 1
    print(n, 'games')


if __name__ == '__main__':
    main()
