"""Descriptive farming statistics for Fish (FARM3.md section 1), from observer data.

Per Fish champion turn (round snapshot at the camp phase = the state at its turn start, plus its
actions from replays/fish-team): one activity, the first that applies of
  dead, home (starts on own spawn), tribute (tribute channel or attempt), fight (an action on an
  enemy champion), clear (an action hitting a camp), capture (starts on an empty group's tile),
  recall (starts in a recall channel and keeps it), wait (a respawning group's tile within 2),
  approach (walks or teleports with a living camp within 3), travel (other walks or teleports),
  idle (anything else).
Also capture payouts and group sequences, group clears with who took part (solo Elk/Golem/Monolith),
enemy-side captures and steals, team spread, and the activity mix by round, score lead and gold.
  python3 tools/fish/farm3_describe.py OUT.json [--cohorts a,b] [--jobs 6]
"""
import argparse
import collections
import multiprocessing as mp
import statistics

from farm3_common import (ALIVE, CAMP_NAMES, CT, EMPTY, GEMSC, GOLDC, HP, ID, NAMES, OBS, RESPAWNING, X, Y,
                          Game, cheb, entries, load, payouts, team_rounds, write_json)

ACTS = ['dead', 'home', 'tribute', 'fight', 'clear', 'capture', 'recall', 'wait', 'approach', 'travel', 'idle']
BIG = {1: 'Elk', 5: 'Golem', 4: 'Monolith'}


def rbucket(r):
    return '1-100' if r <= 100 else '101-300' if r <= 300 else '301-600' if r <= 600 else '601-1000' if r <= 1000 else '1001+'


def lbucket(d):
    return 'behind>100' if d < -100 else 'behind' if d < -20 else 'level' if d <= 20 else 'ahead' if d <= 100 else 'ahead>100'


def gbucket(g):
    return '<30' if g < 30 else '30-89' if g < 90 else '90-199' if g < 200 else '200+'


