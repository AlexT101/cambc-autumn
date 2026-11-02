"""Turn-order measurements from replays alone (no trace): priority churn per team (metric 2), round-boundary
doubles (metric 3) and kill conversion (metric 6).

usage: python3 research/turn-order-2026-11-02/scripts/replay_only.py EXTRACT_DIR OUT.pkl [--source-prefix P]
"""
import pickle
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tolib import G, cheb, index  # noqa: E402

CONTACT = 4


def near_enemy(g, c, r, rad=CONTACT):
    p = g.pos(c, r)
    if p is None:
        return False
    for e in g.members[1 - g.team[c]]:
        q = g.pos(e, r)
        if q is not None and cheb(p, q) <= rad:
            return True
    return False


def on_spawn(g, c, r):
    p = g.pos(c, r)
    if p is None:
        return False
    sp = g.map_spawn[g.team[c]]
    return sp['minX'] <= p[0] <= sp['maxX'] and sp['minY'] <= p[1] <= sp['maxY']


def one(args):
    ex, row = args
    try:
        g = G(ex, row['dir'])
    except Exception as e:  # noqa: BLE001
        return {'error': str(e)}
    import json
    mp = json.load(open(f"{ex}/maps/{g.meta['map']['hash']}.json"))
    g.map_spawn = mp['spawn']
    names = row['teams']
    out = {'dir': row['dir'], 'teams': names, 'winner': g.meta['result']['winner'], 'rounds': g.N,
           'sizes': [len(g.members[0]), len(g.members[1])], 'source': row['source']}
    contact = {}
    for r in range(0, g.N + 1):
        for c in g.ids:
            contact[(c, r)] = r >= 1 and near_enemy(g, c, r)
    # ---- metric 2: churn
    churn = [Counter(), Counter()]
    for t in (0, 1):
        k = churn[t]
        prev_order = g.team_order(t, 1)
        for r in range(1, g.N):
            for c in g.members[t]:
                if not g.alive(c, r):
                    continue
                ch = g.prio(c, r) != g.prio(c, r - 1)
                k['cr'] += 1
                k['cr_changed'] += ch
                if contact[(c, r - 1)]:
                    k['cr_contact'] += 1
                    k['cr_contact_changed'] += ch
            o_next = g.team_order(t, r + 1)
            o_now = g.team_order(t, r)
            k['rounds'] += 1
            k['order_changed'] += o_next != o_now
            inc = [c for c in g.members[t] if contact[(c, r)]]
            outc = [c for c in g.members[t] if g.alive(c, r) and not contact[(c, r)]]
            if inc and outc:
                k['mixed'] += 1
                k['mixed_top_contact'] += o_next[0] in inc
                k['mixed_share'] += len(inc) / (len(inc) + len(outc))
                for c in inc:
                    if o_now[0] != c:
                        k['contact_not_top'] += 1
                        k['contact_jump_top'] += o_next[0] == c
                for c in outc:
                    if o_now[0] != c:
                        k['quiet_not_top'] += 1
                        k['quiet_jump_top'] += o_next[0] == c
            # rank of in-contact vs others, any team composition
            for c in g.members[t]:
                if g.alive(c, r) and contact[(c, r)]:
                    k['contact_rank_moved'] += o_next.index(c) != o_now.index(c)
                    k['contact_rank_up'] += o_next.index(c) < o_now.index(c)
            for c in g.members[t]:
                if g.alive(c, r):
                    key = 'contact' if contact[(c, r)] else 'quiet'
                    k[key + '_n'] += 1
                    k[key + '_rank'] += o_next.index(c) / max(1, len(o_next) - 1)
        k['never_changes'] = int(k['cr_changed'] == 0)
    out['churn'] = churn
    # ---- metric 3: boundary doubles, and in-contact single turns as the control
    dbl = [Counter(), Counter()]
    for r in range(1, g.N):
        seq_r, slot_r, _ = g.order(r)
        seq_n, slot_n, _ = g.order(r + 1)
        a, b = seq_r[-1], seq_n[0]
        if g.team[a] != g.team[b]:
            continue
        t = g.team[a]
        k = dbl[t]
        k['boundaries'] += 1
        same = a == b
        k['same'] += same
        la, lb = g.alive(a, r) and g.pos(a, r) is not None, g.alive(b, r) and g.pos(b, r) is not None
        ca, cb = la and contact[(a, r)], lb and contact[(b, r)]
        if ca or cb:
            k['contact'] += 1
            k['contact_same'] += same and ca
            da, ka = g.champ_damage(a, r)
            db, kb = g.champ_damage(b, r + 1)
            k['contact_hit'] += (da > 0) or (db > 0)
            k['contact_hit_both'] += (da > 0) and (db > 0)
            k['contact_kill'] += bool(ka or kb)
            if same and ca:
                k['same_contact_hit'] += (da > 0) or (db > 0)
                k['same_contact_kill'] += bool(ka or kb)
                k['same_contact_hit2'] += (da > 0) and (db > 0)
    # control: any in-contact turn's hit / kill rate
    for r in range(2, g.N + 1):
        for c in g.ids:
            if g.alive(c, r - 1) and contact[(c, r - 1)]:
                k = dbl[g.team[c]]
                d, ks = g.champ_damage(c, r)
                k['turn_contact'] += 1
                k['turn_contact_hit'] += d > 0
                k['turn_contact_kill'] += bool(ks)
    out['dbl'] = dbl
    # ---- metric 6: kill conversion (team t hunting)
    conv = [Counter(), Counter()]
    conv_rows = [[], []]
    for t in (0, 1):
        busy = {}
        for r in range(1, g.N - 3):
            for e in g.members[1 - t]:
                if busy.get(e, 0) >= r or not g.alive(e, r) or g.pos(e, r) is None:
                    continue
                mx = g.at(e, 'maxHp', r)
                if g.hp(e, r) >= 0.25 * mx or on_spawn(g, e, r):
                    continue
                pe = g.pos(e, r)
                hunters = [c for c in g.members[t] if g.pos(c, r) is not None and cheb(g.pos(c, r), pe) <= CONTACT]
                if not hunters:
                    continue
                busy[e] = r + 3
                seq, slot, _ = g.order(r + 1)
                e_first = slot[e] < min(slot[c] for c in hunters)
                dead_at = None
                for q in range(r + 1, r + 4):
                    if g.died_in(e, q):
                        dead_at = q
                        break
                row_ = dict(r=r, e=e, n_hunters=len(hunters), e_first=e_first, dead_at=dead_at)
                if dead_at is not None:
                    de = g.death(e, dead_at)
                    row_['by_us'] = de.get('by') in g.members[t]
                    outcome = 'killed' if row_['by_us'] else ('camp' if de.get('camp') is not None else 'other')
                else:
                    recalled = any(x['k'] == 'recall_end' and x.get('a') == e for q in range(r + 1, r + 4)
                                   for x in g.by_round[q])
                    healed = any(x['k'] == 'cast' and any(v == e for v, _ in (x.get('heal') or []))
                                 for q in range(r + 1, r + 4) for x in g.by_round[q]) if True else False
                    spawn = on_spawn(g, e, r + 3)
                    outcome = 'recalled' if recalled else 'healed' if healed else 'spawn' if spawn else 'escaped'
                row_['outcome'] = outcome
                conv[t][outcome] += 1
                conv[t]['e_first_' + outcome] += e_first
                conv_rows[t].append(row_)
    out['conv'] = conv
    out['conv_rows'] = conv_rows
    return out


def main():
    ex, outp = sys.argv[1], sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else ''
    rows = [r for r in index(ex) if r['ok'] and r['source'].startswith(prefix)]
    seen, todo = set(), []
    for r in rows:
        if r['dir'] in seen:
            continue
        seen.add(r['dir'])
        todo.append((ex, r))
    with ProcessPoolExecutor(80) as pool:
        res = list(pool.map(one, todo, chunksize=4))
    pickle.dump(res, open(outp, 'wb'))
    print(len(res), 'games;', sum(1 for x in res if 'error' in x), 'errors')


if __name__ == '__main__':
    main()
