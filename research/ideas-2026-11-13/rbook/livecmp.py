"""Did a live book version replay its recordings? Every finished game of --version on a book cell, pinned or not,
against the entry's recorded replay (oppwatch.py reads only the unpinned hourly checks).

    py livecmp.py --version 121 --book ~/tmp-offload/rbook/prio --plain [--opp "Intercontinental Fish"] [--bot variants/BOT]
--book: the rbuild work dir (raw/KEY.repl26a; book_cells.json unless --bot names the uploaded bot, whose
book_data.h then gives the keys). --plain: a plain-priority book (cmp2.mjs: our priority values left out).
Prints counts by (same | diverged | unreadable, result) and each diverged game with its first differing round."""
import argparse, collections, concurrent.futures as cf, json, re
from pathlib import Path

import oppwatch as o

ap = argparse.ArgumentParser()
ap.add_argument('--version', type=int, required=True)
ap.add_argument('--book', required=True)
ap.add_argument('--bot')
ap.add_argument('--opp', default='')
ap.add_argument('--plain', action='store_true')
ap.add_argument('--cells', help='only these cells: a JSON list of [map, side]')
ap.add_argument('--refset', help="only games against this refset ('none': the unpinned opponent checks)")
a = ap.parse_args()
w = Path(a.book).expanduser()
if a.bot:
    keys = re.findall(r'^  \{0x.*// (\S+)$', (o.ROOT / 'bots' / a.bot / 'src/book/book_data.h').read_text(), re.M)
else:
    keys = [c['key'] for c in json.loads((w / 'book_cells.json').read_text())]
book = collections.defaultdict(list)  # a cell can hold one entry an opponent
for k in keys:
    m = re.match(r'^(.+)-([ab])-v\d+-', k)
    book[(m.group(1), m.group(2))].append(k)
cells = json.loads(Path(a.cells).expanduser().read_text()) if a.cells else None
games = []
for line in open(o.GAMES):
    g = json.loads(line)
    if g.get('version') == a.version and g.get('status') == 'finished' and g['opp_name'].startswith(a.opp) and (g['map'], g['side']) in book:
        if a.cells and [g['map'], g['side']] not in cells:
            continue
        if a.refset and (g.get('refset') or 'none') != a.refset:
            continue
        games.append(g)


def one(g):
    return g, o.cell_divergence(g, [w / 'raw' / f'{k}.repl26a' for k in book[(g['map'], g['side'])]], a.plain)


res, bad = collections.Counter(), []
with cf.ThreadPoolExecutor(16) as ex:
    for g, d in ex.map(one, games):
        kind = 'same' if d == -1 else 'unreadable' if d is None else 'diverged'
        res[(g['opp_name'][:22], g.get('refset'), kind, g['result'])] += 1
        if kind == 'diverged':
            bad.append((g['map'], g['side'], g['opp_name'][:12], g.get('refset') or 'none', g.get('created', '')[:16], f'round {d}', g['result']))
for k, v in sorted(res.items(), key=str):
    print(*k, v)
for b in sorted(bad):
    print('  diverged', *b)
