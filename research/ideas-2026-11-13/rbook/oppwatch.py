"""Has Fish or Mite changed? Reads the scheduler's hourly opponent checks (games against the current, unpinned
opponent) and compares each game's replay byte for byte with (a) our pinned games against the reference version
(--refset) in the same cell by the same version of ours, and (b) the previous check with the same version of ours.
Games are deterministic, so any difference means the opponent changed (or the engine did).

    py oppwatch.py [--opp Mite] [--refset r8] [--since 2026-11-12T12] [--json] [--book-version N --book WORK [--book-cells F]]
Last line: CURRENT == REFSET | CHANGED at <time> | UNKNOWN (no comparable game).
--book-version/--book: games of the book bot (version N) on the book's cells (WORK/book_cells.json) must replay the
recorded game (WORK/raw/KEY.repl26a) round for round while the opponent is unchanged; each check group's book games are
compared with cmp.mjs ("book same/diverged"), which works from the first check of a new book version.
--book-cells: the version's own cells instead of WORK/book_cells.json (which follows the latest rebuild): any file
naming the entry keys, such as the uploaded bot's src/book/book_data.h or its verify manifest."""
import argparse, collections, hashlib, json, subprocess, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GAMES = ROOT / 'research/ladder-scrims-2026-11-06/data/games.jsonl'
_h = {}


def rhash(g):
    p = g.get('replay')
    if not p or not (ROOT / p).exists():
        return None
    if p not in _h:
        with zipfile.ZipFile(ROOT / p) as z:
            n = [x for x in z.namelist() if x.endswith('.repl26a')]
            _h[p] = hashlib.sha1(z.read(n[0])).hexdigest()[:10] if n else None
    return _h[p]


def book_divergence(g, recorded, plain=False):
    """First differing round index of a live book game against its recorded game, -1 if none, None if unreadable."""
    p = g.get('replay')
    if not p or not (ROOT / p).exists() or not recorded.exists():
        return None
    with zipfile.ZipFile(ROOT / p) as z, tempfile.NamedTemporaryFile(suffix='.repl26a') as t:
        n = [x for x in z.namelist() if x.endswith('.repl26a')]
        if not n:
            return None
        t.write(z.read(n[0])); t.flush()
        cmp = ['cmp2.mjs', g['side']] if plain else ['cmp.mjs']  # a plain-priority book differs in our priority values only
        r = subprocess.run(['node', str(Path(__file__).parent / cmp[0]), str(recorded), t.name] + cmp[1:], capture_output=True, text=True)
    try:
        v = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None
    return -1 if v['firstDiff'] == -1 and v['finalSame'] else max(v['firstDiff'], 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--opp', default='Intercontinental Fish')
    ap.add_argument('--refset', default='r8')
    ap.add_argument('--since', default='2026-11-12T12')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--book-version', type=int)
    ap.add_argument('--book', help='rbuild work dir of the book the version plays')
    ap.add_argument('--book-cells', help="a file naming the version's entry keys (its book_data.h or verify manifest)")
    ap.add_argument('--book-plain', action='store_true', help='the book plays plain priorities (build_book.py --prio plain)')
    a = ap.parse_args()
    book = {}
    if a.book_version and a.book:
        w = Path(a.book).expanduser()
        if a.book_cells:
            import re
            keys = sorted(set(re.findall(r'([0-9A-Za-z_]+(?:-[0-9A-Za-z_]+)*?-[ab]-v\d+-[0-9a-f]{12})', Path(a.book_cells).expanduser().read_text())))
            cells = []
            for k in keys:
                m = re.match(r'^(.+)-([ab])-v\d+-', k)
                cells.append(dict(key=k, map=m.group(1), side=m.group(2)))
        else:
            cells = json.loads((w / 'book_cells.json').read_text())
        book = {(c['map'], c['side']): w / 'raw' / f"{c['key']}.repl26a" for c in cells}
        missing = [str(p) for p in book.values() if not p.exists()]
        if missing:
            print(f'warning: {len(missing)} recorded replays missing, e.g. {missing[0]}')
    ref, cur = {}, collections.defaultdict(list)
    for line in open(GAMES):
        g = json.loads(line)
        if g.get('status') != 'finished' or not g['opp_name'].startswith(a.opp):
            continue
        cell = (g['version'], g['map'], g['side'])
        if g.get('refset') == a.refset:
            ref.setdefault(cell, g)
        elif g.get('refset') is None and g.get('pin') == 'none' and g['created'] >= a.since:
            cur[g['group']].append(g)
    groups = sorted(cur.values(), key=lambda gs: gs[0]['created'])
    prev = {}
    rows = []
    for gs in groups:
        same_ref = diff_ref = same_prev = diff_prev = book_same = book_diff = 0
        for g in gs:
            cell = (g['version'], g['map'], g['side'])
            if book and g['version'] == a.book_version and (g['map'], g['side']) in book:
                d = book_divergence(g, book[(g['map'], g['side'])], a.book_plain)
                if d is not None:
                    if d < 0: book_same += 1
                    else: book_diff += 1
            h = rhash(g)
            if h is None:
                continue
            if cell in ref and rhash(ref[cell]):
                if rhash(ref[cell]) == h: same_ref += 1
                else: diff_ref += 1
            if cell in prev:
                if prev[cell] == h: same_prev += 1
                else: diff_prev += 1
            prev[cell] = h
        rows.append(dict(time=gs[0]['created'][:16], version=gs[0]['version'], games=len(gs), same_ref=same_ref, diff_ref=diff_ref,
                         same_prev=same_prev, diff_prev=diff_prev, book_same=book_same, book_diff=book_diff))
    last_change = next((r['time'] for r in reversed(rows) if r['diff_prev']), None)
    stable = 0
    for r in reversed(rows):
        if r['diff_prev']:
            break
        stable += r['same_prev'] > 0
    latest = rows[-1] if rows else None
    if latest and latest['book_diff']:
        verdict = 'CHANGED'
    elif not latest or latest['same_ref'] + latest['diff_ref'] + latest['book_same'] == 0:
        verdict = 'UNKNOWN'
    else:
        verdict = 'SAME' if latest['diff_ref'] == 0 else 'CHANGED'
    out = dict(rows=rows, verdict=verdict, last_change=last_change, stable_checks=stable, latest=latest and latest['time'])
    if a.json:
        print(json.dumps(out))
        return
    for r in rows:
        print(f"{r['time']} v{r['version']} games {r['games']}: vs {a.refset} same {r['same_ref']} diff {r['diff_ref']} | vs previous check same {r['same_prev']} diff {r['diff_prev']}"
              + (f" | book same {r['book_same']} diverged {r['book_diff']}" if r['book_same'] + r['book_diff'] else ''))
    msg = {'SAME': f'CURRENT == {a.refset}', 'CHANGED': f'CURRENT != {a.refset}', 'UNKNOWN': f'UNKNOWN against {a.refset} (no comparable game)'}[verdict]
    print(f"{msg}; last change seen between checks: {last_change or 'none'}; unchanged over the last {stable} check(s) (latest {out['latest']})")


if __name__ == '__main__':
    main()
