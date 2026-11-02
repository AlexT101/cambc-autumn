"""Why ast-deadlast loses: its side against the baseline side of the same A/B games, in rounds with a dead ally.

usage: python3 research/turn-order-2026-11-02/scripts/deadslot.py EXTRACT_DIR [CAND_NAME]
Idle = a live champion whose priority for the round decodes to the idle range (raw -11..12; the code above the
payload is raw * 8 + 7 - index in both variants). Rounds are split by whether the team had a dead champion at the
round's start.
"""
import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tolib import G, cheb, index, stdout_lines  # noqa: E402

IDLE = range(-11, 13)


def raw(p):
    return (p >> 16) >> 3


def one(args):
    ex, row, cand = args
    try:
        g = G(ex, row['dir'])
    except Exception as e:  # noqa: BLE001
        return {'error': str(e)}
    names = row['teams']
    out = {'winner_name': names[g.meta['result']['winner']]}
    stats = {}
    # damage taken per champion per round, by enemy champions, and killers
    taken = Counter()
    for e in g.events:
        if e['k'] in ('attack', 'cast') and e.get('a') in g.team:
            for v, x in e.get('dmg') or []:
                if v in g.team and g.team[v] != g.team[e['a']]:
                    taken[(v, e['r'])] += x
    claims = {}
    for t in (0, 1):
        for l in stdout_lines(row['source'], t) if 'source' in row else []:
            if l.startswith('D '):
                p = l.split()
                if len(p) >= 6:
                    claims[(int(p[1]), int(p[2]))] = int(p[5])
    for t in (0, 1):
        name = 'cand' if names[t] == cand else 'ref'
        k = Counter()
        mem = g.members[t]
        for r in range(2, g.N + 1):
            dead = [c for c in mem if not g.alive(c, r - 1)]
            live = [c for c in mem if g.alive(c, r - 1)]
            seg = 'dead' if dead else 'full'
            seq, slot, rank = g.order(r)
            k[seg + '_rounds'] += 1
            # claim collisions among live allies (two claiming one group)
            cl = [claims.get((r, c), -1) for c in live]
            cl = [x for x in cl if x >= 0]
            k[seg + '_claims'] += len(cl)
            k[seg + '_claim_dupes'] += len(cl) - len(set(cl))
            for c in live:
                rw = raw(g.prio(c, r - 1))
                pc = g.pos(c, r - 1)
                near = pc is not None and any(g.pos(e, r - 1) is not None and cheb(pc, g.pos(e, r - 1)) <= 8
                                              for e in g.members[1 - t])
                cls = ('idle_near' if near else 'idle_far') if rw in IDLE else 'busy'
                key = f'{seg}_{cls}'
                k[key] += 1
                k[key + '_slot'] += slot[c]
                k[key + '_enemy_before'] += sum(1 for q in seq[:slot[c]] if g.team[q] != t)
                k[key + '_taken'] += taken[(c, r)]
                k[key + '_hit'] += taken[(c, r)] > 0
                de = g.death(c, r)
                if de:
                    k[key + '_death'] += 1
                    by = de.get('by')
                    if by is not None and by in g.team and g.team[by] != t:
                        k[key + '_death_champ'] += 1
                        if by not in (g.sees(c, r - 1) or []):
                            k[key + '_death_unseen'] += 1
                    k[key + '_death_gems'] += de.get('gems') or 0
                # first sight: enemies at turn start this round, none the round before
                s_now, s_prev = g.sees(c, r) or [], g.sees(c, r - 1) or []
                if s_now and not s_prev and c in g.first[r]:
                    p = g.pos(c, r - 1)
                    ts = g.first[r][c]
                    ds = [cheb(p, q) for q in (g.pos_at(e, r, ts) for e in s_now) if q is not None and p is not None]
                    if ds:
                        k[key + '_sight'] += 1
                        k[key + '_sight_dist'] += min(ds)
                        k[key + '_sight_close'] += min(ds) <= 4
                d, ks = g.champ_damage(c, r)
                k[key + '_dealt'] += d
                k[key + '_kills'] += len(ks)
            # captures and clears by live allies
            for e in g.by_round[r]:
                if e['k'] == 'capture' and e.get('team') == t:
                    k[seg + '_captures'] += 1
                    k[seg + '_capture_gems'] += sum(x[1] for x in e.get('shares') or [])
                if e['k'] == 'group_clear' and e.get('by') in mem:
                    k[seg + '_clears'] += 1
        # respawn rounds: the respawned champion over its first 6 rounds back
        for e in g.events:
            if e['k'] == 'respawn' and e['a'] in mem:
                r0 = e['r']
                k['resp'] += 1
                k['resp_slot'] += g.order(r0)[1][e['a']]
                for q in range(r0, min(g.N, r0 + 6) + 1):
                    k['resp_taken'] += taken[(e['a'], q)]
                    k['resp_death'] += g.died_in(e['a'], q)
        k['games'] += 1
        k['wins'] += g.meta['result']['winner'] == t
        stats[name] = k
    out['stats'] = stats
    return out