def game_stats(args):
    cohort, e = args
    key = e['sha256'][:16]
    obs = load(OBS / f'{key}.json.gz')
    G = Game(obs)
    T = team_rounds(key)
    if T is None:
        return None
    rounds = obs['rounds']
    fish = set(G.fish)
    act = collections.Counter()          # (champ type, activity)
    by_round = collections.Counter()     # (bucket, activity)
    by_lead = collections.Counter()
    by_gold = collections.Counter()
    spread = collections.Counter()
    nearest = []
    gs_of = {}
    for snap in rounds:
        r = snap['r']
        R = T.get(r)
        gs = snap['gs']
        resp_tiles = [t for g in G.groups if gs[g['live']][0] == RESPAWNING for t in g['tiles']]
        live_tiles = [(cm['x'], cm['y']) for cm in G.obs['camps'] if snap['hp'][cm['id']] > 0]
        empty_at = {t for g in G.groups if gs[g['live']][0] == EMPTY for t in g['tiles']}
        sub = snap['sub']
        lead = sub[G.side] - sub[1 - G.side]
        ch = {c[ID]: c for c in snap['ch']}
        team_gold = sum(ch[i][GOLDC] for i in G.fish)
        turns = {t['id']: t for t in R['turns']} if R else {}
        alive_off = [ch[i] for i in G.fish if ch[i][ALIVE] and (ch[i][X], ch[i][Y]) not in G.own_spawn]
        for c in alive_off:
            spread['off'] += 1
            spread[('side', G.side_of((c[X], c[Y])))] += 1
            others = [cheb((c[X], c[Y]), (o[X], o[Y])) for o in alive_off if o is not c]
            if others:
                d = min(others); nearest.append(d)
                spread['ally<=4'] += d <= 4
                spread['with_other'] += 1
        for i in G.fish:
            c = ch[i]; t = turns.get(i)
            pos = (c[X], c[Y])
            kinds = [a[0] for a in t['acts']] if t else []
            if not c[ALIVE]:
                a = 'dead'
            elif pos in G.own_spawn:
                a = 'home'
            elif c[CT] == 2 or 'Submit gems' in kinds:
                a = 'tribute'
            elif t and any(len(x) > 6 and x[6] == 1 and x[7] not in fish for x in t['acts']):
                a = 'fight'
            elif t and any(len(x) > 6 and (x[6] == 2 or (isinstance(x[-1], list) and bool(x[-1]))) for x in t['acts']):
                a = 'clear'
            elif pos in empty_at:
                a = 'capture'
            elif c[CT] == 1 and 'Cancel channel' not in kinds:
                a = 'recall'
            elif any(cheb(pos, p) <= 2 for p in resp_tiles):
                a = 'wait'
            elif 'Move' in kinds or c[CT] == 3 or 'Consumable' in kinds:
                a = 'approach' if any(cheb(pos, p) <= 3 for p in live_tiles) else 'travel'
            else:
                a = 'idle'
            name = NAMES[G.type[i]]
            act[name, a] += 1; act['all', a] += 1
            by_round[rbucket(r), a] += 1
            by_lead[lbucket(lead), a] += 1
            by_gold[gbucket(team_gold), a] += 1
    # payouts and sequences
    pays = payouts(G)
    seq = collections.defaultdict(list)
    capt = collections.Counter()
    for p in pays:
        g = G.groups[p['group']]
        side = 'own' if g['terr'] > 0 else 'enemy' if g['terr'] < 0 else 'middle'
        if p['team'] == G.side:
            fishrec = [i for i in p['recipients'] if i in fish]
            capt['fish', side] += 1
            capt['fish_big', side, CAMP_NAMES[g['big']]] += 1
            capt['fish_recipients', len(fishrec)] += 1
            capt[('fish_rb', rbucket(p['round']), side)] += 1
            for i in fishrec:
                seq[i].append((p['round'], g['id']))
        else:
            capt['enemy', side] += 1
    # clears: windows from a group's respawn (or game start) to all members dead
    hits = collections.defaultdict(lambda: collections.defaultdict(set))  # live group -> window start -> champions
    clears = []
    alive_prev = None
    window = {g['id']: 1 for g in G.groups}
    involved = {g['id']: set() for g in G.groups}
    strength = {}
    for snap in rounds:
        r = snap['r']
        hp = snap['hp']
        R = T.get(r)
        if R and R.get('cp'):
            for c in R['cp']['ch']:
                strength[c[0]] = c[15]
        # camp hits on champions this round
        if R:
            for camp, tgt, *_ in R['attacks']:
                if tgt >= 0 and camp in G.group_of_camp:
                    involved[G.group_of_camp[camp]].add(tgt)
            for t in R['turns']:
                for x in t['acts']:
                    if len(x) > 6:
                        if x[6] == 2 and x[7] in G.group_of_camp:
                            involved[G.group_of_camp[x[7]]].add(t['id'])
                        if isinstance(x[-1], list):
                            for k in x[-1]:
                                if k in G.group_of_camp:
                                    involved[G.group_of_camp[k]].add(t['id'])
        for g in G.groups:
            alive = sum(hp[k] > 0 for k in g['members'])
            gid = g['id']
            if alive_prev is not None:
                was = alive_prev[gid]
                if was > 0 and alive == 0:
                    inv = involved[gid]
                    fi = sorted(inv & fish); en = sorted(inv - fish)
                    clears.append(dict(round=r, group=gid, big=g['big'], fish=fi, enemy=en,
                                       str={i: strength.get(i) for i in fi}, terr=g['terr']))
                    involved[gid] = set()
                if was == 0 and alive > 0:
                    involved[gid] = set()
        alive_prev = {g['id']: sum(hp[k] > 0 for k in g['members']) for g in G.groups}
    clear_stats = collections.Counter()
    solo_big = []
    for c in clears:
        kind = CAMP_NAMES[c['big']]
        if c['fish'] and not c['enemy']:
            clear_stats['fish', kind, 'solo' if len(c['fish']) == 1 else 'team'] += 1
            if len(c['fish']) == 1 and c['big'] in BIG:
                i = c['fish'][0]
                solo_big.append(dict(game=key, round=c['round'], actor=i, champ=NAMES[G.type[i]], kind=kind,
                                     strength=c['str'][i], terr=c['terr']))
        elif c['fish'] and c['enemy']:
            clear_stats['mixed', kind] += 1
        elif c['enemy']:
            clear_stats['enemy', kind] += 1
    # steals: payouts where the other team took part in the clear window
    last_clear = {}
    for c in clears:
        last_clear.setdefault(c['group'], []).append(c)
    steal = collections.Counter()
    for p in pays:
        cl = [c for c in last_clear.get(p['group'], []) if c['round'] <= p['round']]
        if not cl:
            continue
        c = cl[-1]
        fish_team = p['team'] == G.side
        cleared_by_fish = bool(c['fish']); cleared_by_enemy = bool(c['enemy'])
        if fish_team:
            steal['fish_paid', 'fish_only' if not cleared_by_enemy else 'enemy_only' if not cleared_by_fish else 'both'] += 1
        else:
            steal['enemy_paid', 'enemy_only' if not cleared_by_fish else 'fish_only' if not cleared_by_enemy else 'both'] += 1
    seqs = {NAMES[G.type[i]] + f'#{i}': [s[1] for s in v] for i, v in seq.items()}
    return dict(game=key, cohort=cohort, map=obs['map'], side=G.side, rounds=len(rounds), act=act, by_round=by_round,
                by_lead=by_lead, by_gold=by_gold, spread=spread, nearest=nearest, capt=capt, clear=clear_stats,
                solo_big=solo_big, steal=steal, seqs=seqs,
                groups=[dict(id=g['id'], label=g['label'], terr=g['terr'], d_own=g['d_own']) for g in G.groups],
                pays_fish=sum(p['team'] == G.side for p in pays))


