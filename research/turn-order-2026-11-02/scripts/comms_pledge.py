"""Strike pledges in play (ast-comms's PG, PS and PR lines): are they kept, read, and do they kill?

usage: python3 research/turn-order-2026-11-02/scripts/comms_pledge.py EXTRACT_DIR [OUT.pkl]

PG round self target_index need: a pledge posted at our turn end in `round` (binds our turn in round+1).
PS round self target searched_keepable pledge_only chosen: a search under a binding pledge.
PR round self pledger target turn_offset before follow: a strike search read an ally's pledge.
Enemy indexes are positions in the enemy team by id. Kept: the pledger hit the target in round+1 for
>= 90% of `need`, or it died before the pledger's turn there.
"""
import pickle
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tolib import G, index, stdout_lines, traced_team  # noqa: E402


def hits(g, c, r, t):
    d = 0.0
    for e in g.by_round[r]:
        if e.get('a') == c and e['k'] in ('attack', 'cast'):
            for v, x in e.get('dmg') or []:
                if v == t:
                    d += x
    return d


def one(args):
    ex, row = args
    try:
        g = G(ex, row['dir'])
    except Exception as e:  # noqa: BLE001
        return {'error': str(e)}
    us = traced_team(row['source'])
    them = sorted(g.members[1 - us])
    lines = stdout_lines(row['source'], us)
    out = {'pg': [], 'ps': Counter(), 'pr': Counter(), 'rounds': g.N, 'won': g.meta['result']['winner'] == us,
           'kills': sum(1 for r in g.deaths for e in g.deaths[r] if e.get('by') in g.members[us] and not e.get('linked'))}
    pr_pledgers = set()
    for l in lines:
        p = l.split()
        try:
            if p[0] == 'PG' and len(p) == 5:
                r, me, ti, need = int(p[1]), int(p[2]), int(p[3]), int(p[4])
                if r + 1 > g.N or ti < 0 or ti >= len(them):
                    continue
                t = them[ti]
                n = r + 1
                step = g.first[n].get(me)
                de = g.death(t, r) or g.death(t, n)
                died_before = de is not None and (de['r'] == r or step is None or de['s'] < step)
                dmg = hits(g, me, n, t)
                died_in = g.died_in(t, n) or (de is not None and de['r'] == r)
                if died_before:
                    k = 'target died first'
                elif step is None:
                    k = 'no turn (dead/stunned/idle)'
                elif dmg >= 0.9 * need - 1 or (g.death(t, n) or {}).get('by') == me:
                    k = 'kept'
                elif dmg > 0:
                    k = 'hit short'
                else:
                    k = 'not hit'
                out['pg'].append(dict(r=r, me=me, t=t, k=k, died=died_in, by_us=(de or {}).get('by') in g.members[us]))
            elif p[0] == 'PS' and len(p) == 7:
                out['ps']['searches'] += 1
                out['ps']['keepable'] += int(p[4])
                out['ps']['pledge_only'] += int(p[5])
                out['ps']['pledge_only_keepable'] += int(p[5]) and int(p[4])
            elif p[0] == 'PR' and len(p) == 8:
                r, me, a, t, off, before = int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5]), int(p[6])
                out['pr']['reads'] += 1
                out['pr']['before'] += before
                if before:
                    # did the pledger hit it at the turn it pledged, and the reader this turn?
                    tr = r + off
                    if tr <= g.N:
                        out['pr']['pledger_hit'] += hits(g, a, tr, t) > 0 or g.died_in(t, r)
                        out['pr']['reader_hit'] += hits(g, me, r, t) > 0
                        out['pr']['target_died'] += g.died_in(t, r) or g.died_in(t, tr)
                pr_pledgers.add((r, a))
        except (ValueError, IndexError):
            continue
    return out


def report(res):
    res = [x for x in res if 'error' not in x]
    games = len(res)
    pg = [p for x in res for p in x['pg']]
    print(f'{games} games, {len(pg)} pledges ({len(pg) / games:.2f} a game)')
    c = Counter(p['k'] for p in pg)
    for k, v in c.most_common():
        print(f'  {k}: {v} ({100 * v / len(pg):.1f}%)')
    live = [p for p in pg if p['k'] != 'target died first']
    print(f'  kept, of pledges whose target lived to our turn: {100 * c["kept"] / max(1, len(live)):.1f}%')
    print(f'  target died by the end of round r+1: {100 * sum(p["died"] for p in pg) / len(pg):.1f}%')
    ps = Counter()
    pr = Counter()
    for x in res:
        ps.update(x['ps'])
        pr.update(x['pr'])
    print(f'searches under a pledge: {ps["searches"]}, a keeping plan offered {100 * ps["keepable"] / max(1, ps["searches"]):.1f}%;'
          f' pledge-only (leaving) {ps["pledge_only"]}, keepable {ps["pledge_only_keepable"]}')
    print(f'reads: {pr["reads"]} ({pr["reads"] / games:.2f} a game), landing before the target {pr["before"]};'
          f' of those the pledger hit {100 * pr["pledger_hit"] / max(1, pr["before"]):.1f}%,'
          f' the reader hit {100 * pr["reader_hit"] / max(1, pr["before"]):.1f}%, target died {100 * pr["target_died"] / max(1, pr["before"]):.1f}%')
    print(f'kills a game {sum(x["kills"] for x in res) / games:.2f}')


def main():
    ex = sys.argv[1]
    rows, seen, todo = index(ex), set(), []
    for r in rows:
        if r['ok'] and r['source'].endswith('.repl26a') and r['dir'] not in seen:
            seen.add(r['dir'])
            todo.append((ex, r))
    with ProcessPoolExecutor(40) as pool:
        res = list(pool.map(one, todo, chunksize=4))
    if len(sys.argv) > 2:
        pickle.dump(res, open(sys.argv[2], 'wb'))
    report(res)


if __name__ == '__main__':
    main()
