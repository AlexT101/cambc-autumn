"""steps.py OUT.pkl [NPROC]: every champion turn that ends on a tile other than its start, in live v83+ scrims vs Fish/Mite,
with the enemies' one-turn strike bound (compute_strike's, walls ignored) at the end and start tiles, who acts before the
mover's next turn, and the outcome (death before its next turn, kills on its turn and in the window)."""
import gzip, json, os, sys, collections, pickle
import numpy as np
from multiprocessing import Pool

US = '547efb5b-57e5-4355-8501-3b331f506d62'
# type: ranged, basic reach, abilities [(kind, mult, reach, stuns, excl)], kinds: reset, dash, land, dmg, stun, none
F = {
    'Ryth': (False, 1, [('dmg', 1.0, 5, True), ('reset', 0, 0, False)]),
    'Vesper Vale': (True, 3, [('reset', 0, 0, False), ('dash', 0, 2, False)]),
    'Vendetta': (False, 1, [('reset', 0, 0, False), ('dash', 0, 2, False)]),
    'Cassi': (True, 3, [('dmg', 2.0, 4, False), ('stun', 0, 5, True)]),
    'Issac': (False, 1, [('reset', 0, 0, False), ('dash', 0, 2, False)]),
    'Stellar': (True, 3, [('dmg', 2.0, 4, False), ('dmg', 1.4, 5, False)]),
    'Prism': (True, 3, [('dmg', 1.5, 4, True), ('dmg', 1.0, 5, False)]),
    'Marcella': (False, 1, [('reset', 0, 0, True), ('dmg', 2.0, 4, False)]),
    'Willow': (True, 3, [('none', 0, 0, False), ('reset', 0, 0, False)]),
    'Ren': (False, 1, [('dmg', 1.1, 4, True), ('dash', 0, 2, False)]),
    'Varg': (False, 2, [('reset', 0, 0, False), ('none', 0, 0, False)]),
    'Tavi': (True, 3, [('reset', 0, 0, False), ('dmg', 1.6, 4, True)]),
    'Heart of Ruin': (False, 1, [('none', 0, 0, False), ('land', 1.5, 2, True)]),
}
MAXR = 6


def strike(name, s, f, slots):
    ranged, basic, abil = F[name]
    rng = 3 if ranged else 1
    walk = 0 if ranged else 1
    out = np.zeros(MAXR + 1)

    def add(reach, dmg):
        reach = min(reach, MAXR)
        out[:reach + 1] = np.maximum(out[:reach + 1], dmg)
    add(basic + walk, s)
    for k, (kind, m, reach, st) in enumerate(abil):
        if not (slots >> k & 1): continue
        if kind == 'reset':
            add(basic + walk, 2 * s)
            if ranged: add(basic + 1, s)
        elif kind == 'dash':
            add(basic + walk + 2, s)
        elif kind == 'land':
            add(walk + 2 + 1, m * f); add(walk + 2 + 1, m * f + s)
            add(basic + walk + 2, s)
        elif kind == 'dmg':
            add(reach, m * f); add(rng, m * f + s)
        elif kind == 'stun':
            add(reach, 0.0)
    return out


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def in_rect(p, b): return b['minX'] <= p[0] <= b['maxX'] and b['minY'] <= p[1] <= b['maxY']


