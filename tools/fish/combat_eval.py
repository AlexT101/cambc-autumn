"""Evaluate the frozen combat rules (combat_rules.py) on discovery and held-out cohorts.

Discovery: model, confirm, third. Held out: fourth, fifth (later games, disjoint groups).
Writes OUT (JSON: counts, baselines, per-cohort, retained counterexamples) and OUT with
.errors.jsonl.gz (every failed prediction). Refuses to overwrite either.
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

import combat_rules as R
from combat_common import COHORTS, DISCOVERY

KEEP = 12  # counterexamples kept per metric and split in the JSON


class Metric:
    def __init__(self):
        self.n = collections.Counter(); self.ok = collections.Counter(); self.base = collections.Counter()
        self.pos = collections.Counter(); self.confusion = collections.Counter(); self.games = collections.defaultdict(set)
        self.examples = collections.defaultdict(list)

    def add(self, split, cohort, ref, pred, actual, base_pred, errors, name, detail=None):
        for k in (split, f'{split}:{cohort}'):
            self.n[k] += 1; self.ok[k] += pred == actual; self.base[k] += base_pred == actual; self.pos[k] += bool(actual)
        self.confusion[(split, bool(pred), bool(actual))] += 1
        self.games[split].add(ref['game'])
        if pred != actual:
            e = dict(metric=name, split=split, **ref, predicted=pred, actual=actual, detail=detail)
            errors.write(json.dumps(e, separators=(',', ':')) + '\n')
            if len(self.examples[split]) < KEEP:
                self.examples[split].append(e)

    def report(self):
        out = {}
        for k in sorted(self.n):
            out[k] = dict(n=self.n[k], correct=self.ok[k], accuracy=round(self.ok[k] / self.n[k], 4),
                          baseline_correct=self.base[k], baseline=round(self.base[k] / self.n[k], 4),
                          positive_rate=round(self.pos[k] / self.n[k], 4))
        return dict(results=out, games={k: len(v) for k, v in self.games.items()},
                    confusion=[dict(split=s, predicted=p, actual=a, n=n) for (s, p, a), n in sorted(self.confusion.items())],
                    counterexamples=self.examples)


def main(src, out):
    errs_path = out.replace('.json', '.errors.jsonl.gz')
    for p in (out, errs_path):
        if Path(p).exists():
            raise SystemExit(f'refusing to overwrite {p}')
    M = collections.defaultdict(Metric)
    lengths = collections.defaultdict(collections.Counter)
    with gzip.open(errs_path, 'wt') as errors:
        for name, _, _ in COHORTS:
            split = 'discovery' if name in DISCOVERY else 'heldout'
            # Positioning: end-tile choice rows.
            for line in gzip.open(Path(src) / f'{name}-tiles-v1.jsonl.gz', 'rt'):
                r = json.loads(line); x = r['x']
                c = R.contexts(x)
                if c is None:
                    continue
                ctx = c[0]
                ref = dict(game=r['game'], round=r['round'], actor=r['actor'], step=r['step'], context=ctx, type=x['type'])
                actual = R.engaged(x, r['y'])
                # Baseline: the context's majority answer on discovery (m2: no, m1/r: yes).
                base = ctx != 'm2'
                kill = any(q['kill'] for q in c[1])
                det = dict(hpf=round(x['hpf'], 3), gems=x['gems'],
                           danger=round(min(q['danger'] for q in c[1]), 3), kill=kill)
                for mname, use_kill in (('position_health_danger', False), ('position_health_danger_kill', True)):
                    _, pred = R.engage(x, use_kill)
                    M[mname].add(split, name, ref, pred, actual, base, errors, mname, det)
                    M[f'{mname}:{ctx}'].add(split, name, ref, pred, actual, base, errors, f'{mname}:{ctx}', det)
                if kill:
                    M['kill_available_engages'].add(split, name, ref, True, actual, base, errors, 'kill_available_engages', det)
            # Spells, resets and chases: contact-turn rows (ordered by actor, then round).
            last = {}; streaks = {}
            for line in gzip.open(Path(src) / f'{name}-combat-v2.jsonl.gz', 'rt'):
                r = json.loads(line); x = r['x']; y = r['y']
                ref = dict(game=r['game'], round=r['round'], actor=r['actor'], step=r['step'], type=x['type'])
                walks = y['moves'] > 0
                prev = last.get((r['game'], r['actor']))
                last[(r['game'], r['actor'])] = r
                prev_y = prev['y'] if prev and prev['round'] == r['round'] - 1 else None
                e = R.chase_opportunity(x, prev_y)
                if e is not None:
                    det = dict(target_hpf=round(e['hp'] / e['maxhp'], 3), target_d=e['d'], hpf=round(x['hpf'], 3),
                               ratio=round((x['ally_ehp'] + x['ehp']) / max(1.0, x['enemy_ehp']), 3))
                    M['chase'].add(split, name, ref, R.chase(x, e), R.chased(y, e), True, errors, 'chase', det)
                # Chase streaks: consecutive rounds that follow or hit the same fled-from target.
                k = (r['game'], r['actor']); st = streaks.get(k)
                if st and st['round'] == r['round'] - 1 and (
                        any(st['target'] in h[3] for h in y['hits']) or (e is not None and e['id'] == st['target'] and R.chased(y, e))):
                    st['round'] = r['round']; st['len'] += 1; st['hit_last'] = any(st['target'] in h[3] for h in y['hits'])
                else:
                    if st:
                        lengths[split][(min(st['len'], 10), st['hit_last'])] += 1
                    streaks.pop(k, None)
                    if e is not None and R.chased(y, e):
                        streaks[k] = dict(round=r['round'], target=e['id'], len=1,
                                          hit_last=any(e['id'] in h[3] for h in y['hits']))
                s = R.damage_spell_opportunity(x)
                if s is not None:
                    other = any(c['slot'] != s for c in y['casts'])
                    actual = s in y['cast_champ']
                    # Conditional on the turn's movement: cast iff standing still and the cast is unused.
                    M['damage_spell_iff_still'].add(split, name, ref, (not walks) and not other, actual, False, errors,
                                                    'damage_spell_iff_still', dict(walks=walks, other_cast=other))
                    M['damage_spell_iff_still_any_cast'].add(split, name, ref, not walks, actual or other, False, errors,
                                                             'damage_spell_iff_still_any_cast', dict(walks=walks))
                if R.cassi_stun_opportunity(x):
                    actual = 1 in y['cast_champ']
                    M['cassi_stun_unless_still_with_damage'].add(split, name, ref, R.cassi_stun(x, walks), actual, True, errors,
                                                                 'cassi_stun_unless_still_with_damage',
                                                                 dict(walks=walks, damage_cd=x['cd'][0]))
                if R.hor_shield_opportunity(x):
                    actual = any(c['slot'] == 0 for c in y['casts'])
                    M['hor_shield_iff_threat'].add(split, name, ref, R.hor_shield(x), actual, False, errors,
                                                   'hor_shield_iff_threat', dict(threat=round(x['threat'], 1), d1=x['d1']))
                rs = R.reset_opportunity(x, y)
                if rs is not None:
                    actual = any(c['slot'] == rs for c in y['casts'])
                    other = any(c['slot'] != rs for c in y['casts'])
                    M['reset_or_other_cast_after_surviving_basic'].add(split, name, ref, True, actual or other, False, errors,
                                                                       'reset_or_other_cast_after_surviving_basic', None)
                    if not other:
                        M['reset_after_surviving_basic_cast_unused'].add(split, name, ref, True, actual, False, errors,
                                                                         'reset_after_surviving_basic_cast_unused', None)
            print(name, {k: dict(m.n) .get(split, 0) for k, m in M.items() if ':' not in k}, flush=True)
    result = dict(schema=1, source=src, rules=dict(H_MIN=R.H_MIN, DANGER_MAX=R.DANGER_MAX),
                  metrics={k: m.report() for k, m in sorted(M.items())},
                  chase_streaks={sp: [dict(turns=a, last_turn_hit_target=b, n=n) for (a, b), n in sorted(c.items())]
                                 for sp, c in lengths.items()})
    Path(out).write_text(json.dumps(result, indent=1, default=str))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--src', default='replays/fish-combat')
    p.add_argument('out')
    a = p.parse_args()
    main(a.src, a.out)
