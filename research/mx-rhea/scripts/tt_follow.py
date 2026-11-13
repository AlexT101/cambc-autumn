"""Follow one team's champions through a game: segments of constant (branch, farm group, claim) from the debug D
lines, merged with positions, hp, gems and events (camp hits by group, captures, recalls, shop, tributes, deaths,
enemies seen). Usage: py tt_follow.py ANALYSIS_DIR GAME_DIR TEAM [R0 R1] [--champ ID]"""
import gzip, json, sys, zipfile
from collections import defaultdict
from pathlib import Path

BATCH = Path('/home/ubuntu/wt/mx-rhea/replays/batch-20261113-142221-ab-mx-rhea-mirror-study3')


def load(root, d):
    root = Path(root); g = root / d
    meta = json.loads((g/'meta.json').read_text())
    R = json.load(gzip.open(g/'rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(g/'events.jsonl.gz', 'rt')]
    mp = json.loads((g/meta['mapFile']).resolve().read_text())
    return meta, R, ev, mp


def dlines(meta):
    """{(round, cid): (branch, farm, claim)} for both teams, plus other debug lines by (round, cid)."""
    src = None
    for s in meta['sources']:
        p = Path('/home/ubuntu/wt/mx-rhea') / s['source']
        if p.exists(): src = p; break
    D = {}; other = defaultdict(list)
    if src is None: return D, other
    z = zipfile.ZipFile(src)
    for side in 'ab':
        try: txt = z.read(f'team-{side}.stdout').decode(errors='replace')
        except KeyError: continue
        for l in txt.splitlines():
            l = l.lstrip('\x00')
            p = l.split()
            if not p: continue
            if p[0] == 'D' and len(p) >= 6:
                D[(int(p[1]), int(p[2]))] = (p[3], int(p[4]), int(p[5]))
            elif len(p) >= 3 and p[1].isdigit() and p[2].isdigit():
                other[(int(p[1]), int(p[2]))].append(l)
    return D, other


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    champ = None
    if '--champ' in sys.argv: champ = int(sys.argv[sys.argv.index('--champ') + 1]); args.remove(str(champ))
    root, d, team = args[0], args[1], int(args[2])
    r0, r1 = (int(args[3]), int(args[4])) if len(args) >= 5 else (1, 350)
    meta, R, ev, mp = load(root, d)
    D, other = dlines(meta)
    names = {c['id']: c['name'] for c in meta['champions']}
    camp_g = {c['id']: c['group'] for c in mp['camps']}
    gpos = {g['id']: g['tiles'][0] for g in mp['groups']}
    gdesc = {g['id']: f"g{g['id']}@{g['tiles'][0][0]},{g['tiles'][0][1]}({g['gems']}gm/{g['gold']}gd s{g['side']})" for g in mp['groups']}
    print(meta['map']['name'], 'winner', meta['result']['winner'], 'rounds', meta['result']['rounds'], 'gems', meta['result']['gems'])
    print('spawns', mp['spawn'], 'altars', mp['altars'])
    for g in mp['groups']:
        print(' ', gdesc[g['id']], ','.join(sorted(set(g['types']))), 'respawn', g['respawn'])
    ri = {r: i for i, r in enumerate(R['round'])}
    W, H = mp['width'], mp['height']
    block = set(map(tuple, mp['walls'])) | set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars']))
    gst = defaultdict(dict)  # group -> {round: row}
    for row in R['groups']: gst[row[1]][row[0]] = row
    def gstate(g, r):
        rows = gst.get(g, {})
        best = None
        for rr in sorted(rows):
            if rr <= r: best = rows[rr]
            else: break
        if not best: return '?'
        st = {1: 'up', 2: 'clr', 3: 'rsp'}.get(best[2], str(best[2]))
        if best[2] == 1: st += 'A' if best[6] == 1 else ''
        if best[2] == 3: st += str(best[5])
        if best[2] == 2 and best[3] in (0, 1): st += f'h{best[3]}'
        return st
    cache = {}
    def bfs_d(p, g):
        key = (tuple(p), g)
        if key in cache: return cache[key]
        goal = set(map(tuple, next(x for x in mp['groups'] if x['id'] == g)['tiles']))
        from collections import deque
        q = deque([(tuple(p), 0)]); seen_ = {tuple(p)}
        while q:
            (x, y), dd = q.popleft()
            if (x, y) in goal: cache[key] = dd; return dd
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = (x+dx, y+dy)
                    if 0 <= n[0] < W and 0 <= n[1] < H and n not in block and n not in seen_:
                        seen_.add(n); q.append((n, dd+1))
        cache[key] = -1; return -1
    evr = defaultdict(list)
    for e in ev: evr[e['r']].append(e)
    ids = [c['id'] for c in meta['champions'] if c['team'] == team and (champ is None or c['id'] == champ)]
    C = {c['id']: c for c in R['champions']}
    for cid in ids:
        c = C[cid]
        print(f'\n=== {cid} {names[cid]} (team {team})')
        seg = None
        def flush(seg):
            if not seg: return
            k, a, b, p0, p1, hp0, hp1, gm0, gm1, notes, seen = seg
            hc = defaultdict(int)
            rest = []
            for n in notes:
                if n.startswith('h') and n[1:].isdigit(): hc[n[1:]] += 1
                elif n.startswith('recallcancel:damage'): pass
                else: rest.append(n)
            ns = ' '.join(rest) + (' hits ' + ','.join(f'g{g}x{n}' for g, n in hc.items()) if hc else '')
            dist = ''
            if p0 and k[1] >= 0: dist = f' d{bfs_d(p0, k[1])}'
            if k[1] >= 0: dist += f' [{gstate(k[1], a)}>{gstate(k[1], b)}]'
            sn = ' sees ' + ','.join(f'{names[x]}{x}' for x in sorted(seen)) if seen else ''
            print(f'r{a}-{b} ({b-a+1}) {k[0]} f{k[1]}{dist} c{k[2]} {p0}->{p1} hp {hp0}->{hp1} gems {gm0}->{gm1} {ns}{sn}')
        for r in range(r0, r1 + 1):
            i = ri.get(r)
            if i is None: break
            k = D.get((r, cid), ('?', -9, -9))
            pos = (c['x'][i], c['y'][i]) if c['alive'][i] else None
            hp = int(c['hp'][i]); gm = c['gems'][i]
            notes = []
            hits = defaultdict(int)
            for e in evr[r]:
                if e.get('a') == cid:
                    if e['k'] in ('attack', 'cast') and 'camp' in e: hits[camp_g.get(e['camp'])] += 1
                    elif e['k'] in ('attack', 'cast') and 'tgt' in e and e['tgt'] != cid and names.get(e['tgt']) and meta['champions'][e['tgt']]['team'] != team: notes.append(f"hit{names.get(e['tgt'],'?')}{e['tgt']}")
                    elif e['k'] == 'recall_end': notes.append('RECALLED')
                    elif e['k'] == 'shop': notes.append('shop' + str(e.get('items')))
                    elif e['k'] == 'tribute_start': notes.append(f"TRIB{e['gems']}")
                    elif e['k'] == 'tribute_end': notes.append(f"TRIBDONE{e['gems']}")
                    elif e['k'] == 'tribute_cancel': notes.append(f"tribcancel:{e['cause']}")
                    elif e['k'] == 'recall_cancel' and e['cause'] != 'manual': notes.append(f"recallcancel:{e['cause']}")
                    elif e['k'] == 'respawn': notes.append('RESPAWN')
                if e['k'] == 'death' and e['v'] == cid: notes.append(f"DIED(by {names.get(e.get('by'), 'camp')}, bag {e['gems']})")
                if e['k'] == 'death' and e.get('by') == cid: notes.append(f"KILL{names[e['v']]}{e['v']}")
                if e['k'] == 'capture':
                    for s in e['shares']:
                        if s[0] == cid: notes.append(f"CAP g{e['g']} +{s[1]}gm{s[2]}gd")
            for g_, n in hits.items(): notes.append(f'h{g_}')
            for l in other.get((r, cid), []):
                if l.startswith(('RF', 'CREW PICK', 'PREM', 'KTRIB')) or '--all' in sys.argv:
                    notes.append('[' + l[:90] + ']')
            seen = set(c['sees'][i]) if c['sees'][i] else set()
            if seg and seg[0] == k and not any(n.startswith(('DIED', 'RECALLED', 'CAP', 'TRIB', 'shop', 'RESPAWN', 'KILL')) for n in notes):
                seg[2] = r; seg[4] = pos; seg[6] = hp; seg[8] = gm
                seg[9].extend(n for n in notes if not n.startswith('[CREW') or n not in seg[9]); seg[10] |= seen
            else:
                flush(seg)
                seg = [k, r, r, pos, pos, hp, hp, gm, gm, list(notes), set(seen)]
        flush(seg)


if __name__ == '__main__':
    main()