def one(arg):
    d, g = arg
    try:
        m = json.load(open(os.path.join(d, 'meta.json')))
        mp = json.load(open(os.path.join(d, m['mapFile'])))
        R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    except Exception:
        return None
    us = 0 if g['side'] == 'a' else 1
    br = {}; ngl = {}
    if g.get('replay'):
        import zipfile, re
        with zipfile.ZipFile(g['replay']) as z:
            o = z.read('team-' + 'ab'[us] + '.stdout').replace(b'\0', b'').decode('utf-8', 'replace')
        for mm in re.finditer(r'^D (\d+) (\d+) (\S) ', o, re.M): br[(int(mm[1]), int(mm[2]))] = mm[3]
        for mm in re.finditer(r'^NG (\d+) (\d+) (\S) (\S*) (\d) (\d) (-?\d+) (-?\d+) ', o, re.M):
            ngl[(int(mm[1]), int(mm[2]))] = (mm[4], int(mm[5]), int(mm[6]), int(mm[7]) >= 0, int(mm[8]) >= 0)
    rounds = R['round']; IX = {r: i for i, r in enumerate(rounds)}
    champs = R['champions']; ids = [c['id'] for c in champs]; n = len(ids)
    pix = {cid: j for j, cid in enumerate(ids)}
    name = {c['id']: c['name'] for c in m['champions']}
    NM = [name[c] for c in ids]
    TEAM = np.array([c['team'] for c in champs])
    X = [c['x'] for c in champs]; Y = [c['y'] for c in champs]
    HP = [c['hp'] for c in champs]; SH = [c['shield'] for c in champs]; MHP = [c['maxHp'] for c in champs]
    STR = [c['str'] for c in champs]; FOC = [c['foc'] for c in champs]; GEM = [c['gems'] for c in champs]
    CD0 = [c['cd0'] for c in champs]; CD1 = [c['cd1'] for c in champs]; AL = [c['alive'] for c in champs]
    PR = [c['prio'] for c in champs]
    SEES = [c['sees'] for c in champs]
    link = {}
    for j in range(n):
        if NM[j] in ('Cassi', 'Issac'):
            for k in range(n):
                if k != j and TEAM[k] == TEAM[j] and NM[k] in ('Cassi', 'Issac') and NM[k] != NM[j]: link[j] = k
    SP = mp['spawn']
    W, Hh = mp['width'], mp['height']
    blocked = set(map(tuple, mp['walls'])) | set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars']))
    for c in mp['camps']: blocked.add((c['x'], c['y']))
    order = {}
    for i, r in enumerate(rounds):
        pi = IX.get(r - 1)
        pr = [PR[j][pi] if pi is not None else 0 for j in range(n)]
        tl = [sorted([j for j in range(n) if TEAM[j] == t], key=lambda j: (-pr[j], ids[j])) for t in (0, 1)]
        st = 0 if r % 2 == 1 else 1
        seq = []; a, b = list(tl[st]), list(tl[1 - st])
        while a or b:
            if a: seq.append(a.pop(0))
            if b: seq.append(b.pop(0))
        order[r] = seq
    G = lambda r, t: r * 64 + t
    seats = collections.defaultdict(list)
    for r in rounds:
        for t, j in enumerate(order[r]): seats[j].append(G(r, t))
    seat_arr = {j: np.array(v) for j, v in seats.items()}

    def next_seat(j, gg):
        a = seat_arr[j]; k = np.searchsorted(a, gg, side='right')
        return int(a[k]) if k < len(a) else 1 << 40

    byturn = collections.defaultdict(list)
    deaths = []
    for e in ev:
        if e['k'] == 'death':
            deaths.append((e['s'], G(e['r'], e.get('t', -1) if e.get('t', -1) >= 0 else 0), pix[e['v']], pix.get(e.get('by'), -1), e.get('gems', 0) or 0))
        if 'a' in e and e.get('t', -1) >= 0 and e['a'] in pix: byturn[(e['r'], e['t'])].append(e)
    death_s = collections.defaultdict(list)
    for s, gg, v, by, gems in deaths: death_s[v].append((s, gg, by, gems))
    # damage and stuns in seq order, per round
    dmg_ev = collections.defaultdict(list)
    for e in ev:
        if e['k'] in ('attack', 'cast', 'camp_attack'):
            dl = e.get('dmg', []) or []
            if isinstance(dl, (int, float)): dl = [(e.get('tgt'), dl)]
            for v, x in dl:
                if v in pix: dmg_ev[e['r']].append((e['s'], pix[v], x))
            for v in e.get('stun', []) or []:
                if v in pix: dmg_ev[e['r']].append((e['s'], pix[v], None))
    rows = []
    stunned = set()  # champions whose next turn a stun takes
    for i, r in enumerate(rounds):
        if i == 0: continue
        pi = i - 1
        pos = [(X[j][pi], Y[j][pi]) for j in range(n)]
        hp = [(HP[j][pi] or 0) + (SH[j][pi] or 0) for j in range(n)]
        alive = [bool(AL[j][pi]) and X[j][pi] is not None for j in range(n)]
        de = sorted(dmg_ev.get(r, []), key=lambda z: z[0])
        di = 0
        for t, j in enumerate(order[r]):
            evs = byturn.get((r, t), [])
            start = pos[j]
            was_alive = alive[j]
            lost = j in stunned
            stunned.discard(j)
            last_s = None
            killed_now = []
            dealt = 0.0
            for e in evs:
                last_s = e['s']
                if e['k'] in ('attack', 'cast'):
                    for v, x in (e.get('dmg') or []):
                        if v in pix and TEAM[pix[v]] != TEAM[j]: dealt += x
                if e['k'] == 'move' and e.get('to'): pos[j] = tuple(e['to'])
                if e['k'] == 'cast' and e.get('moved'): pos[j] = tuple(e['moved'])
            # apply damage/stuns up to the end of this turn
            end_s = last_s if last_s is not None else -1
            while di < len(de) and (end_s >= 0 and de[di][0] <= end_s):
                s, v, x = de[di]
                if x is None:
                    if NM[v] != 'Marcella': stunned.add(v)
                else: hp[v] -= x
                di += 1
            for (s, gg, by, gems) in death_s.get(j, []):
                pass
            for v in range(n):
                for (s, gg, by, gems) in death_s.get(v, []):
                    if gg == G(r, t) and alive[v]:
                        alive[v] = False
                        if by == j: killed_now.append(v)
            if not was_alive or start[0] is None or pos[j][0] is None or lost: continue
            moved = int(start != pos[j])
            # the mover's window: from its seat to its next
            g0 = G(r, t); g1 = next_seat(j, g0)
            T = TEAM[j]
            H = hp[j]
            if in_rect(pos[j], SP[T]): H = MHP[j][pi] + (SH[j][pi] or 0)
            foes = []
            for k in range(n):
                if TEAM[k] == T or not alive[k] or pos[k][0] is None: continue
                ks = seat_arr[k]
                turns = int(np.searchsorted(ks, g1, side='left') - np.searchsorted(ks, g0, side='right'))
                if k in stunned and turns: turns -= 1
                if turns <= 0: continue
                # cooldown as at its next turn: it acted this round already -> end of round r snapshot
                acted = any(G(r, tt) < g0 and jj == k for tt, jj in enumerate(order[r]))
                ci = i if acted else pi
                slots = (1 if CD0[k][ci] == 0 else 0) | (2 if CD1[k][ci] == 0 else 0)
                f = (FOC[k][pi] or 0) + (1.5 * (GEM[k][pi] or 0) if NM[k] == 'Prism' else 0)
                s_ = STR[k][pi] or 0
                full = strike(NM[k], s_, f, slots); basic = strike(NM[k], s_, f, 0)
                foes.append((k, pos[k], turns, full, basic, s_))
            if not foes: continue

            seen = set(SEES[j][pi] or []) | set(SEES[j][i] or [])
            seen = {pix[x] for x in seen if x in pix}

            def zone(p, only_seen=False):
                single = -1; total = 0.0; tb = 0.0; near = 0
                for (k, q, turns, full, basic, s_) in foes:
                    if only_seen and k not in seen: continue
                    dd = cheb(p, q)
                    if dd > MAXR: continue
                    near += 1
                    ranged = F[NM[k]][0]
                    br = F[NM[k]][1] + (0 if ranged else 1)
                    x = full[dd] + (s_ * (turns - 1) if dd <= br else 0)
                    b = basic[max(0, dd - (turns - 1))] * turns
                    total += x; tb += b
                    if full[dd] >= H and b < H and single < 0: single = k
                return single, total, tb, near
            s_to, tot_to, tb_to, near_to = zone(pos[j])
            occ = {pos[k] for k in range(n) if alive[k] and k != j}
            esc = 0; nb = 0
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (start[0] + dx, start[1] + dy)
                    if (dx or dy) and 0 <= q[0] < W and 0 <= q[1] < Hh and q not in blocked and q not in occ and not in_rect(q, SP[1 - T]):
                        nb += 1
                        zs, zt, _, _ = zone(q)
                        if zs < 0 and zt < H: esc += 1
            allies_near = sum(1 for k in range(n) if k != j and TEAM[k] == T and alive[k] and pos[k][0] is not None and cheb(pos[k], pos[j]) <= 4)
            nk_turns = next((tt for (k, q, tt, *_ ) in foes if k == s_to), 0)
            nk_ratio = next((full[min(MAXR, cheb(pos[j], q))] / max(H, 1) for (k, q, tt, full, *_ ) in foes if k == s_to), 0)
            s_fr, tot_fr, tb_fr, near_fr = zone(start)
            sv_to, svt_to, _, _ = zone(pos[j], True)
            sv_fr, svt_fr, _, _ = zone(start, True)
            if tot_to <= 0 and tot_fr <= 0: continue
            died = None
            for (s, gg, by, gems) in death_s.get(j, []):
                if g0 < gg < g1: died = (by, gems, TEAM[by] if by >= 0 else -1)
            # the window's kills by our side before our death (or before g1)
            dg = g1
            if died is not None:
                for (s, gg, by, gems) in death_s.get(j, []):
                    if g0 < gg < g1: dg = gg
            team_kills = 0; foe_dead = set()
            for v in range(n):
                if TEAM[v] == T: continue
                for (s, gg, by, gems) in death_s.get(v, []):
                    if g0 <= gg < dg and by >= 0 and TEAM[by] == T: team_kills += 1; foe_dead.add(v)
            rows.append(dict(ng=ngl.get((r, ids[j])) if T == us else None, sv_to=sv_to, svt_to=svt_to, sv_fr=sv_fr, svt_fr=svt_fr, br=br.get((r, ids[j]), '') if T == us else '', esc=esc, nb=nb, allies_near=allies_near, nk_turns=nk_turns, nk_ratio=nk_ratio, moved=moved, ours=int(T == us), r=r, j=j, type=NM[j], H=H, maxH=MHP[j][pi], gems=GEM[j][pi] or 0,
                             d=cheb(start, pos[j]), s_to=s_to, s_fr=s_fr, tot_to=tot_to, tot_fr=tot_fr, tb_to=tb_to, tb_fr=tb_fr,
                             nfoe=len(foes), near_to=near_to, killed_now=len(killed_now), team_kills=team_kills,
                             nuker_dead=int(s_to >= 0 and s_to in foe_dead), single_type=NM[s_to] if s_to >= 0 else '',
                             dealt=dealt, killer=NM[died[0]] if died and died[0] >= 0 else '', killer_is_nuker=int(bool(died) and died[0] == s_to and s_to >= 0),
                             closer=min([cheb(pos[j], q) for (k, q, *_ ) in foes]) - min([cheb(start, q) for (k, q, *_ ) in foes]),
                             spawn_to=int(in_rect(pos[j], SP[T])),
                             died=int(died is not None), died_champ=int(died is not None and died[2] >= 0),
                             died_gems=died[1] if died else 0, nalive_foes=sum(1 for k in range(n) if TEAM[k] != T and alive[k])))
    ourdeaths = sum(1 for (ss, gg, v, by, gems) in deaths if TEAM[v] == us and by >= 0)
    ourkills = sum(1 for (ss, gg, v, by, gems) in deaths if TEAM[v] != us and by >= 0 and TEAM[by] == us)
    return dict(od=ourdeaths, ok=ourkills, bot=g.get('bot', ''), dir=d, ver=g['version'], opp=g['opp'], win=g['result'] == 'win', rows=rows)


def main():
    out = sys.argv[1]; npr = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    games = json.load(open('/home/ubuntu/tmp-offload/nukeguard2/games.json'))
    work = []
    if os.environ.get('JOBS'):
        work = pickle.load(open(os.environ['JOBS'], 'rb')); games = {}
    for base in ('/home/ubuntu/tmp-offload/engage/analysis', '/home/ubuntu/tmp-offload/nukeguard2/ana'):
        if not os.path.exists(base + '/index.json'): continue
        for x in json.load(open(base + '/index.json'))['games']:
            mid = os.path.basename(x['source']).split('.')[0]
            if mid in games and x.get('ok', True) and games[mid]['version'] >= 83: work.append((base + '/' + x['dir'], games[mid]))
    seen = set(); w2 = []
    for d, g in work:
        if d in seen: continue
        seen.add(d); w2.append((d, g))
    if len(sys.argv) > 3: w2 = w2[:int(sys.argv[3])]
    with Pool(npr) as p: res = [x for x in p.imap_unordered(one, w2, chunksize=4) if x]
    pickle.dump(res, open(out, 'wb'))
    print(len(res), sum(len(x['rows']) for x in res))


if __name__ == '__main__':
    main()
