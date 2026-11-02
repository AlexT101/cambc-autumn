"""Per-game measurements of ast-measure's traced games (TO, TB, KL, PL, MW lines) against the real turn order.

usage: python3 research/turn-order-2026-11-02/scripts/traced.py EXTRACT_DIR [--out results.json]
Writes a pickle of per-game rows; summarize.py turns it into tables.
"""
import json
import pickle
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tolib import G, cheb, index, stdout_lines, traced_team  # noqa: E402

BANDS = {'K': 'kill', 'X': 'cancel', 'T': 'cancel', 'R': 'cancel', 'P': 'cancel', 'C': 'channel', 'E': 'escape',
         'H': 'heal'}
CANCEL_END = {'T': 'tribute_end', 'R': 'recall_end', 'P': 'teleport_end'}


def parse(lines):
    out = defaultdict(list)
    for l in lines:
        k = l.split(' ', 1)[0]
        if k in ('TO', 'TB', 'KL', 'PL', 'MW'):
            # a whole line has every field; a line cut by the stdout cap or interleaved is dropped
            need = {'TO': 3, 'TB': 1, 'KL': 1, 'PL': 1, 'MW': 0}[k]
            if l.count('|') != need:
                out['bad'].append(l)
                continue
            out[k].append(l)
    return out


def parse_to(l):
    head, needs, allies, epc = l.split('|')
    h = head.split()
    r, me, band, kind, raw, code, our_rank, our_slot, target, their = int(h[1]), int(h[2]), int(h[3]), h[4], int(
        h[5]), int(h[6]), int(h[7]), int(h[8]), int(h[9]), int(h[10])
    nd = [tuple(map(int, x.split(':'))) for x in needs.split()]
    al = [tuple(map(int, x.split(':'))) for x in allies.split()]
    return dict(r=r, me=me, band=band, kind=kind, raw=raw, code=code, our_rank=our_rank, our_slot=our_slot,
                target=target, their=their, needs=nd, allies=al, epc=int(epc))


def template(g, r):
    """Team of each slot of round r."""
    a, b = [0] * len(g.members[0]), [1] * len(g.members[1])
    if g.starts(r) == 1:
        a, b = b, a
    out = []
    for k in range(max(len(a), len(b))):
        out += a[k:k + 1] + b[k:k + 1]
    return out


def channel_events(g, c, r):
    kinds = Counter(e['k'] for e in g.by_round[r] if e.get('a') == c)
    return kinds


