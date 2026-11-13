"""Where champions' turns go and what each class of turn earns, per side: winner vs loser (default, for mirror
A/Bs) or per bot (--by-bot, for CAND vs REF A/Bs). Reads the extract.mjs cache plus each replay's own
`D <round> <champion id> <branch> <farm_group> <claim>` trace lines in team-a/b.stdout.

    node tools/replay/extract.mjs replays/batch-X replays/batch-Y
    py tools/replay/turn_budget.py replays/batch-X replays/batch-Y [--by-bot] [--csv DIR] [--threads N]

Classes (first match wins): dead (incl. the respawn turn), fight (narrative/track.py fight label, or dealing or
taking champion damage that round), tribute, recall (real ones; feints are ignored), teleport, camp (hit a camp),
hold (ended on a cleared group's tile), spawn-heal (on own spawn without moving, shopping or starting below max hp),
bag->altar / bag->camp / bag-other (moved with gems; toward = walking distance to the nearest altar, or to the next
camp group it works, shrank), empty->camp / empty->spawn / empty-other, idle-off, idle-spawn.
"""

import argparse
import csv
import gzip
import json
import os
import re
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, '/home/ubuntu/wt/mac13-castor/tools/replay')

from analysis.data import ROOT, _norm, chebyshev, load_index  # noqa: E402

PHASES = [(1, 150, 'r1-150'), (151, 400, 'r151-400'), (401, 800, 'r401-800'), (801, 10**9, 'r801+')]
EARLY = 300
CLASSES = ['dead', 'fight', 'tribute', 'recall', 'hold+recall', 'teleport', 'camp', 'hold', 'spawn-heal', 'bag->altar', 'bag->camp',
           'bag-other', 'empty->camp', 'empty->spawn', 'empty-other', 'idle-off', 'idle-spawn']
MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Heart of Ruin', 'Issac'}
PRIMARY = ['Monolith', 'Golem', 'Elk', 'Wolf', 'Gem cluster', 'Gold cluster']
SUPPLY = ['asleep', 'awake', 'unclaimed', 'held', 'respawn']
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
CAP = 1 << 20
INF = 1 << 30

_maps = {}


def phase_of(r):
    for lo, hi, name in PHASES:
        if lo <= r <= hi:
            return name
    return PHASES[-1][2]


def rel_side(side, team):
    return 'mid' if side == -1 else 'own' if side == team else 'enemy'


def mapinfo(h):
    from analysis.data import load_map
    from narrative.mapinfo import MapInfo
    if h not in _maps:
        raw = load_map(h).raw
        for grp in raw['groups']:
            grp.setdefault('mirror', grp['id'])  # extract.mjs omits it for a self-symmetric group
        M = MapInfo(raw)
        M.altar_field = M.field(M.altar_tiles)
        _maps[h] = M
    return _maps[h]


def lite_track(v, fights):
    """track.Track without the leg segmentation (fight_of, recalls, group states, _labels)."""
    from narrative.track import FIGHT_GAP, Track
    t = Track.__new__(Track)
    t.v, t.M, t.fights = v, v.M, fights
    t.gstate = t._groups()
    t.fight_of = {}
    for f in fights:
        hit = defaultdict(set)
        for s, r, a, x, *_ in f.its:
            hit[a].add(r)
            hit[x].add(r)
        for c, rs in hit.items():
            rs = sorted(rs)
            for i, r in enumerate(rs):
                nxt = rs[i + 1] if i + 1 < len(rs) else r
                for rr in range(r, nxt + 1 if nxt - r <= FIGHT_GAP else r + 1):
                    t.fight_of.setdefault((c, rr), f)
    t.recalls, t.feints = t._recalls()
    return t


def read_trace(source, ids, N):
    """{(champion id, round): branch char}, plus per-team truncation info."""
    out, info = {}, {}
    try:
        z = zipfile.ZipFile(ROOT / source)
    except (OSError, zipfile.BadZipFile):
        return out, {0: {'missing': True}, 1: {'missing': True}}
    with z:
        names = set(z.namelist())
        for team, fn in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
            if fn not in names:
                info[team] = {'missing': True}
                continue
            raw = z.read(fn)
            last = {}
            for m in D_RE.finditer(raw):
                r, c = int(m.group(1)), int(m.group(2))
                out[(c, r)] = m.group(3).decode()
                last[c] = max(last.get(c, 0), r)
            mine = [c for c in ids[team]]
            lastr = min((last.get(c, 0) for c in mine), default=0)
            info[team] = {'bytes': len(raw), 'last': lastr, 'truncated': len(raw) >= CAP - 4096 or lastr < N - 1,
                          'foreign': sum(1 for c in last if c not in mine)}
    return out, info


def classify(v, M, tr, c, dmg_rounds, respawn_rounds):
    """Per-round class of champion c (index = round), with track.py's labels and per-round info."""
    N = v.N
    t = v.team[c]
    lab, info = tr._labels(c)
    nxt = [None] * (N + 2)
    cur = None
    for r in range(N, 0, -1):
        k = lab[r][0]
        if k in ('camp', 'hold'):
            cur = lab[r][1]
        elif k in ('dead', 'died'):
            cur = None
        nxt[r] = cur
    spawn = M.spawn_set[t]
    dsp = M.dspawn[t]
    af = M.altar_field
    out = [None] * (N + 1)
    for r in range(1, N + 1):
        k = lab[r][0]
        p0, p1 = v.start_pos(c, r), v.pos(c, r)
        if k in ('dead', 'died') or (c, r) in respawn_rounds or p0 is None:
            cls = 'dead'
        elif k == 'fight' or (c, r) in dmg_rounds:
            cls = 'fight'
        elif k == 'trib':
            cls = 'tribute'
        elif k == 'recall':
            # The bot recalls while standing on a capture (branch Q): the hold continues through the channel.
            on = M.tile_group.get(p1)
            cls = 'hold+recall' if on is not None and (tr.group_at(on.gid, r) or {}).get('state') == 2 else 'recall'
        elif k == 'tp':
            cls = 'teleport'
        elif k == 'camp':
            cls = 'camp'
        elif k == 'hold':
            cls = 'hold'
        elif p0 != p1 and p1 is not None:
            bag = v.at(c, 'gems', r - 1) if r > 1 else 0
            ng = nxt[r]
            gf = M.groups[ng].fd if ng is not None else None
            to_camp = gf is not None and gf.get(p1, INF) < gf.get(p0, INF)
            if bag > 0:
                cls = 'bag->altar' if af.get(p1, INF) < af.get(p0, INF) else 'bag->camp' if to_camp else 'bag-other'
            else:
                cls = 'empty->camp' if to_camp else 'empty->spawn' if dsp.get(p1, INF) < dsp.get(p0, INF) else 'empty-other'
        else:
            kinds = {e['k'] for e in info[r]['ev']}
            if p1 in spawn:
                hp0 = v.at(c, 'hp', r - 1) if r > 1 else 1e9
                mx = v.at(c, 'maxHp', r - 1) if r > 1 else 0
                cls = 'spawn-heal' if ('shop' in kinds or 'sell' in kinds or hp0 < mx - 0.5) else 'idle-spawn'
            else:
                cls = 'idle-off'
        out[r] = cls
    return out, lab, info


