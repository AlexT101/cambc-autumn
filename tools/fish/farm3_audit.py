"""Forced vs free decisions for the farm/targeting metrics (FARM3.md, FARM-CHOICE.md, CHOICE.md,
ROUTES.md, CONTINUATION.md's camp-target rule).

A row is *forced* when cambc-rules.yaml (or the label's own horizon) leaves one possible outcome:
  destinations  at most one feasible candidate: reachable (static walk < 999), not the group just
                paid out, and max(walk, remembered respawn) <= 40, the label window (a group still
                respawning past it can be neither hit nor occupied as empty in time)
  camp target   one legal target: a single visible living camp in basic range
  incoming      no free camp tile, a stun or an uncancellable teleport channel (the rows' own
                filter already demands a free tile, no stun and channel 0/1, so none are forced)
  trip          tribute needs >= 1 carried gem: rows with 0 gems are a two-way choice, not forced
  activities    dead turns (shop/priority only), the respawn turn (no walk, attack or cast), stunned
                turns and teleport channels (cannot be cancelled) are forced
Accuracy and the baseline are reported on all rows and on free rows; the forced share says how much
of a headline came from forced rows. Writes OUT.json; refuses to overwrite.
  python3 tools/fish/farm3_audit.py research/fish-2026-11-05/rule-audit-farm.json
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

import choice_model
import routes_model
from farm2_features import featurizer
from farm2_lib import wait_correct
from farm3_common import ALIVE, CT, DEATHS, ID, OBS, Game, entries, load, team_rounds, write_json
from farm3_lib import argmax, candidates, rows_of, score_rows

M = 'research/fish-2026-11-05/'
HORIZON = 40


def feasible(x):
    return [c for c in candidates(x) if max(c['walk'], c['respawn']) <= HORIZON]


def tally(rows, preds, base):
    out = {}
    for name, sel in (('all', lambda r: True), ('forced', lambda r: len(feasible(r['x'])) <= 1),
                      ('free', lambda r: len(feasible(r['x'])) > 1)):
        idx = [i for i, r in enumerate(rows) if sel(r)]
        y = [rows[i]['y']['targets'][0] for i in idx]
        out[name] = dict(n=len(idx), model=sum(preds[i] == t for i, t in zip(idx, y)), baseline=sum(base[i] == t for i, t in zip(idx, y)))
        for k in ('model', 'baseline'):
            out[name][k + '_acc'] = out[name][k] / len(idx) if idx else None
    out['forced_share'] = out['forced']['n'] / out['all']['n']
    out['feasible_candidates_median'] = sorted(len(feasible(r['x'])) for r in rows)[len(rows) // 2]
    return out


def wait_pred(rows):
    return [r['y']['targets'][0] if ok else -1 for r, ok in zip(rows, wait_correct(rows))]


def destinations():
    res = {}
    f3 = json.loads(Path(M + 'farm3-fit.json').read_text()); run = featurizer(f3['sets'], f3['opts'])
    for c in ('fifth', 'sixth', 'seventh'):
        own = rows_of([c]); team = rows_of([c], team=True); base = wait_pred(own)
        res[f'FARM3 farm3 (team memory) {c}'] = tally(own, [argmax(i, s) for i, s in score_rows(team, f3['models']['farm3'], run)], base)
        res[f'FARM3 farm2 refit, own memory {c}'] = tally(own, [argmax(i, s) for i, s in score_rows(own, f3['models']['farm2'], run)], base)
    for fit, cs in (('farm2-fit-A.json', ('fifth', 'confirm', 'sixth')), ('farm2-fit.json', ('seventh',))):
        f2 = json.loads(Path(M + fit).read_text()); run2 = featurizer(f2['sets'], f2['opts'])
        for c in cs:
            own = rows_of([c])
            res[f'FARM-CHOICE {fit} {c}'] = tally(own, [argmax(i, s) for i, s in score_rows(own, f2, run2)], wait_pred(own))
    frozen = json.loads(Path(M + 'choice-fit.json').read_text())
    for c in ('fifth', 'sixth'):
        own = rows_of([c])
        res[f'CHOICE choice-fit.json {c}'] = tally(own, [choice_model.predict(r['x'], frozen) for r in own], wait_pred(own))
    trees = json.loads(Path(M + 'routes-trees.json').read_text())
    for c in ('fourth', 'fifth'):
        own = rows_of([c])
        res[f'ROUTES route/fitted {c}'] = tally(own, [routes_model.route(r['x'], 'fitted', trees['route']) for r in own], wait_pred(own))
    return res


def camp_target():
    from farm_model import camp_target as rule
    res = {}
    for name, path in (('discovery (model)', 'replays/fish-model/breadth-v2.json.gz'), ('confirmation', 'replays/fish-confirm/breadth-v2.json.gz')):
        rows = json.loads(gzip.open(path).read())['rows']['camp_attack']
        st = collections.Counter()
        for r in rows:
            cs = r['candidates']; y = r['target']
            p = rule(cs, r['previous_group']); b = min(cs, key=lambda c: (c['hp'], c['id']))['id']
            kind = 'forced_one_target' if len(cs) == 1 else 'free_one_group' if len({c['group'] for c in cs}) == 1 else 'free_multi_group'
            for k in (kind, 'all') + (('free',) if len(cs) > 1 else ()):
                st[k, 'n'] += 1; st[k, 'rule'] += p == y; st[k, 'min_hp_id'] += b == y; st[k, 'uniform'] += 1 / len(cs)
            if len(cs) > 1:
                # A free row whose candidates all share the lowest HP: only the coordinate tie-break decides.
                lo = min(c['hp'] for c in cs)
                tie = sum(c['hp'] == lo for c in cs) > 1
                k2 = 'free_hp_tied' if tie else 'free_hp_untied'
                st[k2, 'n'] += 1; st[k2, 'rule'] += p == y; st[k2, 'min_hp_id'] += b == y; st[k2, 'uniform'] += 1 / len(cs)
        res[name] = {k: {m: round(st[k, m], 2) for m in ('n', 'rule', 'min_hp_id', 'uniform')}
                     for k in ('all', 'forced_one_target', 'free', 'free_one_group', 'free_multi_group', 'free_hp_tied', 'free_hp_untied')}
        res[name]['forced_share'] = st['forced_one_target', 'n'] / st['all', 'n']
    return res


def routes_rows():
    trees = json.loads(Path(M + 'routes-trees.json').read_text())
    res = {}
    for c, path in (('fifth', 'replays/fish-fifth/routes-v3.jsonl.gz'),):
        inc = collections.Counter(); trip = collections.Counter()
        for line in gzip.open(path, 'rt'):
            r = json.loads(line); x = r['x']; y = r['y']
            if r['kind'] == 'incoming':
                inc['n'] += 1; inc[f"channel {x['channel']}"] += 1; inc['no_free_tile'] += x['free'] == 0
                p = routes_model.predict('incoming', x, trees); inc['tree'] += p == y['joined']; inc['never'] += not y['joined']
                if y['settled'] is not None:
                    q = routes_model.tree(trees['incoming_settled'], routes_model.features('incoming', x))
                    inc['settled_n'] += 1; inc['settled_tree'] += q == y['settled']; inc['settled_never'] += not y['settled']
            elif r['kind'] == 'trip' and x['reason'] != 'opening' and y['status'] in ('farm', 'home', 'tribute'):
                k = 'gems>=1 (three-way)' if x['gems'] > 0 else 'gems=0 (tribute impossible)'
                p = routes_model.predict('trip', x, trees)
                for kk in (k, 'all'):
                    trip[kk, 'n'] += 1; trip[kk, 'tree'] += p == y['status']; trip[kk, 'always_farm'] += y['status'] == 'farm'
                    trip[kk, 'label_tribute'] += y['status'] == 'tribute'; trip[kk, 'pred_tribute'] += p == 'tribute'
        res[c] = dict(incoming=dict(inc), trip={k: {m: trip[k, m] for m in ('n', 'tree', 'always_farm', 'label_tribute', 'pred_tribute')}
                                               for k in ('all', 'gems>=1 (three-way)', 'gems=0 (tribute impossible)')})
    return res


def activities():
    st = collections.Counter()
    for _, e in entries():
        key = e['sha256'][:16]
        obs = load(OBS / f'{key}.json.gz'); G = Game(obs); T = team_rounds(key)
        prev_alive = {}
        for snap in obs['rounds']:
            R = T.get(snap['r']) if T else None
            stun = {c[0]: c[12] for c in R['cp']['ch']} if R and R.get('cp') else {}
            for c in snap['ch']:
                i = c[ID]
                if i not in G.fish:
                    continue
                st['turns'] += 1
                if not c[ALIVE]:
                    st['dead'] += 1
                elif prev_alive.get(i) == 0:
                    st['respawn_turn'] += 1
                elif stun.get(i, -1) >= 0:
                    st['stunned'] += 1
                elif c[CT] == 3:
                    st['teleport_channel'] += 1
                prev_alive[i] = c[ALIVE]
    st['forced'] = st['dead'] + st['respawn_turn'] + st['stunned'] + st['teleport_channel']
    return dict(st)


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('out')
    x = a.parse_args()
    if Path(x.out).exists():
        raise SystemExit(f'refusing to overwrite {x.out}')
    res = dict(definitions=__doc__)
    for name, fn in (('camp_target', camp_target), ('routes', routes_rows), ('activities', activities), ('destinations', destinations)):
        res[name] = fn()
        print(name, json.dumps(res[name])[:600], flush=True)
    write_json(x.out, res)


if __name__ == '__main__':
    main()
