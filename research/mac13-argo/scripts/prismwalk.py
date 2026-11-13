"""Prism (and Vesper) walking breakdown on the extracted mirror, r1-400 and r401-800 (one pass).

    py research/mac13-argo/scripts/prismwalk.py [--procs N] > research/mac13-argo/data/prismwalk_raw.md

(a) walk legs by purpose (class of the round that ends the leg, as roles.py), Prism and Vesper;
(b) captures the Prism shared: whose damage cleared the group this cycle (Prism most / an ally most / enemy most),
    and for ally-cleared groups ("collections") the Prism's walk to the tiles, clear-to-arrival gap, and the clearing
    ally's rounds on or within 2 of the group's tiles in that gap;
(c) shop trips: completed recalls started at >= 90% health, whether a purchase followed on spawn, gold spent, rounds
    from recall start to the next camp hit (Prism and Vesper);
(d) Prism alive rounds within 2 of an altar while not channelling a tribute.
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path
from statistics import mean, median

ROOT = Path('/home/ubuntu/wt/mac13-argo')
ANA = ROOT / 'replays' / 'ana-mirror'
os.environ['CAMBC_ANALYSIS'] = str(ANA)
sys.path.insert(0, str(ROOT / 'tools' / 'replay'))

from analysis import Game  # noqa: E402
from analysis import macro  # noqa: E402
from analysis.data import chebyshev  # noqa: E402

PH = [(1, 400, 'r1-400'), (401, 800, 'r401-800')]
PURPOSES = ['camp', 'hold', 'tribute/altar', 'spawn/recall', 'fight', 'wait_camp', 'died', 'regroup', 'other']
TYPES = ('Prism', 'Vesper Vale')


def ph_of(r):
    for lo, hi, nm in PH:
        if lo <= r <= hi:
            return nm
    return None


def work(d):
    try:
        return _work(d)
    except Exception as ex:
        import traceback
        return {'error': repr(ex), 'tb': traceback.format_exc(), 'dir': d}


def _work(d):
    g = Game(d)
    mp, n, R, ev = g.map, g.n_rounds, g.rounds, g.events
    nr = len(R['round'])
    champs = R['champions']
    name_of, team_of = g.name_of, g.team_of
    cls = macro.classify(g)
    camp_group = {c['id']: c['group'] for c in mp.camps}
    gtiles = {grp['id']: [tuple(t) for t in grp['tiles']] for grp in mp.groups}
    focus = [c for c in champs if name_of[c['id']] in TYPES]
    if not focus:
        return {'empty': True}

    def ix(r):
        return max(0, min(r, nr) - 1)

    def pos(c, r):  # end of round r
        i = ix(r)
        return (c['x'][i], c['y'][i]) if c['alive'][i] and c['x'][i] is not None else None

    out = {'legs': Counter(), 'legr': Counter(), 'walk': Counter(), 'alive': Counter()}
    for c in focus:
        out['alive']['bodies|' + name_of[c['id']]] += 1
    # ---------- (a) legs
    for c in focus:
        cid, t, nm = c['id'], c['team'], name_of[c['id']]
        q = cls[cid]
        for r in range(1, min(n, 800) + 1):
            if q[r] not in (None, 'dead'):
                out['alive'][f'{nm}|{ph_of(r)}'] += 1
        r = 1
        while r <= min(n, 800):
            if q[r] not in macro.WALKS:
                r += 1
                continue
            a = r
            while r <= n and q[r] in macro.WALKS:
                r += 1
            b = r - 1
            end = q[r] if r <= n else None
            ph = ph_of(a)
            pur = {'camp': 'camp', 'hold': 'hold', 'tribute': 'tribute/altar', 'wait_altar': 'tribute/altar', 'spawn': 'spawn/recall',
                   'recall': 'spawn/recall', 'teleport': 'spawn/recall', 'fight': 'fight', 'dead': 'died', 'wait_camp': 'wait_camp'}.get(end, 'other')
            if pur == 'other':
                i0, ib = max(0, a - 2), max(0, b - 1)
                p0 = (c['x'][i0], c['y'][i0]) if c['alive'][i0] and c['x'][i0] is not None else None
                p1 = (c['x'][ib], c['y'][ib]) if c['alive'][ib] and c['x'][ib] is not None else None
                if p0 and p1:
                    for c2 in champs:
                        if c2['id'] == cid or c2['team'] != t or not (c2['alive'][i0] and c2['alive'][ib]) or c2['x'][i0] is None or c2['x'][ib] is None:
                            continue
                        if chebyshev(p1, (c2['x'][ib], c2['y'][ib])) <= 3 and chebyshev(p0, (c2['x'][i0], c2['y'][i0])) > 8:
                            pur = 'regroup'
                            break
            key = f'{nm}|{ph}|{pur}'
            out['legs'][key] += 1
            out['legr'][key] += b - a + 1
            out['walk'][f'{nm}|{ph}'] += b - a + 1

    # ---------- events: per-cycle damage, clears, camp hits, recalls, shops
    cyc = defaultdict(Counter)        # gid -> cid -> damage this cycle
    clear = {}                         # gid -> (round, cid)
    hits = defaultdict(set)            # cid -> rounds with a camp hit
    shops = defaultdict(list)          # cid -> [(round, gold spent)]
    recs = []                          # (cid, start round, end round)
    open_rec = {}
    caps = []                          # (gid, r, team, cycle damage, clear)
    for e in ev:
        k, r = e['k'], e['r']
        if k in ('attack', 'cast') and e.get('cdmg'):
            for camp, amt in e['cdmg']:
                if amt > 0 and camp in camp_group:
                    cyc[camp_group[camp]][e['a']] += amt
                    hits[e['a']].add(r)
        elif k == 'group_clear':
            clear[e['g']] = (r, e.get('by'))
        elif k == 'capture':
            caps.append((e['g'], r, e['team'], dict(cyc.pop(e['g'], {})), clear.pop(e['g'], None), [s[0] for s in e['shares']],
                         {s[0]: s[1] for s in e['shares']}))
        elif k == 'group_respawn':
            cyc.pop(e['g'], None)
            clear.pop(e['g'], None)
        elif k == 'shop' and (e.get('gold') or 0) < 0:
            shops[e['a']].append((r, -e['gold']))
        elif k == 'recall_start':
            open_rec[e['a']] = r
        elif k == 'recall_cancel':
            open_rec.pop(e['a'], None)
        elif k == 'recall_end':
            r0 = open_rec.pop(e['a'], None)
            if r0 is not None:
                recs.append((e['a'], r0, r))

    # ---------- (b) Prism captures
    prism = {c['team']: c for c in focus if name_of[c['id']] == 'Prism'}
    bcap = Counter()
    coll = []   # (phase, walk len, gap clear->arrival, ally near rounds, chebyshev dist at clear, prism gems share)
    for gid, r, t, dmg, cl, sharers, gems in caps:
        P = prism.get(t)
        if P is None or P['id'] not in sharers:
            continue
        ph = ph_of(r)
        if ph is None:
            continue
        pid = P['id']
        tot = sum(dmg.values())
        best = max(dmg, key=dmg.get) if dmg else None
        if best is None:
            kind = 'no damage seen'
        elif best == pid:
            kind = 'prism most'
        elif team_of.get(best) == t:
            kind = 'ally most'
        else:
            kind = 'enemy most'
        bcap[f'{ph}|{kind}'] += 1
        bcap[f'{ph}|{kind}|gems'] += gems.get(pid, 0)
        bcap[f'{ph}|{kind}|prism_dmg_share'] += (dmg.get(pid, 0) / tot) if tot else 0
        if kind != 'ally most' or cl is None:
            continue
        tiles = gtiles[gid]
        # arrival: earliest round ra such that the Prism stood on the tiles at the end of every round ra..r-1
        ra = r
        while ra - 1 >= 1 and (p := pos(P, ra - 1)) is not None and p in tiles:
            ra -= 1
        q = cls[pid]
        wl = 0
        x = ra
        while x >= 1 and q[x] in macro.WALKS:
            wl += 1
            x -= 1
        rc, cb = cl
        pc = pos(P, rc)
        dist = min(chebyshev(pc, tt) for tt in tiles) if pc else None
        allyw = 0
        cbc = champs[g.idx[cb]] if cb in g.idx and team_of.get(cb) == t and cb != pid else None
        if cbc is not None:
            for y in range(rc + 1, ra):
                p = pos(cbc, y)
                if p is not None and min(chebyshev(p, tt) for tt in tiles) <= 2:
                    allyw += 1
        coll.append((ph, wl, ra - rc, allyw, dist, r - rc, cbc is not None))

    # ---------- (c) shop trips
    trips = []   # (type, phase, hp>=0.9, shopped, gold, rounds to next hit or None)
    for cid, r0, r1 in recs:
        nm = name_of[cid]
        if nm not in TYPES:
            continue
        ph = ph_of(r0)
        if ph is None:
            continue
        c = champs[g.idx[cid]]
        i = max(0, r0 - 2)
        hp, mx = c['hp'][i], c['maxHp'][i]
        hs = hp / mx if hp is not None and mx else 0
        nxt = next((x for x in range(r0, n + 1) if x in hits[cid]), None)
        # purchases from arrival until it leaves spawn (or 10 rounds)
        leave = r1
        while leave <= min(n, r1 + 10) and (p := pos(c, leave)) is not None and mp.in_spawn(c['team'], p):
            leave += 1
        gold = sum(gg for rr, gg in shops[cid] if r1 <= rr <= leave)
        trips.append((nm, ph, hs >= 0.9, gold > 0, gold, (nxt - r0) if nxt else None, leave - r1))

    # ---------- (d) Prism near an altar, not channelling a tribute
    alt = Counter()
    for t, P in prism.items():
        q = cls[P['id']]
        for r in range(1, min(n, 800) + 1):
            k = q[r]
            if k in (None, 'dead', 'tribute'):
                continue
            p = pos(P, r)
            if p is None or mp.altar_dist(p) > 2:
                continue
            ph = ph_of(r)
            alt[f'{ph}|{k}'] += 1
            alt[f'{ph}|all'] += 1
            alt[f'{ph}|gems'] += P['gems'][ix(r)] or 0
    return {'legs': dict(out['legs']), 'legr': dict(out['legr']), 'walk': dict(out['walk']), 'alive': dict(out['alive']),
            'bcap': dict(bcap), 'coll': coll, 'trips': trips, 'alt': dict(alt)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--procs', type=int, default=24)
    a = ap.parse_args()
    idx = json.loads((ANA / 'index.json').read_text())['games']
    dirs = sorted({r['dir'] for r in idx if r['ok']})
    acc = {k: Counter() for k in ('legs', 'legr', 'walk', 'alive', 'bcap', 'alt')}
    coll, trips, bad, ng = [], [], 0, 0
    with Pool(a.procs) as pool:
        for o in pool.imap_unordered(work, dirs, chunksize=4):
            if 'error' in o:
                bad += 1
                print('ERR', o['dir'], o['tb'][-500:], file=sys.stderr)
                continue
            if o.get('empty'):
                continue
            ng += 1
            for k in acc:
                acc[k].update(o[k])
            coll += o['coll']
            trips += o['trips']
    P = print
    P(f'# Prism walking ({ng} games with a Prism or Vesper, {bad} errors)\n')
    P('## (a) Walk legs by purpose: % of the champion\'s walk rounds / mean leg length')
    P('| champion | phase | walk % of alive | ' + ' | '.join(PURPOSES) + ' |')
    P('|' + '---|' * (len(PURPOSES) + 3))
    for nm in TYPES:
        for _, _, ph in PH:
            w = acc['walk'][f'{nm}|{ph}'] or 1
            al = acc['alive'][f'{nm}|{ph}'] or 1
            cells = []
            for p in PURPOSES:
                k = f'{nm}|{ph}|{p}'
                cells.append(f'{100 * acc["legr"][k] / w:.0f}% / {acc["legr"][k] / acc["legs"][k]:.1f}' if acc['legs'][k] else '-')
            P(f'| {nm} | {ph} | {100 * w / al:.0f}% | ' + ' | '.join(cells) + ' |')
    P('')
    P('## (b) Captures the Prism shared, by who dealt most of the cycle\'s monster damage')
    for _, _, ph in PH:
        kinds = ['prism most', 'ally most', 'enemy most', 'no damage seen']
        tot = sum(acc['bcap'][f'{ph}|{k}'] for k in kinds) or 1
        P(f'- {ph}: ' + '; '.join(f'{k} {acc["bcap"][f"{ph}|{k}"]} ({100 * acc["bcap"][f"{ph}|{k}"] / tot:.0f}%, Prism gems {acc["bcap"][f"{ph}|{k}|gems"] / max(1, acc["bcap"][f"{ph}|{k}"]):.1f}/capture, '
                            f'Prism damage share {100 * acc["bcap"][f"{ph}|{k}|prism_dmg_share"] / max(1, acc["bcap"][f"{ph}|{k}"]):.0f}%)' for k in kinds if acc['bcap'][f'{ph}|{k}']))
    P('')
    P('Collections (ally did most of the damage): the Prism\'s walk leg into the tiles, the gap from the clear to its arrival, and the clearing ally\'s rounds on or within 2 of the tiles in that gap')
    P('| phase | collections | Prism walk leg median / mean | Chebyshev dist at clear median | clear -> Prism arrival median / mean | clear -> payout median | clearing ally waiting rounds median / mean | ally waited 3+ rounds |')
    P('|---|---|---|---|---|---|---|---|')
    for _, _, ph in PH:
        v = [x for x in coll if x[0] == ph]
        if not v:
            continue
        wl = [x[1] for x in v]
        gap = [x[2] for x in v]
        aw = [x[3] for x in v if x[6]]
        ds = [x[4] for x in v if x[4] is not None]
        pay = [x[5] for x in v]
        P(f'| {ph} | {len(v)} | {median(wl):.0f} / {mean(wl):.1f} | {median(ds) if ds else "-"} | {median(gap):.0f} / {mean(gap):.1f} | {median(pay):.0f} | '
          f'{median(aw) if aw else "-"} / {mean(aw) if aw else 0:.1f} | {100 * mean(x >= 3 for x in aw) if aw else 0:.0f}% |')
    P('')
    P('## (c) Completed recalls: shop trips (recall started at >= 90% health)')
    P('| champion | phase | completed recalls per champion-game | started at >= 90% hp | of those, bought something on spawn | gold per buying trip median / mean | rounds on spawn after arrival median | recall start -> next camp hit median / mean |')
    P('|---|---|---|---|---|---|---|---|')
    games_with = Counter()
    for nm in TYPES:
        for _, _, ph in PH:
            v = [x for x in trips if x[0] == nm and x[1] == ph]
            if not v:
                continue
            hi = [x for x in v if x[2]]
            buy = [x for x in hi if x[3]]
            nh = [x[5] for x in hi if x[5] is not None]
            P(f'| {nm} | {ph} | {len(v) / max(1, acc['alive']['bodies|' + nm]):.2f} | {100 * len(hi) / len(v):.0f}% | {100 * len(buy) / max(1, len(hi)):.0f}% | '
              f'{median(x[4] for x in buy) if buy else 0:.0f} / {mean(x[4] for x in buy) if buy else 0:.0f} | {median(x[6] for x in hi) if hi else 0:.0f} | '
              f'{median(nh) if nh else "-"} / {mean(nh) if nh else 0:.1f} |')
    P('')
    P('## (d) Prism alive rounds within 2 of an altar, not channelling a tribute')
    for _, _, ph in PH:
        al = acc['alive'][f'Prism|{ph}'] or 1
        a_ = acc['alt'][f'{ph}|all']
        mix = sorted(((k.split('|')[1], v) for k, v in acc['alt'].items() if k.startswith(ph + '|') and k.split('|')[1] not in ('all', 'gems')), key=lambda kv: -kv[1])
        P(f'- {ph}: {100 * a_ / al:.1f}% of Prism alive rounds ({a_ / max(1, acc['alive']['bodies|Prism']):.1f} rounds per Prism-game), mean bag {acc["alt"][f"{ph}|gems"] / max(1, a_):.0f}; by class: '
          + ', '.join(f'{k} {100 * v / max(1, a_):.0f}%' for k, v in mix[:6]))


if __name__ == '__main__':
    main()