def main():
    ex = sys.argv[1]
    cand = sys.argv[2] if len(sys.argv) > 2 else 'ast-deadlast'
    rows = [r for r in index(ex) if r['ok']]
    seen, todo = set(), []
    for r in rows:
        if r['dir'] not in seen:
            seen.add(r['dir'])
            todo.append((ex, r, cand))
    with ProcessPoolExecutor(80) as pool:
        res = [x for x in pool.map(one, todo, chunksize=4) if 'error' not in x]
    tot = {'cand': Counter(), 'ref': Counter()}
    for x in res:
        for n in ('cand', 'ref'):
            tot[n].update(x['stats'].get(n, Counter()))
    print(f'{len(res)} games')
    for n in ('cand', 'ref'):
        k = tot[n]
        print(f"\n{n}: games {k['games']} wins {k['wins']} ({100 * k['wins'] / k['games']:.1f}%)")
        for seg in ('full', 'dead'):
            print(f"  {seg}: rounds {k[seg + '_rounds']}, captures/100r {100 * k[seg + '_captures'] / k[seg + '_rounds']:.2f}, "
                  f"capture gems/100r {100 * k[seg + '_capture_gems'] / k[seg + '_rounds']:.1f}, clears/100r "
                  f"{100 * k[seg + '_clears'] / k[seg + '_rounds']:.2f}, claim dupes {k[seg + '_claim_dupes']}/{k[seg + '_claims']}")
            for cls in ('idle_near', 'idle_far', 'busy'):
                key = f'{seg}_{cls}'
                m = k[key]
                if not m:
                    continue
                print(f"    {cls}: champ-rounds {m}, slot {k[key + '_slot'] / m:.2f}, enemy turns before {k[key + '_enemy_before'] / m:.2f}, "
                      f"hit {100 * k[key + '_hit'] / m:.2f}%, taken/round {k[key + '_taken'] / m:.2f}, deaths/1000 "
                      f"{1000 * k[key + '_death'] / m:.3f} (to champs {1000 * k[key + '_death_champ'] / m:.3f}, killer unseen "
                      f"the round before {1000 * k[key + '_death_unseen'] / m:.3f}), gems lost/1000 {1000 * k[key + '_death_gems'] / m:.1f}, "
                      f"dealt/round {k[key + '_dealt'] / m:.2f}, kills/1000 {1000 * k[key + '_kills'] / m:.3f}, first sights "
                      f"{k[key + '_sight']} at dist {k[key + '_sight_dist'] / max(1, k[key + '_sight']):.2f}, within 4 "
                      f"{100 * k[key + '_sight_close'] / max(1, k[key + '_sight']):.1f}%")
        print(f"  respawns {k['resp']}: slot {k['resp_slot'] / max(1, k['resp']):.2f}, taken over 6 rounds "
              f"{k['resp_taken'] / max(1, k['resp']):.1f}, deaths {100 * k['resp_death'] / max(1, k['resp']):.2f}%")


if __name__ == '__main__':
    main()
