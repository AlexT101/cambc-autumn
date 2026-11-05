"""Gem-fight evidence: deaths carrying gems, recalls escaping in reach, big carriers left alone.
usage: gemev.py ANALYSIS_DIR [--own]   (--own: team of bot 0 from the source name -12/-21)"""
import sys, json, gzip, os
from multiprocessing import Pool
from collections import Counter, defaultdict

A = sys.argv[1]
OWN = '--own' in sys.argv


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(d):
    p = os.path.join(A, d)
    try:
        meta = json.load(open(os.path.join(p, 'meta.json')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(p, 'events.jsonl.gz'), 'rt')]
        rd = json.load(gzip.open(os.path.join(p, 'rounds.json.gz')))
    except Exception:
        return None
    us = None
    if OWN:
        src = meta.get('source', '')
        us = 0 if src.endswith('-12.repl26a') else 1 if src.endswith('-21.repl26a') else None
    champs = {c['id']: c for c in meta['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    ranged = {c['id']: c['name'] in ('Vesper Vale', 'Prism', 'Stellar', 'Tavi', 'Willow', 'Cassi') for c in meta['champions']}
    rounds = rd['round']
    ridx = {r: i for i, r in enumerate(rounds)}
    ch = {c['id']: c for c in rd['champions']}
    out = Counter()
    out['games'] = 1
    winner = meta['result']['winner']
    # A. deaths with bags
    for e in ev:
        if e['k'] != 'death':
            continue
        g = e.get('gems', 0) or 0
        if e.get('linked') is not None:
            continue  # count the pair once, by the body killed directly
        side = team[e['v']]
        tag = ('us' if side == us else 'them') if OWN else 'any'
        by = 'camp' if 'camp' in e else 'champ'
        for lo in (10, 20, 40):
            if g >= lo:
                out[f'{tag}_death_bag{lo}_{by}'] += 1
        out[f'{tag}_death_{by}'] += 1
        out[f'{tag}_gems_lost_{by}'] += g
    # tributed totals
    for e in ev:
        if e['k'] == 'tribute_end':
            side = team[e['a']]
            tag = ('us' if side == us else 'them') if OWN else 'any'
            out[f'{tag}_tributed'] += e.get('gems', 0) or 0
    # B. recalls with bags: start..end/cancel
    starts = {}
    dmg_rounds = defaultdict(set)  # champion -> rounds it took champion damage
    for e in ev:
        if e['k'] in ('attack', 'cast'):
            for tid, amt in (e.get('dmg') or []):
                if tid in team and team.get(e.get('a')) is not None and team[tid] != team[e['a']] and amt > 0:
                    dmg_rounds[tid].add(e['r'])
    for e in ev:
        k = e['k']
        if k == 'recall_start':
            starts[e['a']] = e
        elif k in ('recall_end', 'recall_cancel'):
            s = starts.pop(e['a'], None)
            if not s:
                continue
            g = s.get('gems', 0) or 0
            if g < 10:
                continue
            side = team[e['a']]
            tag = ('us' if side == us else 'them') if OWN else 'any'  # the recaller's side
            if k == 'recall_cancel' and e['r'] - s['r'] <= 1:
                continue  # feint, or cut at once
            if k == 'recall_cancel' and e.get('cause') == 'damage':
                e = dict(e); e['cause'] = 'champdmg' if e['r'] in dmg_rounds[e['a']] else 'campdmg'
            r0 = s['r']
            # opposing champions alive and seeing it during the channel, nearest distance
            near = 99
            seen = False
            near_ranged = False
            for r in range(r0, e['r'] + 1):
                i = ridx.get(r)
                if i is None:
                    continue
                me = ch[e['a']]
                if not me['alive'][i] or me['x'][i] is None:
                    continue
                mp = (me['x'][i], me['y'][i])
                for oid, o in ch.items():
                    if team[oid] == side or not o['alive'][i] or o['x'][i] is None:
                        continue
                    dd = cheb(mp, (o['x'][i], o['y'][i]))
                    sees = e['a'] in (o.get('sees') or [[]] * len(rounds))[i] if o.get('sees') else False
                    if sees:
                        seen = True
                    if dd < near:
                        near = dd
                        near_ranged = ranged[oid]
            res = 'done' if k == 'recall_end' else e.get('cause', 'x')
            out[f'{tag}_recall10_{res}'] += 1
            if k == 'recall_end':
                if seen and near <= 6:
                    out[f'{tag}_recall10_escaped_seen_le6'] += 1
                    out[f'{tag}_recall10_escaped_seen_le6_gems'] += g
                if seen and near <= 4:
                    out[f'{tag}_recall10_escaped_seen_le4'] += 1
            out[f'{tag}_recall10_gems_{res}'] += g
    # C. big carriers seen near and left to tribute unharmed
    # per carrier: rounds when it carried >= 20 and an opposing champion saw it within 5;
    # does it then tribute (tribute_end) with no champion damage taken from that round on?
    tribs = defaultdict(list)
    for e in ev:
        if e['k'] == 'tribute_end':
            tribs[e['a']].append(e['r'])
    for cid, c in ch.items():
        side = team[cid]
        tag = ('us' if side == us else 'them') if OWN else 'any'  # carrier side
        last_ep = -100
        for i, r in enumerate(rounds):
            if not c['alive'][i] or (c['gems'][i] or 0) < 20 or c['x'][i] is None:
                continue
            if r - last_ep < 30:
                continue
            cp = (c['x'][i], c['y'][i])
            watcher = None
            for oid, o in ch.items():
                if team[oid] == side or not o['alive'][i] or o['x'][i] is None:
                    continue
                if cheb(cp, (o['x'][i], o['y'][i])) <= 5 and o.get('sees') and cid in o['sees'][i]:
                    if o['hp'][i] >= 0.5 * o['maxHp'][i]:
                        watcher = oid
                        break
            if watcher is None:
                continue
            last_ep = r
            out[f'{tag}_bigcarrier_seen'] += 1
            # outcome within 40 rounds
            nt = [t for t in tribs[cid] if r <= t <= r + 40]
            hurt = any(rr in dmg_rounds[cid] for rr in range(r, r + 41))
            died = False
            j = i
            while j < len(rounds) and rounds[j] <= r + 40:
                if not c['alive'][j]:
                    died = True
                    break
                j += 1
            if died:
                out[f'{tag}_bigcarrier_died'] += 1
            elif nt and not any(rr in dmg_rounds[cid] for rr in range(r, nt[0] + 1)):
                out[f'{tag}_bigcarrier_tributed_unharmed'] += 1
            elif nt:
                out[f'{tag}_bigcarrier_tributed_harmed'] += 1
            else:
                out[f'{tag}_bigcarrier_other'] += 1
    return out


if __name__ == '__main__':
    dirs = [d for d in os.listdir(A) if os.path.isfile(os.path.join(A, d, 'meta.json'))]
    tot = Counter()
    with Pool(24) as pool:
        for c in pool.imap_unordered(one, dirs, chunksize=4):
            if c:
                tot.update(c)
    for k in sorted(tot):
        print(f'{k:45s} {tot[k]:8d}  {tot[k] / tot["games"]:.3f}/game')
