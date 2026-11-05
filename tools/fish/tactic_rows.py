"""Tactical observations of Fish against enemy champions, from the cached actor perspectives.

One pass per cohort writes typed rows (`kind`) to replays/fish-tactics/<cohort>-tactic-v3.jsonl.gz
(v1 lacked `land` on dopp rows and `hit`/`kill` on tiles; v2 lacked side, caster stats on
target rows, enemy spawn flags and the no-enemy `spawn0` baseline rows):

- dash:  every dash cast (ability type 6) with its pre-dash perspective, the legal landing tiles
         (approximate: public terrain + units visible in that perspective) and their features,
         and what the turn did after the dash.
- dopp:  completed, unstunned turns with the dash slot ready at turn start (labels: dashed or not).
- target: every basic attack / unit spell on an enemy champion, with all legal visible targets
         from the action's own before-state (channel, gems, health, stun...).
- chan:  completed turns whose start perspective shows a channelling enemy champion.
- cap:   turns starting on (or within 3 of) an empty camp group with a visible enemy within 8.
- spawn: turns starting alive on Fish's own spawn with a visible enemy within 10.

Features use only the actor's perspectives up to the decision; labels use the turn's actions,
end perspective and the actor's next turns. Reach/danger are combat_common's Chebyshev approximations.
"""
import argparse
import collections
import gzip
import json
import multiprocessing as mp
from pathlib import Path

from breadth import RANGED, dist, spawn, static_groups, xy
from combat_common import COHORTS, KIT, ehp, hits, load, one_turn_damage, shield, stun_timer, stunned_next

DASH_SLOT = {1: 1, 2: 1, 4: 1, 9: 1, 12: 1}
NB = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def erow(e, pos, me, G=None):
    d = dist(pos, xy(e))
    extra = dict(esp=xy(e) in G.ehome, ohome_d=G.homed(xy(e))) if G else {}
    return dict(**extra, id=e['id'], type=e['type'], x=e['x'], y=e['y'], d=d, hp=e['hp'], maxhp=e['maxHp'],
                sh=shield(e), str=e['strength'], focus=e['focus'], gems=e.get('gems', 0), cd=e['cd'],
                ch=e.get('channelType', 0), ct=e.get('channelTimer', 0), stun=stun_timer(e),
                threat=0.0 if stunned_next(e) else one_turn_damage(e, d), mine=one_turn_damage(me, d))


def danger(p, enemies, my_ehp):
    return sum(0 if stunned_next(e) else one_turn_damage(e, dist(p, xy(e))) for e in enemies) / max(my_ehp, 1)


class Game:
    def __init__(self, g):
        m = g['map']
        self.g, self.m = g, m
        self.W, self.H = m['width'], m['height']
        self.walls = set(map(tuple, m['walls']))
        self.holes = set(map(tuple, m['holes']))
        self.altars = set(map(tuple, m['altars']))
        self.bush = set(map(tuple, m['bushes']))
        self.home = spawn(m, g['side'])
        self.ehome = spawn(m, 1 - g['side'])
        self.groups, self.at = static_groups(m)
        self.live = {}
        for t in g['turns']:
            for c in t['start']['camps']:
                k = self.at.get(xy(c))
                if k is not None:
                    self.live[k] = c['group']
        self.inv = {v: k for k, v in self.live.items()}

    def inb(self, p):
        return 0 <= p[0] < self.W and 0 <= p[1] < self.H

    def landings(self, s):
        """Approximate legal dash landings from perspective s (rules: dash)."""
        pos = xy(s['me'])
        vis_en = {xy(e) for e in s['enemies'] if 'x' in e}
        vis_al = {xy(a) for a in s['allies'] if 'x' in a}
        camps = {xy(c) for c in s['camps'] if c['hp'] > 0}
        path_block = self.walls | self.ehome | vis_en | camps
        land_block = path_block | self.holes | self.altars | vis_al
        one = set()
        for dx, dy in NB:
            q = (pos[0] + dx, pos[1] + dy)
            if self.inb(q) and q not in path_block:
                one.add(q)
        out = {q for q in one if q not in land_block}
        for q in one:
            for dx, dy in NB:
                r = (q[0] + dx, q[1] + dy)
                if r != pos and self.inb(r) and r not in land_block and dist(r, pos) <= 2:
                    out.add(r)
        return sorted(out)

    def homed(self, p):
        return min(dist(p, h) for h in self.home)


