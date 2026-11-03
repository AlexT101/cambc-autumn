"""side_damage's ally assumption against what the allies did (ast-comms-meas's SD and TO lines).

usage: python3 research/turn-order-2026-11-02/scripts/comms_sd.py EXTRACT_DIR OUT.pkl
       python3 research/turn-order-2026-11-02/scripts/comms_sd.py --report OUT.pkl

SD round self target health taken our_raw their our_slot before offered acted | ally:now:next:raw:dist ...
  written in offer_kills after our turn in round r, for each enemy we can hit next turn (off its spawn).
  `now`: the ally has a turn left this round (counted whatever the order); `next`: it acts before slot
  `their` next round by its read priority. raw damages are before the target's `taken`.
TO round self band target raw kill_value: the turn's band bid (2 = kill), target of the winning K offer.

The window of an SD record is from our turn in round r to the target's turn in round r+1 (or the end
of round r+1 if it has none). Damage is read from the replay's attack/cast events.
"""
import pickle
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tolib import G, index, stdout_lines, traced_team  # noqa: E402


def parse(lines):
    sd, to = [], {}
    for l in lines:
        if l.startswith('SD '):
            if l.count('|') != 1:
                continue
            head, al = l.split('|')
            h = head.split()
            if len(h) != 12:
                continue
            try:
                rec = dict(r=int(h[1]), me=int(h[2]), t=int(h[3]), hp=int(h[4]), taken=float(h[5]), ours=int(h[6]),
                           their=int(h[7]), our_slot=int(h[8]), before=int(h[9]), offered=int(h[10]), acted=int(h[11]),
                           allies=[tuple(map(int, x.split(':'))) for x in al.split()])
            except ValueError:
                continue
            sd.append(rec)
        elif l.startswith('TO '):
            h = l.split()
            if len(h) != 7:
                continue
            try:
                to[(int(h[1]), int(h[2]))] = (int(h[3]), int(h[4]), int(h[5]), int(h[6]))
            except ValueError:
                continue
    return sd, to


def hits(g, c, r, t, lo=-1, hi=10 ** 15):
    """c's damage to t in round r between steps lo and hi (exclusive), and whether c stunned it."""
    d, stun = 0.0, False
    for e in g.by_round[r]:
        if e.get('a') != c or e['k'] not in ('attack', 'cast') or not (lo < e['s'] < hi):
            continue
        for v, x in e.get('dmg') or []:
            if v == t:
                d += x
        if t in (e.get('stun') or []):
            stun = True
    return d, stun


def turn_step(g, c, r):
    """First actor step of c in round r, else None (no actions, dead, stunned)."""
    return g.first[r].get(c)


