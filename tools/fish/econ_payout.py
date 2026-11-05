"""After a capture payout: farm, home or tribute next? A small tree fitted on FIT, scored on HELD (ECONOMY.md).

    python3 tools/fish/econ_payout.py OUT.json [--episodes replays/fish-econ/episodes-v1.jsonl.gz]

Features are the actor's turn-start state at the payout turn (causal whitelist below). Episodes
whose endpoint follows an enemy sighting, death, timeout or censoring are dropped, as in
ROUTES.md section 3. Refuses to overwrite OUT.
"""
import argparse, collections as C, gzip, json, sys
from pathlib import Path

import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text

sys.path.insert(0, str(Path(__file__).parent))
from econ_common import FIT, write_result  # noqa: E402

NAMES = ['hp_frac', 'gold', 'gems', 'payout_gems', 'payout_gold', 'home_walk', 'altar_walk', 'ready', 'ready_walk',
         'ready_wait', 'n_ready10', 'via_home_extra', 'score_own', 'score_opp', 'visible_allies', 'is_prism', 'is_marcella']


def feats(e):
    x = e['x']
    alt = x['alt_walk'] if x['alt_walk'] is not None else 999
    return [x['hp'] / x['maxhp'], x['gold'], x['gems'], x['dgems'], x['dgold'], x['home_walk'], alt, x['ready'], x['ready_walk'],
            x['ready_wait'], x['n_ready10'], x['ready_home'] - x['ready'], x['score_own'], x['score_opp'], x['nal'],
            e['type'] == 'Prism', e['type'] == 'Marcella']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out'); p.add_argument('--episodes', default='replays/fish-econ/episodes-v1.jsonl.gz')
    p.add_argument('--depth', type=int, default=4); p.add_argument('--leaf', type=int, default=40)
    a = p.parse_args()
    E = []
    with gzip.open(a.episodes, 'rt') as f:
        for line in f:
            d = json.loads(line)
            if d['kind'] == 'payout':
                E.append(d)
    ends = C.Counter((e['cohort'] in FIT, e['y']['end'], e['y']['enemy']) for e in E)
    ok = lambda e: not e['y']['enemy'] and e['y']['end'] in ('farm', 'home', 'trib')
    F = [e for e in E if e['cohort'] in FIT and ok(e)]
    H = [e for e in E if e['cohort'] not in FIT and ok(e)]
    y = lambda S: np.array([e['y']['end'] for e in S])
    t = DecisionTreeClassifier(max_depth=a.depth, min_samples_leaf=a.leaf, random_state=0).fit([feats(e) for e in F], y(F))
    res = dict(depth=a.depth, leaf=a.leaf, features=NAMES, tree=export_text(t, feature_names=NAMES),
               all_episodes={f"{'fit' if k[0] else 'held'} {k[1]} enemy={k[2]}": n for k, n in sorted(ends.items())})
    for name, S in (('fit', F), ('held', H)):
        pr = t.predict([feats(e) for e in S]); yy = y(S)
        maj = C.Counter(y(F)).most_common(1)[0][0]
        res[name] = dict(n=len(S), correct=int((pr == yy).sum()), pct=round(100 * float((pr == yy).mean()), 2),
                         majority=maj, majority_correct=int((yy == maj).sum()),
                         confusion={f'{u}->{v}': int(((yy == u) & (pr == v)).sum()) for u in ('farm', 'home', 'trib') for v in ('farm', 'home', 'trib')},
                         games=len({e['game'] for e in S}))
        by_groups = C.defaultdict(lambda: [0, 0])
        for e, q in zip(S, pr):
            by_groups[e['group']][0] += q == e['y']['end']; by_groups[e['group']][1] += 1
        res[name]['groups'] = len(by_groups)
        res[name]['group_pct_min_max'] = [round(100 * min(c / n for c, n in by_groups.values()), 1),
                                          round(100 * max(c / n for c, n in by_groups.values()), 1)]
    hold = [e for e in H]
    pr = t.predict([feats(e) for e in hold])
    res['held_counterexamples'] = [dict(game=e['game'], round=e['x']['r'], actor=e['actor'], type=e['type'], predicted=str(q),
                                        actual=e['y']['end'], gold=e['x']['gold'], gems=e['x']['gems'], hp=round(e['x']['hp'] / e['x']['maxhp'], 2),
                                        home_walk=e['x']['home_walk'], alt_walk=e['x']['alt_walk'], ready=e['x']['ready'])
                                   for e, q in zip(hold, pr) if q != e['y']['end']][:15]
    write_result(a.out, res)


if __name__ == '__main__':
    main()