def tile_feats(G, p, pos, me, enemies, target):
    my = ehp(me)
    ds = [dist(p, xy(e)) for e in enemies]
    # After a dash (the cast is spent): melee may still walk then attack, ranged attacks from the tile.
    reach = 3 if me['type'] in RANGED else 2
    s = me['strength'] * (1 + 0.5 * (1 - me['hp'] / me['maxHp']) if me['type'] == 12 else 1)
    hor = 1.5 * me['focus'] * (1 + 0.5 * (1 - me['hp'] / me['maxHp'])) if me['type'] == 12 else 0
    hit = [e for e, d in zip(enemies, ds) if d <= reach or (hor and d <= 1)]
    kill = any((s if d <= reach else 0) + (hor if d <= 1 else 0) >= ehp(e) for e, d in zip(enemies, ds))
    return dict(p=list(p), step=dist(p, pos), danger=danger(p, enemies, my), dmin=min(ds, default=99),
                adj=sum(d <= 1 for d in ds), dt=dist(p, (target['x'], target['y'])) if target else None,
                home=G.homed(p), bush=int(p in G.bush), hit=len(hit), kill=int(kill))


def after_hits(t, i, mtype):
    sub = dict(actions=t['actions'][i:])
    return hits(sub, mtype)


def game_rows(args):
    name, cache, entry = args
    g = load(cache, entry)
    G = Game(g)
    key = entry['sha256'][:16]
    base = dict(cohort=name, game=key, group=entry.get('group'), map=entry.get('map'))
    rows = []
    by_actor = collections.defaultdict(list)
    for t in g['turns']:
        by_actor[t['id']].append(t)
    for actor, turns in by_actor.items():
        last_dead = None
        last_seen = {}   # enemy id -> (round, x, y) from own perspectives
        for i, t in enumerate(turns):
            s = t['start']; me = s['me']
            done = t.get('finish') == 'End turn' and 'end' in t
            if not me['alive']:
                last_dead = t['round']
                continue
            pos = xy(me)
            mtype = me['type']
            stunned = any(b['type'] == 1 for b in me['buffs'])
            enemies = [e for e in s['enemies'] if 'x' in e]
            es = sorted((erow(e, pos, me, G) for e in enemies), key=lambda r: (r['d'], r['id']))
            end = t['end']['me'] if done else None
            epos = xy(end) if end and end.get('alive') and 'x' in end else None
            hs = hits(t, mtype)
            hit_ids = sorted({i_ for h in hs for i_ in h[3]})
            kinds = [a['kind'] for a in t['actions'] if a['kind'] != 'Set priority']
            since_resp = t['round'] - last_dead if last_dead is not None else None
            common = dict(base, round=t['round'], actor=actor, step=t['step'], type=mtype, side=g['side'],
                          esp_d=min(dist(pos, h) for h in G.ehome), str=me['strength'], focus=me['focus'],
                          hpf=me['hp'] / me['maxHp'], ehp=ehp(me), maxhp=me['maxHp'], gems=me.get('gems', 0),
                          gold=me.get('gold', 0), cd=me['cd'], pos=list(pos), at_home=pos in G.home,
                          home_d=G.homed(pos), since_resp=since_resp, stunned=stunned,
                          ch=me['channelType'], ct=me['channelTimer'], done=done,
                          n_al=len(s['allies']), allies=[dict(id=a['id'], type=a['type'], x=a['x'], y=a['y'],
                                                             hp=a['hp'], maxhp=a['maxHp'], sh=shield(a))
                                                        for a in s['allies'] if 'x' in a],
                          enemies=es, hit_ids=hit_ids, kinds=kinds, end=list(epos) if epos else None,
                          end_alive=bool(end and end.get('alive')), danger0=danger(pos, enemies, ehp(me)))
            # Dash events (any context).
            for j, a in enumerate(t['actions']):
                if a['kind'] == 'Cast ability' and a.get('ability') == 6 and 'before' in a:
                    b = a['before']; bm = b['me']; bpos = xy(bm)
                    ben = [e for e in b['enemies'] if 'x' in e]
                    bes = sorted((erow(e, bpos, bm, G) for e in ben), key=lambda r: (r['d'], r['id']))
                    later = after_hits(t, j + 1, mtype) if mtype != 12 else after_hits(t, j, mtype)
                    tgt_ids = sorted({i_ for h in later for i_ in h[3]})
                    tgt = next((e for e in ben if e['id'] in tgt_ids), None)
                    cands = G.landings(b)
                    to = tuple(a['to'])
                    rows.append(dict(common, kind='dash', j=j, bpos=list(bpos), to=list(to), slot=a['slot'],
                                     bhpf=bm['hp'] / bm['maxHp'], bcd=bm['cd'], benemies=bes,
                                     before_kinds=[x['kind'] for x in t['actions'][:j] if x['kind'] != 'Set priority'],
                                     after_kinds=[x['kind'] for x in t['actions'][j + 1:] if x['kind'] != 'Set priority'],
                                     tgt_ids=tgt_ids, legal=to in cands,
                                     cands=[tile_feats(G, p, bpos, bm, ben, tgt) for p in cands],
                                     chosen=tile_feats(G, to, bpos, bm, ben, tgt)))
            if not done or stunned:
                continue
            dashed = any(a['kind'] == 'Cast ability' and a.get('ability') == 6 for a in t['actions'])
            if mtype in DASH_SLOT and me['cd'][DASH_SLOT[mtype]] == 0 and me['channelType'] in (0, 1):
                near = es[0] if es else None
                land = [tile_feats(G, p, pos, me, enemies, near) for p in G.landings(s)] if near and near['d'] <= 6 else []
                rows.append(dict(common, kind='dopp', dashed=dashed, land=land,
                                 next_dash=[any(a['kind'] == 'Cast ability' and a.get('ability') == 6
                                                for a in nt['actions']) for nt in turns[i + 1:i + 4]]))
            # Attack / unit-spell target choices from each action's own before-state.
            for j, a in enumerate(t['actions']):
                if a['kind'] not in ('Attack', 'Cast ability') or 'before' not in a:
                    continue
                ab = a.get('ability')
                if a['kind'] == 'Cast ability' and ab not in (2, 4):
                    continue
                b = a['before']; bm = b['me']; bpos = xy(bm)
                ben = [e for e in b['enemies'] if 'x' in e]
                hit = [e for e in ben if [e['x'], e['y']] == a['to']]
                if not hit:
                    continue
                rng = 4 if a['kind'] == 'Cast ability' else (3 if mtype in RANGED else 1)
                cands = [erow(e, bpos, bm, G) for e in ben if dist(bpos, xy(e)) <= rng]
                rows.append(dict(base, kind='target', round=t['round'], actor=actor, step=a['step'], type=mtype,
                                 act='basic' if a['kind'] == 'Attack' else f"cast{a['slot']}", ability=ab,
                                 chosen=hit[0]['id'], cands=cands, hpf=bm['hp'] / bm['maxHp'],
                                 gems=bm.get('gems', 0), str=bm['strength'], focus=bm['focus'], cd=bm['cd'],
                                 hp=bm['hp'], maxhp=bm['maxHp'], side=g['side'], pos=list(bpos)))
            if any(e['ch'] for e in es):
                rows.append(dict(common, kind='chan'))
            # Capture contests: on, or within 3 of, an empty group.
            if es and es[0]['d'] <= 8:
                gs = {q[0]: q for q in s['groups']}
                mine = G.at.get(pos)
                near = []
                for gr in G.groups:
                    lid = G.live.get(gr['id'])
                    if lid is None or lid not in gs or gs[lid][1] != 2:
                        continue
                    dg = min(dist(pos, p) for p in gr['tiles'])
                    if dg <= 3:
                        tiles = set(map(tuple, gr['tiles']))
                        near.append(dict(gid=gr['id'], d=dg, state=gs[lid], gold=gr['gold'], gems=gr['gems'],
                                         size=len(tiles), on=gr['id'] == mine,
                                         en_on=[e['id'] for e in es if (e['x'], e['y']) in tiles],
                                         al_on=[a['id'] for a in s['allies'] if xy(a) in tiles],
                                         end_on=bool(epos and epos in tiles),
                                         free=[list(p) for p in tiles if p not in {xy(c) for c in enemies + s['allies']}]))
                if near:
                    rows.append(dict(common, kind='cap', near=near,
                                     future_on=[[bool(nt['start']['me']['alive'] and 'x' in nt['start']['me'] and
                                                      xy(nt['start']['me']) in set(map(tuple, G.groups[n['gid']]['tiles'])))
                                                 for n in near] for nt in turns[i + 1:i + 6]]))
            if pos in G.home and not (es and es[0]['d'] <= 10) and me['channelType'] == 0:
                # Baseline: on spawn with no enemy within 10 (not channelling).
                rows.append(dict(base, kind='spawn0', round=t['round'], actor=actor, type=mtype, hpf=me['hp'] / me['maxHp'],
                                 since_resp=since_resp, n_seen=len(es), end=list(epos) if epos else None,
                                 left=bool(epos and epos not in G.home), kinds=kinds))
            if pos in G.home and es and es[0]['d'] <= 10:
                exits = []
                for dx, dy in NB:
                    q = (pos[0] + dx, pos[1] + dy)
                    if G.inb(q) and q not in G.walls | G.holes | G.altars and q not in {xy(c) for c in enemies + s['allies']}:
                        exits.append(dict(p=list(q), home=q in G.home, danger=danger(q, enemies, ehp(me)),
                                          dmin=min(dist(q, xy(e)) for e in enemies)))
                fut = []
                for nt in turns[i + 1:i + 6]:
                    nm = nt['start']['me']
                    fut.append(dict(alive=nm['alive'], home=bool(nm['alive'] and 'x' in nm and xy(nm) in G.home),
                                    hpf=nm['hp'] / nm['maxHp'] if nm['alive'] else 0))
                rows.append(dict(common, kind='spawn', exits=exits, future=fut,
                                 en_home_d=[min(dist(xy(e), h) for h in G.home) for e in enemies]))
            for e in enemies:
                last_seen[e['id']] = (t['round'], e['x'], e['y'])
    return rows


