"""Chooses which entries a book keeps when the bundle limit binds.

    py pick_entries.py WORK --blob BYTES --opp "Intercontinental Fish:r8" --opp Mite:r9 > WORK/keys.txt

Reads WORK/sizes.out (rbuild's "cell MAP SIDE KEY BYTES" lines of a build without a limit), WORK/fp_book.json and
games.jsonl. An entry is worth the chance the host loses its cell unaided: 1 - (w + 1) / (n + 2) over the n of our
versions that played the cell against that opponent, w of them winning. Entries are kept by worth per byte (streams plus
fingerprints) until --blob bytes. The dropped ones are listed on stderr.
--drop TAG:MAP:SIDE,..: entries left out whatever their worth (a cell whose forced pick makes that opponent's entry
unreachable). --balance: the last --opp's worth is scaled (0.5 to 2) to bring the two opponents' kept counts as close
as the limit allows (the user wants Fish and Mite coverage roughly level)."""
import argparse, collections, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ap = argparse.ArgumentParser()
ap.add_argument('work')
ap.add_argument('--blob', type=int, required=True)
ap.add_argument('--opp', action='append', required=True)
ap.add_argument('--versions', default='117,118,119')
ap.add_argument('--drop', default='')
ap.add_argument('--balance', action='store_true')
a = ap.parse_args()
work = Path(a.work).expanduser()
versions = {int(v) for v in a.versions.split(',')}
opps = [(o.partition(':')[0], o.partition(':')[2], o.partition(':')[0].split()[-1].lower()) for o in a.opp]
res = collections.defaultdict(dict)  # (tag, map, side) -> version -> won
for line in open(ROOT / 'research/ladder-scrims-2026-11-06/data/games.jsonl'):
    g = json.loads(line)
    if g.get('status') != 'finished' or g.get('version') not in versions:
        continue
    for name, ref, tag in opps:
        if g['opp_name'].startswith(name) and g.get('refset') == ref:
            res[(tag, g['map'], g['side'])].setdefault(g['version'], g['result'] == 'win')
tags = {c['key']: c['opp'] for c in json.loads((work / 'book_cells.json').read_text())}
fps = json.loads((work / 'fp_book.json').read_text())
ents = []
lines = {}  # a key recorded in the same run has a line from each of its builds: the last is the book's
for line in open(work / 'sizes.out'):
    p = line.split()
    if len(p) == 5 and p[0] == 'cell' and p[3] in tags:
        lines[p[3]] = p
for p in lines.values():
    if True:
        key, size = p[3], int(p[4]) + sum((len(n) + 1) // 2 for n in fps[p[3]])
        r = res[(tags[key], p[1], p[2])]
        worth = 1 - (sum(r.values()) + 1) / (len(r) + 2)
        ents.append((worth / size, worth, size, key, tags[key]))
drop = {tuple(x.split(':')) for x in a.drop.split(',') if x}
out = [e for e in ents if (e[4], *re.match(r'^(.+)-([ab])-v\d+-', e[3]).groups()) in drop]
ents = [e for e in ents if e not in out]
by = lambda es, t: sum(1 for e in es if e[4] == t)


def pick(scale):
    total, kept, dropped = 0, [], []
    for e in sorted(ents, key=lambda e: -e[0] * (scale if e[4] == opps[-1][2] else 1)):
        if total + e[2] <= a.blob:
            total += e[2]
            kept.append(e)
        else:
            dropped.append(e)
    return total, kept, dropped


scales = [0.5 + 0.05 * i for i in range(31)] if a.balance else [1.0]
gap = lambda r: abs(by(r[1], opps[0][2]) - by(r[1], opps[-1][2]))
scale = min(scales, key=lambda x: (gap(pick(x)), abs(x - 1)))
total, kept, dropped = pick(scale)
print(f'scale {scale:.2f}; left out by --drop: {len(out)}', file=sys.stderr)
for e in sorted(kept, key=lambda e: e[3]):
    print(e[3])
print(f'kept {len(kept)} entries, {total} bytes; dropped {len(dropped)}, expected cells lost {sum(e[1] for e in dropped):.1f}', file=sys.stderr)
for _, _, tag in opps:
    print(f'  {tag}: kept {by(kept, tag)}, dropped {by(dropped, tag)} (expected cells lost {sum(e[1] for e in dropped if e[4] == tag):.1f})', file=sys.stderr)
for e in sorted(dropped, key=lambda e: e[3]):
    print(f'  dropped {e[4]} {e[3]} {e[2]} bytes, worth {e[1]:.2f}', file=sys.stderr)
