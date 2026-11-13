"""Which cells (map, our side) can take another team's win against Fish r8, and how its picks sit against ours.

    py cells.py [--rows TSV.gz ...] [--book WORK] [--repro TXT] [--out DIR]
Reads our Fish r8 games (games.jsonl: our team and Fish's per cell, which are fixed), the book host's cells
(--book: a book work dir's book_cells.json, and --repro: the host wins hostcheck.py found it repeats), and Fish's games from
big-arm's capture table (fwin's rows.json plus --rows pulls). Writes DIR/cands.json: per uncovered cell, the other
teams' wins by class:
  exact   the winner's picks are ours in order (same ids and spawn tiles: no pick forced);
  prefixK the first K picks are ours, a later one differs (forced; pick 0 unchanged for K >= 1);
  blind   pick 0 differs (forced; every opponent on the cell meets the other pick 0)."""
import argparse, collections, gzip, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GAMES = ROOT / 'research/ladder-scrims-2026-11-06/data/games.jsonl'
NAMES = ["Ryth", "Vesper Vale", "Vendetta", "Cassi & Issac", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi", "Heart of Ruin"]
IX = {n: i for i, n in enumerate(NAMES)}
FISH = '1890540d-1ffc-4847-adbf-d0d08772f268'
OURS = '547efb5b'
COLS = "match_id,created_at,kind,map,group_id,position,team_a,team_b,name_a,name_b,result_a,picks_a,picks_b,engine,rank_a,rank_b,rating_a,rating_b,replay,map_id".split(',')


def our_cells(opp='Intercontinental Fish', refset='r8'):
    """cell -> our picks, map -> the opponent's picks, cell -> {version: [results]} from our pinned games."""
    ours, theirs, res = {}, {}, collections.defaultdict(lambda: collections.defaultdict(list))
    for line in open(GAMES):
        g = json.loads(line)
        if g.get('status') != 'finished' or not g.get('opp_name', '').startswith(opp) or g.get('refset') != refset:
            continue
        cell = (g['map'], g['side'])
        ours[cell] = [IX[x] for x in g['our_picks']]
        theirs[g['map']] = [IX[x] for x in g['opp_picks']]
        res[cell][g['version']].append(g['result'])
    return ours, theirs, res


def covered(work='~/tmp-offload/rbook/ff', repro='~/tmp-offload/rbook/ff/repro1.txt'):
    """The book's cells (WORK/book_cells.json) and those left to the host (hostcheck's repro list: MAP SIDE OPP)."""
    book = {(c['map'], c['side']) for c in json.load(open(Path(work).expanduser() / 'book_cells.json'))}
    left = set()
    p = Path(repro).expanduser()
    if p.exists():
        left = {tuple(l.split()[:2]) for l in p.read_text().splitlines() if l.strip()}
    return book, left


def fish_rows(extra):
    out = {}
    base = Path('~/tmp-offload/fwin/rows.json').expanduser()
    if base.exists():
        for r in json.load(open(base)):
            out[r['match_id']] = r
    for f in extra:
        for line in gzip.open(f, 'rt'):
            p = line.rstrip('\n').split('\t')
            if len(p) != len(COLS):
                continue
            r = dict(zip(COLS, p))
            s = 'a' if r['team_a'] == FISH else 'b'
            o = 'b' if s == 'a' else 'a'
            try:
                r['f_picks'], r['op_picks'] = json.loads(r['picks_' + s]), json.loads(r['picks_' + o])
            except Exception:
                continue
            if not r['f_picks'] or not r['op_picks']:
                continue
            r['f_side'], r['opp'], r['opp_id'] = s, r['name_' + o], r['team_' + o]
            r['f_win'] = (r['result_a'] == 'win') == (s == 'a') if r['result_a'] in ('win', 'loss') else None
            out[r['match_id']] = r
    return sorted(out.values(), key=lambda r: r['created_at'])


def klass(theirs, mine):
    if theirs == mine:
        return 'exact'
    k = 0
    while k < min(len(theirs), len(mine)) and theirs[k] == mine[k]:
        k += 1
    return 'blind' if k == 0 else f'prefix{k}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', nargs='*', default=[])
    ap.add_argument('--book', default='~/tmp-offload/rbook/ff')
    ap.add_argument('--repro', default='~/tmp-offload/rbook/ff/repro1.txt')
    ap.add_argument('--out', default=str(Path.home() / 'tmp-offload/rbook-foreign'))
    a = ap.parse_args()
    ours, fish, res = our_cells()
    book, left = covered(a.book, a.repro)
    won = {c for c, v in res.items() if any('win' in r for r in v.values())}
    unc = set(ours) - book - left
    R = fish_rows(a.rows)
    print(f'{len(R)} Fish games to {R[-1]["created_at"]}; cells {len(ours)}: book {len(book)}, left to the host {len(left)}, '
          f'uncovered {len(unc)} ({len(unc & won)} with a win of ours, {len(unc - won)} without)')
    cands = collections.defaultdict(list)
    drafts = collections.Counter()
    for r in R:
        if r['opp_id'].startswith(OURS) or r['map'] not in fish:
            continue
        drafts[r['f_picks'] == fish[r['map']]] += 1
        if r['f_win'] is not False or r['f_picks'] != fish[r['map']]:
            continue
        cell = (r['map'], 'b' if r['f_side'] == 'a' else 'a')
        cands[cell].append(dict(match=r['match_id'], created=r['created_at'], kind=r['kind'], opp=r['opp'], picks=r['op_picks'],
                                klass=klass(r['op_picks'], ours[cell]), same_set=sorted(r['op_picks']) == sorted(ours[cell]), replay=r.get('replay') or ''))
    print(f"other teams' games: Fish drafted its r8 team in {drafts[True]}, another in {drafts[False]}")
    order = lambda k: (0, 0) if k == 'exact' else (2, 0) if k == 'blind' else (1, -int(k[6:]))
    for name, cs in (('all cells', set(ours)), ('uncovered', unc), ('uncovered, no win of ours', unc - won)):
        best = collections.Counter(min((g['klass'] for g in cands[c]), key=order) if cands.get(c) else 'none' for c in cs)
        print(f'{name}: best class per cell', dict(sorted(best.items(), key=lambda kv: order(kv[0]) if kv[0] != 'none' else (9, 0))))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    json.dump(dict(ours={f'{m}:{s}': p for (m, s), p in ours.items()}, fish=fish, book=sorted(book), left=sorted(left), won=sorted(won),
                   cands={f'{m}:{s}': v for (m, s), v in cands.items()}), open(out / 'cands.json', 'w'))


if __name__ == '__main__':
    main()