def work(task):
    from narrative.combat import engagements
    from narrative.game import View
    d, source, teams, mhash = task['dir'], task['source'], task['teams'], task['mapHash']
    M = mapinfo(mhash)
    v = View(d, M, teams)
    g = v.g
    N = v.N
    team = v.team
    ids = [[c for c in v.ids if team[c] == t] for t in (0, 1)]
    ctype = {c: g.name_of[c] for c in v.ids}
    fights = engagements(v)
    tr = lite_track(v, fights)
    trace, tinfo = read_trace(source, ids, N)
    camp_group = M.camp_group
    ginfo = {grp['id']: grp for grp in M.raw['groups']}
    gtype = {}
    camp_type = {c['id']: c['type'] for c in M.raw['camps']}
    for gid, grp in ginfo.items():
        types = [camp_type[c] for c in grp['camps']]
        gtype[gid] = {'Gem cluster': 'GemCl', 'Gold cluster': 'GoldCl'}.get(prim := min(types, key=PRIMARY.index), prim)

    cnt = Counter()          # summed in main: keys start with team
    dmg_rounds = set()
    for s, r, a, x, amt, *_ in g.champ_damage:
        dmg_rounds.add((a, r))
        dmg_rounds.add((x, r))
    respawn_rounds = {(e['a'], e['r']) for e in g.events if e['k'] == 'respawn'}
    moves = Counter()
    for e in g.events:
        if e['k'] == 'move' or (e['k'] == 'cast' and e.get('moved')):
            moves[team[e['a']]] += 1

    # ---- 1. turn budget
    examples = []
    for c in v.ids:
        t = team[c]
        ty = ctype[c]
        mr = 'melee' if ty in MELEE else 'ranged'
        classes, lab, info = classify(v, M, tr, c, dmg_rounds, respawn_rounds)
        idle_run, idle_at, trip = 0, None, 0
        for r in range(1, N + 1):
            cls = classes[r]
            p1 = v.pos(c, r)
            if cls.startswith('bag'):
                trip += 1
            elif cls != 'tribute':
                trip = 0
            elif any(e['k'] == 'tribute_start' for e in info[r]['ev']):
                cnt[(t, 'trip_n')] += 1
                cnt[(t, 'trip_rounds')] += trip
                trip = 0
            ph = phase_of(r)
            ch = trace.get((c, r), '?')
            cnt[(t, 'cls', ph, cls)] += 1
            cnt[(t, 'clsmr', mr, cls)] += 1
            cnt[(t, 'clstype', ty, cls)] += 1
            if r <= EARLY:
                cnt[(t, 'cls', 'r1-300', cls)] += 1
            cnt[(t, 'br', ph, ch)] += 1
            if r <= EARLY:
                cnt[(t, 'br', 'r1-300', ch)] += 1
            cnt[(t, 'x', ch, cls)] += 1
            if cls != 'dead':
                cnt[(t, 'alive')] += 1
                if r <= EARLY:
                    cnt[(t, 'alive300')] += 1
            if cls == 'idle-off':
                if not idle_run:
                    idle_at = (r, p1, ch)
                idle_run += 1
            if idle_run and (cls != 'idle-off' or r == N):
                cnt[(t, 'idle_runs', 'ge50' if idle_run >= 50 else 'ge10' if idle_run >= 10 else 'lt10')] += idle_run
                if idle_run >= 50:
                    cnt[(t, 'idle_long_br', idle_at[2])] += idle_run
                if idle_run >= 30:
                    examples.append(('idle-off30', t, idle_at[0], idle_run,
                                     f'{ty}#{c} idle off spawn {idle_run} rounds at {idle_at[1]} branch {idle_at[2]}'))
                idle_run = 0
            if cls != 'dead':
                bag = v.at(c, 'gems', r)
                cnt[(t, 'bag_rounds')] += bag
                cnt[(t, 'bag30')] += bag >= 30

    # ---- 2. earnings, tributes
    deaths = []
    first_death = [None, None]
    cap_rec = []
    for e in g.events:
        k, r = e['k'], e['r']
        if k == 'capture':
            for cid, gems, gold in e['shares']:
                t = team[cid]
                cnt[(t, 'cap_gems')] += gems
                cnt[(t, 'cap_gold')] += gold
                cnt[(t, 'capph', phase_of(r))] += gems
                if r <= EARLY:
                    cnt[(t, 'cap_gems300')] += gems
            rel = rel_side(ginfo[e['g']]['side'], e['team'])
            cnt[(e['team'], 'captures', rel)] += 1
            cnt[(e['team'], 'capgems', rel)] += sum(s[1] for s in e['shares'])
            if r <= EARLY:
                cnt[(e['team'], 'captures300', rel)] += 1
        elif k == 'tribute_end':
            t = team[e['a']]
            cnt[(t, 'trib_gems')] += e['gems']
            cnt[(t, 'tribph', phase_of(r))] += e['gems']
            cnt[(t, 'tribs')] += 1
            cnt[(t, 'trib_bag', min(e['gems'] // 20 * 20, 100))] += 1
            if r <= EARLY:
                cnt[(t, 'trib_gems300')] += e['gems']
        elif k == 'tribute_blocked':
            cnt[(team[e['a']], 'trib_blocked')] += 1
        elif k == 'lock_place':
            cnt[(team[e['a']], 'locks')] += 1
        elif k == 'tribute_cancel':
            cnt[(team[e['a']], 'trib_cancel', str(e.get('cause')))] += 1
        elif k == 'death':
            t = team[e['v']]
            camp = 'camp' in e and e.get('by') not in team
            cnt[(t, 'lost_camp' if camp else 'lost_champ')] += e.get('gems', 0)
            if r <= EARLY:
                cnt[(t, 'lost300')] += e.get('gems', 0)
            if not camp and e.get('by') in team:
                cnt[(team[e['by']], 'kill_gems')] += e.get('gemsTo', 0)
            if e.get('linked') is not None:
                continue
            cnt[(t, 'deaths_camp' if camp else 'deaths')] += 1
            if not camp and e.get('by') in team:
                cnt[(team[e['by']], 'kills')] += 1
                if r <= EARLY:
                    cnt[(team[e['by']], 'kills300')] += 1
            if first_death[t] is None:
                first_death[t] = r
            deaths.append(death_context(v, M, trace, e, camp))
    for t in (0, 1):
        cnt[(t, 'moves')] += moves[t]
        cnt[(t, 'earned')] += sum(c['earnedGold'] for c in g.champs if c['team'] == t)
        n_rc = [rc for rc in tr.recalls if team[rc['c']] == t]
        for rc in n_rc:
            b = trace.get((rc['c'], rc['r0']), '?')
            cnt[(t, 'rc', b)] += 1
            cnt[(t, 'rc_done', b)] += rc['done']
            cnt[(t, 'rc_bag', b)] += rc['gems'] > 0
            cnt[(t, 'rc_dist', b)] += min(M.dspawn[t].get(rc['from'], 99), 99)
            cnt[(t, 'rc_rounds', b)] += rc['r1'] - rc['r0'] + 1
        cnt[(t, 'recalls')] += len(n_rc)
        cnt[(t, 'recalls_done')] += sum(1 for rc in n_rc if rc['done'])
        cnt[(t, 'champ_rounds')] += N * len(ids[t])

    # ---- 3. clears and holds
    clears = []
    ep = {}
    pending = {}
    for e in g.events:
        k, r = e['k'], e['r']
        if k in ('attack', 'cast') and e.get('cdmg'):
            for camp, amt in e['cdmg']:
                gid = camp_group[camp]
                x = ep.setdefault(gid, {'r0': r, 'hit': [set(), set()], 'turns': [set(), set()], 'dmg': [0.0, 0.0],
                                        'taken': [0.0, 0.0], 'camp_deaths': [0, 0]})
                ta = team[e['a']]
                x['hit'][ta].add(e['a'])
                x['turns'][ta].add((e['a'], r))
                x['dmg'][ta] += amt
        elif k == 'camp_attack' and e['g'] in ep:
            x = ep[e['g']]
            if e.get('tgt') in team:
                x['taken'][team[e['tgt']]] += e.get('dmg', 0)
            for vv, amt in e.get('xdmg', []):
                if vv in team:
                    x['taken'][team[vv]] += amt
        elif k == 'death' and 'camp' in e and e.get('by') not in team:
            gid = camp_group.get(e['camp'])
            if gid in ep:
                ep[gid]['camp_deaths'][team[e['v']]] += 1
        elif k == 'group_clear':
            gid = e['g']
            x = ep.pop(gid, None)
            if x is None:
                continue
            ct = team[e['by']] if e.get('by') in team else (0 if x['dmg'][0] >= x['dmg'][1] else 1)
            rec = {'team': ct, 'type': gtype[gid], 'gems': ginfo[gid]['gems'], 'rel': rel_side(ginfo[gid]['side'], ct),
                   'r0': x['r0'], 'r': r, 'hitters': len(x['hit'][ct]), 'enemy_hitters': len(x['hit'][1 - ct]),
                   'turns': len(x['turns'][ct]), 'taken': x['taken'][ct], 'camp_deaths': x['camp_deaths'][ct],
                   'holds': [], 'resets': [], 'capture': None, 'gid': gid}
            pending[gid] = rec
            clears.append(rec)
        elif k == 'capture_hold' and e['g'] in pending:
            pending[e['g']]['holds'].append((r, e['team']))
        elif k == 'capture_reset' and e['g'] in pending:
            pending[e['g']]['resets'].append((r, e['team'], bool(e.get('contested'))))
        elif k == 'capture' and e['g'] in pending:
            rec = pending.pop(e['g'])
            rec['capture'] = (r, e['team'], len(e['shares']))
            if e['team'] != rec['team']:
                examples.append(('stolen', rec['team'], r, rec['gems'], f"{rec['type']} ({rec['gems']} gems, {rec['rel']}) cleared r{rec['r']} stolen"))
        elif k == 'group_respawn':
            pending.pop(e['g'], None)

    # ---- 4. supply
    rows = defaultdict(list)
    for row in g.rounds['groups']:
        rows[row[1]].append(row)
    for gid, rs in rows.items():
        gems = ginfo[gid]['gems']
        j, cur = 0, None
        for r in range(1, N + 1):
            while j < len(rs) and rs[j][0] <= r:
                cur = rs[j]
                j += 1
            if cur is None:
                continue
            state, hold, awake = cur[2], cur[3], cur[6]
            cat = ('awake' if awake == 1 else 'asleep') if state == 1 else ('held' if hold in (0, 1) else 'unclaimed') \
                if state == 2 else 'respawn'
            for t in (0, 1):
                rel = rel_side(ginfo[gid]['side'], t)
                cnt[(t, 'supt', rel, gtype[gid], cat)] += 1
                if cat == 'asleep':
                    # Upper bound: each asleep round is 1/(respawn + 15) of a farm cycle left unused.
                    cnt[(t, 'suppot', rel)] += gems / (ginfo[gid]['respawn'] + 15)
                cnt[(t, 'sup', 'all', rel, cat)] += gems
                if r <= EARLY:
                    cnt[(t, 'sup', 'r1-300', rel, cat)] += gems

    # ---- 6. fights
    frec = []
    for f in fights:
        part = [sum(1 for c in f.part if team[c] == t) for t in (0, 1)]
        near = [0, 0]
        if f.loc:
            for c in v.ids:
                p = v.pos(c, f.r0 - 1)
                if p is not None and chebyshev(p, f.loc) <= 8:
                    near[team[c]] += 1
        dd, bags = [0, 0], [0, 0]
        for r in range(f.r0, f.r1 + 2):
            for e in v.deaths.get(r, []):
                if e['v'] in f.part:
                    bags[team[e['v']]] += e.get('gems', 0)
                    if e.get('linked') is None:
                        dd[team[e['v']]] += 1
        frec.append({'part': part, 'near': near, 'deaths': dd, 'bags': bags, 'r0': f.r0, 'first': f.first_team})

    # ---- 7. game-level
    gems_at, hold_at = {}, {}
    for rr in (200, 400, 600):
        i = min(rr, N) - 1
        gems_at[rr] = [g.rounds['gems'][0][i], g.rounds['gems'][1][i]]
        hold_at[rr] = [gems_at[rr][t] + sum(v.col[c]['gems'][i] for c in ids[t] if v.col[c]['alive'][i]) for t in (0, 1)]
    big = sorted(deaths, key=lambda d_: -d_['gems'])[:3]
    for d_ in big:
        if d_['gems'] >= 60:
            examples.append(('bagdeath', d_['team'], d_['r'], d_['gems'], f"{d_['type']} died with {d_['gems']} gems ({d_['cause']}, "
                                                              f"allies<=8 {d_['allies8']}, enemies<=8 {d_['enemies8']}, branch {d_['branch']})"))
    return {'dir': d, 'source': source, 'teams': teams, 'map': g.map_name, 'N': N, 'winner': g.winner,
            'final': g.final_gems, 'cnt': cnt, 'deaths': deaths, 'clears': clears, 'fights': frec, 'gems_at': gems_at, 'hold_at': hold_at,
            'first_death': first_death, 'trace': tinfo, 'examples': examples}


def death_context(v, M, trace, e, camp):
    c, r, s = e['v'], e['r'], e['s']
    t = v.team[c]
    at = tuple(e['at'])
    allies, enemies = [], []
    for x in v.ids:
        if x == c:
            continue
        p = v.pos_at(x, r, s)
        if p is None:
            continue
        dist = chebyshev(p, at)
        (allies if v.team[x] == t else enemies).append(dist)
    dsp = M.dspawn[t]
    back = None
    for rr in range(r - 4, r):
        p = v.pos(c, rr)
        if p is not None:
            back = p
            break
    retreat = back is not None and dsp.get(at, INF) <= dsp.get(back, INF) - 2
    brs = [trace.get((c, rr), '?') for rr in range(r - 4, r + 1)]
    half = M.half_of(at)
    return {'team': t, 'r': r, 'gems': e.get('gems', 0), 'cause': 'camp' if camp else 'champ', 'type': v.g.name_of[c],
            'allies4': sum(1 for x in allies if x <= 4), 'allies8': sum(1 for x in allies if x <= 8),
            'enemies8': sum(1 for x in enemies if x <= 8), 'ground': 'mid' if half == -1 else 'own' if half == t else 'enemy',
            'retreat': retreat, 'R4': 'R' in brs, 'branch': next((b for b in reversed(brs) if b not in '-?'), '-')}


# ---------------------------------------------------------------- aggregation and report

def pct(a, b):
    return f'{100 * a / b:.1f}' if b else '-'


def f1(x):
    return '-' if x is None else f'{x:.1f}' if abs(x) < 100 else f'{x:.0f}'


def ratio(a, b, k=1.0):
    return a * k / b if b else None


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    out += ['| ' + ' | '.join(str(x) for x in row) + ' |' for row in rows]
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sources', nargs='+')
    ap.add_argument('--by-bot', action='store_true', help='group by bot name instead of winner/loser')
    ap.add_argument('--csv', help='also write CSV tables to this directory')
    ap.add_argument('--threads', type=int, default=min(90, os.cpu_count() or 4))
    ap.add_argument('--examples', type=int, default=6)
    a = ap.parse_args()

    index = load_index()
    tasks, seen = [], set()
    for src in a.sources:
        # Replays live in the primary checkout; a relative path from a worktree is read against it.
        p = _norm(src) if Path(src).exists() or Path(src).is_absolute() else _norm(ROOT / src)
        rows = [r for r in index if r['source'] == p or r['source'].startswith(p + '/')]
        if not rows:
            sys.exit(f'no extracted replays under {src} (run node tools/replay/extract.mjs {src})')
        for r in rows:
            if not r['ok']:
                continue
            key = (r['dir'], tuple(r['teams'])) if a.by_bot else r['dir']
            if key in seen:
                continue
            seen.add(key)
            tasks.append({'dir': r['dir'], 'source': r['source'], 'teams': r['teams'], 'mapHash': r['mapHash']})
    print(f'# Turn budget: {len(tasks)} games from {", ".join(a.sources)}\n', flush=True)
    if not a.by_bot:
        print('Mirror mode: identical replays (a map pair swapped between two copies of one bot) count once; '
              'sides are the game winner (W) and loser (L).\n')
    with ProcessPoolExecutor(a.threads) as ex:
        res = list(ex.map(work, tasks, chunksize=1))

    def lab(rg, t):
        return rg['teams'][t] if a.by_bot else ('W' if t == rg['winner'] else 'L')

    sides = sorted({lab(rg, t) for rg in res for t in (0, 1)}, key=lambda s: (s != 'W', s))
    C = Counter()
    games = Counter()
    deaths, clears, fights, persides = [], [], [], []
    for rg in res:
        for k, val in rg['cnt'].items():
            C[(lab(rg, k[0]),) + k[1:]] += val
        for t in (0, 1):
            games[lab(rg, t)] += 1
        for d_ in rg['deaths']:
            deaths.append(dict(d_, side=lab(rg, d_['team'])))
        for c_ in rg['clears']:
            c2 = dict(c_, side=lab(rg, c_['team']))
            if c_['capture']:
                c2['cap_side'] = lab(rg, c_['capture'][1])
            clears.append(c2)
        for f in rg['fights']:
            for t in (0, 1):
                fights.append({'side': lab(rg, t), 'me': f['part'][t], 'them': f['part'][1 - t], 'near_me': f['near'][t],
                               'near_them': f['near'][1 - t], 'lost': f['deaths'][t], 'killed': f['deaths'][1 - t],
                               'bag_lost': f['bags'][t], 'bag_won': f['bags'][1 - t], 'first': f['first'] == t})
    out = []
    P = out.append

    # ---- data caveats
    trunc = sum(1 for rg in res for t in (0, 1) if rg['trace'][t].get('truncated'))
    missing = sum(1 for rg in res for t in (0, 1) if rg['trace'][t].get('missing'))
    qrounds = sum(v for k, v in C.items() if k[1] == 'br' and k[2] in [p[2] for p in PHASES] and k[3] == '?')
    allr = sum(v for k, v in C.items() if k[1] == 'br' and k[2] in [p[2] for p in PHASES])
    foreign = sum(rg['trace'][t].get('foreign', 0) for rg in res for t in (0, 1))
    P(f'Trace: {trunc} of {2 * len(res)} team stdouts truncated (1 MiB cap or D lines end before the last round), '
      f'{missing} missing; {pct(qrounds, allr)}% of champion-rounds have no D line (branch `?`); '
      f'{foreign} D-line champion ids outside the printing team.\n')

    # ---- 1. turn budget
    phases = [p[2] for p in PHASES] + ['r1-300']
    P('## 1. Turn budget (% of champion-rounds)\n')
    head = ['class'] + [f'{ph} {s}' for ph in ['all'] + phases for s in sides]
    tot = {(s, ph): sum(v for k, v in C.items() if k[0] == s and k[1] == 'cls' and k[2] == ph) for s in sides for ph in phases}
    for s in sides:
        tot[(s, 'all')] = sum(tot[(s, ph)] for ph in phases[:-1])
    rows = []
    for cl in CLASSES:
        row = [cl]
        for ph in ['all'] + phases:
            for s in sides:
                n = sum(C[(s, 'cls', p_, cl)] for p_ in phases[:-1]) if ph == 'all' else C[(s, 'cls', ph, cl)]
                row.append(pct(n, tot[(s, ph)]))
        rows.append(row)
    P(table(head, rows) + '\n')
    P('By attack type (all rounds):\n')
    mrs = ['melee', 'ranged']
    head = ['class'] + [f'{m} {s}' for m in mrs for s in sides]
    mt = {(s, m): sum(v for k, v in C.items() if k[0] == s and k[1] == 'clsmr' and k[2] == m) for s in sides for m in mrs}
    P(table(head, [[cl] + [pct(C[(s, 'clsmr', m, cl)], mt[(s, m)]) for m in mrs for s in sides] for cl in CLASSES]) + '\n')
    types = sorted({k[2] for k in C if k[1] == 'clstype'})
    tt = {(s, ty): sum(v for k, v in C.items() if k[0] == s and k[1] == 'clstype' and k[2] == ty) for s in sides for ty in types}
    key_cls = ['dead', 'fight', 'camp', 'hold', 'tribute', 'recall', 'spawn-heal', 'idle-spawn', 'idle-off']
    P('By champion type (% of that type\'s champion-rounds; walk = all bag/empty walking):\n')
    head = ['type', 'side', 'rounds'] + key_cls + ['walk']
    rows = []
    for ty in types:
        for s in sides:
            n = tt[(s, ty)]
            if not n:
                continue
            walk = sum(C[(s, 'clstype', ty, cl)] for cl in CLASSES if cl.startswith(('bag', 'empty')))
            rows.append([ty, s, n] + [pct(C[(s, 'clstype', ty, cl)], n) for cl in key_cls] + [pct(walk, n)])
    P(table(head, rows) + '\n')

    brs = sorted({k[3] for k in C if k[1] == 'br'})
    P('Bot branch (D lines), % of champion-rounds:\n')
    head = ['branch'] + [f'{ph} {s}' for ph in ['all', 'r1-300'] for s in sides]
    bt = {(s, ph): sum(v for k, v in C.items() if k[0] == s and k[1] == 'br' and k[2] == ph) for s in sides for ph in phases}
    rows = []
    for b in brs:
        row = [f'`{b}`']
        for ph in ['all', 'r1-300']:
            for s in sides:
                if ph == 'all':
                    n = sum(C[(s, 'br', p_, b)] for p_ in phases[:-1])
                    d_ = sum(bt[(s, p_)] for p_ in phases[:-1])
                else:
                    n, d_ = C[(s, 'br', ph, b)], bt[(s, ph)]
                row.append(pct(n, d_))
        rows.append(row)
    P(table(head, rows) + '\n')
    P('Branch x replay class (both sides pooled; % of the branch\'s rounds, cells under 1% blank):\n')
    xt = Counter()
    for k, val in C.items():
        if k[1] == 'x':
            xt[(k[2], k[3])] += val
    head = ['branch', 'n'] + CLASSES
    rows = []
    for b in brs:
        n = sum(xt[(b, cl)] for cl in CLASSES)
        rows.append([f'`{b}`', n] + [(f'{100 * xt[(b, cl)] / n:.0f}' if n and xt[(b, cl)] / n >= 0.01 else '') for cl in CLASSES])
    P(table(head, rows) + '\n')
    P('Replay class -> bot branches (pooled; % of the class\'s rounds, top 4):\n')
    rows = []
    for cl in CLASSES:
        n = sum(xt[(b, cl)] for b in brs)
        if n:
            top = sorted(brs, key=lambda b: -xt[(b, cl)])[:4]
            rows.append([cl, n, ', '.join(f'`{b}` {100 * xt[(b, cl)] / n:.0f}' for b in top if xt[(b, cl)])])
    P(table(['class', 'n', 'branches'], rows) + '\n')

    # ---- 2. earnings
    P('## 2. Earnings (per game per side unless noted)\n')
    rows = []

    def per_game(key):
        return [f1(C[(s,) + key] / games[s]) for s in sides]

    def cls_n(s, cl):
        return sum(C[(s, 'cls', p_, cl)] for p_ in phases[:-1])

    rows.append(['gems captured'] + per_game(('cap_gems',)))
    rows.append(['gems tributed'] + per_game(('trib_gems',)))
    rows.append(['gems taken by kills'] + per_game(('kill_gems',)))
    rows.append(['gems lost at death to champions'] + per_game(('lost_champ',)))
    rows.append(['gems lost at death to camps'] + per_game(('lost_camp',)))
    rows.append(['gold earned (lifetime)'] + per_game(('earned',)))
    rows.append(['r1-300 gems captured'] + per_game(('cap_gems300',)))
    rows.append(['r1-300 gems tributed'] + per_game(('trib_gems300',)))
    rows.append(['r1-300 gems lost at death'] + per_game(('lost300',)))
    rows.append(['gems captured per camp-hit round'] + [f1(ratio(C[(s, 'cap_gems')], cls_n(s, 'camp'))) for s in sides])
    rows.append(['gems captured per hold round'] + [f1(ratio(C[(s, 'cap_gems')], cls_n(s, 'hold'))) for s in sides])
    rows.append(['gems captured per (camp+hold) round'] + [f1(ratio(C[(s, 'cap_gems')], cls_n(s, 'camp') + cls_n(s, 'hold'))) for s in sides])
    rows.append(['gems tributed per 100 alive rounds'] + [f1(ratio(C[(s, 'trib_gems')], C[(s, 'alive')], 100)) for s in sides])
    rows.append(['mean bag carried per alive round'] + [f1(ratio(C[(s, 'bag_rounds')], C[(s, 'alive')])) for s in sides])
    rows.append(['% alive rounds carrying 30+'] + [pct(C[(s, 'bag30')], C[(s, 'alive')]) for s in sides])
    rows.append(['tributes per 1000 alive rounds'] + [f1(ratio(C[(s, 'tribs')], C[(s, 'alive')], 1000)) for s in sides])
    rows.append(['mean bag at tribute'] + [f1(ratio(C[(s, 'trib_gems')], C[(s, 'tribs')])) for s in sides])
    rows.append(['walk steps per tributed gem'] + [f1(ratio(C[(s, 'moves')], C[(s, 'trib_gems')])) for s in sides])
    rows.append(['bag-walk rounds per tributed gem'] + [f1(ratio(sum(cls_n(s, c_) for c_ in CLASSES if c_.startswith('bag')),
                                                                 C[(s, 'trib_gems')])) for s in sides])
    rows.append(['bag-walk rounds just before a tribute (mean trip)'] + [f1(ratio(C[(s, 'trip_rounds')], C[(s, 'trip_n')])) for s in sides])
    rows.append(['idle-off rounds in stretches of 50+ (% of idle-off)'] + [pct(C[(s, 'idle_runs', 'ge50')], sum(C[(s, 'idle_runs', k_)] for k_ in ('ge50', 'ge10', 'lt10'))) for s in sides])
    rows.append(['idle-off rounds in 50+ stretches by branch at its start, per game'] + [', '.join(
        f'`{k[2]}` {v / games[s]:.1f}' for k, v in sorted(((k, v) for k, v in C.items() if k[0] == s and k[1] == 'idle_long_br'), key=lambda x: -x[1])[:4]) for s in sides])
    rows.append(['altar locks placed / tribute attempts blocked, per game'] + [f'{C[(s, "locks")] / games[s]:.2f} / {C[(s, "trib_blocked")] / games[s]:.2f}' for s in sides])
    rows.append(['real recalls per game (completed)'] + [f'{f1(C[(s, "recalls")] / games[s])} ({f1(C[(s, "recalls_done")] / games[s])})' for s in sides])
    canc = Counter()
    for k, val in C.items():
        if k[1] == 'trib_cancel':
            canc[(k[0], k[2])] += val
    rows.append(['tribute cancels per game (cause)'] + [', '.join(f'{c_} {canc[(s, c_)] / games[s]:.2f}' for c_ in sorted({k[1] for k in canc})) or '0' for s in sides])
    P(table(['metric'] + sides, rows) + '\n')
    head = ['per game', 'side'] + [p_[2] for p_ in PHASES]
    rows = []
    for key, name in (('capph', 'gems captured'), ('tribph', 'gems tributed')):
        for s in sides:
            rows.append([name, s] + [f1(C[(s, key, p_[2])] / games[s]) for p_ in PHASES])
    for s in sides:
        rows.append(['alive champion-rounds', s] + [f1(sum(C[(s, 'cls', p_[2], cl)] for cl in CLASSES if cl != 'dead') / games[s]) for p_ in PHASES])
    P('By phase:\n\n' + table(head, rows) + '\n')
    P('Real recalls (completed or lasting 2+ rounds; feints excluded) by the branch at their start:\n')
    rbs = sorted({k[2] for k in C if k[1] == 'rc'}, key=lambda b: -sum(C[(s, 'rc', b)] for s in sides))
    head = ['side'] + [f'`{b}`' for b in rbs]
    rows = []
    for s in sides:
        rows.append([s] + [f'{C[(s, "rc", b)] / games[s]:.1f}/g, {pct(C[(s, "rc_done", b)], C[(s, "rc", b)])}% done, '
                           f'{pct(C[(s, "rc_bag", b)], C[(s, "rc", b)])}% bag, {f1(ratio(C[(s, "rc_dist", b)], C[(s, "rc", b)]))} from spawn'
                           if C[(s, 'rc', b)] else '-' for b in rbs])
    P(table(head, rows) + '\n')
    P('Bag size at tribute (% of tributes): ' + '; '.join(
        f'{s}: ' + ', '.join(f'{b}{"+" if b == 100 else "-" + str(b + 19)} {pct(C[(s, "trib_bag", b)], C[(s, "tribs")])}' for b in range(0, 120, 20))
        for s in sides) + '\n')

    # ---- 3. clears
    P('## 3. Clears and captures\n')

    def clear_stats(cs, s=None):
        n = len(cs)
        if not n:
            return None
        gems = sum(c_['gems'] for c_ in cs)
        own = sum(1 for c_ in cs if c_['capture'] and c_['capture'][1] == c_['team'])
        stolen = sum(1 for c_ in cs if c_['capture'] and c_['capture'][1] != c_['team'])
        nocap = sum(1 for c_ in cs if not c_['capture'])
        capd = [c_ for c_ in cs if c_['capture'] and c_['capture'][1] == c_['team']]
        gems = gems or float('nan')  # gold clusters
        return {'n': n, 'turns_gem': sum(c_['turns'] for c_ in cs) / gems, 'taken_gem': sum(c_['taken'] for c_ in cs) / gems,
                'own': 100 * own / n, 'stolen': 100 * stolen / n, 'nocap': 100 * nocap / n,
                'holders': statistics.mean(c_['capture'][2] for c_ in capd) if capd else None,
                'to_pay': statistics.mean(c_['capture'][0] - c_['r'] for c_ in capd) if capd else None,
                'resets': sum(len(c_['resets']) for c_ in cs) / n,
                'contested': sum(sum(1 for x in c_['resets'] if x[2]) for c_ in cs) / n,
                'dur': statistics.mean(c_['r'] - c_['r0'] for c_ in cs), 'turns': statistics.mean(c_['turns'] for c_ in cs),
                'enemy_hit': 100 * sum(1 for c_ in cs if c_['enemy_hitters']) / n,
                'camp_deaths': sum(c_['camp_deaths'] for c_ in cs) / n}

    def hb(c_):
        return '1' if c_['hitters'] <= 1 else '2' if c_['hitters'] == 2 else '3+'

    head = ['group type', 'hitters', 'n', 'champ-turns', 'rounds', 'turns/gem', 'r1-300 turns/gem (n)', 'camp dmg/gem', 'own capture %',
            'stolen %', 'uncaptured %', 'holders at payout', 'clear->payout', 'resets/clear', 'enemy also hit %']
    rows = []
    for ty in PRIMARY[:4] + ['GemCl', 'GoldCl']:
        for h in ('1', '2', '3+'):
            st = clear_stats([c_ for c_ in clears if c_['type'] == ty and hb(c_) == h])
            if st and st['n'] >= 5:
                ea = clear_stats([c_ for c_ in clears if c_['type'] == ty and hb(c_) == h and c_['r'] <= EARLY])
                rows.append([ty, h, st['n'], f1(st['turns']), f1(st['dur']), f'{st["turns_gem"]:.2f}',
                             f'{ea["turns_gem"]:.2f} ({ea["n"]})' if ea else '-', f1(st['taken_gem']),
                             f1(st['own']), f1(st['stolen']), f1(st['nocap']), f1(st['holders']), f1(st['to_pay']),
                             f'{st["resets"]:.2f}', f1(st['enemy_hit'])])
    P(table(head, rows) + '\n')
    head = ['side', 'clears/game', 'solo %', 'turns/gem', 'camp dmg/gem', 'own capture %', 'stolen from %',
            'steals/game', 'holders at payout', 'clear->payout', 'resets/clear', 'contested/clear', 'camp deaths/clear']
    rows = []
    for s in sides:
        cs = [c_ for c_ in clears if c_['side'] == s]
        st = clear_stats(cs)
        steals = sum(1 for c_ in clears if c_.get('cap_side') == s and c_['side'] != s)
        if st:
            rows.append([s, f1(st['n'] / games[s]), f1(100 * sum(1 for c_ in cs if c_['hitters'] <= 1) / st['n']),
                         f'{st["turns_gem"]:.2f}', f1(st['taken_gem']), f1(st['own']), f1(st['stolen']),
                         f'{steals / games[s]:.2f}', f1(st['holders']), f1(st['to_pay']), f'{st["resets"]:.2f}',
                         f'{st["contested"]:.2f}', f'{st["camp_deaths"]:.3f}'])
    P(table(head, rows) + '\n')
    P('Clears per game by group side (relative to the clearing team) and type:\n')
    TY = ('Wolf', 'Elk', 'Golem', 'Monolith', 'GemCl', 'GoldCl')
    head = ['side'] + [f'{rel} {ty}' for rel in ('own', 'mid', 'enemy') for ty in TY]
    rows = []
    for s in sides:
        row = [s]
        for rel in ('own', 'mid', 'enemy'):
            for ty in TY:
                row.append(f'{sum(1 for c_ in clears if c_["side"] == s and c_["rel"] == rel and c_["type"] == ty) / games[s]:.2f}')
        rows.append(row)
    P(table(head, rows) + '\n')

    # ---- 4. supply
    P('## 4. Supply (% of gem-weighted group-rounds in each state, groups by side relative to the team)\n')
    P('`asleep` = monsters up and asleep (nobody within range for 2 camp phases): available, unworked. '
      '`unclaimed` = cleared, nobody holding.\n')
    for win in ('all', 'r1-300'):
        head = ['side', 'groups'] + SUPPLY
        rows = []
        for s in sides:
            for rel in ('own', 'mid', 'enemy'):
                n = sum(C[(s, 'sup', win, rel, cat)] for cat in SUPPLY)
                if n:
                    rows.append([s, rel] + [pct(C[(s, 'sup', win, rel, cat)], n) for cat in SUPPLY])
        P(f'{win}:\n\n' + table(head, rows) + '\n')
    P('By group type (unweighted % of group-rounds; own/mid/enemy relative to the side):\n')
    head = ['side', 'type'] + [f'{rel} {cat}' for rel in ('own', 'mid', 'enemy') for cat in ('asleep', 'awake', 'unclaimed')]
    rows = []
    for ty in ('Wolf', 'Elk', 'Golem', 'Monolith', 'GemCl', 'GoldCl'):
        for s in sides:
            row = [s, ty]
            for rel in ('own', 'mid', 'enemy'):
                n = sum(C[(s, 'supt', rel, ty, cat)] for cat in SUPPLY)
                row += [pct(C[(s, 'supt', rel, ty, cat)], n) for cat in ('asleep', 'awake', 'unclaimed')]
            rows.append(row)
    P(table(head, rows) + '\n')
    P('Upper bound on gems left asleep per game (each asleep round = 1/(respawn+15) of a farm cycle): ' + '; '.join(
        f'{s}: ' + ', '.join(f'{rel} {C[(s, "suppot", rel)] / games[s]:.0f}' for rel in ('own', 'mid', 'enemy')) for s in sides) + '\n')
    head = ['side'] + [f'{rel} captures/game (gems)' for rel in ('own', 'mid', 'enemy')] + ['r1-300 own/mid/enemy']
    rows = []
    for s in sides:
        rows.append([s] + [f'{C[(s, "captures", rel)] / games[s]:.1f} ({C[(s, "capgems", rel)] / games[s]:.0f})'
                           for rel in ('own', 'mid', 'enemy')]
                    + ['/'.join(f'{C[(s, "captures300", rel)] / games[s]:.1f}' for rel in ('own', 'mid', 'enemy'))])
    P(table(head, rows) + '\n')

    # ---- 5. deaths
    P('## 5. Deaths\n')
    head = ['metric'] + sides
    rows = []
    fd = defaultdict(list)
    died_first = Counter()
    for rg in res:
        f0, f1_ = rg['first_death']
        for t in (0, 1):
            fd[lab(rg, t)].append(rg['first_death'][t] if rg['first_death'][t] is not None else rg['N'] + 1)
        if f0 is not None or f1_ is not None:
            first = 0 if (f1_ is None or (f0 is not None and f0 < f1_)) else 1 if (f0 is None or f1_ < f0) else None
            if first is not None:
                died_first[lab(rg, first)] += 1
    ds = {s: [d_ for d_ in deaths if d_['side'] == s] for s in sides}
    rows.append(['deaths/game (to champions + camps)'] + [f'{f1(sum(1 for d_ in ds[s] if d_["cause"] == "champ") / games[s])} + '
                                                          f'{sum(1 for d_ in ds[s] if d_["cause"] == "camp") / games[s]:.2f}' for s in sides])
    rows.append(['median first-death round (none = length+1)'] + [f1(statistics.median(fd[s])) for s in sides])
    rows.append(['% of games this side died first'] + [pct(died_first[s], games[s]) for s in sides])
    for name, fn in [('% alone (no ally within 8)', lambda d_: d_['allies8'] == 0),
                     ('% ally within 4', lambda d_: d_['allies4'] > 0),
                     ('% 2+ enemies within 8', lambda d_: d_['enemies8'] >= 2),
                     ('% on own ground', lambda d_: d_['ground'] == 'own'),
                     ('% on mid ground', lambda d_: d_['ground'] == 'mid'),
                     ('% on enemy ground', lambda d_: d_['ground'] == 'enemy'),
                     ('% walking toward spawn (last 4 rounds)', lambda d_: d_['retreat']),
                     ('% branch R in last 4 rounds', lambda d_: d_['R4']),
                     ('% carrying 30+ gems', lambda d_: d_['gems'] >= 30)]:
        rows.append([name] + [pct(sum(1 for d_ in ds[s] if fn(d_)), len(ds[s])) for s in sides])
    rows.append(['mean enemies within 8'] + [f1(statistics.mean(d_['enemies8'] for d_ in ds[s])) if ds[s] else '-' for s in sides])
    rows.append(['mean gems carried at death'] + [f1(statistics.mean(d_['gems'] for d_ in ds[s])) if ds[s] else '-' for s in sides])
    rows.append(['r1-300 deaths/game'] + [f'{sum(1 for d_ in ds[s] if d_["r"] <= EARLY) / games[s]:.2f}' for s in sides])
    P(table(head, rows) + '\n')
    lost = {s: Counter() for s in sides}
    for d_ in deaths:
        lost[d_['side']][d_['type']] += d_['gems']
    P('Gems lost at death by champion type, per game (% of the side\'s loss): ' + '; '.join(
        f'{s}: ' + ', '.join(f'{ty} {n / games[s]:.1f} ({pct(n, sum(lost[s].values()))}%)' for ty, n in lost[s].most_common(4))
        for s in sides) + '\n')
    P(f'Deaths carrying 100+ gems: ' + '; '.join(f'{s} {sum(1 for d_ in ds[s] if d_["gems"] >= 100) / games[s]:.2f}/game holding '
                                              f'{pct(sum(d_["gems"] for d_ in ds[s] if d_["gems"] >= 100), sum(d_["gems"] for d_ in ds[s]))}% of gems lost'
                                              for s in sides) + '\n')
    bd = {s: Counter(d_['branch'] for d_ in ds[s]) for s in sides}
    P('Branch at death (last D line): ' + '; '.join(f'{s}: ' + ', '.join(f'`{b}` {pct(n, len(ds[s]))}%' for b, n in bd[s].most_common(6)) for s in sides) + '\n')
    ctx = Counter()
    for d_ in deaths:
        ctx[(d_['side'], min(d_['allies8'], 3), min(d_['enemies8'], 3))] += 1
    P('Deaths by (allies within 8, enemies within 8), per 10 games:\n')
    head = ['side', 'allies\\enemies', '0', '1', '2', '3+']
    rows = []
    for s in sides:
        for al in range(4):
            rows.append([s, f'{al}{"+" if al == 3 else ""}'] + [f'{10 * ctx[(s, al, en)] / games[s]:.1f}' for en in range(4)])
    P(table(head, rows) + '\n')

    # ---- 6. fights
    P('## 6. Kills and fights\n')
    rows = []
    for s in sides:
        fs = [f for f in fights if f['side'] == s]
        rows.append([s, f1(C[(s, 'kills')] / games[s]), f'{C[(s, "kills300")] / games[s]:.2f}', f1(len(fs) / games[s]),
                     pct(sum(1 for f in fs if f['first']), len(fs)), pct(sum(1 for f in fs if f['killed'] > f['lost']), len(fs)),
                     pct(sum(1 for f in fs if f['killed'] < f['lost']), len(fs)),
                     f1(sum(f['bag_won'] - f['bag_lost'] for f in fs) / games[s])])
    P(table(['side', 'kills/game', 'r1-300 kills/game', 'fights/game', 'initiated %', 'won on kills %', 'lost on kills %',
             'net bag gems/game'], rows) + '\n')

    def size(f):
        return f'{min(f["me"], 3)}{"+" if f["me"] >= 3 else ""}v{min(f["them"], 3)}{"+" if f["them"] >= 3 else ""}'

    P('By fight size (participants, side v enemy): fights per game, then net kills per fight (killed - lost):\n')
    sizes = sorted({size(f) for f in fights})
    head = ['side'] + sizes
    rows = []
    for s in sides:
        row = [s]
        for z in sizes:
            fs = [f for f in fights if f['side'] == s and size(f) == z]
            row.append(f'{len(fs) / games[s]:.2f} / {sum(f["killed"] - f["lost"] for f in fs) / len(fs):+.2f}' if fs else '-')
        rows.append(row)
    row = ['pooled']
    for z in sizes:
        fs = [f for f in fights if size(f) == z]
        row.append(f'{len(fs) / sum(games.values()):.2f} / {sum(f["killed"] - f["lost"] for f in fs) / len(fs):+.2f}' if fs else '-')
    rows.append(row)
    P(table(head, rows) + '\n')
    P('By head-count difference at the start (own minus enemy champions alive within 8 of the fight, previous round end): '
      'fights per game / net kills per fight / % won on kills:\n')
    head = ['side'] + [str(x) for x in range(-3, 4)]
    rows = []
    for s in sides:
        row = [s]
        for dlt in range(-3, 4):
            fs = [f for f in fights if f['side'] == s and max(-3, min(3, f['near_me'] - f['near_them'])) == dlt]
            row.append(f'{len(fs) / games[s]:.2f} / {sum(f["killed"] - f["lost"] for f in fs) / len(fs):+.2f} / '
                       f'{pct(sum(1 for f in fs if f["killed"] > f["lost"]), len(fs))}' if fs else '-')
        rows.append(row)
    row = ['pooled']
    for dlt in range(-3, 4):
        fs = [f for f in fights if max(-3, min(3, f['near_me'] - f['near_them'])) == dlt]
        row.append(f'{len(fs) / sum(games.values()):.2f} / {sum(f["killed"] - f["lost"] for f in fs) / len(fs):+.2f} / '
                   f'{pct(sum(1 for f in fs if f["killed"] > f["lost"]), len(fs))}' if fs else '-')
    rows.append(row)
    P(table(head, rows) + '\n')

    # ---- 7. what decides games
    P('## 7. What decides games\n')
    rows = []
    for kind, rr in [('tributed', 200), ('tributed', 400), ('tributed', 600), ('tributed+carried', 200),
                     ('tributed+carried', 400), ('tributed+carried', 600)]:
        lead, ties, n = 0, 0, 0
        buckets = Counter()
        for rg in res:
            if rg['N'] < rr:
                continue
            a_, b_ = rg['gems_at' if kind == 'tributed' else 'hold_at'][rr]
            n += 1
            if a_ == b_:
                ties += 1
                continue
            lt = 0 if a_ > b_ else 1
            lead += lt == rg['winner']
            diff = abs(a_ - b_)
            bk = '1-49' if diff < 50 else '50-149' if diff < 150 else '150+'
            buckets[(bk, lt == rg['winner'])] += 1
        rows.append([f'{kind} r{rr}', n, ties, pct(lead, n - ties)] +
                    [f'{pct(buckets[(bk, True)], buckets[(bk, True)] + buckets[(bk, False)])} (n={buckets[(bk, True)] + buckets[(bk, False)]})'
                     for bk in ('1-49', '50-149', '150+')])
    P(table(['gems, round', 'games reaching it', 'tied', 'leader wins %', 'lead 1-49', 'lead 50-149', 'lead 150+'], rows) + '\n')
    rows = []

    def decided(fn):
        w = n = 0
        for rg in res:
            x = fn(rg)
            if x is None:
                continue
            n += 1
            w += x == rg['winner']
        return f'{pct(w, n)} (n={n})'

    def by_cnt(key):
        def fn(rg):
            a_, b_ = rg['cnt'][(0,) + key], rg['cnt'][(1,) + key]
            return None if a_ == b_ else 0 if a_ > b_ else 1
        return fn

    def first_dead(rg):
        f0, f1_ = rg['first_death']
        if f0 is None and f1_ is None:
            return None
        if f0 == f1_:
            return None
        return 1 if (f1_ is None or (f0 is not None and f0 < f1_)) else 0
    rows.append(['team that did not die first wins', decided(first_dead)])
    rows.append(['more kills wins', decided(by_cnt(('kills',)))])
    rows.append(['more r1-300 kills wins', decided(by_cnt(('kills300',)))])
    rows.append(['more gems captured wins', decided(by_cnt(('cap_gems',)))])
    rows.append(['more r1-300 gems captured wins', decided(by_cnt(('cap_gems300',)))])
    rows.append(['fewer gems lost at death wins', decided(lambda rg: None if rg['cnt'][(0, 'lost_champ')] + rg['cnt'][(0, 'lost_camp')]
                                                       == rg['cnt'][(1, 'lost_champ')] + rg['cnt'][(1, 'lost_camp')] else
                                                       0 if rg['cnt'][(0, 'lost_champ')] + rg['cnt'][(0, 'lost_camp')] <
                                                       rg['cnt'][(1, 'lost_champ')] + rg['cnt'][(1, 'lost_camp')] else 1)])
    rows.append(['more mid-group captures wins', decided(by_cnt(('captures', 'mid')))])
    P(table(['predictor', 'win %'], rows) + '\n')
    Ns = sorted(rg['N'] for rg in res)
    q = lambda p: Ns[min(len(Ns) - 1, int(p * len(Ns)))]
    low = [rg for rg in res if max(rg['final']) < 200]
    P(f'Games where neither side tributes 200: {len(low)} ({", ".join(sorted({rg["map"] for rg in low})[:8])}).\n')
    P(f'Game length: median {q(0.5)}, quartiles {q(0.25)}-{q(0.75)}, min {Ns[0]}, max {Ns[-1]}; '
      f'{pct(sum(1 for n in Ns if n >= 2000), len(Ns))}% reach round 2000; '
      f'{pct(sum(1 for rg in res if max(rg["final"]) >= 1000), len(res))}% end on 1000 gems.\n')

    # ---- examples
    P('## Examples\n')
    ex = defaultdict(list)
    for rg in res:
        for kind, t, r, mag, text in rg['examples']:
            ex[kind].append((rg, t, r, mag, text))
    for kind in ('bagdeath', 'stolen', 'idle-off30'):
        items = ex.get(kind, [])
        items.sort(key=lambda x: -x[3])
        once, shown = set(), []
        for it in items:
            if it[0]['dir'] not in once:
                once.add(it[0]['dir'])
                shown.append(it)
        P(f'**{kind}** ({len(items)} in all, largest first, one per game):\n')
        for rg, t, r, mag, text in shown[:a.examples]:
            P(f'- `{rg["source"]}` ({rg["dir"]}) r{r} team {"AB"[t]} ({lab(rg, t)}): {text}')
        P('')
    print('\n'.join(out))

    if a.csv:
        od = Path(a.csv)
        od.mkdir(parents=True, exist_ok=True)
        with open(od / 'budget.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['side', 'kind', 'key', 'class', 'rounds'])
            for k, val in sorted(C.items(), key=str):
                if k[1] in ('cls', 'clsmr', 'clstype', 'br', 'x'):
                    w.writerow([k[0], k[1], k[2], k[3], val])
        with open(od / 'deaths.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(deaths[0].keys()) if deaths else ['side'])
            w.writeheader()
            w.writerows(deaths)
        with open(od / 'clears.csv', 'w', newline='') as f:
            keys = ['side', 'team', 'type', 'gems', 'rel', 'r0', 'r', 'hitters', 'enemy_hitters', 'turns', 'taken', 'camp_deaths',
                    'capture', 'resets']
            w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            w.writeheader()
            w.writerows(clears)
        with open(od / 'games.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['dir', 'source', 'map', 'rounds', 'winner', 'gemsA', 'gemsB', 'sideA', 'sideB'])
            for rg in res:
                w.writerow([rg['dir'], rg['source'], rg['map'], rg['N'], rg['winner'], rg['final'][0], rg['final'][1],
                            lab(rg, 0), lab(rg, 1)])


if __name__ == '__main__':
    main()