def one(args):
    ex, row = args
    d, source = row['dir'], row['source']
    try:
        g = G(ex, d)
    except Exception as e:  # noqa: BLE001
        return {'error': str(e), 'dir': d}
    us = traced_team(source)
    raw = stdout_lines(source, us)
    sd, to = parse(raw)
    trusted = g.N
    if sum(len(l) + 1 for l in raw) > 1_000_000:
        last = 0
        for l in reversed(raw):
            p = l.split()
            if len(p) > 1 and p[1].isdigit():
                last = int(p[1])
                break
        trusted = last - 1
    recs = []
    for s in sd:
        r, me, t = s['r'], s['me'], s['t']
        if r + 1 > min(trusted, g.N) or t not in g.team:
            continue
        seq_r, slot_r, _ = g.order(r)
        seq_n, slot_n, _ = g.order(r + 1)
        # our turn step in r: SD is printed at its end; use our last event or slot
        my_events = [e['s'] for e in g.by_round[r] if e.get('a') == me and e['t'] >= 0]
        my_end = max(my_events) if my_events else None
        t_step = turn_step(g, t, r + 1)
        # target's death in the window
        died, died_by, died_step = False, None, None
        de = g.death(t, r)
        if de is not None and (my_end is None or de['s'] > my_end):
            died, died_by, died_step = True, de.get('by'), de['s']
        if not died:
            de = g.death(t, r + 1)
            if de is not None and (t_step is None or de['s'] < t_step):
                died, died_by, died_step = True, de.get('by'), de['s']
        hi_n = t_step if t_step is not None else 10 ** 15
        # our own next turn
        our_n_step = turn_step(g, me, r + 1)
        our_first = slot_n.get(me, 99) < slot_n.get(t, 99)
        our_dmg, our_stun = hits(g, me, r + 1, t, -1, hi_n)
        allies = []
        counted = set()
        for (a, now, nxt, araw, dist) in s['allies']:
            counted.add(a)
            dn = hits(g, a, r, t, my_end if my_end is not None else -1)[0] if now else 0.0
            dx = hits(g, a, r + 1, t, -1, hi_n)[0] if nxt else 0.0
            # ally acted before the target next round in fact
            a_first = slot_n.get(a, 99) < slot_n.get(t, 99)
            allies.append(dict(a=a, now=now, next=nxt, raw=araw, dist=dist, dmg_now=dn, dmg_next=dx, a_first=a_first,
                               alive_r=g.alive(a, r), any_now=hits(g, a, r, t, my_end if my_end is not None else -1)[0],
                               any_next=hits(g, a, r + 1, t, -1, hi_n)[0]))
        uncounted = 0.0
        for a in g.members[us]:
            if a == me or a in counted:
                continue
            uncounted += hits(g, a, r, t, my_end if my_end is not None else -1)[0] + hits(g, a, r + 1, t, -1, hi_n)[0]
        # healing / shield on the target in the window (enemy heals)
        healed = 0.0
        for rr, lo, hi in ((r, my_end if my_end is not None else -1, 10 ** 15), (r + 1, -1, hi_n)):
            for e in g.by_round[rr]:
                if lo < e['s'] < hi and e['k'] in ('cast',) and e.get('heal'):
                    for v, x in e.get('heal') if isinstance(e.get('heal'), list) else []:
                        if v == t:
                            healed += x
        tob = to.get((r, me))
        won_bid = tob is not None and tob[0] == 2 and tob[1] == t and tob[2] == tob[3]
        recs.append(dict(s, died=died, died_by_us=died_by in g.members[us] if died_by is not None else False,
                         died_by_me=died_by == me, our_first=our_first, our_turn=our_n_step is not None,
                         our_dmg=our_dmg, our_stun=our_stun, allies=allies, uncounted=uncounted, healed=healed,
                         won_bid=won_bid, me_alive_n=g.alive(me, r + 1) or g.died_in(me, r + 1)))
    return {'dir': d, 'recs': recs, 'trusted': trusted, 'n_to': len(to)}


