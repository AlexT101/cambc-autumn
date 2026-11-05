"""Fish's home trips: gates, the timer-1 keep rule, walk vs recall, and why recalls complete (ECONOMY.md).

    python3 tools/fish/econ_home.py OUT.json [--episodes replays/fish-econ/episodes-v1.jsonl.gz]

Thresholds were read off the four oldest cohorts (FIT) and are reported unchanged on fifth +
sixth (HELD). Every metric has its denominator, a baseline and counterexamples (game, round,
actor). Refuses to overwrite OUT.
"""
import argparse, collections as C, gzip, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from econ_common import FIT, write_result  # noqa: E402
from breadth import static_groups, spawn  # noqa: E402
from econ_rows import COHORTS, bfs  # noqa: E402

H_HOME = 0.63     # health fraction at or below which a recall is kept off a capture
H_CAPTURE = 0.40  # the same while standing on an empty group (capturing)
GOLD = 30         # one shard
WALK = 5          # walk home iff the walk is at most this many steps (the recall's 5 turn ends)
FULL = {40, 50, 60, 80, 150}  # a group's respawn timer equals its full value only in its payout round


def load(path):
    out = C.defaultdict(list)
    with gzip.open(path, 'rt') as f:
        for line in f:
            d = json.loads(line)
            if d['kind'] in ('t1', 't4', 'arrival', 'payout'):
                out[d['kind']].append(d)
    return out


def role(e): return 'fit' if e['cohort'] in FIT else 'held'


def ref(e, x=None): return dict(game=e['game'], round=(x or e['x'])['r'], actor=e['actor'], type=e['type'])


def hp(x): return x['hp'] / x['maxhp']


def gate(x): return hp(x) <= H_HOME or x['gold'] >= GOLD


def t1_rule(x):
    """Keep the recall at timer 1 (so it completes)?"""
    if x['gstate'] == 2:
        return hp(x) <= H_CAPTURE
    if x['gstate'] == 3 and x['own_resp'] in FULL:
        return hp(x) <= H_HOME
    return gate(x)


def score(rows, pred, label, keep=8):
    by = C.defaultdict(lambda: [0, 0])
    bad = []
    for e in rows:
        ok = pred(e) == label(e)
        by[role(e)][0] += ok; by[role(e)][1] += 1
        if not ok and len(bad) < keep * 2 and (role(e) == 'held' or len(bad) < keep):
            bad.append(ref(e) | dict(predicted=pred(e), actual=label(e)))
    return {k: dict(correct=v[0], n=v[1], pct=round(100 * v[0] / v[1], 2)) for k, v in by.items()} | dict(counterexamples=bad)


