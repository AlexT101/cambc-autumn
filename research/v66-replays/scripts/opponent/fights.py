# Q2 per-game fight-behaviour features for both teams -> opp/fightfeat/<dir>.json
# Run from repo root.
import sys, os, json
from collections import defaultdict, Counter, deque
from multiprocessing import Pool
sys.path.insert(0, 'research/v66-replays/scripts/extract')
sys.path.insert(0, 'research/v66-replays/scripts/opponent')
from common import *
from feat import bfs
OUT = S + '/opp/fightfeat'
RANGED = {'Vesper Vale', 'Prism', 'Stellar', 'Tavi', 'Willow', 'Cassi'}


def bucket_diff(d):
    return '<=-2' if d <= -2 else ('>=+2' if d >= 2 else f'{d:+d}')


def one(r):
    d = r['dir']
    m = meta(d); mj = mapj(m); ev = events(d); R = rounds(d)
    us = r['us']; N = len(R['round'])
    ch = R['champions']
    ids = [c['id'] for c in ch]
    ix = {c['id']: i for i, c in enumerate(ch)}
    team = {c['id']: c['team'] for c in ch}
    name = {c['id']: c['name'] for c in m['champions']}
    D = [bfs(mj, 0), bfs(mj, 1)]
    pk = [('CI', c['team']) if name[c['id']] in ('Cassi', 'Issac') else i for i, c in enumerate(ch)]  # Cassi & Issac count as one pick
    role = lambda t: 'us' if t == us else 'them'

    def P(i, ri):
        c = ch[i]
        if ri < 0 or ri >= N or not c['alive'][ri] or c['x'][ri] is None: return None
        return (c['x'][ri], c['y'][ri])
    pos = [[P(i, ri) for ri in range(N)] for i in range(len(ch))]
    out = defaultdict(Counter)   # key: role|measure -> Counter
    ex = defaultdict(list)        # examples

    def add(t, meas, key, v=1):
        out[role(t) + '|' + meas][key] += v

    # ---- (a) local advantage response; (c) low-hp behaviour
    for ri in range(N - 10):
        rr = R['round'][ri]
        alive = [i for i in range(len(ch)) if pos[i][ri] is not None]
        for i in alive:
            c = ch[i]; t = c['team']; p = pos[i][ri]
            if D[t].get(p, 99) == 0 or c['chan'][ri] in (2, 3): continue
            en = [j for j in alive if ch[j]['team'] != t]
            if not en: continue
            dists = {j: cheb(p, pos[j][ri]) for j in en}
            e = min(dists, key=dists.get); d0 = dists[e]
            if d0 > 8: continue
            seen = ch[e]['id'] in (c['sees'][ri + 1] or []) if ri + 1 < N else False
            A = [j for j in alive if ch[j]['team'] == t and cheb(p, pos[j][ri]) <= 8]
            E = [j for j in en if dists[j] <= 8]
            nA = len({pk[j] for j in A}); nE = len({pk[j] for j in E})
            hpA = sum(ch[j]['hp'][ri] for j in A); hpE = sum(ch[j]['hp'][ri] for j in E)
            if pos[i][ri + 2] is None:
                outc = 'died'
            else:
                en2 = [pos[j][ri + 2] for j in range(len(ch)) if ch[j]['team'] != t and pos[j][ri + 2] is not None]
                d2 = min((cheb(pos[i][ri + 2], q) for q in en2), default=99)
                outc = 'close' if d2 < d0 else ('open' if d2 > d0 else 'hold')
            if d0 <= 5 and seen:
                add(t, 'adv_cnt', bucket_diff(nA - nE) + '|' + outc)
                ratio = hpA / max(1, hpE)
                hb = '<0.5' if ratio < 0.5 else '0.5-0.8' if ratio < 0.8 else '0.8-1.25' if ratio < 1.25 else '1.25-2' if ratio < 2 else '>2'
                add(t, 'adv_hp', hb + '|' + outc)
            # low hp self behaviour
            frac = c['hp'][ri] / c['maxHp'][ri]
            if frac < 0.3 and d0 <= 8 and (ri == 0 or ch[i]['hp'][ri - 1] / ch[i]['maxHp'][ri - 1] >= 0.3):
                # first round below 30% (episode start)
                res = 'stay'
                for k in range(1, 11):
                    if pos[i][ri + k] is None: res = 'died'; break
                    if D[t].get(pos[i][ri + k], 99) == 0: res = 'home'; break
                # how: did it keep a recall (channel 1 with chanT<=3 at some round end) before home
                rec = any(ch[i]['chan'][ri + k] == 1 and ch[i]['chanT'][ri + k] <= 3 for k in range(1, 6) if ri + k < N)
                d3 = None
                if pos[i][ri + 3] is not None:
                    en3 = [pos[j][ri + 3] for j in range(len(ch)) if ch[j]['team'] != t and pos[j][ri + 3] is not None]
                    d3 = min((cheb(pos[i][ri + 3], q) for q in en3), default=99)
                mv = 'na' if d3 is None else ('open' if d3 > d0 else 'close' if d3 < d0 else 'hold')
                add(t, 'lowhp', f'{res}|rec{int(rec)}|{mv}')
                add(t, 'lowhp_dn', f'{res}|nE{min(len(E),3)}nA{min(len(A),3)}')
            # chase: enemy e' low hp within 8 of c (count once per (enemy, round-of-entry) at enemy side)
    # chase (from hunters' side): for each victim episode start, how many hunters close in, killed by hunters, depth
    for ri in range(1, N - 10):
        for v in range(len(ch)):
            p = pos[v][ri]
            if p is None: continue
            tv = ch[v]['team']
            frac = ch[v]['hp'][ri] / ch[v]['maxHp'][ri]
            if not (frac < 0.3 and ch[v]['hp'][ri - 1] / ch[v]['maxHp'][ri - 1] >= 0.3): continue
            if D[tv].get(p, 99) == 0: continue
            H = [j for j in range(len(ch)) if ch[j]['team'] != tv and pos[j][ri] is not None and cheb(pos[j][ri], p) <= 8]
            if not H: continue
            ht = 1 - tv
            closing = 0
            for j in H:
                if pos[j][ri + 2] is not None and pos[v][ri + 2] is not None and cheb(pos[j][ri + 2], pos[v][ri + 2]) < cheb(pos[j][ri], p): closing += 1
            add(ht, 'chase_closers', f'{closing}of{min(len(H),3)}')
            # victim's own-side depth: walk dist to victim's own spawn
            depth = D[tv].get(p, 99)
            dv = D[tv].get(p, 99); dh = D[ht].get(p, 99)
            add(ht, 'chase_where', 'victim_own_half' if dv < dh else 'hunter_own_half')
    # ---- event pass: positions/hp at action moments
    curpos = {}; curhp = {}; curgems = {}
    deaths = []
    by_round_dmg = defaultdict(lambda: defaultdict(list))  # (round)->team->[(att, tgt, amt)]
    prev_r = 0
    dmg_pair = Counter()
    dash = []
    for e in ev:
        rr = e['r']
        if rr != prev_r:
            ri = rr - 2
            for i, c in enumerate(ch):
                curpos[c['id']] = pos[i][ri] if ri >= 0 else None
                curhp[c['id']] = c['hp'][ri] if ri >= 0 else c['maxHp'][0]
                curgems[c['id']] = c['gems'][ri] if ri >= 0 else 0
            prev_r = rr
        k = e['k']
        if k == 'move': curpos[e['a']] = tuple(e['to'])
        elif k in ('respawn', 'recall_end', 'teleport_end'):
            curpos[e['a']] = tuple(e.get('at') or e.get('to'))
        elif k == 'death':
            deaths.append(e); curpos[e['v']] = None
        elif k in ('attack', 'cast'):
            a = e['a']; t = team[a]
            f = tuple(e['f'])
            if k == 'cast' and e.get('ab') == 'Dash' and e.get('moved'):
                land = tuple(e['moved'])
                en = [(c, curpos[c]) for c in ids if team[c] != t and curpos.get(c) is not None]
                if en:
                    b0 = min(cheb(f, q) for _, q in en); b1 = min(cheb(land, q) for _, q in en)
                    if b0 <= 8:
                        dash.append(dict(r=rr, a=a, t=t, b0=b0, b1=b1, stun=len(e.get('stun', [])), hit=len([x for x in e.get('dmg', []) if team.get(x[0]) is not None]),
                                         depth=D[1 - t].get(land, 99), own=D[t].get(land, 99)))
                curpos[a] = land
            hits = [(x, amt) for x, amt in e.get('dmg', []) if x in team and team[x] != t]
            for x, amt in hits:
                dmg_pair[(name[a], name[x], role(t))] += amt
                by_round_dmg[rr][t].append((a, x, amt))
                tp = curpos.get(x)
                if tp is not None:
                    dd = cheb(f, tp)
                    add(t, 'dmg_dist', ('ranged' if name[a] in RANGED else 'melee') + '|' + ('>=2' if dd >= 2 else '<=1'), amt)
            # target selection for single-target hits
            tgt = e.get('tgt')
            if tgt is not None and tgt in team and team[tgt] != t and (k == 'attack' or e.get('ab') in ('Damage', 'CC')):
                rng = 4 if k == 'cast' else (3 if name[a] in RANGED else 1)
                cand = [c for c in ids if team[c] != t and curpos.get(c) is not None and cheb(f, curpos[c]) <= rng]
                if tgt not in cand: cand.append(tgt)
                if len(cand) >= 2:
                    hp = {c: curhp[c] for c in cand}
                    fr = {c: curhp[c] / ch[ix[c]]['maxHp'][max(0, rr - 2)] for c in cand}
                    add(t, 'tsel', 'n')
                    add(t, 'tsel', 'lowhp', int(hp[tgt] == min(hp.values())))
                    add(t, 'tsel', 'lowfrac', int(fr[tgt] == min(fr.values())))
                    add(t, 'tsel', 'chance', 1 / len(cand))
                    gm = {c: curgems.get(c, 0) for c in cand}
                    if len(set(gm.values())) > 1:
                        add(t, 'tsel', 'gn'); add(t, 'tsel', 'maxgems', int(gm[tgt] == max(gm.values()))); add(t, 'tsel', 'gchance', 1 / len(cand))
                    if any(name[c] == 'Prism' for c in cand):
                        add(t, 'tsel', 'pn'); add(t, 'tsel', 'prism', int(name[tgt] == 'Prism')); add(t, 'tsel', 'pchance', 1 / len(cand))
            for x, amt in hits:
                curhp[x] = curhp.get(x, 0) - amt
        if k == 'capture':
            for cid, gm, gold in e['shares']: curgems[cid] = curgems.get(cid, 0) + gm
    # focus fire
    for rr, tt in by_round_dmg.items():
        for t, lst in tt.items():
            att = {a for a, x, _ in lst}
            if len(att) < 2: continue
            tg = Counter()
            for a, x, amt in lst: tg[x] += amt
            main = tg.most_common(1)[0][0]
            share = tg[main] / sum(tg.values())
            add(t, 'focus', 'rounds')
            add(t, 'focus', 'share', share)
            add(t, 'focus', 'all_one', int(len(tg) == 1))
    # dash outcomes
    death_by = [(e['r'], e['v'], e.get('by')) for e in deaths]
    for x in dash:
        t = x['t']
        kind = 'engage' if x['b1'] < x['b0'] else ('escape' if x['b1'] > x['b0'] else 'lateral')
        kill = any(rr - x['r'] in range(0, 4) and by is not None and team.get(by) == t and team[v] != t for rr, v, by in death_by)
        died = any(rr - x['r'] in range(0, 6) and v == x['a'] for rr, v, by in death_by)
        nm = name[x['a']]
        add(t, 'dash', f'{nm}|{kind}')
        add(t, 'dash', f'{nm}|{kind}|kill', int(kill)); add(t, 'dash', f'{nm}|{kind}|died', int(died))
        add(t, 'dash', f'{nm}|{kind}|adj', int(x['b1'] <= 1))
        add(t, 'dash', f'{nm}|{kind}|deep', int(x['depth'] <= 8))
        add(t, 'dash', f'{nm}|{kind}|stun', int(x['stun'] > 0))
        if kind == 'engage' and x['depth'] <= 6 and len(ex[role(t) + '|deepdash']) < 5:
            ex[role(t) + '|deepdash'].append((x['r'], nm, x['depth']))
    # (f) kill opportunities at round end: enemy hp <= strength of a champion in reach (ranged<=3, melee<=2)
    for ri in range(N - 1):
        for v in range(len(ch)):
            p = pos[v][ri]
            if p is None: continue
            tv = ch[v]['team']
            if D[tv].get(p, 99) == 0: continue
            hunters = []
            for j in range(len(ch)):
                if ch[j]['team'] == tv or pos[j][ri] is None or ch[j]['chan'][ri] in (2, 3): continue
                reach = 3 if name[ch[j]['id']] in RANGED else 2
                if cheb(pos[j][ri], p) <= reach and ch[j]['str'][ri] >= ch[v]['hp'][ri]: hunters.append(j)
            if not hunters: continue
            ht = 1 - tv
            died = pos[v][ri + 1] is None
            killed_by = None
            if died:
                for e in deaths:
                    if e['r'] == ri + 2 and e['v'] == ch[v]['id']: killed_by = e.get('by'); break
            res = 'killed' if died and killed_by is not None and team.get(killed_by) == ht else ('died_other' if died else 'survived')
            add(ht, 'killopp', res)
            if res == 'survived' and len(ex[role(ht) + '|missed']) < 6:
                ex[role(ht) + '|missed'].append((R['round'][ri] + 1, name[ch[v]['id']], round(ch[v]['hp'][ri]), [name[ch[j]['id']] for j in hunters]))
    res = dict(dir=d, map=r['map'], opp=r['opp'], us=us, won=r['won'], source=r['source'],
               out={k: dict(v) for k, v in out.items()}, ex=ex,
               dmg_pair=[[a, b, ro, v] for (a, b, ro), v in dmg_pair.items()])
    with open(f'{OUT}/{d}.json', 'w') as f:
        json.dump(res, f)
    return d


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    gs = games()
    if len(sys.argv) > 2: gs = gs[:int(sys.argv[2])]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 40) as p:
        for d in p.imap_unordered(one, gs): pass
    print('done', len(gs))