def report(res):
    recs = [x for g in res if 'recs' in g for x in g['recs']]
    games = sum(1 for g in res if 'recs' in g)
    print(f'{games} games, {len(recs)} SD records ({len(recs) / games:.1f} a game)')
    # 1. ally terms
    terms = Counter()
    sums = defaultdict(float)
    for x in recs:
        tk = x['taken']
        for a in x['allies']:
            for kind in ('now', 'next'):
                if not a[kind]:
                    continue
                # the share of a two-turn assumption is not split: count both separately by actual
                act = a['dmg_now'] if kind == 'now' else a['dmg_next']
                terms[(kind, 'counted')] += 1
                terms[(kind, 'hit')] += act > 0
                if kind == 'next':
                    terms[('next', 'acted_after_target')] += not a['a_first']
            if a['now'] or a['next']:
                ass = a['raw'] * tk
                act = a['dmg_now'] + a['dmg_next']
                sums['assumed'] += ass
                sums['actual'] += act
                terms['ally_counted'] += 1
                terms['ally_hit'] += act > 0
                terms['ally_full'] += act >= 0.9 * ass
            else:
                terms['ally_visible_not_counted'] += 1
                terms['ally_visible_not_counted_hit'] += (a['any_now'] + a['any_next']) > 0
    print('\n## Ally terms in side_damage (all SD records)')
    for k in ('now', 'next'):
        c = terms[(k, 'counted')]
        if c:
            print(f"  {k}: counted {c}, hit the target {terms[(k, 'hit')]} ({100 * terms[(k, 'hit')] / c:.1f}%)"
                  + (f", acted after the target {terms[('next', 'acted_after_target')]} ({100 * terms[('next', 'acted_after_target')] / c:.1f}%)" if k == 'next' else ''))
    c = terms['ally_counted']
    print(f"  per counted ally: hit {100 * terms['ally_hit'] / c:.1f}%, >=90% of assumed {100 * terms['ally_full'] / c:.1f}%;"
          f" damage actual/assumed {sums['actual'] / max(1, sums['assumed']):.2f}")
    print(f"  visible allies in reach not counted: {terms['ally_visible_not_counted']}, of which hit {terms['ally_visible_not_counted_hit']}")

    def table(sel, name):
        xs = [x for x in recs if sel(x)]
        if not xs:
            return
        n = len(xs)
        died = sum(x['died'] for x in xs)
        print(f'\n## {name}: {n} ({n / games:.2f} a game); target died in window {died} ({100 * died / n:.1f}%), by us {sum(x["died_by_us"] for x in xs)}')
        cls = Counter()
        assumed_ally = actual_ally = 0.0
        for x in xs:
            tk = x['taken']
            a_ass = sum(a['raw'] * tk for a in x['allies'] if a['now'] or a['next'])
            a_act = sum(a['dmg_now'] + a['dmg_next'] for a in x['allies'])
            assumed_ally += a_ass
            actual_ally += a_act
            if x['died']:
                cls['killed'] += 1
                continue
            ours_ass = x['ours'] * tk
            if not x['our_first']:
                cls['we acted after the target'] += 1
            elif not x['me_alive_n'] or not x['our_turn']:
                cls['we had no turn (dead, stunned, idle)'] += 1
            elif x['our_dmg'] <= 0:
                cls['we acted first but did not hit it'] += 1
            elif x['our_dmg'] < 0.9 * ours_ass and x['our_dmg'] + a_act + x['uncounted'] < x['hp']:
                if a_act + x['uncounted'] < 0.9 * a_ass:
                    cls['we hit short and allies short'] += 1
                else:
                    cls['we hit short (allies delivered)'] += 1
            elif a_act + x['uncounted'] < 0.9 * a_ass:
                cls['allies short (we delivered)'] += 1
            else:
                cls['other (heal/shield/estimate)'] += 1
        for k, v in cls.most_common():
            print(f'  {k}: {v} ({100 * v / n:.1f}%)')
        print(f'  ally damage assumed {assumed_ally / n:.0f} a record, actual {actual_ally / n:.0f}')
        return xs

    table(lambda x: x['offered'] == 1, 'Offered kill bids (side_damage >= health, acting first)')
    table(lambda x: x['won_bid'], 'Winning K bids')
    table(lambda x: x['offered'] == 1 and any(a['now'] or a['next'] for a in x['allies']) and x['ours'] * x['taken'] < x['hp'],
          'Offered kill bids that need allies (our own blow short)')
    table(lambda x: x['offered'] == 1 and x['ours'] * x['taken'] >= x['hp'], 'Offered kill bids we kill alone')

    # 2. counterfactual: exact pledges = allies' actual damage in place of the assumed
    print('\n## Exact pledges (oracle: actual ally damage) in kill bids')
    flips = Counter()
    for x in recs:
        if not x['before']:
            continue
        tk = x['taken']
        ours = x['ours'] * tk
        a_ass = sum(a['raw'] * tk for a in x['allies'] if a['now'] or a['next'])
        a_act = sum(a['dmg_now'] + a['dmg_next'] for a in x['allies'] if a['now'] or a['next'])
        assumed_ok = ours + a_ass >= x['hp']
        exact_ok = ours + a_act >= x['hp']
        key = ('bid' if assumed_ok else 'no bid', 'exact bid' if exact_ok else 'exact no bid')
        flips[key] += 1
        flips[key + ('died',)] += x['died']
    for k in [('bid', 'exact bid'), ('bid', 'exact no bid'), ('no bid', 'exact bid'), ('no bid', 'exact no bid')]:
        n = flips[k]
        if n:
            print(f'  assumed {k[0]:6s} / {k[1]:13s}: {n} ({n / games:.2f} a game), target died {100 * flips[k + ("died",)] / n:.1f}%')
    # 3. kills without a seat: records where we could not act before (before = 0)
    xs = [x for x in recs if not x['before']]
    print(f'\n## Records without the seat (can_act_before false): {len(xs)}, target died {100 * sum(x["died"] for x in xs) / max(1, len(xs)):.1f}%')


def main():
    if sys.argv[1] == '--report':
        report(pickle.load(open(sys.argv[2], 'rb')))
        return
    ex, outp = sys.argv[1], sys.argv[2]
    rows = [r for r in index(ex) if r['ok'] and r['source'].endswith('.repl26a')]
    seen, todo = set(), []
    for r in rows:
        if r['dir'] in seen:
            continue
        seen.add(r['dir'])
        todo.append((ex, r))
    with ProcessPoolExecutor(40) as pool:
        res = list(pool.map(one, todo, chunksize=4))
    pickle.dump(res, open(outp, 'wb'))
    print(len(res), 'games;', sum(1 for x in res if 'error' in x), 'errors')
    report(res)


if __name__ == '__main__':
    main()