def travel(arrivals):
    """Recall arrivals with a next camp group hit: (episode, walk from the timer-4 tile to that
    group, 4 turns left of the channel + the walk from spawn). Positive direct - via: home was
    also the quicker way to the next camp."""
    caches = {c: d for c, d, _ in COHORTS}
    by_game = C.defaultdict(list)
    for e in arrivals:
        if e['y']['kind'] == 'recall':
            by_game[(e['cohort'], e['game'])].append(e)
    out = []
    for (cohort, game), es in by_game.items():
        with gzip.open(Path(caches[cohort]) / f'{game}.json.gz') as f:
            m = json.load(f)
        side = m['side']; m = m['map']
        home = spawn(m, side); away = spawn(m, 1 - side)
        blocked = set(map(tuple, m['walls'] + m['holes'] + m['altars'])) | away
        groups, _ = static_groups(m)
        fields = {}
        alt = []
        for a_ in map(tuple, m['altars']):
            adj = [(a_[0] + dx, a_[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            alt.append(bfs(m, [p for p in adj if p not in blocked and 0 <= p[0] < m['width'] and 0 <= p[1] < m['height']], blocked))
        alt_home = min((f.get(h, 999) for f in alt for h in home), default=999)
        for e in es:
            e['alt_via'] = 4 + alt_home
            if not e['y']['next']:
                continue
            k = e['y']['next']['group']
            if k not in fields:
                tiles = set(map(tuple, groups[k]['tiles']))
                adj = {(x + dx, y + dy) for x, y in tiles for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
                fields[k] = bfs(m, sorted(p for p in adj if p not in blocked and 0 <= p[0] < m['width'] and 0 <= p[1] < m['height']), blocked)
            f = fields[k]
            out.append((e, f.get((e['x']['x'], e['x']['y']), 999), 4 + min(f.get(h, 999) for h in home)))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out'); p.add_argument('--episodes', default='replays/fish-econ/episodes-v1.jsonl.gz')
    a = p.parse_args()
    D = load(a.episodes)
    res = dict(constants=dict(H_HOME=H_HOME, H_CAPTURE=H_CAPTURE, GOLD=GOLD, WALK=WALK, FULL=sorted(FULL)), episodes=a.episodes)

    # 1. Gate: every completed recall satisfies hp <= 0.63 or gold >= 30 at its last keep (timer 1).
    rec = [e for e in D['arrival'] if e['y']['kind'] == 'recall']
    res['gate_completed_recalls'] = score(rec, lambda e: gate(e['x']['t1']), lambda e: True)
    res['gate_completed_recalls']['baseline_hp_only'] = {
        r: sum(hp(e['x']['t1']) <= H_HOME for e in rec if role(e) == r) for r in ('fit', 'held')}
    res['gate_completed_recalls']['baseline_gold_only'] = {
        r: sum(e['x']['t1']['gold'] >= GOLD for e in rec if role(e) == r) for r in ('fit', 'held')}
    viol = [e for e in rec if not gate(e['x']['t1'])]
    res['gate_completed_recalls']['violations_by'] = dict(
        type=C.Counter(e['type'] for e in viol).most_common(),
        gold_at_arrival_ge_30=sum(e['y']['gold_arrive'] >= GOLD for e in viol),
        on_paid_group_tile=sum(e['x']['t1']['gstate'] == 3 for e in viol),
        carrying_gems=sum(e['x']['t1']['gems'] > 0 for e in viol), n=len(viol))

    # 2. Post-payout, healthy and quiet: P(next endpoint is home) by the gold gate.
    pay = [e for e in D['payout'] if not e['y']['enemy'] and e['y']['end'] in ('farm', 'home', 'trib') and e['type'] != 'Prism']
    t = C.Counter()
    for e in pay:
        x = e['x']
        if hp(x) > H_HOME:
            t[(role(e), x['gold'] >= GOLD, x['home_walk'] <= WALK, e['y']['end'] == 'home')] += 1
    res['payout_healthy_home_rate'] = {
        f'{r} gold>={GOLD}={g} home_walk<={WALK}={near}': f"{t[(r, g, near, True)]}/{t[(r, g, near, True)] + t[(r, g, near, False)]}"
        for r in ('fit', 'held') for g in (False, True) for near in (False, True)}

    # 3. Timer-1 keep rule over every timer-1 decision (meaningful: both outcomes occur).
    t1 = D['t1']
    res['t1_rule'] = score(t1, lambda e: t1_rule(e['x']), lambda e: e['y']['keep'])
    for name, pred in (('always_keep', lambda e: True), ('always_cancel', lambda e: False),
                       ('health_only', lambda e: hp(e['x']) <= (H_CAPTURE if e['x']['gstate'] == 2 else H_HOME))):
        res['t1_rule']['baseline_' + name] = {r: sum(pred(e) == e['y']['keep'] for e in t1 if role(e) == r) for r in ('fit', 'held')}
    branch = C.Counter()
    for e in t1:
        x = e['x']
        b = 'capturing' if x['gstate'] == 2 else 'paid_this_round' if x['gstate'] == 3 and x['own_resp'] in FULL else \
            'paid_tile_later' if x['gstate'] == 3 else 'elsewhere'
        branch[(role(e), b, t1_rule(x) == e['y']['keep'])] += 1
    res['t1_rule']['by_branch'] = {f'{r} {b}': f'{branch[(r, b, True)]}/{branch[(r, b, True)] + branch[(r, b, False)]}'
                                   for r in ('fit', 'held') for b in ('capturing', 'paid_this_round', 'paid_tile_later', 'elsewhere')}

    # 4. Walk vs recall, for arrivals that pass the gate (deliberate home trips).
    arr = [e for e in D['arrival'] if gate(e['x'])]
    res['walk_vs_recall'] = score(arr, lambda e: 'walk' if e['x']['home_walk'] <= WALK else 'recall', lambda e: e['y']['kind'])
    res['walk_vs_recall']['baseline_always_recall'] = {r: sum(e['y']['kind'] == 'recall' for e in arr if role(e) == r) for r in ('fit', 'held')}
    sweep = {}
    for w in range(2, 10):
        sweep[w] = {r: sum(('walk' if e['x']['home_walk'] <= w else 'recall') == e['y']['kind'] for e in arr if role(e) == r) for r in ('fit', 'held')}
    res['walk_vs_recall']['sweep'] = sweep
    dist = C.Counter((min(e['x']['home_walk'], 12), e['y']['kind']) for e in arr if role(e) == 'fit')
    res['walk_vs_recall']['fit_by_distance'] = {d: dict(walk=dist[(d, 'walk')], recall=dist[(d, 'recall')]) for d in range(1, 13)}
    ungated = [e for e in D['arrival'] if not gate(e['x']) and e['y']['kind'] == 'walk']
    res['walk_vs_recall']['ungated_walk_ins'] = dict(n=len(ungated), from_adjacent=sum(e['x']['home_walk'] == 1 for e in ungated),
                                                     spent_on_arrival=sum(e['y']['spent'] > 0 for e in ungated))

    # 5. Why completed recalls complete: retreat / shop / other, at the last keep.
    cat = C.Counter()
    for e in rec:
        x = e['x']['t1']
        c = 'retreat (hp<=0.63)' if hp(x) <= H_HOME else 'shop (gold>=30, healthy)' if x['gold'] >= GOLD else 'other'
        if e['x']['t1']['ne'] > 0: c += ', enemy in sight'
        cat[(role(e), c)] += 1
    res['completed_recall_reasons'] = {f'{r} {c}': n for (r, c), n in sorted(cat.items())}
    # 6. Prepared recalls: how often the first keep (timer 4) happens and leads home.
    t4 = C.Counter()
    for e in D['t4']:
        x = e['x']; y = e['y']
        st = 'capturing' if x['gstate'] == 2 else 'paid tile' if x['gstate'] == 3 else 'elsewhere'
        t4[(role(e), st, 'cancel' if not y['keep'] else 'arrive' if y['arrive'] else 'interrupted' if y['interrupted'] else 'kept, cancelled later')] += 1
    res['t4_prepared_recalls'] = {f'{r} {st} {o}': n for (r, st, o), n in sorted(t4.items())}
    tr = travel(rec)
    tc = C.Counter()
    for e, direct, via in tr:
        x = e['x']['t1']
        c = 'retreat' if hp(x) <= H_HOME else 'shop' if x['gold'] >= GOLD else 'other'
        tc[(role(e), c, 'shortcut' if via < direct else 'detour 0-5' if via - direct <= 5 else 'detour >5')] += 1
    res['completed_recall_next_camp'] = {f'{r} {c} {s}': n for (r, c, s), n in sorted(tc.items())}
    ac = C.Counter()
    for e in rec:
        x = e['x']['t1']
        c = 'retreat' if hp(x) <= H_HOME else 'shop' if x['gold'] >= GOLD else 'other'
        if 'alt_via' in e and e['x']['gems'] > 0 and e['x']['alt_walk'] is not None:
            ac[(role(e), c, 'altar shortcut' if e['alt_via'] < e['x']['alt_walk'] else 'no altar shortcut')] += 1
        else:
            ac[(role(e), c, 'no gems')] += 1
    res['completed_recall_altar_shortcut'] = {f'{r} {c} {s}': n for (r, c, s), n in sorted(ac.items())}
    res['completed_recall_next_camp_note'] = ('direct: walk from the timer-4 tile to the next camp group hit after arrival; '
                                              'via: 4 channel turns left + walk from spawn to it')
    write_result(a.out, res)


if __name__ == '__main__':
    main()
