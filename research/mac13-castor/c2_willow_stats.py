#!/usr/bin/env python3
"""Willow medic stats from an extract.mjs cache (C2, briefs/c2-medic.md).

  py research/mac13-castor/c2_willow_stats.py ANALYSIS_DIR [--threads N]

Per team name (index.json rows), over team-games with a Willow: her alive rounds, heals and healing
(per game, per 100 alive rounds), whom she heals (Prism / other), her heal-ready turns by the nearest
nearest damaged ally (missing >= 60% of her heal: within 4 / 5-8 / 9-12 / 13+ / none), the team's completed recalls,
deaths and damage taken, and the camp damage allies take by their distance from Willow. Positions and
health are the end of the previous round (approximate: allies acting before her move first)."""
import gzip, json, os, sys
from collections import defaultdict
from multiprocessing import Pool

WILLOW, PRISM = 8, 6  # enums.champions


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def game(args):
    root, d, teams = args
    meta = json.load(open(os.path.join(root, d, 'meta.json')))
    champs = meta['champions']
    if not any(c['type'] == WILLOW for c in champs):
        return []
    mp = json.load(open(os.path.normpath(os.path.join(root, d, meta['mapFile']))))
    spawn = mp['spawn']
    rounds = json.load(gzip.open(os.path.join(root, d, 'rounds.json.gz')))
    events = [json.loads(l) for l in gzip.open(os.path.join(root, d, 'events.jsonl.gz'), 'rt')]
    rc = {c['id']: c for c in rounds['champions']}
    n = len(rounds['round'])
    idx = {r: i for i, r in enumerate(rounds['round'])}
    typ = {c['id']: c['type'] for c in champs}
    team_of = {c['id']: c['team'] for c in champs}
    out = []
    for t in (0, 1):
        ws = [c['id'] for c in champs if c['team'] == t and c['type'] == WILLOW]
        if not ws:
            continue
        w = ws[0]
        W = rc[w]
        allies = [c['id'] for c in champs if c['team'] == t and c['id'] != w]
        sp = spawn[t]
        on_spawn = lambda x, y: sp['minX'] <= x <= sp['maxX'] and sp['minY'] <= y <= sp['maxY']
        s = defaultdict(float)
        s['games'] = 1
        s['won'] = 1 if meta['result']['winner'] == t else 0
        s['alive_rounds'] = sum(W['alive'])
        # heal-ready turns, from the previous round's end state
        for i in range(1, n):
            if not W['alive'][i - 1] or not W['alive'][i] or W['cd0'][i - 1] != 0 or W['chan'][i - 1] in (2, 3) or (W['chan'][i - 1] == 1 and W['chanT'][i - 1] < 4):
                continue
            wp = (W['x'][i - 1], W['y'][i - 1])
            if wp[0] is None:
                continue
            amount = 3 * W['foc'][i - 1]
            s['ready'] += 1
            if on_spawn(*wp):
                s['ready_spawn'] += 1
                continue
            best = 99
            for a in allies:
                A = rc[a]
                if not A['alive'][i - 1] or A['x'][i - 1] is None:
                    continue
                if on_spawn(A['x'][i - 1], A['y'][i - 1]):
                    continue
                if A['maxHp'][i - 1] - A['hp'][i - 1] >= 0.6 * amount:
                    best = min(best, cheb(wp, (A['x'][i - 1], A['y'][i - 1])))
            s['ready_d4' if best <= 4 else 'ready_d8' if best <= 8 else 'ready_d12' if best <= 12 else 'ready_far' if best < 99 else 'ready_none'] += 1
        for e in events:
            k = e['k']
            if k == 'cast' and e.get('a') == w and e.get('ab') == 'Heal':
                for tgt, amt in e.get('heal', []):
                    s['heals'] += 1
                    s['healing'] += amt
                    if typ.get(tgt) == PRISM:
                        s['heals_prism'] += 1
                        s['healing_prism'] += amt
            elif k == 'recall_end' and team_of.get(e['a']) == t:
                s['recalls'] += 1
            elif k == 'death' and team_of.get(e['v']) == t:
                s['deaths'] += 1
            elif k == 'camp_attack' and team_of.get(e.get('tgt')) == t:
                i = idx.get(e['r'])
                hits = [(e['tgt'], e['dmg'])] + [tuple(x) for x in e.get('xdmg', [])]
                for tgt, dmg in hits:
                    if team_of.get(tgt) != t:
                        continue
                    s['camp_dmg'] += dmg
                    if tgt == w:
                        s['camp_dmg_willow'] += dmg
                        continue
                    j = (i or 0) - 1
                    if j < 0 or not W['alive'][j] or W['x'][j] is None:
                        s['camp_dmg_wdead'] += dmg
                        continue
                    A = rc[tgt]
                    dd = cheb((W['x'][j], W['y'][j]), (A['x'][j], A['y'][j])) if A['x'][j] is not None else 99
                    s['camp_dmg_d4' if dd <= 4 else 'camp_dmg_d8' if dd <= 8 else 'camp_dmg_d16' if dd <= 16 else 'camp_dmg_far'] += dmg
        for c in champs:
            if c['team'] != t:
                continue
            st = c['stats']
            s['dmg_taken'] += st.get('monsterDamageTaken', 0) + st.get('championDamageTaken', 0)
            if c['id'] == w:
                s['willow_gold'] += c['earnedGold']
                s['willow_camp_dmg_done'] += st.get('monsterDamageDone', 0)
        out.append((teams[t], dict(s)))
    return out


