"""Does Fish go after channelling enemies (recall, tribute, teleport)? Read off COMBAT's caches.

Inputs: replays/fish-combat/<cohort>-combat-v2.jsonl.gz (contact turns, combat_data.py) and
<cohort>-tiles-v1.jsonl.gz (positioning contexts, combat_rules.py), both from the actor's start view.

1. Hit rate: every visible enemy with one-turn damage reach > 0 from Fish (combat_common), Fish off
   its spawn. Label: that enemy is hit this turn (basic or spell). Split by the enemy's channel at
   Fish's turn start: none, recall timer 4 (started this round, often a prepared recall Fish cannot
   tell from a real one), recall timer <= 3 (kept at least one turn), tribute, teleport. Compared
   at the same distance and own-health band.
2. Positioning: COMBAT.md's engage rule (kill or hp > 0.49 and danger <= 0.28) per context, split
   by whether the nearest enemy is recalling. If Fish prioritised interrupting recalls, recalling
   enemies would be engaged more often than the rule predicts.
3. Stuns: a ready stun slot (STUN_SLOTS) and an enemy within 4 that is tributing: is the
   tributer stunned (the only way to cancel a tribute short of a kill)?
"""
import argparse
import collections
import gzip
import json

from combat_common import STUN_SLOTS
from combat_rules import engage, engaged
from tactic_common import FIT, HELD, write

SPLITS = (('fit', FIT), ('held', HELD))


def chan_class(e):
    if e['channel'] == 0:
        return 'none'
    if e['channel'] == 1:
        return 'recall t4' if e['ctimer'] >= 4 else 'recall t<=3'
    return 'tribute' if e['channel'] == 2 else 'teleport'


def load(c, kind):
    with gzip.open(f'replays/fish-combat/{c}-{kind}.jsonl.gz', 'rt') as f:
        for line in f:
            yield json.loads(line)


def main(out):
    res = {}
    for part, cos in SPLITS:
        hit = collections.Counter(); pos = collections.Counter(); stun = collections.Counter()
        for c in cos:
            ch = {}
            for r in load(c, 'combat-v2'):
                x = r['x']; es = x['enemies']
                ch[r['game'], r['round'], r['actor']] = chan_class(es[0])
                if x['at_home']:
                    continue
                hit_ids = {i for h in r['y']['hits'] for i in h[3]}
                for e in es:
                    if e['mine'] <= 0:
                        continue
                    k = chan_class(e)
                    band = (f"d{min(e['d'], 4)}", 'hp<0.5' if x['hpf'] < 0.5 else 'hp>=0.5')
                    for key in ((k,), (k,) + band):
                        hit[key, 'n'] += 1; hit[key, 'hit'] += e['id'] in hit_ids
                slot = STUN_SLOTS.get(x['type'])
                if slot is not None and x['cd'][slot] == 0:
                    near = [e for e in es if e['d'] <= 4 and e['type'] != 7 and e['stun'] <= 0]
                    stuns = [h for h in r['y']['hits'] if h[0] == 'cast' and h[1] == slot]
                    stunned = {i for h in stuns for i in h[3]}
                    for e in near:
                        k = 'tribute' if e['channel'] == 2 else 'other'
                        stun[k, 'n'] += 1; stun[k, 'stunned'] += e['id'] in stunned
            for r in load(c, 'tiles-v1'):
                e = engage(r['x'])
                k = ch.get((r['game'], r['round'], r['actor']))
                if e is None or k is None:
                    continue
                rec = 'nearest recalling' if k.startswith('recall') else 'nearest not recalling'
                key = (e[0], rec, 'rule engage' if e[1] else 'rule decline')
                pos[key, 'n'] += 1; pos[key, 'engaged'] += engaged(r['x'], r['y'])
        res[part] = dict(
            hit_rate={' '.join(k): dict(n=hit[k, 'n'], hit=hit[k, 'hit'], rate=round(hit[k, 'hit'] / hit[k, 'n'], 3))
                      for k in sorted({k for k, _ in hit})},
            positioning={' / '.join(k): dict(n=pos[k, 'n'], engaged=pos[k, 'engaged'], rate=round(pos[k, 'engaged'] / pos[k, 'n'], 3))
                         for k in sorted({k for k, _ in pos})},
            stun={k: dict(n=stun[k, 'n'], stunned=stun[k, 'stunned'], rate=round(stun[k, 'stunned'] / max(1, stun[k, 'n']), 3))
                  for k in ('tribute', 'other')})
        print(part)
        for k, v in res[part]['hit_rate'].items():
            if len(k.split()) <= 2:
                print('  hit', k, v)
        for k, v in res[part]['positioning'].items():
            print('  pos', k, v)
        print('  stun', res[part]['stun'])
    write(out, res)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    main(p.parse_args().out)