def merge(results, field):
    tot = collections.Counter()
    for r in results:
        tot.update(r[field])
    return tot


def table(counter, rows):
    out = {}
    for row in rows:
        n = sum(v for (k, a), v in counter.items() if k == row)
        if n:
            out[row] = dict(n=n, **{a: round(counter[row, a] / n, 4) for a in ACTS})
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out'); p.add_argument('--cohorts'); p.add_argument('--jobs', type=int, default=6)
    a = p.parse_args()
    from pathlib import Path
    if Path(a.out).exists():
        raise SystemExit(f'refusing to overwrite {a.out}')
    todo = list(entries(set(a.cohorts.split(',')) if a.cohorts else None))
    with mp.Pool(min(6, a.jobs)) as pool:
        res = [r for r in pool.map(game_stats, todo, chunksize=2) if r]
    act = merge(res, 'act')
    champs = sorted({k for k, _ in act})
    near = [d for r in res for d in r['nearest']]
    spread = merge(res, 'spread')
    capt = merge(res, 'capt')
    out = dict(
        games=len(res), definitions=__doc__,
        activity=table(act, ['all'] + [c for c in champs if c != 'all']),
        by_round=table(merge(res, 'by_round'), ['1-100', '101-300', '301-600', '601-1000', '1001+']),
        by_lead=table(merge(res, 'by_lead'), ['behind>100', 'behind', 'level', 'ahead', 'ahead>100']),
        by_gold=table(merge(res, 'by_gold'), ['<30', '30-89', '90-199', '200+']),
        spread=dict(off_spawn_turns=spread['off'], own_side=spread['side', 1], middle=spread['side', 0], enemy_side=spread['side', -1],
                    with_other_ally_off_spawn=spread['with_other'], nearest_ally_within_4=spread['ally<=4'],
                    nearest_ally_median=statistics.median(near) if near else None,
                    nearest_ally_quartiles=statistics.quantiles(near, n=4) if len(near) > 4 else None),
        captures={' '.join(map(str, k)): v for k, v in sorted(capt.items(), key=lambda kv: str(kv[0]))},
        clears={' '.join(map(str, k)): v for k, v in sorted(merge(res, 'clear').items(), key=lambda kv: str(kv[0]))},
        steals={' '.join(map(str, k)): v for k, v in sorted(merge(res, 'steal').items(), key=lambda kv: str(kv[0]))},
        solo_big=[s for r in res for s in r['solo_big']],
        per_game=[dict(game=r['game'], cohort=r['cohort'], map=r['map'], side=r['side'], rounds=r['rounds'], seqs=r['seqs'],
                       groups=r['groups'], pays_fish=r['pays_fish']) for r in res],
    )
    write_json(a.out, out)
    print('games', len(res))
    for k, v in out['activity'].items():
        print(k, v)


if __name__ == '__main__':
    main()
