"""Compact per-turn economic rows for every Fish actor in the six decoded cohorts (ECONOMY.md).

    python3 tools/fish/econ_rows.py OUT.jsonl.gz [--jobs 6]

One JSON line per game: metadata, static map facts and, per actor, one row per recorded turn
(columns in COLS). All per-turn values come from the actor's own cached perspectives (start,
before-action and end contexts); nothing omniscient. The spawn is breadth.spawn (exclusive
cached maxima). Walking distances are king-step BFS over walls, holes, altars and the enemy
spawn (camps ignored). Shards bought are derived from the actor's own shop turns: spent gold
= 30 x shards + 10 x consumables. Refuses to overwrite OUT.
"""
import argparse, collections, gzip, json, os, sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from breadth import spawn, static_groups, xy, dist  # noqa: E402

RES = Path('research/fish-2026-11-05')
COHORTS = [('model', 'replays/fish-model', 'manifest.json'),
           ('confirm', 'replays/fish-confirm', 'confirmation-manifest.json'),
           ('third', 'replays/fish-third', 'third-manifest.json'),
           ('fourth', 'replays/fish-fourth', 'fourth-manifest.json'),
           ('fifth', 'replays/fish-fifth', 'fifth-manifest.json'),
           ('sixth', 'replays/fish-sixth', 'sixth-manifest.json'),
           ('seventh', 'replays/fish-seventh', 'seventh-manifest.json')]
# Action bits.
MOVE, ATK_CAMP, ATK_CHAMP, ATK_OTHER, CAST, RECALL, CANCEL, SUBMIT, TRIB_OK, SHOP, LOCK, TELE, WARD, BLOCKED = (1 << i for i in range(14))
COLS = ['r', 'alive', 'x', 'y', 'hp', 'maxhp', 'gems', 'gold', 'ch', 'tm', 'stun', 'flags',
        'ealive', 'ex', 'ey', 'ehp', 'egems', 'egold', 'ech', 'etm',
        'acts', 'nmove', 'shards', 'spent', 'cons',
        'ne', 'ned', 'ne_any', 'nal', 'al_gems', 'al_trib', 'al_trib_gems', 'al_recall_gems',
        'home_walk', 'home_cheb', 'alt_walk', 'alt_idx', 'alt_cheb',
        'grp', 'gstate', 'gteam', 'gtimer', 'score_own', 'score_opp',
        'camps_live_near', 'awake_near', 'sub_gems', 'trib_gems', 'fin',
        'ready', 'ready_walk', 'ready_wait', 'ready_grp', 'ready_gold', 'ready_gems', 'n_ready10', 'hit', 'own_resp', 'ready_home', 'ready_home_grp']


def bfs(m, sources, blocked):
    f = {p: 0 for p in sources}
    q = collections.deque(sources)
    while q:
        x, y = q.popleft(); d = f[x, y] + 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = (x + dx, y + dy)
                if (dx or dy) and 0 <= p[0] < m['width'] and 0 <= p[1] < m['height'] and p not in blocked and p not in f:
                    f[p] = d; q.append(p)
    return f


def contexts(t):
    return [t['start']] + [a['before'] for a in t['actions'] if 'before' in a] + ([t['end']] if 'end' in t else [])


