"""Fish's tributes: Prism's winning gate, the post-payout altar trade-off, capture, altar choice,
channels (ECONOMY.md).

    python3 tools/fish/econ_tribute.py OUT.json [--episodes ...episodes-v1.jsonl.gz] [--rows ...rows-v3.jsonl.gz]

Rules were read off the four oldest cohorts (FIT) and are reported unchanged on fifth + sixth
(HELD). Refuses to overwrite OUT.
"""
import argparse, collections as C, gzip, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from econ_common import FIT, ROLE, ROWS, CANCEL, TRIB_OK, games, write_result  # noqa: E402

WIN = 1000
K, SLACK, FREE = 8, 2, 2   # tribute iff alt_walk <= ready + SLACK and gems >= K * (alt_walk - FREE)


def role(e): return 'fit' if e['cohort'] in FIT else 'held'


def ref(e): return dict(game=e['game'], round=e['x']['r'], actor=e['actor'], type=e['type'])


def frac(rows, pred):
    out = {}
    for r in ('fit', 'held'):
        s = [e for e in rows if role(e) == r]
        k = sum(1 for e in s if pred(e))
        out[r] = dict(k=k, n=len(s), pct=round(100 * k / len(s), 2) if s else None)
    return out


def payout_rule(x):
    return x['alt_walk'] <= x['ready'] + SLACK and x['gems'] >= K * (x['alt_walk'] - FREE)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--episodes', default='replays/fish-econ/episodes-v1.jsonl.gz')
    p.add_argument('--rows', default=ROWS)
    a = p.parse_args()
    D = C.defaultdict(list)
    with gzip.open(a.episodes, 'rt') as f:
        for line in f:
            d = json.loads(line)
            if d['kind'] in ('trib', 'adj', 'payout'):
                D[d['kind']].append(d)
    res = dict(constants=dict(WIN=WIN, K=K, SLACK=SLACK, FREE=FREE), episodes=a.episodes, rows=a.rows)

    # 1. Prism: own bag + team score + every visible ally's bag >= 1000 at each tribute start.
    pt = [e for e in D['trib'] if e['type'] == 'Prism']
    tot = lambda e, g: g + e['x']['score_own'] + e['x']['al_gems']
    res['prism_gate'] = dict(
        rule='own bag + team score + bags of all allies in sight >= 1000',
        starts=frac(pt, lambda e: tot(e, e['x']['sub_gems']) >= WIN),
        games={r: len({e['game'] for e in pt if role(e) == r}) for r in ('fit', 'held')},
        old_rule_tributing_allies_only=frac(pt, lambda e: e['x']['sub_gems'] + e['x']['score_own'] + e['x']['al_trib_gems'] >= WIN),
        bag_plus_score_only=frac(pt, lambda e: e['x']['sub_gems'] + e['x']['score_own'] >= WIN),
        min_margin=min(tot(e, e['x']['sub_gems']) - WIN for e in pt),
        smallest=sorted(((tot(e, e['x']['sub_gems']), e['x']['r']), ref(e) | dict(bag=e['x']['sub_gems'], score=e['x']['score_own'], allies=e['x']['al_gems'])) for e in pt)[:5],
        bags=sorted(e['x']['sub_gems'] for e in pt))
    pa = [e for e in D['adj'] if e['type'] == 'Prism']
    t = C.Counter((role(e), tot(e, e['x']['gems']) >= WIN, e['x']['ne'] > 0, e['y']['start']) for e in pa)
    res['prism_gate']['adjacent_frames'] = {f'{r} gate={g} enemy={en}': f'{t[(r, g, en, True)]}/{t[(r, g, en, True)] + t[(r, g, en, False)]} start'
                                           for r in ('fit', 'held') for g in (False, True) for en in (False, True)}
    pp = [e for e in D['payout'] if e['type'] == 'Prism' and e['y']['end'] in ('farm', 'home', 'trib')]
    res['prism_gate']['payouts_then_tribute'] = frac(pp, lambda e: e['y']['end'] == 'trib')

    # 2. Others after a payout: the altar must be no farther than the next ready camp (+2) and the
    #    bag at least 8 gems per walking step beyond 2.
    ok = lambda e: (not e['y']['enemy'] and e['y']['end'] in ('farm', 'home', 'trib') and e['type'] != 'Prism'
                    and e['x']['alt_walk'] is not None and e['x']['gems'] > 0)
    pay = [e for e in D['payout'] if ok(e)]
    y = lambda e: e['y']['end'] == 'trib'
    res['payout_tribute'] = dict(
        rule=f'tribute iff alt_walk <= ready + {SLACK} and gems >= {K} * (alt_walk - {FREE})',
        accuracy=frac(pay, lambda e: payout_rule(e['x']) == y(e)),
        baseline_never=frac(pay, lambda e: not y(e)))
    best_alt = {}
    for r in ('fit', 'held'):
        s = [e for e in pay if role(e) == r]
        best_alt[r] = {k: sum((e['x']['alt_walk'] <= k) == y(e) for e in s) for k in range(0, 13)}
    res['payout_tribute']['baseline_alt_walk_le_k'] = best_alt
    for r in ('fit', 'held'):
        s = [e for e in pay if role(e) == r]
        cm = C.Counter((payout_rule(e['x']), y(e)) for e in s)
        res['payout_tribute'][f'confusion_{r}'] = dict(tp=cm[(True, True)], fp=cm[(True, False)], fn=cm[(False, True)], tn=cm[(False, False)])
    near = [e for e in pay if e['x']['alt_walk'] <= 12]
    res['payout_tribute']['meaningful_alt_walk_le_12'] = dict(accuracy=frac(near, lambda e: payout_rule(e['x']) == y(e)),
                                                              baseline_never=frac(near, lambda e: not y(e)))
    res['payout_tribute']['by_type_held'] = {
        tname: dict(rule=sum(payout_rule(e['x']) == y(e) for e in pay if role(e) == 'held' and e['type'] == tname),
                    never=sum(not y(e) for e in pay if role(e) == 'held' and e['type'] == tname),
                    n=sum(1 for e in pay if role(e) == 'held' and e['type'] == tname))
        for tname in sorted({e['type'] for e in pay})}
    win = C.Counter((role(e), e['x']['gems'] + e['x']['score_own'] + e['x']['al_gems'] >= WIN, payout_rule(e['x']), y(e)) for e in pay)
    res['payout_tribute']['winning_bag'] = {f'{r} win={w} rule={ru}': f'{win[(r, w, ru, True)]}/{win[(r, w, ru, True)] + win[(r, w, ru, False)]} tribute'
                                            for r in ('fit', 'held') for w in (False, True) for ru in (False, True)}
    errs = [e for e in pay if role(e) == 'held' and payout_rule(e['x']) != y(e)]
    res['payout_tribute']['held_counterexamples'] = [ref(e) | dict(gems=e['x']['gems'], alt_walk=e['x']['alt_walk'], ready=e['x']['ready'],
                                                                    actual=e['y']['end']) for e in errs[:12]]

    # 3. Tribute while capturing: frames within 1 of an altar with gems, on an empty group vs not.
    t = C.Counter((role(e), e['x']['gstate'] == 2, e['y']['start']) for e in D['adj'])
    res['capture'] = {f'{r} capturing={c}': f'{t[(r, c, True)]}/{t[(r, c, True)] + t[(r, c, False)]} start'
                      for r in ('fit', 'held') for c in (False, True)}
    res['capture']['starts_on_empty_group'] = frac(D['trib'], lambda e: e['x']['gstate'] == 2)

    # 4. Altar choice: of tributes reached by an approach walk on maps with 2+ altars, the altar
    #    nearest by walk at the approach start.
    mul = [e for e in D['trib'] if e['n_altars'] >= 2 and e['y']['approach'] > 0]
    res['altar_choice'] = dict(nearest_at_approach_start=frac(mul, lambda e: e['y']['approach_x']['alt_idx'] == e['x']['alt_idx']))

    # 5. Bags tributed, per type (descriptive), and the channel's end.
    bags = C.defaultdict(list)
    for e in D['trib']:
        bags[e['type']].append(e['x']['sub_gems'] or 0)
    res['bags'] = {k: dict(n=len(v), q=[sorted(v)[int(q * (len(v) - 1))] for q in (0, .1, .25, .5, .75, .9)]) for k, v in bags.items()}
    ends = C.Counter()
    for g in games(a.rows):
        for aid, rows in g['actors'].items():
            for i, r in enumerate(rows):
                if not r.acts & TRIB_OK: continue
                end = 'censored'
                for q in rows[i + 1:]:
                    if not q.alive: end = 'died'; break
                    if q.ch == 2:
                        if q.acts & CANCEL: end = 'cancelled by Fish'; break
                        continue
                    end = 'completed' if q.score_own > r.score_own or q.gems < r.gems else 'interrupted'
                    break
                ends[(ROLE[g['cohort']], end)] += 1
    res['channel_ends'] = {f'{r} {e}': n for (r, e), n in sorted(ends.items())}
    write_result(a.out, res)


if __name__ == '__main__':
    main()
