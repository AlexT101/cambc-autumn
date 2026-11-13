"""Picks one r8 win of another team per uncovered cell for rbuild's --extra, exact draft first, then forced.

    py forced.py WORK [--cands CANDS.json] [--cells nowin|uncovered]
Extracts every other-team win on disk for the cells (WORK/stage), scores each with r8check's priority signature, and
writes WORK/extra.tsv (the best r8 game per cell: exact, then the longest prefix of our picks, then the shortest game)
and WORK/classes.json (key -> class, the pick at which our draft first departs from 525's, Fish's picks seen by then,
and whether Mite r9's picks on the map share that prefix, i.e. whether Mite meets the forced pick too).
Exact entries are keyed v900, forced ones v901 (rbuild --force-versions 901)."""
import argparse, concurrent.futures as cf, json, re, subprocess, zipfile
from pathlib import Path

from r8check import sig

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXTRACT = HERE.parent / 'rbook/extract.mjs'
HOME = Path.home() / 'tmp-offload'
DIRS = [HOME / 'rbook-foreign/dl', HOME / 'fwin/dl']
NAMES = ["Ryth", "Vesper Vale", "Vendetta", "Cassi & Issac", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi", "Heart of Ruin"]
R8 = 0.9  # r8 games score 1.0, other Fish versions ~0.13


def replay(match):
    return next((d / f'{match}.zip' for d in DIRS if (d / f'{match}.zip').exists()), None)


def depart(k):
    return 0 if k == 'blind' else 99 if k == 'exact' else int(k[6:])


def mite_picks():
    out = {}
    for line in open(ROOT / 'research/ladder-scrims-2026-11-06/data/games.jsonl'):
        g = json.loads(line)
        if g.get('refset') == 'r9' and g.get('opp_name', '').startswith('Mite') and g.get('status') == 'finished':
            out[g['map']] = [NAMES.index(x) for x in g['opp_picks']]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('--cands', default=str(HOME / 'rbook-foreign/c2/cands.json'))
    ap.add_argument('--cells', default='nowin', choices=['nowin', 'uncovered'])
    ap.add_argument('--jobs', type=int, default=16)
    a = ap.parse_args()
    W = Path(a.work).expanduser()
    (W / 'stage/ent').mkdir(parents=True, exist_ok=True)
    (W / 'stage/raw').mkdir(exist_ok=True)
    C = json.load(open(a.cands))
    skip = {tuple(x) for x in C['book']} | {tuple(x) for x in C['left']}
    if a.cells == 'nowin':
        skip |= {tuple(x) for x in C['won']}
    jobs = []
    for cell, games in C['cands'].items():
        m, s = cell.split(':')
        if (m, s) in skip:
            continue
        for g in games:
            z = replay(g['match'])
            if z:
                team = re.sub(r'[^a-z0-9]', '', g['opp'].lower())[:8]
                key = f"{m}-{s}-v{900 if g['klass'] == 'exact' else 901}-{team}-{g['match'][-12:]}"
                jobs.append(dict(key=key, zip=str(z), map=m, side=s, klass=g['klass'], match=g['match'], opp=g['opp'], picks=g['picks']))

    def one(j):
        ent = W / 'stage/ent' / f"{j['key']}.json"
        if not ent.exists():
            raw = W / 'stage/raw' / f"{j['key']}.repl26a"
            with zipfile.ZipFile(j['zip']) as z:
                raw.write_bytes(z.read([n for n in z.namelist() if n.endswith('.repl26a')][0]))
            tmp = ent.with_suffix('.tmp')
            r = subprocess.run(['node', str(EXTRACT), str(tmp), f"{raw}:{j['side']}:{j['key']}"], capture_output=True, text=True)
            if r.returncode or not tmp.exists():
                return j, None
            tmp.rename(ent)
        e = json.load(open(ent))
        return j, dict(sig=sig(e)[0], rounds=e['rounds'], outcome=e['outcome'], problems=e['problems'][:2])

    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(one, jobs))
    fish, mite = C['fish'], mite_picks()
    best, rows = {}, []
    for j, r in res:
        ok = r is not None and r['sig'] is not None and r['sig'] >= R8 and not r['problems']
        rows.append(dict(j, **(r or {}), r8=ok))
        if not ok:
            continue
        c = (j['map'], j['side'])
        rank = (-depart(j['klass']), r['rounds'])
        if c not in best or rank < best[c][0]:
            best[c] = (rank, j, r)
    classes = {}
    with open(W / 'extra.tsv', 'w') as f:
        for (m, s), (_, j, r) in sorted(best.items()):
            f.write(f"{W / 'stage/raw' / (j['key'] + '.repl26a')} {s} {j['key']} {m}\n")
            k = depart(j['klass'])
            fp, mp = fish[m], mite.get(m)
            classes[j['key']] = dict(cell=f'{m}:{s}', klass=j['klass'], departs_at_pick=None if k == 99 else k, fish_picks_seen=fp[:k] if k < 99 else fp,
                                     ours=C['ours'][f'{m}:{s}'], theirs=j['picks'], fish=fp, mite_r9=mp,
                                     mite_meets_forced=None if k == 99 or mp is None else mp[:k] == fp[:k], opp=j['opp'], match=j['match'], rounds=r['rounds'])
    json.dump(classes, open(W / 'classes.json', 'w'), indent=1)
    json.dump(rows, open(W / 'stage/scored.json', 'w'), indent=1)
    cells = {(j['map'], j['side']) for j in jobs}
    print(f'{len(jobs)} games on disk over {len(cells)} cells; r8 {sum(x["r8"] for x in rows)}; cells with an r8 win {len(best)}')


if __name__ == '__main__':
    main()
