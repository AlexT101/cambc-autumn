"""TEAM.md section 3: Fish's micro at camps (observer labels; Willow features from her own view).

stepout  A Fish champion hit by a camp in round r's camp phase, alive at r+1, its group still
         awake at r+1: does it stand within range of an awake member at r+1's camp phase?
         hits in hand = (hp + shield at its turn start) / camp damage it took in phase r.
wake     The first damage by a Fish champion to a group none of whose members was awake at
         the camp phase and none woken earlier that round: Fish champions within 4 of a member.
willow   Fish Willow's moving turns with two or more visible allies off spawn: the ally she
         ends nearest (strict) against the ally she started nearest, and other candidates.

    python3 tools/fish/team_campfight.py research/fish-2026-11-05/team-campfight.json
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from team_common import (ALIVE, CAMP_RANGE, CAMP_STR, GEMS, HELD_OUT, ID, NAMES, X, Y, cheb, entries,  # noqa: E402
                         load_actor, load_team, spawn_tiles, write_json)


def group_kind(members):
    ts = {m['type'] for m in members}
    for t, name in ((4, 'monolith'), (5, 'golem'), (1, 'elk'), (0, 'wolf')):
        if t in ts:
            return name
    return 'cluster'


def campfight(g, s, C, ex):
    side = g['side']
    team = {r['id']: r['team'] for r in g['roster']}
    typ = {r['id']: r['type'] for r in g['roster']}
    camps = g['camps']
    members = collections.defaultdict(list)
    for c in camps:
        members[c['group']].append(c)
    rs = {R['r']: R for R in g['rounds'] if R['cp']}
    pos = {}
    for r in sorted(rs):
        R = rs[r]
        # --- wake
        for c in R['cp']['ch']:
            pos[c[ID]] = (c[X], c[Y], c[ALIVE])
        awake_g = {camps[a]['group'] for a, _ in R['cp']['awake']}
        woken = set()
        for t in R['turns']:
            for x in t['acts']:
                if x[0] in ('Attack', 'Cast ability') and len(x) > 6 and x[6] == 2:
                    gid = camps[x[7]]['group']
                    if gid in awake_g or gid in woken:
                        continue
                    woken.add(gid)
                    if team[t['id']] != side:
                        continue
                    gm = members[gid]
                    kind = group_kind(gm)
                    near = [i for i, p in pos.items() if team[i] == side and p[2] and min(cheb(p[:2], (m['x'], m['y'])) for m in gm) <= 4]
                    W = C[f'{s} wake {kind}']
                    W['n'] += 1
                    W['alone (no other Fish within 4)'] += len([i for i in near if i != t['id']]) == 0
                    C[f'{s} waker type'][NAMES[typ[t['id']]]] += 1
                    if kind in ('golem', 'monolith') and len(near) <= 1 and len(ex[f'{s} solo big wake']) < 10:
                        ex[f'{s} solo big wake'].append([g['game'], r, t['id'], kind])
            if t.get('end'):
                pos[t['id']] = (t['end'][X], t['end'][Y], t['end'][ALIVE])
        # --- stepout
        R1 = rs.get(r + 1)
        if not R1:
            continue
        dmg, grp = collections.Counter(), collections.defaultdict(set)
        for cid, tid, hb, ha in R['attacks']:
            if tid >= 0 and team[tid] == side and hb is not None and hb > ha:
                dmg[tid] += hb - ha
                grp[tid].add(camps[cid]['group'])
        aw1 = collections.defaultdict(list)
        for cid, _ in R1['cp']['awake']:
            aw1[camps[cid]['group']].append(camps[cid])
        hit1 = {tid for _, tid, _, _ in R1['attacks']}
        ch1 = {c[ID]: c for c in R1['cp']['ch']}
        turns = {t['id']: t for t in R['turns']}
        for tid, d in dmg.items():
            t = turns.get(tid)
            if not t or not t['start'] or not t['start'][4]:
                continue
            gs = [x for x in grp[tid] if aw1.get(x)]
            if not gs or not ch1[tid][ALIVE]:
                C[f'{s} stepout excluded']['group cleared' if not gs else 'died'] += 1
                continue
            c1 = ch1[tid]
            stay = any(cheb((c1[X], c1[Y]), (m['x'], m['y'])) <= CAMP_RANGE[m['type']] for x in gs for m in aw1[x])
            hih = (t['start'][2] + t['start'][3]) / d
            b = '<1' if hih < 1 else '1-2' if hih < 2 else '2-4' if hih < 4 else '4-8' if hih < 8 else '>=8'
            carry = 'carrier' if (t['end'][GEMS] if t.get('end') else 0) else 'gemless'
            C[f'{s} stepout'][f'{b} {carry} n'] += 1
            C[f'{s} stepout'][f'{b} {carry} stay'] += stay
            C[f'{s} stepout']['n'] += 1
            C[f'{s} stepout']['stay'] += stay
            if stay and hih < 2:
                C[f'{s} stepout low hih stays'][('hit again' if tid in hit1 else 'not hit')] += 1
            if not stay and hih >= 8 and len(ex[f'{s} healthy leaves']) < 10:
                ex[f'{s} healthy leaves'].append([g['game'], r, tid, round(hih, 1)])


def willow(a, s, C):
    side = a['side']
    sp = spawn_tiles(a['map'], side)
    names = {r['id']: r['name'] for r in a['roster']}
    for t in a['turns']:
        m0 = t['start']['me']
        if m0['type'] != 8 or not m0['alive'] or not t.get('end') or not any(x['kind'] == 'Move' for x in t['actions']):
            continue
        m1 = t['end']['me']
        endpos = {q['id']: (q['x'], q['y']) for q in t['end']['allies'] if 'x' in q}
        al = [q for q in t['start']['allies'] if 'x' in q and (q['x'], q['y']) not in sp and q['id'] in endpos]
        if len(al) < 2:
            continue
        de = {q['id']: cheb(endpos[q['id']], (m1['x'], m1['y'])) for q in al}
        best = min(de.values())
        lab = [i for i, v in de.items() if v == best]
        W = C[f'{s} willow']
        if len(lab) > 1:
            W['tie excluded'] += 1
            continue
        lab = lab[0]
        ds = {q['id']: cheb((q['x'], q['y']), (m0['x'], m0['y'])) for q in al}
        W['n'] += 1
        W['nearest at start'] += min(al, key=lambda q: (ds[q['id']], q['id']))['id'] == lab
        W['most missing health'] += max(al, key=lambda q: (q['maxHp'] - q['hp'], -q['id']))['id'] == lab
        W['lowest health fraction'] += min(al, key=lambda q: (q['hp'] / q['maxHp'], q['id']))['id'] == lab
        W['lowest id'] += min(al, key=lambda q: q['id'])['id'] == lab
        C[f'{s} willow ends nearest'][names[lab]] += 1


def main(out):
    C = collections.defaultdict(collections.Counter)
    ex = collections.defaultdict(list)
    for cohort, cache, e in entries():
        s = 'held_out' if cohort in HELD_OUT else 'discovery'
        key = e['sha256'][:16]
        campfight(load_team(key), s, C, ex)
        a = load_actor(cache, key)
        if any(r['type'] == 8 and r['team'] == a['side'] for r in a['roster']):
            willow(a, s, C)
    res = {'definitions': __doc__, **{k: dict(v) for k, v in C.items()}, 'examples': ex}
    write_json(out, res)
    for k, v in sorted(C.items()):
        print(k, dict(v))


if __name__ == '__main__':
    main(sys.argv[1])