def one(job):
    cohort, path, entry = job
    with gzip.open(path) as fh:
        g = json.load(fh)
    m, side = g['map'], g['side']
    home, away = spawn(m, side), spawn(m, 1 - side)
    altars = [tuple(a) for a in m['altars']]
    blocked = set(map(tuple, m['walls'] + m['holes'])) | set(altars) | away
    hf = bfs(m, sorted(home), blocked)
    afs = []
    for a in altars:
        adj = [(a[0] + dx, a[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
        afs.append(bfs(m, [p for p in adj if p not in blocked and 0 <= p[0] < m['width'] and 0 <= p[1] < m['height']], blocked))
    groups, at = static_groups(m)
    # Walk to any free tile beside each static group (its camp tiles count as free: they are
    # reachable once the group is dead, and a live group is approached from beside it).
    gfs = []
    for gr in groups:
        tiles = set(map(tuple, gr['tiles']))
        adj = {(x + dx, y + dy) for x, y in tiles for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        gfs.append(bfs(m, sorted(p for p in adj if p not in blocked and 0 <= p[0] < m['width'] and 0 <= p[1] < m['height']), blocked))
    # From the spawn: the recall lands on a spawn tile, a walk arrives on the nearest one.
    sw = [min((f.get(h, 999) for h in home), default=999) for f in gfs]
    live = {}
    for t in g['turns']:
        for s in contexts(t):
            for c in s['camps']:
                live[c['group']] = at[xy(c)]
    # live ids name static groups (positions only; no dynamic state copied)
    rev = {sg: l for l, sg in live.items()}
    actors = collections.defaultdict(list)
    for t in g['turns']:
        actors[t['id']].append(t)
    out = {}
    for aid, turns in actors.items():
        shards = 0
        rows = []
        memory = {}  # static group -> (round seen, state, respawn), this actor's own sightings only
        for t in turns:
            s = t['start']; me = s['me']; e = t.get('end'); em = e['me'] if e else None
            pos = xy(me) if me['alive'] else None
            for q in s['groups']:
                if q[0] in live:
                    memory[live[q[0]]] = (t['round'], q[1], q[4])
            own_g = at.get(pos) if pos else None
            best = (999, 999, 999, -1); n10 = 0; bh = (999, -1)
            if pos:
                # Via home: there by walk or the 5-turn recall, whichever is quicker, then out.
                T = min(hf.get(pos, 999), 5)
                for gr in groups:
                    k = gr['id']
                    if k == own_g: continue
                    w = gfs[k].get(pos, 999)
                    seen = memory.get(k)
                    if seen is None or seen[1] in (1, 2): wait = 0
                    elif seen[1] == 3: wait = max(0, seen[2] - (t['round'] - seen[0]))
                    else: wait = 0
                    c = max(w, wait)
                    ch_ = max(T + sw[k], wait)
                    if (ch_, k) < bh: bh = (ch_, k)
                    if c <= 10: n10 += 1
                    if (c, w, k) < (best[0], best[1], best[3]): best = (c, w, wait, k)
            own_resp = None
            if own_g is not None and own_g in memory and memory[own_g][1] == 3 and memory[own_g][0] == t['round']:
                own_resp = memory[own_g][2]
            hit = None
            for a in t['actions']:
                b = a.get('before')
                if b and a['kind'] in ('Attack', 'Cast ability'):
                    tc = next((c for c in b['camps'] if c['hp'] > 0 and list(xy(c)) == a['to']), None)
                    if tc is None and a['kind'] == 'Cast ability':
                        tc = next((c for c in b['camps'] if c['hp'] > 0 and dist(xy(c), a['to']) <= 1), None)
                    if tc is not None:
                        hit = at[xy(tc)]; break
            acts = 0; nmove = 0; sub_gems = None
            ctx = contexts(t)
            for a in t['actions']:
                k = a['kind']
                if k == 'Move': acts |= MOVE; nmove += 1
                elif k == 'Movement blocked': acts |= BLOCKED
                elif k == 'Attack':
                    b = a.get('before') or s
                    to = tuple(a['to'])
                    if any(xy(c) == to for c in b['enemies']): acts |= ATK_CHAMP
                    elif any(xy(c) == to for c in b['camps']): acts |= ATK_CAMP
                    else: acts |= ATK_OTHER
                elif k == 'Cast ability': acts |= CAST
                elif k == 'Recall': acts |= RECALL
                elif k == 'Cancel channel': acts |= CANCEL
                elif k == 'Submit gems':
                    acts |= SUBMIT
                    if sub_gems is None and 'before' in a: sub_gems = a['before']['me'].get('gems', 0)
                elif k == 'Shop': acts |= SHOP
                elif k == 'Place altar lock': acts |= LOCK
                elif k == 'Teleport channel': acts |= TELE
                elif k == 'Place ward': acts |= WARD
            if acts & SUBMIT and any(z['me'].get('channelType') == 2 for z in ctx[1:]):
                acts |= TRIB_OK
            spent = cons = 0
            if acts & SHOP and em is not None:
                spent = me['gold'] - em['gold']
                ks = [(c, (spent - 10 * c) // 30) for c in range(3) if spent >= 10 * c and (spent - 10 * c) % 30 == 0]
                if ks:
                    cons, k = ks[0]
                    shards_before = shards
                    shards += k
                else:
                    shards_before = shards
            else:
                shards_before = shards
            en = [c for c in s['enemies'] if c.get('alive')]
            al = s['allies']
            gs = {q[0]: q for q in s['groups']}
            grp = at.get(pos) if pos else None
            q = None
            if grp is not None:
                q = gs.get(rev.get(grp))
            near = [c for c in s['camps'] if c['hp'] > 0 and pos and dist(pos, xy(c)) <= 5]
            if pos:
                aw = [(f.get(pos, 999), i) for i, f in enumerate(afs)]
                awd, ai = min(aw) if aw else (999, -1)
                ac = min((dist(pos, a) for a in altars), default=999)
            else:
                awd, ai, ac = None, None, None
            trib_gems = None
            if me['alive'] and me['channelType'] == 2:
                trib_gems = me.get('gems', 0)
            rows.append([
                t['round'], int(me['alive']), me.get('x'), me.get('y'), round(me.get('hp', 0), 2), me.get('maxHp'), me.get('gems', 0), me.get('gold', 0),
                me.get('channelType', 0), me.get('channelTimer', 0), int(any(b['type'] == 1 for b in me.get('buffs', []))), me.get('roundFlags', 0),
                int(em['alive']) if em else None, em.get('x') if em else None, em.get('y') if em else None, round(em.get('hp', 0), 2) if em else None,
                em.get('gems', 0) if em else None, em.get('gold', 0) if em else None, em.get('channelType', 0) if em else None, em.get('channelTimer', 0) if em else None,
                acts, nmove, shards_before, spent, cons,
                len(en), min((dist(pos, xy(c)) for c in en), default=99) if pos else None,
                max(len([c for c in z['enemies'] if c.get('alive')]) for z in ctx),
                len(al), sum(c.get('gems', 0) for c in al), sum(1 for c in al if c.get('channelType') == 2),
                sum(c.get('gems', 0) for c in al if c.get('channelType') == 2), sum(c.get('gems', 0) for c in al if c.get('channelType') == 1),
                hf.get(pos, 999) if pos else None, min(dist(pos, h) for h in home) if pos else None, awd, ai, ac,
                grp, q[1] if q else None, q[2] if q else None, q[3] if q else None,
                s['score'][side], s['score'][1 - side],
                len(near), sum(1 for c in near if c['awake']), sub_gems, trib_gems, t.get('finish'),
                best[0] if pos else None, best[1] if pos else None, best[2] if pos else None, best[3] if pos else None,
                groups[best[3]]['gold'] if pos and best[3] >= 0 else None, groups[best[3]]['gems'] if pos and best[3] >= 0 else None,
                n10 if pos else None, hit, own_resp, bh[0] if pos else None, bh[1] if pos else None])
            for z in contexts(t)[1:]:
                for q in z['groups']:
                    if q[0] in live:
                        memory[live[q[0]]] = (t['round'], q[1], q[4])
        out[aid] = rows
    names = {c['id']: c['name'] for c in g['roster']}
    return {'cohort': cohort, 'game': entry['sha256'][:16], 'group': entry.get('group') or entry.get('match'),
            'map': entry.get('map'), 'side': side, 'n': m['champsPerTeam'], 'altars': altars,
            'W': m['width'], 'H': m['height'], 'names': {str(k): v for k, v in names.items()},
            'team': {str(c['id']): c['team'] for c in g['roster']},
            'cols': COLS, 'actors': {str(k): v for k, v in out.items()}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out'); p.add_argument('--jobs', type=int, default=6)
    a = p.parse_args()
    if os.path.exists(a.out): sys.exit(f'refusing to overwrite {a.out}')
    jobs = []
    for cohort, d, man in COHORTS:
        for e in json.load(open(RES / man)):
            f = Path(d) / f"{e['sha256'][:16]}.json.gz"
            if not f.exists(): sys.exit(f'missing cache {f}')
            jobs.append((cohort, str(f), e))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    tmp = a.out + '.part'
    with Pool(a.jobs) as pool, gzip.open(tmp, 'wt') as out:
        for i, res in enumerate(pool.imap_unordered(one, jobs)):
            out.write(json.dumps(res, separators=(',', ':')) + '\n')
            if i % 50 == 0: print(f'{i}/{len(jobs)}', file=sys.stderr, flush=True)
    os.rename(tmp, a.out)
    print(f'{len(jobs)} games -> {a.out}', file=sys.stderr)


if __name__ == '__main__':
    main()
