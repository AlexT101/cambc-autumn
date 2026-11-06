"""Per-turn rows for the strategic engage/avoid/retreat/pursuit study (ENGAGE.md).

One JSON line per game, actors' turns in sequence, from the cached actor perspectives
(replays/fish-<cohort>/<SHA16>.json.gz). Every field under 'x' is causal: the actor's own start
perspective, its earlier own perspectives (memory), public map data, and enemy liveness (which
Fish can read for unseen champions). Fields under 'y' describe this turn's own actions and end
state (labels). Later turns of the same actor (labels) are read by the analysis scripts.

  python3 tools/fish/engage_rows.py COHORT [--jobs 6]   ->  replays/fish-engage/<cohort>-rows-v1.jsonl.gz
"""
import argparse
import collections
import gzip
import json
import multiprocessing as mp
from pathlib import Path

from breadth import RANGED, dist, spawn, static_groups, xy
from combat_common import COHORTS, ehp, hits, one_turn_damage, shield, stunned_next

OUT = Path('replays/fish-engage')
MEM = 40          # rounds an unseen enemy's last sighting is kept
RADIUS = 24       # BFS depth limit for walk distances from an enemy tile
NB = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def contexts(t):
    return [t['start']] + [a['before'] for a in t['actions'] if 'before' in a] + ([t['end']] if 'end' in t else [])


class Terrain:
    def __init__(self, m, side):
        self.m = m
        self.W, self.H = m['width'], m['height']
        self.block = set(map(tuple, m['walls'] + m['holes'] + m['altars']))
        self.home = spawn(m, side)
        self.ehome = spawn(m, 1 - side)
        self.bush = set(map(tuple, m['bushes']))
        self.altars = [tuple(a) for a in m['altars']]
        self.hf = self.bfs(sorted(self.home), self.block | self.ehome, 10 ** 9)
        self.ehf = self.bfs(sorted(self.ehome), self.block | self.home, 10 ** 9)
        self.cache = collections.OrderedDict()

    def bfs(self, sources, blocked, limit):
        f = {p: 0 for p in sources}
        q = collections.deque(sources)
        while q:
            x, y = q.popleft(); d = f[x, y] + 1
            if d > limit:
                continue
            for dx, dy in NB:
                p = (x + dx, y + dy)
                if 0 <= p[0] < self.W and 0 <= p[1] < self.H and p not in blocked and p not in f:
                    f[p] = d; q.append(p)
        return f

    def field(self, p):
        p = tuple(p)
        if p in self.cache:
            self.cache.move_to_end(p)
            return self.cache[p]
        f = self.bfs([p], self.block, RADIUS)
        self.cache[p] = f
        if len(self.cache) > 4000:
            self.cache.popitem(last=False)
        return f

    def walk(self, a, b):
        return self.field(a).get(tuple(b), 99)


def L_of(value, n):
    r = (-value) % (n + 1)
    rank = r if r else n + 1
    return (-value - rank) // (n + 1)


def erow(e, pos, me, T):
    d = dist(pos, xy(e))
    return dict(id=e['id'], type=e['type'], x=e['x'], y=e['y'], d=d, hp=round(e['hp'], 1), mhp=e['maxHp'],
                sh=round(shield(e), 1), gems=e.get('gems', 0), ch=e.get('channelType', 0), ct=e.get('channelTimer', 0),
                stn=stunned_next(e), str=e['strength'], foc=e['focus'], cd=e['cd'],
                thr=0.0 if stunned_next(e) else round(one_turn_damage(e, d), 1), mine=round(one_turn_damage(me, d), 1),
                esp=xy(e) in T.ehome, bush=xy(e) in T.bush)


def arow(a, pos, enemies):
    return dict(id=a['id'], type=a['type'], x=a['x'], y=a['y'], d=dist(pos, xy(a)), hp=round(a['hp'], 1),
                mhp=a['maxHp'], sh=round(shield(a), 1), gems=a.get('gems', 0), ch=a.get('channelType', 0),
                ct=a.get('channelTimer', 0), str=a['strength'], foc=a['focus'], cd=a['cd'], stn=stunned_next(a),
                ed=min((dist(xy(a), xy(e)) for e in enemies), default=99))


def camp_hits(t, at):
    out = []
    for a in t['actions']:
        b = a.get('before')
        if not b or a['kind'] not in ('Attack', 'Cast ability'):
            continue
        tc = next((c for c in b['camps'] if c['hp'] > 0 and list(xy(c)) == a['to']), None)
        if tc is None and a['kind'] == 'Cast ability':
            tc = next((c for c in b['camps'] if c['hp'] > 0 and dist(xy(c), a['to']) <= 1), None)
        if tc is not None and xy(tc) in at:
            out.append(at[xy(tc)])
    return out