def main(name, manifest, cache, out, jobs):
    if Path(out).exists():
        raise SystemExit(f'refusing to overwrite {out}')
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    entries = json.loads(Path(manifest).read_text())
    counts = collections.Counter()
    tmp = out + '.part'
    with gzip.open(tmp, 'wt') as f, mp.Pool(jobs) as pool:
        for rows in pool.imap_unordered(game_rows, [(name, cache, e) for e in entries]):
            for r in rows:
                counts[r['kind']] += 1
                f.write(json.dumps(r, separators=(',', ':')) + '\n')
            counts['games'] += 1
    Path(tmp).rename(out)
    print(name, dict(counts), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cohort', choices=[c[0] for c in COHORTS])
    p.add_argument('--out', default='replays/fish-tactics')
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--limit', type=int, default=0)
    a = p.parse_args()
    name, manifest, cache = next(c for c in COHORTS if c[0] == a.cohort)
    out = str(Path(a.out) / f'{name}-tactic-v3.jsonl.gz')
    if a.limit:
        entries = json.loads(Path(manifest).read_text())[:a.limit]
        rows = [r for e in entries for r in game_rows((name, cache, e))]
        print(collections.Counter(r['kind'] for r in rows))
        print(sum(r['legal'] for r in rows if r['kind'] == 'dash'), sum(r['kind'] == 'dash' for r in rows))
    else:
        main(name, manifest, cache, out, a.jobs)
