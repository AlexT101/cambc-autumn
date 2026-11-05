"""TEAM.md section 2: who camps hit, and what Fish's turn order does to it (observer labels).

For every camp-phase attack: candidates = living champions within the monster's range at the
camp-phase snapshot; the rule says nearest, ties to the earlier actor in that round's order.
Fish ties: attacks whose nearest set holds two or more Fish champions and the target is Fish.
Counterfactual orders among the tied Fish: id order (all priorities 0) and the reverse of Fish's.

    python3 tools/fish/team_aggro.py research/fish-2026-11-05/team-aggro.json
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from team_common import (ALIVE, CAMP_NAMES, CAMP_RANGE, CAMP_STR, GEMS, HELD_OUT, HP, ID, MAXHP, NAMES, PRIO, SHIELD, X, Y,  # noqa: E402
                         cheb, decode_level, entries, load_team, mode_of, starts, write_json)


def ehp(c):
    return c[HP] + c[SHIELD]


def frac(c):
    return min(1.0, ehp(c) / c[MAXHP])


def main(out):
    C = collections.defaultdict(collections.Counter)
    ex = collections.defaultdict(list)
    for cohort, _, e in entries():
        s = 'held_out' if cohort in HELD_OUT else 'discovery'
        g = load_team(e['sha256'][:16])
        side = g['side']
        team = {r['id']: r['team'] for r in g['roster']}
        typ = {r['id']: r['type'] for r in g['roster']}
        n = sum(1 for r in g['roster'] if r['team'] == side)
        camps = g['camps']
        for R in g['rounds']:
            if not R['cp'] or not R['order']:
                continue
            ch = {c[ID]: c for c in R['cp']['ch']}
            pos = {cid: i for i, cid in enumerate(R['order'])}
            for cid, tid, hb, ha in R['attacks']:
                cp = camps[cid]
                rng, dmg = CAMP_RANGE[cp['type']], CAMP_STR[cp['type']]
                d = {c[ID]: cheb((c[X], c[Y]), (cp['x'], cp['y'])) for c in ch.values() if c[ALIVE] and c[X] >= 0}
                cand = [i for i, v in d.items() if v <= rng]
                if tid < 0:
                    C[s]['unresolved target'] += 1
                    continue
                if not cand:
                    C[s]['no candidate'] += 1
                    continue
                dm = min(d[i] for i in cand)
                tied = [i for i in cand if d[i] == dm]
                pred = min(tied, key=lambda i: pos.get(i, 99))
                C[s]['attacks'] += 1
                C[s]['rule correct'] += pred == tid
                if len(tied) > 1:
                    C[s]['tied'] += 1
                    C[s]['tied correct'] += pred == tid
                if pred != tid and len(ex[s + ' rule']) < 10:
                    ex[s + ' rule'].append([g['game'], R['r'], cid, tid, tied])
                if team[tid] == side:
                    C[s]['fish hits'] += 1
                    C[s + ' fish hit by'][CAMP_NAMES[cp['type']]] += 1
                    if ha is not None and ha <= 0:
                        C[s]['fish killed by camp'] += 1
                        C[s]['fish gems lost to camps'] += ch[tid][GEMS]
                elif ha is not None and ha <= 0:
                    C[s]['enemy killed by camp'] += 1
                    C[s]['enemy gems lost to camps'] += ch[tid][GEMS]
                # Fish-internal ties.
                ftied = [ch[i] for i in tied if team[i] == side]
                if len(ftied) >= 2 and team[tid] == side and all(team[i] == side for i in tied):
                    T = C[s + ' fish ties']
                    T['n'] += 1
                    order = sorted(ftied, key=lambda c: pos.get(c[ID], 99))
                    picks = {'fish': ch[tid], 'id_order': min(ftied, key=lambda c: c[ID]), 'reverse': order[-1]}
                    mixed_gems = any(c[GEMS] == 0 for c in ftied) and any(c[GEMS] > 0 for c in ftied)
                    mixed_life = any(ehp(c) > dmg for c in ftied) and any(ehp(c) <= dmg for c in ftied)
                    T['mixed carriers'] += mixed_gems
                    T['mixed lethal'] += mixed_life
                    hih = lambda c: ehp(c) / max(dmg, 1)
                    for k, c in picks.items():
                        T[f'{k}: max health fraction'] += frac(c) == max(frac(x) for x in ftied)
                        T[f'{k}: max hits in hand'] += hih(c) == max(hih(x) for x in ftied)
                        if mixed_gems:
                            T[f'{k}: gemless takes it'] += c[GEMS] == 0
                        if mixed_life:
                            T[f'{k}: survivor takes it'] += ehp(c) > dmg
                    if mixed_gems and ch[tid][GEMS] > 0 and len(ex[s + ' carrier tanks']) < 10:
                        ex[s + ' carrier tanks'].append([g['game'], R['r'], cid, tid, [c[ID] for c in ftied]])
                # Cross-team ties: a Fish champion and an enemy both nearest.
                if any(team[i] == side for i in tied) and any(team[i] != side for i in tied):
                    first_fish = min((i for i in tied if team[i] == side), key=lambda i: pos.get(i, 99))
                    md = mode_of(decode_level(ch[first_fish][PRIO], n)[1])
                    md = 'contact' if md.startswith('contact') else md
                    key = f"fish {'starts' if starts(side, R['r']) else 'second'}, {md}"
                    C[s + ' cross ties: fish hit'][key + ' | fish hit'] += team[tid] == side
                    C[s + ' cross ties: fish hit'][key + ' | n'] += 1
                # Positioning: two or more Fish in range of the hitting monster.
                frange = [ch[i] for i in cand if team[i] == side]
                if team[tid] == side and len(frange) >= 2:
                    P = C[s + ' fish in range']
                    P['n'] += 1
                    P['victim has max ehp'] += ehp(ch[tid]) == max(ehp(c) for c in frange)
                    P['uniform expectation x n'] += sum(1 for c in frange if ehp(c) == max(ehp(x) for x in frange)) / len(frange)
                    P['victim nearer than all other fish'] += sum(1 for c in frange if d[c[ID]] == dm) == 1
                    C[s + ' victim type'][NAMES[typ[tid]]] += 1
                    for c in frange:
                        C[s + ' in-range type'][NAMES[typ[c[ID]]]] += 1
    res = {'definitions': __doc__, **{k: dict(v) for k, v in C.items()}, 'examples': ex}
    write_json(out, res)
    for k, v in C.items():
        print(k, dict(v))


if __name__ == '__main__':
    main(sys.argv[1])