def one(job):
    cohort, cache, entry, team_cache = job
    key = entry['sha256'][:16]
    with gzip.open(Path(cache) / f'{key}.json.gz') as f:
        g = json.load(f)
    m, side = g['map'], g['side']
    T = Terrain(m, side)
    groups, at = static_groups(m)
    n = sum(1 for c in g['roster'] if c['team'] == side)
    live = {}
    for t in g['turns']:
        for s in contexts(t):
            for c in s['camps']:
                if xy(c) in at:
                    live[c['group']] = at[xy(c)]
    rev = {v: k for k, v in live.items()}
    # Enemy liveness by round: readable by Fish for unseen champions (rules: vision.unseen_units).
    alive = {}
    tp = Path(team_cache) / f'{key}.json.gz'
    if tp.exists():
        with gzip.open(tp) as f:
            obs = json.load(f)
        for R in obs['rounds']:
            if R['cp']:
                alive[R['r']] = {c[0]: c[1] for c in R['cp']['ch']}
    enemy_ids = [c['id'] for c in g['roster'] if c['team'] != side]
    actors = collections.defaultdict(list)
    for t in g['turns']:
        actors[t['id']].append(t)
    out = {}
    for aid, turns in actors.items():
        mem = {}            # enemy id -> last sighting dict (own perspectives only)
        last_contact = None  # last round an enemy was visible in any own context
        last_camp = None     # (round, static group) of the last own camp hit
        last_champ_hit = None  # (round, enemy id)
        rows = []
        for t in turns:
            s = t['start']; me = s['me']; e = t.get('end')
            r = t['round']
            row = dict(r=r, alive=int(me['alive']))
            if me['alive'] and 'x' in me:
                pos = xy(me)
                es = sorted((erow(c, pos, me, T) for c in s['enemies'] if c.get('alive')), key=lambda q: (q['d'], q['id']))
                al = [arow(c, pos, s['enemies']) for c in s['allies'] if c.get('alive') and 'x' in c]
                vis = {q['id'] for q in es}
                later = {}
                for z in contexts(t)[1:]:
                    zm = z['me']
                    if not zm.get('alive') or 'x' not in zm:
                        continue
                    for c in z['enemies']:
                        if c.get('alive') and c['id'] not in vis and c['id'] not in later:
                            later[c['id']] = dict(id=c['id'], type=c['type'], x=c['x'], y=c['y'], d=dist(xy(zm), xy(c)))
                lv = alive.get(r, {})
                M = []
                for i, q in mem.items():
                    if i in vis or r - q['r'] > MEM:
                        continue
                    M.append(dict(q, d=dist(pos, (q['x'], q['y'])), alive=lv.get(i)))
                gs = {q[0]: q for q in s['groups']}
                og = at.get(pos)
                q = gs.get(rev.get(og)) if og is not None else None
                aggro = [c for c in s['camps'] if c['hp'] > 0 and c['awake']
                         and dist(pos, xy(c)) <= {0: 3, 1: 4, 4: 5, 5: 4}.get(c['type'], 0)]
                d1 = es[0]['d'] if es else None
                wd0 = T.walk(xy(es[0]), pos) if es and es[0]['d'] <= RADIUS else None
                x = dict(type=me['type'], ranged=me['type'] in RANGED, x=pos[0], y=pos[1], hp=round(me['hp'], 1),
                         mhp=me['maxHp'], sh=round(shield(me), 1), gems=me.get('gems', 0), gold=me.get('gold', 0),
                         str=me['strength'], foc=me['focus'], cd=me['cd'], ch=me.get('channelType', 0),
                         ct=me.get('channelTimer', 0), stn=any(b['type'] == 1 for b in me.get('buffs', [])),
                         prio=me.get('priority', 0), Lstart=L_of(me.get('priority', 0), n) if me.get('priority', 0) else None,
                         home=pos in T.home, hw=T.hf.get(pos, 999), ehw=T.ehf.get(pos, 999), bush=pos in T.bush,
                         so=s['score'][side], sx=s['score'][1 - side], E=es, A=al, M=M, later=list(later.values()),
                         d1=d1, wd0=wd0, grp=og, gst=q[1] if q else None, gteam=q[2] if q else None,
                         gtm=q[3] if q else None, aggro=len(aggro), aggro_str=sum({0: 20, 1: 60, 4: 200, 5: 120}.get(c['type'], 0) for c in aggro),
                         camps_near=sum(1 for c in s['camps'] if c['hp'] > 0 and dist(pos, xy(c)) <= 5),
                         lc=r - last_contact if last_contact is not None else None,
                         lcamp=(r - last_camp[0], last_camp[1]) if last_camp else None,
                         lhit=(r - last_champ_hit[0], last_champ_hit[1]) if last_champ_hit else None,
                         ealive=sum(1 for i in enemy_ids if lv.get(i)), n=n)
                row['x'] = x
                if e is not None and e['me'].get('alive') and 'x' in e['me']:
                    em = e['me']; ep = xy(em)
                    acts = [a['kind'] for a in t['actions']]
                    pw = [a['value'] for a in t['actions'] if a['kind'] == 'Set priority']
                    hs = hits(t, me['type'])
                    y = dict(ex=ep[0], ey=ep[1], ehp=round(em['hp'], 1), egems=em.get('gems', 0), ech=em.get('channelType', 0),
                             ect=em.get('channelTimer', 0), moves=acts.count('Move'),
                             dash=any(a['kind'] == 'Cast ability' and a.get('ability') == 6 for a in t['actions']),
                             hitc=sorted({i for h in hs for i in h[3]}), camp=sorted(set(camp_hits(t, at))),
                             recall='Recall' in acts, cancel='Cancel channel' in acts, submit='Submit gems' in acts,
                             tele='Teleport channel' in acts, shop='Shop' in acts, ward='Place ward' in acts,
                             blocked='Movement blocked' in acts,
                             pw=pw[-1] if pw else None, L=L_of(pw[-1], n) if pw else None,
                             ed={q['id']: dist(ep, (q['x'], q['y'])) for q in es},
                             md={q['id']: dist(ep, (q['x'], q['y'])) for q in M},
                             ehw=T.hf.get(ep, 999), eehw=T.ehf.get(ep, 999), ebush=ep in T.bush,
                             wd1=T.walk(xy(es[0]), ep) if es and es[0]['d'] <= RADIUS else None,
                             finish=t.get('finish'))
                    row['y'] = y
            rows.append(row)
            # Memory updates: own perspectives of this turn only.
            for z in contexts(t):
                zm = z['me']
                if not zm.get('alive') or 'x' not in zm:
                    continue
                for c in z['enemies']:
                    if c.get('alive'):
                        mem[c['id']] = dict(id=c['id'], type=c['type'], r=r, x=c['x'], y=c['y'], hp=round(c['hp'], 1),
                                            mhp=c['maxHp'], gems=c.get('gems', 0), ch=c.get('channelType', 0))
                        last_contact = r
            if me['alive']:
                ch_ = camp_hits(t, at)
                if ch_:
                    last_camp = (r, ch_[-1])
                hs = hits(t, me['type'])
                if hs:
                    last_champ_hit = (r, hs[-1][3][0])
        out[aid] = rows
    return dict(cohort=cohort, game=key, group=entry.get('group') or entry.get('match'), map=entry.get('map'),
                side=side, W=m['width'], H=m['height'], n=n,
                roster=g['roster'], actors={str(k): v for k, v in out.items()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cohort', choices=[c[0] for c in COHORTS])
    p.add_argument('--jobs', type=int, default=6)
    p.add_argument('--team-cache', default='replays/fish-team')
    p.add_argument('--limit', type=int, default=None)
    a = p.parse_args()
    name, manifest, cache = next(c for c in COHORTS if c[0] == a.cohort)
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f'{name}-rows-v1.jsonl.gz' if a.limit is None else OUT / f'{name}-rows-v1-limit{a.limit}.jsonl.gz'
    if dest.exists():
        raise SystemExit(f'refusing to overwrite {dest}')
    entries = json.loads(Path(manifest).read_text())[:a.limit]
    jobs = [(name, cache, e, a.team_cache) for e in entries]
    tmp = dest.with_suffix('.tmp')
    with gzip.open(tmp, 'wt') as f, mp.Pool(a.jobs) as pool:
        for k, res in enumerate(pool.imap(one, jobs)):
            f.write(json.dumps(res, separators=(',', ':')) + '\n')
            if (k + 1) % 10 == 0:
                print(name, k + 1, len(jobs), flush=True)
    tmp.rename(dest)
    print('wrote', dest)


if __name__ == '__main__':
    main()
