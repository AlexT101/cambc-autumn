"""Recall-to-farm trips (RFCHOOSE ... RFLAND) whose farm group changes within 5 turns of landing: the rounds the recall
cost against walking from where it started to the group finally chosen (walk from the recall tile vs channel + walk
from the landing tile). Usage: py tt_recall.py ANALYSIS_DIR"""
import gzip, json, sys, zipfile
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from tt_pursuit import fields, ROOT


def game(args):
    d, src = args
    g = ROOT / 'replays/ana-mirror' / d
    try:
        meta = json.loads((g/'meta.json').read_text())
        ev = [json.loads(l) for l in gzip.open(g/'events.jsonl.gz', 'rt')]
        mp = json.loads((g/meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(g/'rounds.json.gz'))
        z = zipfile.ZipFile(ROOT / src)
    except Exception:
        return None
    winner = meta['result']['winner']
    team = {c['id']: c['team'] for c in meta['champions']}
    name = {c['id']: c['name'] for c in meta['champions']}
    D = {}; lands = []
    for side in 'ab':
        try: txt = z.read(f'team-{side}.stdout').decode(errors='replace')
        except KeyError: continue
        for l in txt.splitlines():
            p = l.lstrip('\x00').split()
            if not p: continue
            if p[0] == 'D' and len(p) >= 6: D[(int(p[1]), int(p[2]))] = int(p[4])
            elif p[0] == 'RFLAND' and len(p) >= 4: lands.append((int(p[1]), int(p[2]), int(p[3])))
    F = fields(mp)
    rend = {}
    for e in ev:
        if e['k'] == 'recall_end': rend[(e['a'], e['r'])] = (tuple(e['f']), tuple(e['to']))
    ri = {r: i for i, r in enumerate(R['round'])}
    C = {c['id']: c for c in R['champions']}
    out = []
    for rl, cid, gl in lands:
        if rl > 600: continue
        fe = rend.get((cid, rl)) or rend.get((cid, rl - 1))
        if not fe: continue
        f, to = fe
        later = [D.get((rr, cid), -9) for rr in range(rl, rl + 6)]
        new = next((x for x in later if x >= 0 and x != gl), None)
        if new is None or new not in F:
            out.append((team[cid] == winner, name[cid], 'kept', 0, 0)); continue
        a = F[new][f[0]][f[1]]; b = F[new][to[0]][to[1]]
        if a < 0 or b < 0: continue
        # rounds lost: channel (5 turn ends, one of them the arrival turn is a full turn: count 4) + walk from landing - walk from start
        lost = 4 + b - a
        i0 = ri.get(rl - 6)
        if i0 is not None and C[cid]['hp'][i0] < 0.6 * C[cid]['maxHp'][i0]: lost = min(lost, 0)  # also a heal trip
        orig = F[gl][f[0]][f[1]] if gl in F else -1
        out.append((team[cid] == winner, name[cid], 'switched', lost, orig))
    return out


if __name__ == '__main__':
    ana = sys.argv[1]
    idx = json.load(open(Path(ana)/'index.json'))['games']
    seen = {}
    for r in idx:
        if r['dir'] not in seen and Path(ROOT/r['source']).exists(): seen[r['dir']] = r['source']
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, list(seen.items()), chunksize=4):
            if o: rows.extend(o)
    nTG = 2 * len(seen)
    C = Counter((w, k) for w, n, k, l, o in rows)
    print('landings r<=600 per team-game:', {f"{'W' if w else 'L'} {k}": round(v / (nTG / 2), 2) for (w, k), v in sorted(C.items())})
    sw = [r for r in rows if r[2] == 'switched']
    pos = [r for r in sw if r[3] > 0]
    print(f'switched: {len(sw)}; recall cost more than walking from its start tile to the new group in {len(pos)} '
          f'({len(pos)/max(1,len(sw)):.0%}), mean excess {sum(r[3] for r in pos)/max(1,len(pos)):.1f} rounds; '
          f'excess rounds per team-game W {sum(r[3] for r in pos if r[0])/(nTG/2):.1f} L {sum(r[3] for r in pos if not r[0])/(nTG/2):.1f}')
    print('by champion (switched, excess>0):', Counter(r[1] for r in pos).most_common(8))
