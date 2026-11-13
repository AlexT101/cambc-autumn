"""Kept-promise rate of hub picks: for each HUB line (an ally's pick priced with the Prism's premium as its
collection), the team's next capture of that group within WINDOW rounds, and who got its gems.
usage: hubkept.py EXTRACT_DIR [WINDOW]"""
import gzip, json, sys, re, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

WINDOW = int(sys.argv[2]) if len(sys.argv) > 2 else 80
HUB = re.compile(rb'HUB (\d+) (\d+) g(\d+) at (\d+) (\d+) mode (\S) gems (\d+) prem (\S+) eta (-?\d+)')


def one(d):
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(meta['source'])
    except Exception:
        return None
    typ = {c['id']: c['name'] for c in meta['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    out = Counter()
    by_tile = {}
    for g in mp['groups']:
        for t in g['tiles']:
            by_tile[tuple(t)] = g['id']
    caps = [e for e in ev if e['k'] == 'capture']
    for side, name in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
        if meta['teams'][side]['name'] != 'phb-hub':
            continue
        if not any(typ[c] == 'Prism' and team[c] == side for c in typ):
            continue
        out['games'] += 1
        seen = set()
        for m in HUB.finditer(z.read(name)):
            r, gx, gy = int(m[1]), int(m[4]), int(m[5])
            gid = by_tile.get((gx, gy))
            if gid is None:
                out['nogroup'] += 1
                continue
            cap = next((e for e in caps if e['g'] == gid and r <= e['r'] <= r + WINDOW and e['team'] == side), None)
            key = (gid, cap['r'] if cap else -r)
            if key in seen:
                out['dup'] += 1
                continue
            seen.add(key)
            out['picks'] += 1
            out['mode_' + m[6].decode()] += 1
            if not cap:
                # Taken by the enemy, or not captured in the window.
                enemy = next((e for e in caps if e['g'] == gid and r <= e['r'] <= r + WINDOW), None)
                out['enemy' if enemy else 'none'] += 1
                continue
            gems = sum(gm for cid, gm, gd in cap['shares'])
            pg = sum(gm for cid, gm, gd in cap['shares'] if typ[cid] == 'Prism')
            out['captured'] += 1
            out['gems'] += gems
            out['prism_gems'] += pg
            out['kept' if pg * 2 >= gems and gems > 0 else 'broken'] += 1
    return out


if __name__ == '__main__':
    dirs = [p.parent for p in Path(sys.argv[1]).glob('*/meta.json')]
    tot = Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one, [str(x) for x in dirs], chunksize=8):
            if r:
                tot.update(r)
    n = max(1, tot['games'])
    print(f"{tot['games']} cand team-games with a Prism; hub picks {tot['picks']} ({tot['picks'] / n:.1f} a game), dup lines {tot['dup']}")
    print('modes', {k[5:]: v for k, v in tot.items() if k.startswith('mode_')})
    p = max(1, tot['picks'])
    print(f"captured by us {tot['captured']} ({tot['captured'] / p:.0%}), by enemy {tot['enemy']}, none {tot['none']}")
    print(f"kept (Prism took >= half): {tot['kept']} = {tot['kept'] / p:.0%} of picks, {tot['kept'] / max(1, tot['captured']):.0%} of our captures")
    print(f"gems of our captures to Prism: {tot['prism_gems']} / {tot['gems']} = {tot['prism_gems'] / max(1, tot['gems']):.0%}")
