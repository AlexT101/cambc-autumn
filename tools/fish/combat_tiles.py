"""End-tile choice (positioning) episodes for Fish champions near visible enemies.

One row per alive, unstunned, normally completed turn whose start perspective shows a
living enemy champion within 5, with no dash, teleport or tribute that turn. Candidates are
the start tile and its walkable neighbours, judged from public terrain and units visible at
turn start (hidden blockers are not modelled). The label is the end tile. Tile features use
only the start perspective: enemy positions, health, cooldowns, stats, and own state.
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

from breadth import RANGED, dist, spawn, xy
from combat_common import COHORTS, KIT, ehp, hits, load, one_turn_damage, shield, stunned_next


def tile_features(g, t, me, enemies, allies, home, pos, cand):
    reset = KIT[me['type']][0]
    reset_ready = reset is not None and me['cd'][reset] == 0
    ranged = me['type'] in RANGED
    my_ehp = max(ehp(me), 1)
    rows = []
    for p in cand:
        ds = [dist(p, xy(e)) for e in enemies]
        danger = sum(0 if stunned_next(e) else one_turn_damage(e, d) for e, d in zip(enemies, ds))
        reach_n = sum((not stunned_next(e)) and one_turn_damage(e, d) > 0 for e, d in zip(enemies, ds))
        stay = p == pos
        if ranged:
            can = [e for e, d in zip(enemies, ds) if d <= 3 and (stay or reset_ready)]
        else:
            # Walking and attacking are independent: adjacency before or after the step.
            can = [e for e, d in zip(enemies, ds) if d <= 1] + [e for e in enemies if dist(pos, xy(e)) <= 1]
        kill = any(one_turn_damage(me, 1 if not ranged else 3) >= ehp(e) for e in can)
        rows.append(dict(p=p, stay=int(stay), danger=danger / my_ehp, reach_n=reach_n, dmin=min(ds),
                         dsum=sum(min(d, 8) for d in ds) / len(ds), can_hit=int(bool(can)), kill=int(kill),
                         home=min(dist(p, h) for h in home), home_now=min(dist(pos, h) for h in home),
                         allies2=sum(dist(p, xy(a)) <= 2 for a in allies),
                         ally_min=min((dist(p, xy(a)) for a in allies), default=9)))
    return rows


def main(name, manifest, cache, out):
    if Path(out).exists():
        raise SystemExit(f'refusing to overwrite {out}')
    entries = json.loads(Path(manifest).read_text())
    counts = collections.Counter()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, 'wt') as f:
        for n, entry in enumerate(entries):
            g = load(cache, entry)
            m_ = g['map']
            home = spawn(m_, g['side'])
            static = set(map(tuple, m_['walls'] + m_['holes'] + m_['altars'])) | spawn(m_, 1 - g['side'])
            for t in g['turns']:
                s = t['start']; me = s['me']
                if not (me['alive'] and t.get('finish') == 'End turn' and 'end' in t and 'x' in t['end']['me']):
                    continue
                if any(b['type'] == 1 for b in me['buffs']) or me['channelType'] not in (0, 1):
                    continue
                pos = xy(me)
                enemies = [e for e in s['enemies'] if 'x' in e]
                if not enemies or min(dist(pos, xy(e)) for e in enemies) > 5:
                    continue
                counts['contact5'] += 1
                kinds = [a['kind'] for a in t['actions']]
                if any(a['kind'] == 'Cast ability' and a['ability'] == 6 for a in t['actions']) or \
                        'Teleport channel' in kinds or 'Submit gems' in kinds:
                    counts['excluded_dash_teleport_tribute'] += 1
                    continue
                blocked = static | {xy(c) for c in s['allies'] + enemies} | {xy(c) for c in s['camps'] if c['hp'] > 0}
                cand = [pos] + [(pos[0] + dx, pos[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                                if (dx or dy) and 0 <= pos[0] + dx < m_['width'] and 0 <= pos[1] + dy < m_['height']
                                and (pos[0] + dx, pos[1] + dy) not in blocked]
                endp = xy(t['end']['me'])
                if endp not in cand:
                    counts['end_not_candidate'] += 1
                    continue
                feats = tile_features(g, t, me, enemies, s['allies'], home, pos, cand)
                hs = hits(t, me['type'])
                x = dict(type=me['type'], hpf=me['hp'] / me['maxHp'], ehpf=min(1, ehp(me) / me['maxHp']),
                         gems=me.get('gems', 0), gold=me.get('gold', 0), cd=me['cd'], round=t['round'],
                         n_e=len(enemies), n_a=len(s['allies']), at_home=pos in home, tiles=feats)
                y = dict(choice=cand.index(endp), hit=bool(hs), blocked='Movement blocked' in kinds,
                         first=next((k for k in kinds if k in ('Attack', 'Move', 'Cast ability')), None))
                f.write(json.dumps(dict(cohort=name, game=entry['sha256'][:16], group=entry.get('group'),
                                        round=t['round'], actor=t['id'], step=t['step'], x=x, y=y),
                                   separators=(',', ':')) + '\n')
                counts['rows'] += 1
            if (n + 1) % 20 == 0:
                print(name, n + 1, dict(counts), flush=True)
    print(name, dict(counts), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cohort', choices=[c[0] for c in COHORTS])
    p.add_argument('--out', default='replays/fish-combat')
    a = p.parse_args()
    name, manifest, cache = next(c for c in COHORTS if c[0] == a.cohort)
    main(name, manifest, cache, str(Path(a.out) / f'{name}-tiles-v1.jsonl.gz'))
