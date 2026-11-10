"""Ward coverage of our team (ocean) from extracted replays: what our wards add to what the team sees, how often
our wards duplicate each other, and where unseen enemies stand.

    python3 wardmeas.py EXTRACT_DIR [TEAMNAME]
"""
import gzip, json, os, sys, collections, glob

def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def clusters(bushes):
    S = set(map(tuple, bushes)); cid = {}; n = 0; sizes = []
    for t in S:
        if t in cid: continue
        st = [t]; cid[t] = n; k = 0
        while st:
            x, y = st.pop(); k += 1
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q in S and q not in cid: cid[q] = n; st.append(q)
        sizes.append(k); n += 1
    return cid, sizes

def los(a, b, walls, cid):
    """Rough line of sight a -> b: no wall or other-cluster bush strictly between (Bresenham), b not a bush of
    another cluster. Lower-bounds blocking (shadowcast differs at corners)."""
    ca = cid.get(a)
    if b in cid and cid[b] != ca: return False
    x0, y0 = a; x1, y1 = b; dx = abs(x1 - x0); dy = -abs(y1 - y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
    err = dx + dy; x, y = x0, y0
    while (x, y) != (x1, y1):
        e2 = 2 * err
        if e2 >= dy: err += dy; x += sx
        if e2 <= dx: err += dx; y += sy
        if (x, y) == (x1, y1): break
        if (x, y) in walls: return False
        if (x, y) in cid and cid[(x, y)] != ca: return False
    return True

def game(d, us, tot, maps):
    meta = json.load(open(os.path.join(d, 'meta.json')))
    names = {t['name']: i for i, t in enumerate(meta['teams'])}
    if us not in names: return
    T = names[us]
    m = maps.setdefault(meta['map']['hash'], None)
    if m is None:
        mm = json.load(open(os.path.join(os.path.dirname(d.rstrip('/')), 'maps', meta['map']['hash'] + '.json')))
        cid, sizes = clusters(mm['bushes'])
        m = maps[meta['map']['hash']] = (set(map(tuple, mm['walls'])), cid, sizes, mm)
    walls, cid, sizes, mm = m
    R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    ch = R['champions']; ours = [c for c in ch if c['team'] == T]; theirs = [c for c in ch if c['team'] != T]
    tot['games'] += 1
    tot['bushy'] += len(mm['bushes']) > 0
    nr = len(R['round'])
    for i in range(nr):
        pos = {c['id']: (c['x'][i], c['y'][i]) for c in ch if c['alive'][i]}
        wards = {w[0]: (w[2], w[3]) for w in R['wards'][i] if w[1] == T}
        # our wards
        wl = list(wards.values())
        tot['ward_rounds'] += len(wl)
        tot['ward_in_bush'] += sum(1 for w in wl if w in cid)
        for a in range(len(wl)):
            for b in range(a + 1, len(wl)):
                tot['ward_pairs'] += 1
                if wl[a] in cid and cid[wl[a]] == cid.get(wl[b]): tot['pair_same_cluster'] += 1
                if cheb(wl[a], wl[b]) <= 3: tot['pair_within3'] += 1
        seen = {c['id']: set(c['sees'][i] or []) for c in ours}
        union = set().union(*seen.values()) if seen else set()
        for e in theirs:
            if e['id'] not in pos: continue
            pe = pos[e['id']]
            tot['enemy_rounds'] += 1
            near = [c for c in ours if c['id'] in pos and cheb(pos[c['id']], pe) <= 8]
            tot['enemy_near8'] += bool(near)
            self_seers, ward_seers = [], []
            for c in ours:
                if e['id'] not in seen[c['id']]: continue
                pc = pos.get(c['id'])
                selfsee = pc is not None and cheb(pc, pe) <= 8 and los(pc, pe, walls, cid)
                (self_seers if selfsee else ward_seers).append(c)
            if e['id'] in union:
                tot['union_seen'] += 1
                tot['seen_by_sum'] += len(self_seers) + len(ward_seers)
                if ward_seers and not self_seers:
                    tot['ward_only_team'] += 1
                    tot['ward_only_team_near8'] += bool(near)
                if ward_seers:
                    tot['ward_seen'] += 1
                    # a teammate within 10 (8) of the enemy that does not see it: what sharing ward sightings adds
                    blind = [c for c in ours if c['id'] in pos and e['id'] not in seen[c['id']]]
                    if any(cheb(pos[c['id']], pe) <= 10 for c in blind): tot['ward_share10'] += 1
                    if any(cheb(pos[c['id']], pe) <= 8 for c in blind): tot['ward_share8'] += 1
                # any sighting a teammate within 8 lacks (sharing all sightings)
                blind = [c for c in ours if c['id'] in pos and e['id'] not in seen[c['id']]]
                if any(cheb(pos[c['id']], pe) <= 8 for c in blind): tot['any_share8'] += 1
            else:
                tot['unseen'] += 1
                inb = pe in cid
                tot['unseen_bush'] += inb
                if near:
                    tot['unseen_near8'] += 1
                    if inb:
                        tot['unseen_near8_bush'] += 1
                        if any(w in cid and cid[w] == cid[pe] for w in wl): tot['unseen_near8_bush_warded'] += 1
                        # a redundant ward of ours exists this round (same cluster or within 3 of another)
                        red = any(wl[a] in cid and cid[wl[a]] == cid.get(wl[b]) or cheb(wl[a], wl[b]) <= 3 for a in range(len(wl)) for b in range(a + 1, len(wl)))
                        tot['unseen_near8_bush_while_redundant'] += red
                        # a ward of ours placeable (within 2) by some ally right now would sit in that cluster
                        if any(cheb(pos[c['id']], q) <= 2 for c in near for q in [pe]): pass

def main():
    root = sys.argv[1]; us = sys.argv[2] if len(sys.argv) > 2 else 'oc-wdash-494'
    tot = collections.Counter(); maps = {}
    for d in sorted(glob.glob(os.path.join(root, '*/meta.json'))):
        game(os.path.dirname(d), us, tot, maps)
    t = tot
    print(json.dumps(dict(t), indent=0))
    f = lambda a, b: f'{100 * t[a] / max(1, t[b]):.1f}%'
    print(f"games {t['games']} (bushy {t['bushy']})")
    print(f"enemy-rounds seen by the team: {f('union_seen', 'enemy_rounds')}; within 8 of an ally: {f('enemy_near8', 'enemy_rounds')}")
    print(f"mean seers per seen enemy: {t['seen_by_sum'] / max(1, t['union_seen']):.2f}")
    print(f"team sees only through wards: {f('ward_only_team', 'union_seen')} of seen; near8 {t['ward_only_team_near8']}")
    print(f"ward sightings a blind ally within 10 lacks: {f('ward_share10', 'ward_seen')} of ward sightings ({t['ward_share10'] / max(1, t['games']):.0f}/game); within 8: {t['ward_share8'] / max(1, t['games']):.0f}/game")
    print(f"any sighting a blind ally within 8 lacks: {t['any_share8'] / max(1, t['games']):.0f}/game ({f('any_share8', 'union_seen')} of seen)")
    print(f"unseen enemy-rounds: {f('unseen', 'enemy_rounds')}; in bush {f('unseen_bush', 'unseen')}; near8 {f('unseen_near8', 'unseen')}; near8 in bush {f('unseen_near8_bush', 'unseen_near8')}; of those cluster warded by us {f('unseen_near8_bush_warded', 'unseen_near8_bush')}, while a redundant ward {f('unseen_near8_bush_while_redundant', 'unseen_near8_bush')}")
    print(f"our wards: {t['ward_rounds'] / max(1, t['games']):.0f} ward-rounds/game, in bush {f('ward_in_bush', 'ward_rounds')}; pairs same cluster {f('pair_same_cluster', 'ward_pairs')}, within 3 {f('pair_within3', 'ward_pairs')}")

main()