def one(args):
    ex, row = args
    d, source = row['dir'], row['source']
    try:
        g = G(ex, d)
    except Exception as e:  # noqa: BLE001
        return {'error': str(e), 'dir': d}
    us = traced_team(source)
    them = 1 - us
    raw = stdout_lines(source, us)
    L = parse(raw)
    # the 1 MiB stdout cap cuts late rounds: trust rounds before the last one printed
    trusted = g.N
    if sum(len(l) + 1 for l in raw) > 1_000_000:
        last = 0
        for l in reversed(raw):
            p = l.split()
            if len(p) > 1 and p[1].isdigit():
                last = int(p[1])
                break
        trusted = last - 1
    out = {'trusted': trusted, 'dir': d, 'source': source, 'us': us, 'won': g.meta['result']['winner'] == us, 'rounds': g.N,
           'bids': [], 'tb': [], 'suppressed': [], 'allowed': [], 'forks': [], 'pl': [], 'mw': Counter(), 'turns': 0, 'kl_turns': 0}
    # our turns this game (alive champion-rounds)
    for c in g.members[us]:
        out['turns'] += sum(g.col[c]['alive'][:trusted])
    to_by = {}
    out['bad'] = len(L['bad'])
    for l in L['TO']:
        try:
            t = parse_to(l)
        except ValueError:
            out['bad'] += 1
            continue
        if t['r'] < trusted:
            to_by[(t['r'], t['me'])] = t
    # ---- Metric 1: bid outcomes
    for (r, me), t in to_by.items():
        if t['band'] == 0 or t['kind'] == '-' or r + 1 > g.N:
            continue
        seq, slot, rank = g.order(r + 1)
        seq_r, slot_r, rank_r = g.order(r)
        kind = t['kind']
        b = dict(r=r, me=me, kind=kind, cls=BANDS.get(kind, kind), assumed_rank=t['our_rank'],
                 assumed_slot=t['our_slot'], rank=rank[me], slot=slot[me])
        if kind in ('K', 'X', 'T', 'R', 'P'):
            tg = t['target']
            b['need'] = [(tg, t['their'], slot.get(tg, 99))]
        else:
            b['need'] = [(h, s, slot.get(h, 99)) for h, s in t['needs']]
        b['assumed_before'] = all(t['our_slot'] < s for _, s, _ in b['need']) if b['need'] else None
        b['before'] = all(slot[me] < s for _, _, s in b['need']) if b['need'] else None
        # goal
        nxt = r + 1
        if kind == 'K':
            tg = t['target']
            de = g.death(tg, nxt)
            b['ok'] = de is not None
            b['ok_by_us'] = de is not None and de.get('by') in g.members[us]
            # killed before its own turn in r+1
            b['ok_before_turn'] = de is not None and (tg not in g.first[nxt] or de['s'] < g.first[nxt][tg])
        elif kind in ('X', 'T', 'R', 'P'):
            tg = t['target']
            ks = channel_events(g, tg, nxt)
            ends = ks.get('tribute_end', 0) + ks.get('recall_end', 0) + ks.get('teleport_end', 0)
            canc = ks.get('tribute_cancel', 0) + ks.get('recall_cancel', 0) + ks.get('teleport_cancel', 0)
            b['ok'] = (canc > 0 or g.died_in(tg, nxt)) and ends == 0
        elif kind == 'C':
            ks = channel_events(g, me, nxt)
            b['ok'] = (ks.get('tribute_end', 0) + ks.get('recall_end', 0) + ks.get('teleport_end', 0)) > 0
        elif kind == 'E':
            b['ok'] = not g.died_in(me, nxt) and not g.died_in(me, r)
        elif kind == 'H':
            b['ok'] = not g.died_in(t['target'], nxt)
            b['healed'] = any(e.get('a') == me and e['k'] == 'cast' and e.get('heal') for e in g.by_round[nxt])
        # failure-to-act-before classification
        if b['assumed_before'] and b['before'] is False:
            causes = []
            if rank[me] > t['our_rank']:
                our_code = t['code']
                read = {a[0]: a for a in t['allies']}
                for a in g.members[us]:
                    if a == me or rank[a] > rank[me]:
                        continue
                    ra = read.get(a)
                    if ra is None:
                        continue
                    assumed_above = ra[1] > our_code or (ra[1] == our_code and a < me)
                    if assumed_above:
                        continue
                    later = slot_r.get(a, -1) > slot_r.get(me, -1)
                    ta = to_by.get((r, a))
                    band = ta['kind'] if ta and ta['band'] > 0 else ('dead' if not g.alive(a, r) else 'plain')
                    if later:
                        causes.append(('ally_later', band))
                    elif ra[2] == 0:
                        causes.append(('ally_unseen', band))
                    else:
                        causes.append(('ally_other', band))
                if not causes:
                    causes.append(('rank_other', ''))
            else:
                # our rank held: an enemy we needed to precede came earlier than assumed
                moved = [(h, s0, s1) for h, s0, s1 in b['need'] if s1 < s0]
                if moved:
                    for h, s0, s1 in moved:
                        # changed its priority after our turn in round r, or before (stale read)
                        changed = g.prio(h, r) != g.prio(h, r - 1)
                        acted_after = slot_r.get(h, -1) > slot_r.get(me, -1)
                        causes.append(('enemy_reordered', 'after_us' if acted_after and changed else (
                            'changed' if changed else 'other_enemy')))
                else:
                    causes.append(('other', ''))
            b['causes'] = causes
        b['epc'] = t['epc']
        out['bids'].append(b)
    # ---- Metric 2b: Safety's turns_before_ours next-round term
    for l in L['TB']:
        head, ents = l.split('|')
        h = head.split()
        if int(h[1]) >= trusted:
            continue
        r, me, my_slot_now, my_slot_next = int(h[1]), int(h[2]), int(h[3]), int(h[4])
        if r + 1 > g.N:
            continue
        seq, slot, rank = g.order(r + 1)
        for x in ents.split():
            e, acted, es, tbo, dist = map(int, x.split(':'))
            if e not in slot:
                continue
            pred = es < my_slot_next
            act = slot[e] < slot[me]
            fix_me = (es < slot[me]) == act
            fix_e = (slot[e] < my_slot_next) == act
            own_change = g.prio(me, r) != g.prio(me, r - 1)
            enemy_change = g.prio(e, r) != g.prio(e, r - 1)
            # did e hit us in round r+1 before our turn there (or kill us)?
            hit = False
            if dist <= 5:
                ts = g.first[r + 1].get(me, 10 ** 12)
                for ev in g.by_round[r + 1]:
                    if ev['s'] >= ts:
                        break
                    if ev.get('a') == e and ev['k'] in ('attack', 'cast') and any(v == me for v, _ in ev.get('dmg') or []):
                        hit = True
                        break
            out['tb'].append((r, me, e, dist, pred, act, fix_me, fix_e, own_change, enemy_change, acted, hit))
    # ---- Metric 4: forks
    for l in L['KL']:
        head, ents = l.split('|')
        h = head.split()
        if int(h[1]) >= trusted:
            continue
        r, me, our_slot = int(h[1]), int(h[2]), int(h[3])
        out['kl_turns'] += 1
        es = [tuple(map(int, x.split(':'))) for x in ents.split()]
        killable = [x for x in es if x[3] >= x[1] > 0]
        # a kill that the read order allows but the worst case (unsettled enemy at rank 0) does not
        seqn, slotn, _ = g.order(r + 1) if r + 1 <= g.N else (None, {}, None)
        t0 = to_by.get((r, me))
        for x in es:
            h_, hp_, dwc, drd, wc, rd, acted_ = x
            if hp_ <= 0 or r + 1 > g.N:
                continue
            if drd >= hp_ and our_slot < rd and not (dwc >= hp_ and our_slot < wc):
                out['suppressed'].append(dict(r=r, me=me, e=h_, acted=acted_, wc=wc, rd=rd, our_slot=our_slot,
                                              real_before=slotn.get(me, 99) < slotn.get(h_, -1),
                                              died=g.died_in(h_, r + 1), bid=t0['kind'] if t0 else '?'))
            elif dwc >= hp_ and our_slot < wc:
                out['allowed'].append(dict(real_before=slotn.get(me, 99) < slotn.get(h_, -1), died=g.died_in(h_, r + 1)))
        if len(killable) < 2 or r + 1 > g.N:
            continue
        guaranteed = [x for x in killable if x[4] > our_slot]
        if guaranteed:
            continue  # the seat guarantees preceding one of them already
        # enemy slots before ours next round
        before = template(g, r + 1)[:our_slot].count(them)
        pigeon = len(killable) > before
        seq, slot, rank = g.order(r + 1)
        killed = [x[0] for x in killable if g.died_in(x[0], r + 1)]
        preceded = [x[0] for x in killable if slot.get(me, 99) < slot.get(x[0], -1)]
        t = to_by.get((r, me))
        out['forks'].append(dict(r=r, me=me, n=len(killable), pigeon=pigeon, our_slot=our_slot, real_slot=slot.get(me),
                                 killed=len(killed), preceded=len(preceded), bid=t['kind'] if t else '?',
                                 band=t['band'] if t else -1))
    # ---- Metric 5: ally blocking in the strike search
    pl = {}
    for l in L['PL']:
        head, ents = l.split('|')
        h = head.split()
        if int(h[1]) >= trusted:
            continue
        r, me = int(h[1]), int(h[2])
        allies_near = int(h[4])
        key = (r, me)
        rec = pl.setdefault(key, {'allies_near': 0, 'foes': {}})
        rec['allies_near'] = max(rec['allies_near'], allies_near)
        for x in ents.split():
            v = list(map(int, x.split(':')))
            f = rec['foes'].setdefault(v[0], v)
            # OR the flags over the turn's searches
            for i in range(2, 7):
                f[i] = max(f[i], v[i])
            if f[7] == -99 and v[7] != -99:
                f[7], f[8] = v[7], v[8]
    for (r, me), rec in pl.items():
        foes = rec['foes']
        legal = len(foes)
        only = []
        for e, v in foes.items():
            here, walk, walk_o, dash, dash_o, ux, uy = v[2:9]
            if not (here or walk or dash) and (walk_o or dash_o) and ux != -99:
                only.append((e, v[1], (ux, uy)))
        res = dict(r=r, me=me, legal=legal, allies_near=rec['allies_near'], only=[])
        for e, hp, tile in only:
            # who held it at our turn, and did it leave later this round or next
            ts = g.first[r].get(me)
            holder = None
            for a in g.members[us]:
                if a == me:
                    continue
                p = g.pos_at(a, r, ts if ts is not None else 0)
                if p == tile:
                    holder = a
            vac_r = holder is not None and g.pos(holder, r) != tile
            vac_n = holder is not None and r + 1 <= g.N and g.pos(holder, r + 1) != tile
            our_dmg, _ = g.champ_damage(me, r)
            res['only'].append(dict(e=e, hp=hp, holder=holder, vac_r=vac_r, vac_n=vac_n,
                                    died=g.died_in(e, r) or g.died_in(e, r + 1), we_hit=our_dmg > 0))
        out['pl'].append(res)
    for l in L['MW']:
        if int(l.split()[1]) < trusted:
            out['mw'][l.split()[3]] += 1
    return out


def main():
    ex = sys.argv[1]
    outp = sys.argv[2] if len(sys.argv) > 2 else '/tmp/claude-1000/traced.pkl'
    rows = [r for r in index(ex) if r['ok'] and r['source'].endswith('.repl26a')]
    seen, todo = set(), []
    for r in rows:
        if r['dir'] in seen:
            continue
        seen.add(r['dir'])
        todo.append((ex, r))
    with ProcessPoolExecutor(64) as pool:
        res = list(pool.map(one, todo, chunksize=4))
    pickle.dump(res, open(outp, 'wb'))
    print(len(res), 'games;', sum(1 for x in res if 'error' in x), 'errors')


if __name__ == '__main__':
    main()
