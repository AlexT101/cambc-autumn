"""Scoreboard of lost games: per game, the winner (W) and loser (L) side by side, from extracted replays.

    py research/mac13-argo/scripts/scoreboard.py [--analysis DIR] [--out FILE] [--procs N] [--limit N]

Writes one JSON row per distinct game (gzipped JSONL). Rounds index the state at the END of the round (rounds.json's
index r-1). Wealth = collected gems = tributed + carried; it equals cap + kill bags - bags lost to champions - bags
lost to camps (checked per game: `ident_bad`).
"""

import argparse
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from itertools import accumulate
from multiprocessing import Pool
from pathlib import Path

ROOT = Path('/home/ubuntu/wt/mac13-argo')
ANA = ROOT / 'replays' / 'ana-mirror'
for i, a in enumerate(sys.argv):
    if a == '--analysis' and i + 1 < len(sys.argv):
        ANA = Path(sys.argv[i + 1]).resolve()
os.environ['CAMBC_ANALYSIS'] = str(ANA)
sys.path.insert(0, str(ROOT / 'tools' / 'replay'))

from analysis import Game  # noqa: E402
from analysis import macro  # noqa: E402
from analysis.data import chebyshev  # noqa: E402

CP = [100, 150, 200, 300, 400, 500, 600, 800, 1000]
PHASES = [('p1', 1, 150), ('p2', 151, 400), ('p3', 401, 800), ('p4', 801, 10 ** 6)]
CLASSES = macro.CLASSES
GCLS = ['wolf', 'wolf_cl', 'elk', 'golem', 'gem_cl', 'gold_cl', 'mixed_cl', 'monolith']
ZONES = ['own', 'mid', 'enemy']
RAD = 8
ITEMS = None


def gclass(types):
    s = set(types)
    if 'Monolith' in s:
        return 'monolith'
    if 'Golem' in s:
        return 'golem'
    if 'Elk' in s:
        return 'elk'
    if 'Wolf' in s:
        return 'wolf' if s == {'Wolf'} else 'wolf_cl'
    if s == {'Gem cluster'}:
        return 'gem_cl'
    if s == {'Gold cluster'}:
        return 'gold_cl'
    return 'mixed_cl'


def zone(side, t):
    return 'mid' if side == -1 else 'own' if side == t else 'enemy'


def cum(a):
    return list(accumulate(a))


def items_summary(flat):
    sh = em = eq = 0
    fams = []
    for k in range(0, len(flat or []), 2):
        nm, c = ITEMS[flat[k]], flat[k + 1]
        if 'Emblem' in nm:
            em += c
            eq += c * (25 if nm.startswith('Greed') else 5)
            fams += [nm.split(' Emblem')[0]] * c
        elif 'Shard' in nm:
            sh += c
            eq += c
    return {'sh': sh, 'em': em, 'eq': eq, 'fam': sorted(fams)}


def work(d):
    try:
        return _work(d)
    except Exception as ex:  # keep the pool going; report the failure
        import traceback
        return {'dir': d, 'error': repr(ex), 'tb': traceback.format_exc()}


