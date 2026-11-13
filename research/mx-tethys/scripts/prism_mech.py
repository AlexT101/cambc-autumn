"""Early first-Prism deaths (both teams drafted Prism, death round <= 300): per-game features of the 40 rounds before
the death, for mechanism classification. Writes JSONL rows.

    py research/mx-tethys/scripts/prism_mech.py ANALYSIS_ROOT BATCH_NAME OUT.jsonl [--max-round 300]
"""
import gzip, json, re, sys, zipfile
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

WT = Path('/home/ubuntu/wt/mx-tethys')
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
MAXR = 300


def walkfield(mp, sp):
    W, H = mp['width'], mp['height']
    block = {tuple(p) for k in ('walls', 'holes', 'altars') for p in mp[k]}
    INF = 10**6
    dist = [[INF] * H for _ in range(W)]
    q = deque()
    for x in range(sp['minX'], sp['maxX'] + 1):
        for y in range(sp['minY'], sp['maxY'] + 1):
            dist[x][y] = 0; q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in block and dist[nx][ny] == INF:
                    dist[nx][ny] = dist[x][y] + 1; q.append((nx, ny))
    return dist


def one(dd):
    try:
        m = json.loads((dd / 'meta.json').read_text())
        mp = json.loads((dd / m['mapFile']).resolve().read_text())
        R = json.load(gzip.open(dd / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(WT / m['source'])
    except Exception:
        return None
    names = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    prisms = {team[i]: i for i in names if names[i] == 'Prism'}
    if len(prisms) != 2: return None
    first = next((e for e in ev if e['k'] == 'death' and e['v'] in prisms.values()), None)
    if not first or first['r'] > MAXR: return None
    br, grp = {}, {}
    for name in ('team-a.stdout', 'team-b.stdout'):
        try: data = z.read(name)
        except KeyError: continue
        for r, cid, b, g, cl in D_RE.findall(data):
            br[(int(r), int(cid))] = b.decode(); grp[(int(r), int(cid))] = int(g)
    v = first['v']; t = team[v]; o = prisms[1 - t]; D = first['r']
    rix = {r: i for i, r in enumerate(R['round'])}
    C = {c['id']: c for c in R['champions']}
    sp = mp['spawn']
    home = walkfield(mp, sp[t])
    def pos(c, r):
        i = rix.get(r)
        if i is None or not C[c]['alive'][i] or C[c]['x'][i] is None: return None
        return (C[c]['x'][i], C[c]['y'][i])
    allies = [c for c in names if team[c] == t and c != v]
    enemies = [c for c in names if team[c] != t]
    # Rounds the victim saw (or was seen by) an enemy, over the last 40.
    rows = []
    for r in range(max(1, D - 40), D + 1):
        i = rix.get(r)
        if i is None: continue
        vp = pos(v, r)
        if vp is None: continue
        sees = [x for x in (C[v]['sees'][i] or []) if team.get(x) != t]
        seenby = [x for x in (C[v]['seenBy'][i] or []) if team.get(x) != t]
        en8 = [c for c in enemies if (p := pos(c, r)) and cheb(p, vp) <= 8]
        al8 = [c for c in allies if (p := pos(c, r)) and cheb(p, vp) <= 8]
        ald = sorted(cheb(p, vp) for c in allies if (p := pos(c, r)))
        end = sorted(cheb(p, vp) for c in enemies if (p := pos(c, r)))
        rows.append(dict(r=r, p=vp, hp=C[v]['hp'][i] / max(1, C[v]['maxHp'][i]), br=br.get((r, v), '?'), g=grp.get((r, v)),
                         sees=sees, seenby=seenby, en8=len(en8), al8=len(al8), ald=ald, end=end, home=home[vp[0]][vp[1]],
                         turn=C[v]['turn'][i], gems=C[v]['gems'][i], foc=C[v]['foc'][i],
                         ofoc=C[o]['foc'][i] if C[o]['alive'][i] else None,
                         albr=[br.get((r, c), '?') for c in allies]))
    if not rows: return None
    # Contact: the last unbroken run (gaps <= 2 rounds) of rounds where an enemy champion was in the victim's sight.
    contact = None; gap = 0
    for row in reversed(rows):
        if row['sees']:
            contact = row['r']; gap = 0
        else:
            gap += 1
            if gap > 2 and contact is not None: break
    stuns = []  # (round, caster) of stuns landing on the victim in the last 40
    dmg = Counter(); dmg_by = Counter()
    for e in ev:
        if D - 40 <= e['r'] <= D and e['k'] in ('cast', 'attack'):
            if v in (e.get('stun') or []): stuns.append((e['r'], names[e['a']], e['a']))
            for tid, amt in (e.get('dmg') or []):
                if tid == v and e['r'] >= D - 15: dmg[names[e['a']]] += amt; dmg_by[e['a']] += 1
    stunned_turns = [row['r'] for row in rows if row['turn'] == 5]
    # Final engagement: champion hits on the victim with no quiet gap longer than one ability cooldown (8 rounds).
    hits = sorted((e['r'], e['a']) for e in ev if D - 40 <= e['r'] <= D and e['k'] in ('cast', 'attack')
                  and team.get(e.get('a')) != t and (any(tid == v for tid, _ in e.get('dmg') or []) or v in (e.get('stun') or [])))
    fh = None
    for r_, a_ in reversed(hits):
        if fh is not None and fh[0] - r_ > 8: break
        fh = (r_, a_)
    rowat = {row['r']: row for row in rows}
    fhrow = rowat.get(fh[0] - 1) or rowat.get(fh[0]) if fh else None
    blind = None
    if fh:
        seen_before = set()
        for rr in (fh[0] - 1, fh[0]):
            if rr in rowat: seen_before |= set(rowat[rr]['sees'])
        blind = fh[1] not in seen_before
    vcasts = sum(1 for e in ev if (fh[0] - 15 if fh else D - 15) <= e['r'] <= D and e.get('a') == v and e['k'] in ('cast', 'attack')
                 and any(team.get(tid) != t for tid, _ in e.get('dmg') or []))
    ally_out = sum(a for e in ev if D - 15 <= e['r'] <= D and e['k'] in ('cast', 'attack') and team.get(e.get('a')) == t and e.get('a') != v
                   for tid, a in e.get('dmg') or [] if team.get(tid) != t)
    enemy_out = sum(a for e in ev if D - 15 <= e['r'] <= D and e['k'] in ('cast', 'attack') and team.get(e.get('a')) != t
                    for tid, a in e.get('dmg') or [] if team.get(tid) == t)
    first_stun = min((s_[0] for s_ in stuns), default=None)
    cr = next((row for row in rows if row['r'] == contact), None) if contact else None
    peak_en = max(row['en8'] for row in rows[-10:])
    return {'src': m['source'].split('/')[-1], 'map': m['map']['name'], 'dir': dd.name, 'W': mp['width'], 'D': D, 'v': v, 'vteam': t,
            'winner': m['result']['winner'], 'killer': names.get(first.get('by'), 'camp'), 'killer_id': first.get('by'),
            'assists': [names[a] for a in first.get('assists') or []], 'bag': first.get('gems') or 0,
            'picks': m['draft']['picks'][t], 'epicks': m['draft']['picks'][1 - t],
            'contact': contact, 'contact_len': (D - contact) if contact else None,
            'contact_row': cr, 'last': rows[-1], 'peak_en': peak_en,
            'first_hit': fh, 'first_hit_by': names.get(fh[1]) if fh else None, 'fh_row': fhrow, 'blind': blind,
            'vcasts': vcasts, 'ally_out': ally_out, 'enemy_out': enemy_out, 'first_stun': first_stun,
            'stuns': stuns, 'stunned_turns': stunned_turns, 'dmg15': dict(dmg), 'trace': rows}


def main():
    global MAXR
    root = Path(sys.argv[1]); bname = sys.argv[2]; out = sys.argv[3]
    if '--max-round' in sys.argv: MAXR = int(sys.argv[sys.argv.index('--max-round') + 1])
    dirs = [dd for dd in sorted(root.iterdir()) if (dd / 'meta.json').exists() and bname in (json.loads((dd / 'meta.json').read_text()).get('source') or '')]
    n = 0
    with ProcessPoolExecutor(24) as ex, open(out, 'w') as f:
        for x in ex.map(one, dirs, chunksize=4):
            if x: f.write(json.dumps(x) + '\n'); n += 1
    print(len(dirs), 'dirs;', n, 'early first Prism deaths')


if __name__ == '__main__':
    main()
