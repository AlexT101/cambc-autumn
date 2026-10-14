import math
from collections import deque

from .data import TYPE_ABBR

STRENGTH = {'Wolf': 20, 'Elk': 60, 'Gem cluster': 0, 'Gold cluster': 0, 'Monolith': 200}
CAPTURE_ROUNDS = 6
SIDE = {0: 'own', 1: 'enemy', -1: 'mid'}

_bfs = {}


def walk_dist(mp, sources):
    """King-move walking distance from the nearest source tile (walls, holes and altars block)."""
    key = (mp.hash, tuple(sorted(sources)))
    if key in _bfs:
        return _bfs[key]
    blocked = mp.walls | mp.holes | set(mp.altars)
    dist = {s: 0 for s in sources}
    q = deque(sources)
    while q:
        x, y = q.popleft()
        d = dist[(x, y)] + 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = (x + dx, y + dy)
                if (dx or dy) and 0 <= p[0] < mp.W and 0 <= p[1] < mp.H and p not in blocked and p not in dist:
                    dist[p] = d
                    q.append(p)
    if len(_bfs) > 400:
        _bfs.clear()
    _bfs[key] = dist
    return dist


def group_key(mp, g):
    return ''.join(sorted(TYPE_ABBR[t] for t in mp.groups[g]['types']))


def members(mp, g):
    return [(c['hp'], STRENGTH[c['type']]) for c in mp.camps if c['group'] == g]


def model_damage(ms, S):
    """Least camp damage taken clearing members [(hp, strength)] with total Strength S per attack round: every member hits until it dies,
    kills in Smith's-rule order (highest strength per hp first); a member killed in attack round k has attacked k - 1 times."""
    if S <= 0:
        return None
    t = dmg = 0.0
    for hp, s in sorted(ms, key=lambda m: -(m[1] / m[0]) if m[0] else 0):
        t += hp / S
        dmg += s * max(0, math.ceil(t - 1e-9) - 1)
    return dmg


def table(mp, strengths):
    """Own and middle groups without monoliths, team A frame. strengths[0] is the team's total Strength for clear time and cycle."""
    S = strengths[0]
    s = mp.spawn[0]
    from_spawn = walk_dist(mp, [(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)])
    blocked = mp.walls | mp.holes | set(mp.altars)
    near_altar = sorted({(a[0] + dx, a[1] + dy) for a in mp.altars for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - blocked)
    from_altar = walk_dist(mp, near_altar)
    rows = []
    for grp in mp.groups:
        if grp['side'] == 1 or 'Monolith' in grp['types']:
            continue
        ms = members(mp, grp['id'])
        tiles = [tuple(t) for t in grp['tiles']]
        hp = sum(m[0] for m in ms)
        walk = min(from_spawn.get(t, 999) for t in tiles)
        altar = min(from_altar.get(t, 999) for t in tiles)
        clear = math.ceil(hp / S)
        gems = grp['gems']
        cycle = clear + CAPTURE_ROUNDS + 2 * altar + max(1, math.ceil(gems / 10))
        dmg = [model_damage(ms, x) for x in strengths]
        rows.append({'label': mp.group_label(grp['id']), 'side': SIDE[grp['side']], 'hp': hp, 'str': sum(m[1] for m in ms), 'gems': gems,
                     'gold': grp['gold'], 'respawn': grp['respawn'], 'walk': walk, 'altar': altar, 'clear': clear, 'min_dmg': dmg,
                     'gems_per_effort': gems / (walk + clear + CAPTURE_ROUNDS), 'gems_per_cycle': gems / cycle,
                     'dmg_per_gem': dmg[0] / gems if gems else None, 'gems_per_khp': 1000 * gems / hp})
    rows.sort(key=lambda r: -r['gems_per_cycle'])
    return rows


def render(ctx, rep):
    strengths = ctx.params['camp_strength']
    S = strengths[0]
    rep.p(f'Static value of each camp group on the maps in {ctx.describe()}: own and middle groups, team A frame, monolith groups left out. '
          f'Strengths: S = {S:g} for clear time and cycle (team total), plus minimum damage at {", ".join(f"{x:g}" for x in strengths[1:])} (single attackers). '
          'Change them in `analysis/params.py` (`camp_strength`).',
          '- `walk`: walking distance (king moves around walls, holes and altars) from the nearest own spawn tile to the nearest capture tile; '
          '`altar`: from the nearest tile within 1 of an altar.\n'
          f'- `clear` = ceil(hp / S) attack rounds; `min dmg @S`: least camp damage taken while clearing, when every member attacks the attacker until it dies '
          'and kills go in Smith\'s-rule order (camps hit the nearest champion, so spreading or kiting can only be better; the economy report compares actual damage with this).\n'
          f'- `gems/effort` = gems / (walk + clear + {CAPTURE_ROUNDS} capture rounds); `gems/cycle` = gems / (clear + {CAPTURE_ROUNDS} + 2 x altar + tribute turns), '
          'a repeated farm-and-tribute loop from the altar; rows are sorted by it.')
    seen = {gi['map'] for gi in ctx.games}
    headers = (['group', 'side', 'hp', 'str', 'gems', 'gold', 'respawn', 'walk', 'altar', 'clear'] + [f'min dmg @{x:g}' for x in strengths]
               + ['gems/1k hp', 'gems/effort', 'gems/cycle', f'min dmg/gem @{S:g}'])
    csv_rows = []
    for name in sorted(seen):
        mp = ctx.map_of(name)
        rows = table(mp, strengths)
        rep.h(f'{name} ({mp.W}x{mp.H}, {mp.symmetry})', 3)
        out = []
        for r in rows:
            cells = [r['label'], r['side'], r['hp'], r['str'], r['gems'], r['gold'], r['respawn'], r['walk'], r['altar'], r['clear']]
            cells += [f'{d:.0f}' for d in r['min_dmg']]
            cells += [f'{r["gems_per_khp"]:.1f}', f'{r["gems_per_effort"]:.2f}', f'{r["gems_per_cycle"]:.2f}',
                      f'{r["dmg_per_gem"]:.1f}' if r['dmg_per_gem'] is not None else '-']
            out.append(cells)
            csv_rows.append([name] + cells)
        rep.table(headers, out)
    rep.write_csv('camps', ['map'] + headers, csv_rows)
