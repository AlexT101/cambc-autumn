"""Fish contact-turn observations: causal turn-start features x, outcome labels y.

A contact turn is an alive, completed (End turn) Fish turn whose start perspective shows at
least one living enemy champion. Not-stunned turns only (a stunned turn cannot act). Features
come from that actor's own start perspective and its earlier own perspectives (memory);
y uses the turn's actions, its end perspective and the actor's next six turns (labels only).
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

from breadth import RANGED, dist, spawn, xy
from combat_common import (COHORTS, KIT, contexts, ehp, hits, load, one_turn_damage, shield,
                           stun_timer, stunned_next)

HORIZON = 6


def enemy_row(e, me, pos):
    d = dist(pos, xy(e))
    return dict(id=e['id'], type=e['type'], d=d, hp=e['hp'], maxhp=e['maxHp'], shield=shield(e),
                str=e['strength'], focus=e['focus'], cd=e['cd'], stun=stun_timer(e), gems=e.get('gems', 0),
                channel=e.get('channelType', 0), ctimer=e.get('channelTimer', 0), x=e['x'], y=e['y'],
                threat=0.0 if stunned_next(e) else one_turn_damage(e, d),
                mine=one_turn_damage(me, d))


def features(g, t, home, memory):
    s = t['start']; m = s['me']; pos = xy(m)
    es = sorted((enemy_row(e, m, pos) for e in s['enemies']), key=lambda r: (r['d'], r['id']))
    allies = []
    for a in s['allies']:
        ad = dist(pos, xy(a))
        allies.append(dict(id=a['id'], type=a['type'], d=ad, hp=a['hp'], maxhp=a['maxHp'], shield=shield(a),
                           str=a['strength'], focus=a['focus'], cd=a['cd'], channel=a.get('channelType', 0),
                           stun=stun_timer(a)))
    # Allies' reach to each enemy, from the ally's own position (the actor sees it).
    for e in es:
        e['ally_dmg'] = sum(0 if a['stun'] > 0 else one_turn_damage(
            dict(type=a['type'], strength=a['str'], focus=a['focus'], cd=a['cd'], hp=a['hp'], maxHp=a['maxhp']),
            dist((a_['x'], a_['y']), (e['x'], e['y'])))
            for a, a_ in zip(allies, s['allies']))
        e['ehp'] = e['hp'] + e['shield']
    me_ehp = ehp(m)
    threat = sum(e['threat'] for e in es)
    x = dict(type=m['type'], ranged=m['type'] in RANGED, hp=m['hp'], maxhp=m['maxHp'], shield=shield(m),
             hpf=m['hp'] / m['maxHp'], ehp=me_ehp, gems=m.get('gems', 0), gold=m.get('gold', 0),
             str=m['strength'], focus=m['focus'], cd=m['cd'], channel=m['channelType'], ctimer=m['channelTimer'],
             attack_ready=bool(m['roundFlags'] & 2), cast_ready=bool(m['roundFlags'] & 1024),
             at_home=pos in home, home_d=min(dist(pos, p) for p in home), round=t['round'],
             score_own=s['score'][g['side']], score_opp=s['score'][1 - g['side']],
             enemies=es, allies=allies, d1=es[0]['d'], threat=threat, threat_ratio=threat / max(me_ehp, 1),
             n_e4=sum(e['d'] <= 4 for e in es), n_e8=len(es),
             n_a4=sum(a['d'] <= 4 for a in allies), n_a8=sum(a['d'] <= 8 for a in allies),
             kill_self=any(e['mine'] >= e['ehp'] for e in es),
             kill_team=any(e['mine'] + e['ally_dmg'] >= e['ehp'] for e in es),
             ally_ehp=sum(a['hp'] + a['shield'] for a in allies if a['d'] <= 8),
             enemy_ehp=sum(e['ehp'] for e in es),
             gap=t['round'] - memory['last_contact'] if memory['last_contact'] is not None else None,
             prev_d1=memory['prev_d1'], prev_hit=memory['prev_hit'],
             prev_hp=memory['prev_hp'], prev_enemy_ids=memory['prev_enemy_ids'],
             took=(memory['prev_end_hp'] - m['hp']) if memory['prev_end_hp'] is not None else None)
    return x


def labels(t, x, home, turns, index):
    s = t['start']; m = s['me']; pos = xy(m); end = t['end']['me']; epos = xy(end)
    hs = hits(t, m['type'])
    es = x['enemies']
    dd = min(dist(epos, (e['x'], e['y'])) for e in es) - x['d1']
    acts = [a for a in t['actions'] if a['kind'] != 'Set priority']
    casts = [dict(slot=a['slot'], ability=a['ability'], to=a['to']) for a in acts if a['kind'] == 'Cast ability']
    future = []
    for nt in turns[index + 1:index + 1 + HORIZON]:
        ns = nt['start']; nm = ns['me']
        ne = [e for e in ns['enemies']]
        future.append(dict(round=nt['round'], alive=nm['alive'], home=nm['alive'] and 'x' in nm and xy(nm) in home,
                           hpf=nm['hp'] / nm['maxHp'] if nm['alive'] else 0,
                           d1=min((dist(xy(nm), xy(e)) for e in ne), default=None) if nm['alive'] and 'x' in nm else None,
                           ids=[e['id'] for e in ne],
                           hit=bool(hits(nt, nm['type'])) if nm['alive'] else False,
                           act=[a['kind'] for a in nt['actions'] if a['kind'] != 'Set priority'],
                           channel=nm.get('channelType', 0) if nm['alive'] else None))
    return dict(hit=bool(hs), hits=hs, basic=any(h[0] == 'basic' for h in hs),
                cast_champ=[h[1] for h in hs if h[0] == 'cast'], casts=casts,
                moves=sum(a['kind'] == 'Move' for a in acts), dd=dd,
                end_d1=x['d1'] + dd, end_home=epos in home, home_dd=min(dist(epos, p) for p in home) - x['home_d'],
                kinds=[a['kind'] for a in acts], end_channel=t['end']['me']['channelType'],
                end_hp=end['hp'], future=future)


def main(name, manifest, cache, out):
    entries = json.loads(Path(manifest).read_text())
    counts = collections.Counter()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    if Path(out).exists():
        raise SystemExit(f'refusing to overwrite {out}')
    with gzip.open(out, 'wt') as f:
        for n, entry in enumerate(entries):
            g = load(cache, entry)
            key = entry['sha256'][:16]
            home = spawn(g['map'], g['side'])
            actors = collections.defaultdict(list)
            for t in g['turns']:
                actors[t['id']].append(t)
            for actor, turns in actors.items():
                memory = dict(last_contact=None, prev_d1=None, prev_hit=None, prev_hp=None, prev_enemy_ids=None,
                              prev_end_hp=None)
                for i, t in enumerate(turns):
                    s = t['start']; m = s['me']
                    counts['turns'] += 1
                    ok = (m['alive'] and s['enemies'] and t.get('finish') == 'End turn' and 'end' in t
                          and not any(b['type'] == 1 for b in m['buffs']) and 'x' in t['end']['me'])
                    if m['alive'] and s['enemies'] and not ok:
                        counts['contact_excluded'] += 1
                    if ok:
                        x = features(g, t, home, memory)
                        y = labels(t, x, home, turns, i)
                        f.write(json.dumps(dict(cohort=name, game=key, group=entry.get('group'), map=entry.get('map'),
                                                round=t['round'], actor=actor, step=t['step'], x=x, y=y),
                                           separators=(',', ':')) + '\n')
                        counts['rows'] += 1
                    # Memory update uses only this actor's own perspectives of this turn.
                    seen = [c for c in contexts(t) if c['me']['alive'] and c['enemies']]
                    if seen:
                        memory['last_contact'] = t['round']
                    if m['alive']:
                        memory['prev_d1'] = min((dist(xy(m), xy(e)) for e in s['enemies']), default=None)
                        memory['prev_enemy_ids'] = [e['id'] for e in s['enemies']]
                        memory['prev_hit'] = bool(hits(t, m['type']))
                        memory['prev_hp'] = m['hp']
                        memory['prev_end_hp'] = t['end']['me']['hp'] if 'end' in t and t['end']['me']['alive'] else None
                    else:
                        memory.update(prev_d1=None, prev_enemy_ids=None, prev_hit=None, prev_hp=None, prev_end_hp=None)
            if (n + 1) % 20 == 0:
                print(name, n + 1, dict(counts), flush=True)
    print(name, dict(counts), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cohort', choices=[c[0] for c in COHORTS])
    p.add_argument('--out', default='replays/fish-combat')
    a = p.parse_args()
    name, manifest, cache = next(c for c in COHORTS if c[0] == a.cohort)
    main(name, manifest, cache, str(Path(a.out) / f'{name}-combat-v2.jsonl.gz'))
