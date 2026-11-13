"""Per farm-break game: where both teams' champion-time went in the break window, captures by location and contest,
deaths, retreats, idle capacity. Writes /tmp/mxi-study/farmwin.jsonl (one row per game)."""
import csv, json, re, sys, zipfile, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, '/home/ubuntu/wt/mx-iapetus/tools/replay')
from analysis.data import Game, ROOT, chebyshev  # noqa
from analysis import macro  # noqa

REP = '/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/reports/20261113-143253/macro-breaks.csv'
D_RE = re.compile(rb'D (\d+) (\d+) (\S) (-?\d+) (-?\d+)')
CLUSTER = {'Gem cluster', 'Gold cluster'}


def read_trace(src):
    out = {}
    with zipfile.ZipFile(ROOT / src) as z:
        for fn in ('team-a.stdout', 'team-b.stdout'):
            raw = z.read(fn).replace(b'\0', b'')
            for m in D_RE.finditer(raw):
                out[(int(m.group(2)), int(m.group(1)))] = (m.group(3).decode(), int(m.group(4)), int(m.group(5)))
    return out


def work(d):
    g = Game(d)
    mp, n, R = g.map, g.n_rounds, g.rounds
    Wt = g.winner
    Lt = 1 - Wt
    wealth, carried, comp = macro._wealth(g)
    brk = 0
    for i in range(n):
        if wealth[Lt][i] >= wealth[Wt][i]:
            brk = i + 1
    w0, w1 = brk + 1, min(n, brk + 100)
    if w0 > w1:
        return None
    Wc, Lc = macro._window_sum(comp[Wt], w0, w1), macro._window_sum(comp[Lt], w0, w1)
    parts = {'farm': Wc['cap'] - Lc['cap'], 'fight': (Wc['kg'] - Wc['lostc']) - (Lc['kg'] - Lc['lostc']),
             'camp': Lc['lostm'] - Wc['lostm']}
    cause = max(('farm', 'fight', 'camp'), key=lambda k: parts[k])
    if max(parts.values()) <= 0 and wealth[Lt][n - 1] >= wealth[Wt][n - 1]:
        cause = 'bank'
    if cause != 'farm':
        return None
    cls = macro.classify(g)
    fields = macro.group_fields(mp)
    H = mp.H
    tr = read_trace(g.meta['source'])
    champs = R['champions']
    team_of, name_of = g.team_of, g.name_of
    role = {Wt: 'W', Lt: 'L'}
    camp_group = {c['id']: c['group'] for c in mp.camps}
    # spawn distance to groups
    sp_tiles = []
    for t in (0, 1):
        s = mp.spawn[t]
        sp_tiles.append([(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)])
    gd = {}
    for grp in mp.groups:
        f = fields[grp['id']]
        gd[grp['id']] = [min(f[x * H + y] for x, y in sp_tiles[t]) for t in (0, 1)]

    def rel(gid, t):  # position of group relative to team t
        a, b = gd[gid][t], gd[gid][1 - t]
        if a >= 1 << 19 and b >= 1 << 19:
            return 'mid'
        if abs(a - b) <= max(2, 0.1 * (a + b)):
            return 'mid'
        return 'own' if a < b else 'enemy'
    gmeta = {grp['id']: grp for grp in mp.groups}
    pure_cluster = {gid: all(t in CLUSTER for t in grp['types']) for gid, grp in gmeta.items()}

    # damage rounds
    dmg_rounds = g.damaged_rounds
    champ_hit_rounds = defaultdict(set)
    for s, r, a, v, amt, *_ in g.champ_damage:
        champ_hit_rounds[v].add(r)

    # --- champion time
    time = {'W': defaultdict(Counter), 'L': defaultdict(Counter)}        # type -> class -> rounds
    br = {'W': defaultdict(Counter), 'L': defaultdict(Counter)}          # type -> branch -> rounds (alive)
    walk_br = {'W': Counter(), 'L': Counter()}                           # (type, branch, walk-led-to) rounds
    farm_target = {'W': Counter(), 'L': Counter()}                       # F-branch walk rounds by farm group rel side
    alive_rounds = {'W': Counter(), 'L': Counter()}
    for c in champs:
        cid = c['id']
        t = team_of[cid]
        ro = role[t]
        ty = name_of[cid]
        cl = cls[cid]
        for r in range(w0, w1 + 1):
            k = cl[r]
            time[ro][ty][k] += 1
            if k != 'dead':
                alive_rounds[ro][ty] += 1
                b = tr.get((cid, r))
                bc = b[0] if b else '?'
                br[ro][ty][bc] += 1
                if k in ('walk', 'walk_bag'):
                    # what the walk led to
                    j = r + 1
                    while j <= n and cl[j] in ('walk', 'walk_bag'):
                        j += 1
                    led = cl[j] if j <= n else 'end'
                    walk_br[ro][(ty, bc, k, led)] += 1
                    if bc == 'F' and b[1] >= 0 and b[1] in gd:
                        farm_target[ro][(rel(b[1], t), 'cluster' if pure_cluster[b[1]] else 'monster')] += 1

    # --- captures in window, with cycle contest info
    last_respawn = defaultdict(int)
    touch = defaultdict(lambda: [set(), set()])   # gid -> per team set of 'hit','hold' in this cycle
    clear_by = {}
    caps = []
    for e in g.events:
        k, r = e['k'], e['r']
        if k == 'group_respawn':
            touch.pop(e['g'], None)
            clear_by.pop(e['g'], None)
        elif k in ('attack', 'cast') and e.get('cdmg') and e.get('camp') is not None:
            gid = camp_group.get(e['camp'])
            if gid is not None:
                touch[gid][team_of[e['a']]].add('hit')
        elif k == 'cast' and e.get('cdmg'):
            pass
        elif k == 'capture_hold':
            touch[e['g']][e['team']].add('hold')
        elif k == 'capture_reset' and e.get('contested'):
            touch[e['g']][0].add('cont'); touch[e['g']][1].add('cont')
        elif k == 'group_clear':
            by = e.get('by')
            clear_by[e['g']] = team_of.get(by, 2) if by is not None else 2
        elif k == 'capture':
            if w0 <= r <= w1:
                gid = e['g']
                t = e['team']
                gems = sum(s[1] for s in e['shares'])
                gold = sum(s[2] for s in e['shares'])
                sharers = [name_of[s[0]] for s in e['shares']]
                caps.append({'r': r, 'g': gid, 'team': role[t], 'gems': gems, 'gold': gold,
                             'rel_L': rel(gid, Lt), 'cluster': pure_cluster[gid],
                             'other_touched': sorted(touch[gid][1 - t]), 'self_touched': sorted(touch[gid][t]),
                             'cleared_by': role.get(clear_by.get(gid, 2), 'N'), 'sharers': sharers,
                             'types': ''.join(sorted(macro.ABBR[x] for x in gmeta[gid]['types']))})
            touch.pop(e['g'], None)

    # --- group idle capacity in the window: rounds a group was up and asleep, or cleared and unheld
    grows = R['groups']
    st = {}
    idle = {'W': Counter(), 'L': Counter()}   # (rel to that team, cluster, kind) -> value-rounds (gems/(respawn+6))
    gi = 0
    rounds_list = R['round']
    for i in range(min(n, w1)):
        r = rounds_list[i] if i < len(rounds_list) else i + 1
        while gi < len(grows) and grows[gi][0] <= r:
            row = grows[gi]
            st[row[1]] = row
            gi += 1
        if r < w0:
            continue
        for gid, row in st.items():
            state, team, timer, resp, awake, hp = row[2], row[3], row[4], row[5], row[6], row[7]
            kind = None
            if state == 1 and awake == 0:
                kind = 'asleep'
            elif state == 2 and team not in (0, 1):
                kind = 'unheld'
            if kind is None:
                continue
            grp = gmeta[gid]
            val = (grp['gems'] + 0.25 * grp['gold']) / (grp['respawn'] + 6)
            # attribute to the team whose half it is on (own); mid counted for both as 'mid'
            for t in (0, 1):
                idle[role[t]][(rel(gid, t), pure_cluster[gid], kind)] += val

    # --- deaths overlapping the window
    deaths = []
    dl = sorted(g.deaths, key=lambda e: e['s'])
    for e in dl:
        r = e['r']
        v = e['v']
        if e.get('linked') is not None:
            continue
        resp = r + 61
        if resp < w0 or r > w1:
            continue
        lost = max(0, min(w1, resp - 1) - max(w0, r) + 1)
        by = e.get('by')
        b = None
        for rr in range(r, max(1, r - 3), -1):
            if (v, rr) in tr:
                b = tr[(v, rr)][0]
                break
        prevcls = cls[v][r - 1] if r > 1 else None
        nb = 2 if name_of[v] in ('Cassi', 'Issac') else 1
        deaths.append({'r': r, 'team': role[team_of[v]], 'type': name_of[v], 'bag': e.get('gems', 0),
                       'killer': name_of.get(by, 'camp') if by is not None else 'camp', 'branch': b, 'prev': prevcls,
                       'lost_rounds': lost * nb, 'in_window': w0 <= r <= w1})

    # --- retreats
    retreats = {'W': Counter(), 'L': Counter()}
    rex = []
    for c in champs:
        cid = c['id']
        t = team_of[cid]
        ro = role[t]
        ty = name_of[cid]
        enemies = [cc for cc in champs if cc['team'] != t]
        for r in range(w0, w1 + 1):
            b = tr.get((cid, r))
            if not b or b[0] != 'R' or cls[cid][r] == 'dead':
                continue
            dmg5 = any(rr in dmg_rounds[cid] for rr in range(r, r + 6))
            cdmg5 = any(rr in champ_hit_rounds[cid] for rr in range(r, r + 6))
            i = max(0, r - 2)
            p = (c['x'][i], c['y'][i]) if c['alive'][i] else None
            nd = 99
            nearest = None
            if p and p[0] is not None:
                for ec in enemies:
                    if ec['alive'][i] and ec['x'][i] is not None:
                        dd = chebyshev(p, (ec['x'][i], ec['y'][i]))
                        if dd < nd:
                            nd, nearest = dd, name_of[ec['id']]
            seen = c['sees'][r - 1] if r - 1 < len(c['sees']) else []
            bag = c['gems'][i] or 0
            band = '<=4' if nd <= 4 else '5-8' if nd <= 8 else '9-12' if nd <= 12 else '>12'
            retreats[ro][(ty, 'dmg' if dmg5 else 'nodmg', 'cdmg' if cdmg5 else 'nocd', band, 'seen' if seen else 'unseen')] += 1
            # did the retreater stop working a group? class next round
    # --- earned per type (capture gems)
    capgems = {'W': Counter(), 'L': Counter()}
    for e in g.events:
        if e['k'] == 'capture' and w0 <= e['r'] <= w1:
            for cid, gems, gold in e['shares']:
                capgems[role[team_of[cid]]][name_of[cid]] += gems
    ser = lambda dd: {('|'.join(map(str, k)) if isinstance(k, tuple) else k): v for k, v in dd.items()}
    return {'dir': d, 'map': g.map_name, 'brk': brk, 'parts': parts, 'gap_end': wealth[Wt][w1 - 1] - wealth[Lt][w1 - 1], 'w0': w0, 'w1': w1, 'n': n,
            'picks': g.picks[Wt], 'picksL': g.picks[Lt],
            'time': {ro: {ty: dict(v) for ty, v in time[ro].items()} for ro in time},
            'br': {ro: {ty: dict(v) for ty, v in br[ro].items()} for ro in br},
            'walk_br': {ro: ser(walk_br[ro]) for ro in walk_br},
            'farm_target': {ro: ser(farm_target[ro]) for ro in farm_target},
            'alive': {ro: dict(alive_rounds[ro]) for ro in alive_rounds},
            'caps': caps, 'idle': {ro: ser(idle[ro]) for ro in idle}, 'deaths': deaths,
            'retreats': {ro: ser(retreats[ro]) for ro in retreats},
            'capgems': {ro: dict(capgems[ro]) for ro in capgems}}


def main():
    idx = json.load(open('/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/index.json'))
    rows = sorted({r['dir'] for r in idx['games'] if 'mirror-study' in r['source']})
    if len(sys.argv) > 1:
        rows = rows[:int(sys.argv[1])]
    out = open('/tmp/mxi-study/farmwin.jsonl', 'w')
    with ProcessPoolExecutor(24) as ex:
        k = 0
        for res in ex.map(work, rows, chunksize=2):
            if res is not None:
                out.write(json.dumps(res) + '\n')
                k += 1
    print('farm games', k)
    out.close()
    print(len(rows))


if __name__ == '__main__':
    main()