def _work(d):
    g = Game(d)
    mp, n, R, ev = g.map, g.n_rounds, g.rounds, g.events
    W = g.winner
    L = 1 - W
    team_of, name_of = g.team_of, g.name_of
    champs = R['champions']
    nr = len(R['round'])
    gcls = {grp['id']: gclass(grp['types']) for grp in mp.groups}
    gside = {grp['id']: grp['side'] for grp in mp.groups}
    camp_group = {c['id']: c['group'] for c in mp.camps}
    grate = {grp['id']: grp['gems'] / (grp['respawn'] + 6) for grp in mp.groups}

    def ix(r):  # rounds index for the end of round r
        return max(0, min(r, nr) - 1)

    # ---------- per-round component deltas, per team
    keys = ['cap', 'kg', 'lostc', 'lostm', 'kills', 'deaths', 'cdeaths', 'raid_n', 'raid_g', 'lost_own_n', 'lost_own_g',
            'steal_n', 'steal_g', 'cap_n', 'campdmg', 'spent', 'refund', 'cap_gold'] + \
        ['cap_' + c for c in GCLS] + ['cap_' + z for z in ZONES]
    comp = [{k: [0.0] * (n + 2) for k in keys} for _ in (0, 1)]
    cleared_by = {}
    deaths = []
    tributes = defaultdict(list)   # cid -> [start, gems, dur, outcome, gems_end, end_round]
    open_trib = {}
    type_cap = [Counter(), Counter()]
    type_campdmg = [Counter(), Counter()]
    type_kills = [Counter(), Counter()]
    type_deaths = [Counter(), Counter()]
    type_cdeaths = [Counter(), Counter()]
    camp_hit_round = defaultdict(set)   # group -> rounds with camp damage
    first_kill_r = None
    for e in ev:
        k = e['k']
        r = min(e['r'], n)
        if k == 'capture':
            gid, t = e['g'], e['team']
            gems = sum(s[1] for s in e['shares'])
            gold = sum(s[2] for s in e['shares'])
            z = zone(gside[gid], t)
            C = comp[t]
            C['cap'][r] += gems
            C['cap_gold'][r] += gold
            C['cap_n'][r] += 1
            C['cap_' + gcls[gid]][r] += gems
            C['cap_' + z][r] += gems
            if z == 'enemy':
                C['raid_n'][r] += 1
                C['raid_g'][r] += gems
                comp[1 - t]['lost_own_n'][r] += 1
                comp[1 - t]['lost_own_g'][r] += gems
            cb = cleared_by.pop(gid, None)
            if cb is not None and cb != t:
                C['steal_n'][r] += 1
                C['steal_g'][r] += gems
            for cid, gm, _ in e['shares']:
                type_cap[t][name_of[cid]] += gm
        elif k == 'group_clear':
            if e.get('by') in team_of:
                cleared_by[e['g']] = team_of[e['by']]
        elif k in ('attack', 'cast'):
            if e.get('cdmg'):
                t = team_of[e['a']]
                s = 0.0
                for camp, amt in e['cdmg']:
                    if amt > 0:
                        s += amt
                        gid = camp_group.get(camp)
                        if gid is not None:
                            camp_hit_round[gid].add(e['r'])
                comp[t]['campdmg'][r] += s
                type_campdmg[t][name_of[e['a']]] += s
        elif k == 'death':
            v = e['v']
            t = team_of[v]
            bag = e.get('gems', 0) or 0
            by = e.get('by')
            if by is not None and by in team_of:
                comp[t]['lostc'][r] += bag
                comp[team_of[by]]['kg'][r] += bag
            else:
                comp[t]['lostm'][r] += bag
            if e.get('linked') is not None:
                if deaths and deaths[-1]['r'] == e['r'] and deaths[-1]['team'] == t:
                    deaths[-1]['bag'] += bag
                continue
            comp[t]['deaths'][r] += 1
            type_deaths[t][name_of[v]] += 1
            if by is not None and by in team_of:
                comp[team_of[by]]['kills'][r] += 1
                type_kills[team_of[by]][name_of[by]] += 1
                if first_kill_r is None:
                    first_kill_r = e['r']
            else:
                comp[t]['cdeaths'][r] += 1
                type_cdeaths[t][name_of[v]] += 1
            at = tuple(e['at'])
            i0 = g.start_idx(e['r'])
            allies = sum(1 for c in g.team_ids[t] if c != v and (p := g.pos(c, i0)) and chebyshev(p, at) <= RAD)
            enemies = sum(1 for c in g.team_ids[1 - t] if (p := g.pos(c, i0)) and chebyshev(p, at) <= RAD)
            deaths.append({'r': e['r'], 'team': t, 'type': name_of[v], 'bag': bag,
                           'killer': (name_of[by] if by in team_of else 'camp') if by is not None else 'camp',
                           'outn': enemies > allies + 1, 'allies': allies, 'enemies': enemies,
                           'zone': zone(mp.half(at), t) if mp.half(at) != -1 else 'mid'})
        elif k == 'shop':
            gd = e.get('gold') or 0
            t = team_of[e['a']]
            if gd < 0:
                comp[t]['spent'][r] += -gd
            else:
                comp[t]['refund'][r] += gd
        elif k == 'sell':
            comp[team_of[e['a']]]['refund'][r] += e.get('gold') or 0
        elif k == 'tribute_start':
            open_trib[e['a']] = [e['r'], e['gems'], e.get('dur'), None, None, None]
        elif k in ('tribute_end', 'tribute_cancel'):
            x = open_trib.pop(e['a'], None)
            if x is not None:
                x[3] = 'done' if k == 'tribute_end' else 'cancel:' + str(e.get('cause'))
                x[4] = e.get('gems')
                x[5] = e['r']
                tributes[e['a']].append(x)
    for a, x in open_trib.items():
        x[3] = 'open'
        tributes[a].append(x)
    cc = [{k: cum(v) for k, v in comp[t].items()} for t in (0, 1)]

    # ---------- wealth, identity check
    carried = [[0] * (n + 1) for _ in (0, 1)]
    trib = [[0] * (n + 1) for _ in (0, 1)]
    earned = [[0.0] * (n + 1) for _ in (0, 1)]
    bank = [[0] * (n + 1) for _ in (0, 1)]
    for r in range(1, n + 1):
        i = ix(r)
        for t in (0, 1):
            trib[t][r] = R['gems'][t][i]
        for c in champs:
            t = c['team']
            carried[t][r] += c['gems'][i] or 0
            earned[t][r] += c['earned'][i] or 0
            bank[t][r] += c['gold'][i] or 0
    wealth = [[trib[t][r] + carried[t][r] for r in range(n + 1)] for t in (0, 1)]
    ident_bad = 0
    for t in (0, 1):
        for r in range(1, n + 1):
            x = cc[t]['cap'][r] + cc[t]['kg'][r] - cc[t]['lostc'][r] - cc[t]['lostm'][r]
            if abs(x - wealth[t][r]) > 0.5:
                ident_bad += 1

    # ---------- break rounds
    D = [wealth[W][r] - wealth[L][r] for r in range(n + 1)]
    b0 = max((r for r in range(1, n + 1) if D[r] <= 0), default=0)
    b0s = max((r for r in range(1, n + 1) if D[r] < 0), default=0)
    b100 = max((r for r in range(1, n + 1) if D[r] <= 100), default=0)
    b50 = max((r for r in range(1, n + 1) if D[r] <= 50), default=0)
    lmax = min(D[1:]) if n else 0
    lmax_r = D.index(lmax) if n else 0
    first_lead = next((r for r in range(1, n + 1) if D[r] != 0), 0)

    # ---------- labour (macro classes), alive, cohesion, supply per round
    cls = macro.classify(g)
    lab = [{k: [0] * (n + 2) for k in CLASSES} for _ in (0, 1)]
    per = lambda: [0.0] * (n + 2)  # noqa: E731
    ser = [{k: per() for k in ('alive', 'nn', 'nn_n', 'clus', 'clus_n', 'fieldn',
                               'up_own', 'up_mid', 'up_enemy', 'idle_own', 'idle_mid', 'idle_enemy',
                               'idlev_own', 'idlev_mid', 'idlev_enemy', 'idle1_own', 'idle1_mid', 'idle1_enemy')}
           for _ in (0, 1)]
    type_lab = [defaultdict(Counter), defaultdict(Counter)]
    for c in champs:
        cid, t = c['id'], c['team']
        q = cls[cid]
        for r in range(1, n + 1):
            k = q[r]
            if k is None:
                continue
            lab[t][k][r] += 1
            type_lab[t][name_of[cid]][k] += 1
            if k != 'dead':
                ser[t]['alive'][r] += 1
    # cohesion
    for r in range(1, n + 1):
        i = ix(r)
        for t in (0, 1):
            pts = [((c['x'][i], c['y'][i])) for c in champs if c['team'] == t and c['alive'][i] and c['x'][i] is not None]
            m = len(pts)
            if m == 0:
                continue
            for a in range(m):
                if mp.in_spawn(t, pts[a]):
                    continue
                dn = min((chebyshev(pts[a], pts[b]) for b in range(m) if b != a), default=None)
                ser[t]['fieldn'][r] += 1
                if dn is not None:
                    ser[t]['nn'][r] += dn
                    ser[t]['nn_n'][r] += 1
            # largest cluster, allies linked within RAD
            par = list(range(m))

            def f(x):
                while par[x] != x:
                    par[x] = par[par[x]]
                    x = par[x]
                return x
            for a in range(m):
                for b in range(a + 1, m):
                    if chebyshev(pts[a], pts[b]) <= RAD:
                        par[f(a)] = f(b)
            big = max(Counter(f(a) for a in range(m)).values())
            ser[t]['clus'][r] += big / m
            ser[t]['clus_n'][r] += 1
    # supply: groups up (monsters alive = 1, cleared unclaimed = 2) and not worked this round
    grows = R['groups']
    gi = 0
    gst = {grp['id']: (1, 2) for grp in mp.groups}   # (state, holder team)
    gstats = {c: Counter() for c in GCLS}
    for grp in mp.groups:
        gstats[gcls[grp['id']]]['groups'] += 1
    for r in range(1, n + 1):
        while gi < len(grows) and grows[gi][0] <= r:
            row = grows[gi]
            gst[row[1]] = (row[2], row[3])
            gi += 1
        for gid, (s, holder) in gst.items():
            cl = gcls[gid]
            gstats[cl]['rounds'] += 1
            if s not in (1, 2):
                continue
            gstats[cl]['up'] += 1
            worked = (r in camp_hit_round[gid]) or (s == 2 and holder in (0, 1))
            if not worked:
                gstats[cl]['idle%d' % s] += 1
            for t in (0, 1):
                z = zone(gside[gid], t)
                S = ser[t]
                S['up_' + z][r] += 1
                if not worked:
                    S['idle_' + z][r] += 1
                    S['idlev_' + z][r] += grate[gid]
                    if s == 1:
                        S['idle1_' + z][r] += 1
    for t in (0, 1):
        for k in ('cap_n',):
            pass
    caps_by_cls = [Counter(), Counter()]
    for e in ev:
        if e['k'] == 'capture':
            caps_by_cls[e['team']][gcls[e['g']]] += 1
    for cl in GCLS:
        gstats[cl]['caps0'] = caps_by_cls[0][cl]
        gstats[cl]['caps1'] = caps_by_cls[1][cl]
    sc = [{k: cum(v) for k, v in ser[t].items()} for t in (0, 1)]
    lc = [{k: cum(v) for k, v in lab[t].items()} for t in (0, 1)]

    def win(t, a, b):
        """Window aggregate for team t over rounds a..b inclusive."""
        b = min(b, n)
        if b < a:
            return None
        o = {}
        for k in CLASSES:
            o['L_' + k] = lc[t][k][b] - lc[t][k][a - 1]
        for k, v in sc[t].items():
            o[k] = v[b] - v[a - 1]
        for k in ('campdmg', 'kills', 'deaths', 'cdeaths', 'raid_n', 'raid_g', 'lost_own_n', 'lost_own_g', 'steal_n',
                  'steal_g', 'cap_n', 'cap', 'kg', 'lostc', 'lostm'):
            o[k] = cc[t][k][b] - cc[t][k][a - 1]
        o['rounds'] = b - a + 1
        return o

    def comps_at(t, r):
        r = max(0, min(r, n))
        o = {k: cc[t][k][r] for k in ['cap', 'kg', 'lostc', 'lostm', 'kills', 'deaths', 'cdeaths', 'cap_gold',
                                      'raid_g', 'lost_own_g', 'steal_g', 'spent', 'refund', 'campdmg']
             + ['cap_' + c for c in GCLS] + ['cap_' + z for z in ZONES]}
        o.update(trib=trib[t][r], carried=carried[t][r], wealth=wealth[t][r], earned=round(earned[t][r], 1),
                 bank=bank[t][r])
        return o

    # ---------- items per champion type at r300 / r600 and gold
    items = {}
    for r in (300, 600):
        if r > n:
            continue
        i = ix(r)
        items[str(r)] = [{name_of[c['id']]: items_summary(c['items'][i]) for c in champs if c['team'] == t} for t in (0, 1)]

    # ---------- Prism
    prism = [None, None]
    for c in champs:
        if name_of[c['id']] != 'Prism':
            continue
        t, cid = c['team'], c['id']
        fd = next((x['r'] for x in deaths if x['team'] == t and x['type'] == 'Prism'), None)
        pr = {'id': cid, 'first_death': fd, 'deaths': type_deaths[t]['Prism'], 'kills': type_kills[t]['Prism'],
              'cap': type_cap[t]['Prism'], 'trib': tributes.get(cid, [])}
        for r in (200, 300, 400, 600):
            if r <= n:
                i = ix(r)
                pr[f'foc{r}'] = c['foc'][i]
                pr[f'gems{r}'] = c['gems'][i]
        prism[t] = pr
    all_trib = [[x for cid in g.team_ids[t] for x in tributes.get(cid, [])] for t in (0, 1)]

    # ---------- per-champion-type summary (whole game)
    types = [{} for _ in (0, 1)]
    for t in (0, 1):
        for nm, lab_c in type_lab[t].items():
            alive = sum(v for k, v in lab_c.items() if k != 'dead')
            types[t][nm] = {'alive': alive, 'cap': type_cap[t][nm], 'campdmg': round(type_campdmg[t][nm]),
                            'kills': type_kills[t][nm], 'deaths': type_deaths[t][nm], 'cdeaths': type_cdeaths[t][nm],
                            'lab': dict(lab_c)}

    fn = Path(g.meta['source']).name
    mapfile = fn.split('-', 1)[1].rsplit('-', 1)[0]
    tri = g.final_gems
    row = {
        'dir': d, 'map': mapfile, 'W': W, 'n': n, 'end': '1000' if tri[W] >= 1000 else ('r2000' if n >= 2000 else 'other'),
        'gems': tri, 'picks': g.picks[0], 'npick': len(g.picks[0]), 'mirror_draft': g.picks[0] == g.picks[1],
        'size': [mp.W, mp.H], 'area': mp.W * mp.H, 'sym': mp.symmetry, 'ngroups': len(mp.groups),
        'ident_bad': ident_bad, 'first_kill': first_kill_r, 'first_lead': first_lead,
        'brk': {'b0': b0, 'b0s': b0s, 'b50': b50, 'b100': b100, 'l_lead_max': -lmax, 'l_lead_max_r': lmax_r},
        'D': {str(r): D[min(r, n)] for r in CP},
        'gstats': {k: dict(v) for k, v in gstats.items()},
    }
    marks = sorted(set(CP + [b0, b0s, b50, b100, min(n, b0 + 100), n]))
    for side, t in (('w', W), ('l', L)):
        row[side] = {
            'team': t,
            'at': {str(r): comps_at(t, r) for r in marks},
            'win': {nm: win(t, a, b) for nm, a, b in PHASES} | {
                'pre': win(t, 1, b0), 'r1_300': win(t, 1, 300), 'surge': win(t, b0 + 1, b100), 'post': win(t, b100 + 1, n),
                'brk100': win(t, b0 + 1, b0 + 100), 'game': win(t, 1, n)},
            'items': {r: v[t] for r, v in items.items()},
            'prism': prism[t],
            'trib': [[x[0], x[1], x[3]] for x in all_trib[t]],
            'deaths': [x for x in deaths if x['team'] == t],
            'types': types[t],
            'spent_end': sum(c['stats']['spentGold'] for c in g.champs if c['team'] == t),
        }
    return row