def main():
    root = sys.argv[1]
    threads = int(sys.argv[sys.argv.index('--threads') + 1]) if '--threads' in sys.argv else 16
    rows = json.load(open(os.path.join(root, 'index.json')))['games']
    # A mirror's identical replays swap the names: both rows count, which leaves per-game means as they are.
    jobs = sorted({(root, r['dir'], tuple(r['teams'])) for r in rows if r.get('ok', True)})
    tot = defaultdict(lambda: defaultdict(float))
    with Pool(threads) as p:
        for res in p.imap_unordered(game, jobs, chunksize=4):
            for name, s in res:
                for k, v in s.items():
                    tot[name][k] += v
    for name, s in sorted(tot.items()):
        g = s['games']
        ar = s['alive_rounds']
        print(f"## {name}: {int(g)} Willow team-games, won {100 * s['won'] / g:.1f}%")
        print(f"  Willow alive rounds/game {ar / g:.0f}; heals/game {s['heals'] / g:.1f} ({100 * s['heals'] / ar:.2f} per 100 alive rounds); "
              f"healing/game {s['healing'] / g:.0f}; per heal {s['healing'] / max(1, s['heals']):.0f}")
        print(f"  heals on Prism {100 * s['heals_prism'] / max(1, s['heals']):.1f}% ({s['healing_prism'] / g:.0f} HP/game), others {(s['healing'] - s['healing_prism']) / g:.0f} HP/game")
        rd = s['ready']
        print(f"  heal-ready turns/game {rd / g:.0f}: on spawn {100 * s['ready_spawn'] / rd:.1f}%, damaged ally <=4 {100 * s['ready_d4'] / rd:.1f}%, "
              f"5-8 {100 * s['ready_d8'] / rd:.1f}%, 9-12 {100 * s['ready_d12'] / rd:.1f}%, 13+ {100 * s['ready_far'] / rd:.1f}%, none damaged {100 * s['ready_none'] / rd:.1f}%")
        print(f"  team recalls/game {s['recalls'] / g:.1f}; deaths/game {s['deaths'] / g:.2f}; damage taken/game {s['dmg_taken'] / g:.0f}; camp damage/game {s['camp_dmg'] / g:.0f}")
        cd = s['camp_dmg'] - s['camp_dmg_willow'] - s['camp_dmg_wdead']
        if cd > 0:
            print(f"  allies' camp damage by distance from Willow: <=4 {100 * s['camp_dmg_d4'] / cd:.1f}%, 5-8 {100 * s['camp_dmg_d8'] / cd:.1f}%, "
                  f"9-16 {100 * s['camp_dmg_d16'] / cd:.1f}%, >16 {100 * s['camp_dmg_far'] / cd:.1f}% (Willow's own {s['camp_dmg_willow'] / g:.0f}/game, while she is dead {s['camp_dmg_wdead'] / g:.0f}/game)")
        print(f"  Willow gold earned/game {s['willow_gold'] / g:.0f}; her camp damage done/game {s['willow_camp_dmg_done'] / g:.0f}")


if __name__ == '__main__':
    main()