def main():
    global ITEMS
    ap = argparse.ArgumentParser()
    ap.add_argument('--analysis')
    ap.add_argument('--out', default=str(ROOT / 'research/mac13-argo/data/scoreboard.jsonl.gz'))
    ap.add_argument('--procs', type=int, default=24)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    idx = json.loads((ANA / 'index.json').read_text())['games']
    dirs = sorted({r['dir'] for r in idx if r['ok']})
    if a.limit:
        dirs = dirs[:a.limit]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    bad = 0
    with Pool(a.procs, initializer=_init) as pool, gzip.open(a.out, 'wt') as f:
        for k, row in enumerate(pool.imap_unordered(work, dirs, chunksize=4)):
            if 'error' in row:
                bad += 1
                print('ERR', row['dir'], row['error'], row['tb'][-600:], file=sys.stderr)
                continue
            f.write(json.dumps(row, separators=(',', ':')) + '\n')
            if k % 250 == 0:
                print(k, len(dirs), file=sys.stderr, flush=True)
    print('done', len(dirs) - bad, 'rows', bad, 'errors', file=sys.stderr)


def _init():
    global ITEMS
    p = ANA / 'enums.json'
    if not p.exists():
        p = Path('/home/ubuntu/cambc-autumn/replays/.analysis/enums.json')
    ITEMS = json.loads(p.read_text())['items']


if __name__ == '__main__':
    _init()
    main()
