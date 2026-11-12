"""How our Prism dies, from extracted replays (tools/replay/extract.mjs --out DIR).

    python3 deaths.py EXTROOT/TAG [--dump N] [--min-gems G]

Our side is the team whose name does not start with rt-. One row per Prism death, with the EP rounds before it:
health, cooldowns, what its turn was (cast, hit a champion, hit a camp, walk towards or away from the nearest enemy,
idle, stunned, out of fuel, channel), who was near, and the damage it took by source. Printed: how often it dies and
what that costs, the shape of the last rounds, and the turns it ran out of fuel (near an enemy or not).
"""
import collections, gzip, json, os, sys
from multiprocessing import Pool

EP = 8  # rounds before the death that are read
NEAR = 6


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        mp = json.load(open(os.path.join(d, meta['mapFile']))) if 'mapFile' in meta else None
    except Exception as e:
        sys.stderr.write(f'{d}: {e!r}\n')
        return None
    names = [t['name'] for t in meta['teams']]
    us = 0 if not names[0].startswith('rt-') else 1
    bdir = os.path.basename(os.path.dirname(meta['source']))
    opp = 'Flp4' if 'Flp4' in bdir else 'Mt3q'
    res = meta['result']; win = res['winner'] == us
    team = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}
    rounds = R['round']; idx = {r: i for i, r in enumerate(rounds)}
    prisms = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    out = dict(src=meta['source'], dir=os.path.basename(d), opp=opp, win=win, end=res['rounds'], prism=bool(prisms),
               deaths=[], turns=collections.Counter(), oof_near=0, oof_far=0, alive_near=0, alive_far=0,
               all_oof=0, all_turns=0, eprism=any(typ[c] == 'Prism' and team[c] != us for c in ch))
    for c in ch:
        if team[c] != us: continue
        t = ch[c]['turn']
        out['all_oof'] += sum(1 for x in t if x == 6)
        out['all_turns'] += sum(1 for x in t if x in (1, 2, 3, 5, 6))
    if not prisms: return out
    p = prisms[0]; P = ch[p]
    spawn = mp['spawn'][us] if mp else None
    foes = [c for c in ch if team[c] != us]; mates = [c for c in ch if team[c] == us and c != p]

    def pos(c, i):
        C = ch[c]
        return (C['x'][i], C['y'][i]) if C['alive'][i] and C['x'][i] is not None else None

    def near(i, group, r=NEAR):
        me = pos(p, i)
        if not me: return 0, 99
        ds = [cheb(me, q) for q in (pos(c, i) for c in group) if q]
        return sum(1 for x in ds if x <= r), min(ds, default=99)

    # Out-of-fuel turns of the Prism, near an enemy (within 8 at the end of the round before) or not.
    for i, r in enumerate(rounds):
        t = P['turn'][i]
        if t not in (1, 2, 3, 5, 6): continue
        j = max(0, i - 1)
        n8, _ = near(j, foes, 8)
        if n8: out['alive_near'] += 1; out['oof_near'] += t == 6
        else: out['alive_far'] += 1; out['oof_far'] += t == 6

    by_round = collections.defaultdict(list)
    for e in ev: by_round[e['r']].append(e)
    for e in ev:
        if e['k'] != 'death' or e['v'] != p: continue
        r = e['r']
        killer = typ.get(e.get('by')) if 'by' in e and e.get('by') is not None else None
        row = dict(r=r, gems=e.get('gems', 0), killer=killer or 'camp', camp='camp' in e and killer is None, steps=[])
        for q in range(max(1, r - EP), r + 1):
            i = idx.get(q); j = idx.get(q - 1)
            if i is None: continue
            # State at the start of round q is the end of q-1.
            st = j if j is not None else i
            me = pos(p, st)
            ne, de = near(st, foes); na, da = near(st, mates)
            act = []; dmg = collections.Counter(); stunned_by = []
            for x in by_round.get(q, []):
                k = x['k']
                if x.get('a') == p:
                    if k == 'move':
                        # towards or away from the nearest enemy
                        fs = [pp for pp in (pos(c, st) for c in foes) if pp]
                        if fs:
                            f0 = min(fs, key=lambda pp: cheb(pp, tuple(x['f'])))
                            d0, d1 = cheb(f0, tuple(x['f'])), cheb(f0, tuple(x['to']))
                            act.append('M+' if d1 < d0 else 'M-' if d1 > d0 else 'M=')
                        else: act.append('M')
                    elif k == 'attack': act.append('Ac' if 'tgt' in x else 'Ak' if 'camp' in x else 'Al')
                    elif k == 'cast': act.append(f"C{x.get('slot')}" + ('c' if x.get('dmg') else 'k' if x.get('cdmg') else '0'))
                    elif k in ('recall_start', 'tribute_start', 'teleport_start'): act.append(k[:3])
                if k in ('attack', 'cast') and team.get(x.get('a')) != us:
                    for vid, amt in x.get('dmg', []) or []:
                        if vid == p: dmg['basic' if k == 'attack' else 'spell'] += amt
                    if p in (x.get('stun') or []): stunned_by.append(typ.get(x.get('a')))
                if k == 'camp_attack':
                    if x.get('tgt') == p: dmg['camp'] += x.get('dmg', 0) if isinstance(x.get('dmg'), (int, float)) else 0
                    for vid, amt in x.get('xdmg', []) or []:
                        if vid == p: dmg['camp'] += amt
            row['steps'].append(dict(q=q, hp=P['hp'][st] / max(1, P['maxHp'][st]) if P['alive'][st] else 0, cd=(P['cd0'][st], P['cd1'][st]),
                                     turn=P['turn'][i], chan=P['chan'][st], ne=ne, de=de, na=na, da=da, act=act, dmg=dict(dmg),
                                     stun=stunned_by, me=me, gems=P['gems'][st],
                                     home=(max(spawn['minX'] - me[0], 0, me[0] - spawn['maxX']), max(spawn['minY'] - me[1], 0, me[1] - spawn['maxY'])) if spawn and me else None))
        out['deaths'].append(row)
    return out


def load(root):
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool:
        return [r for r in pool.map(one, dirs, chunksize=8) if r]


def pct(a, b): return f'{100 * a / max(1, b):.1f}%'


def main():
    root = sys.argv[1]
    dump = int(sys.argv[sys.argv.index('--dump') + 1]) if '--dump' in sys.argv else 0
    ming = int(sys.argv[sys.argv.index('--min-gems') + 1]) if '--min-gems' in sys.argv else 0
    G = load(root)
    n = len(G); PG = [g for g in G if g['prism']]
    print(f'{root}: {n} games, win {pct(sum(g["win"] for g in G), n)}; Prism games {len(PG)}, win {pct(sum(g["win"] for g in PG), len(PG))}; '
          f'no Prism win {pct(sum(g["win"] for g in G if not g["prism"]), n - len(PG))}')
    for opp in ('Flp4', 'Mt3q'):
        s = [g for g in PG if g['opp'] == opp]
        print(f'  {opp}: Prism games {len(s)}, win {pct(sum(g["win"] for g in s), len(s))}, Prism deaths a game {sum(len(g["deaths"]) for g in s) / max(1, len(s)):.2f}')
    D = [(g, d) for g in PG for d in g['deaths']]
    print(f'Prism deaths: {len(D)} ({len(D) / len(PG):.2f} a Prism game); to camps {sum(d["camp"] for _, d in D)}')
    for name, f in [('no death', lambda g: not g['deaths']), ('1 death', lambda g: len(g['deaths']) == 1), ('2+ deaths', lambda g: len(g['deaths']) >= 2),
                    ('death before r600', lambda g: any(d['r'] < 600 for d in g['deaths'])),
                    ('death with 40+ gems', lambda g: any(d['gems'] >= 40 for d in g['deaths'])),
                    ('death with 100+ gems', lambda g: any(d['gems'] >= 100 for d in g['deaths'])),
                    ('death with 200+ gems', lambda g: any(d['gems'] >= 200 for d in g['deaths']))]:
        s = [g for g in PG if f(g)]
        print(f'  {name}: {len(s)} games ({pct(len(s), len(PG))}), win {pct(sum(g["win"] for g in s), len(s))}')
    print(f'  gems lost a Prism game: {sum(d["gems"] for _, d in D) / len(PG):.1f}')
    for lo, hi in [(0, 1), (1, 20), (20, 40), (40, 100), (100, 200), (200, 10000)]:
        s = [(g, d) for g, d in D if lo <= d['gems'] < hi]
        print(f'    bag {lo}-{hi}: {len(s)} deaths, game win {pct(sum(g["win"] for g, _ in s), len(s))}')
    D = [(g, d) for g, d in D if d['gems'] >= ming]
    print(f'\nDeaths read below: {len(D)} (bag >= {ming})')
    kc = collections.Counter(d['killer'] for _, d in D)
    print('  killers:', ', '.join(f'{k} {v}' for k, v in kc.most_common()))
    # Shape of the last rounds
    tm = collections.Counter(); tot = 0; empty = 0; stunned = 0; oofd = 0; dsrc = collections.Counter()
    hp_at = collections.defaultdict(list); ne_at = collections.defaultdict(list); na_at = collections.defaultdict(list)
    start80 = []; cls = collections.Counter()
    for g, d in D:
        S = d['steps']
        last = d['r']
        ep = None
        for s in S:
            k = last - s['q']
            hp_at[k].append(s['hp']); ne_at[k].append(s['ne']); na_at[k].append(s['na'])
            if s['hp'] >= 0.8: ep = k
        start80.append(ep)
        any_oof = False; any_stun = False; acted_c = False; closing = False; opening = False; chan = False
        for s in S:
            k = last - s['q']
            if k > 5 or k == 0 and not s['act'] and s['turn'] in (0, 4): continue
            tot += 1
            t = s['turn']
            lab = 'stunned' if t == 5 else 'oof' if t == 6 else 'channel' if t == 3 else 'dead/none' if t in (0, 4) else \
                  'cast@champ' if any(a.startswith('C') and a.endswith('c') for a in s['act']) else \
                  'cast@camp' if any(a.startswith('C') and a.endswith('k') for a in s['act']) else \
                  'cast@none' if any(a.startswith('C') for a in s['act']) else \
                  'hit champ' if 'Ac' in s['act'] else 'hit camp' if 'Ak' in s['act'] else \
                  'walk closer' if 'M+' in s['act'] else 'walk away' if 'M-' in s['act'] else 'walk level' if any(a.startswith('M') for a in s['act']) else 'idle'
            tm[lab] += 1
            if min(s['cd']) > 1 and s['cd'][0] > 1 and s['cd'][1] > 1: empty += 1
            any_oof |= t == 6; any_stun |= t == 5 or bool(s['stun'])
            acted_c |= lab in ('cast@champ', 'hit champ'); closing |= lab == 'walk closer'; opening |= lab == 'walk away'; chan |= t == 3
            for k2, v in s['dmg'].items(): dsrc[k2] += v
        oofd += any_oof; stunned += any_stun
        cls['fought (cast or hit a champion in the last 6)'] += acted_c
        cls['walked closer in the last 6'] += closing
        cls['walked away in the last 6'] += opening
        cls['channelled in the last 6'] += chan
    print('  health share by rounds before death (median):', ', '.join(f'-{k}: {sorted(v)[len(v) // 2]:.2f}' for k, v in sorted(hp_at.items(), reverse=True)))
    print('  enemies within 6 (mean):', ', '.join(f'-{k}: {sum(v) / len(v):.2f}' for k, v in sorted(ne_at.items(), reverse=True)))
    print('  allies within 6 (mean):', ', '.join(f'-{k}: {sum(v) / len(v):.2f}' for k, v in sorted(na_at.items(), reverse=True)))
    c80 = collections.Counter('never in 8' if x is None else f'{x} rounds before' for x in start80)
    print('  last round at 80%+ health:', ', '.join(f'{k}: {v}' for k, v in sorted(c80.items())))
    print(f'  turns in the last 6 rounds ({tot}):', ', '.join(f'{k} {pct(v, tot)}' for k, v in tm.most_common()))
    print(f'  of those turns, both spells cooling (2+ rounds left): {pct(empty, tot)}')
    for k, v in cls.items(): print(f'  {k}: {pct(v, len(D))}')
    print(f'  stunned at least once in the last 6: {pct(stunned, len(D))}; out of fuel at least once: {pct(oofd, len(D))}')
    tot_d = sum(dsrc.values())
    print('  damage taken in the last 6 by source:', ', '.join(f'{k} {pct(v, tot_d)}' for k, v in dsrc.most_common()))
    # Fuel
    an = sum(g['alive_near'] for g in PG); af = sum(g['alive_far'] for g in PG)
    on = sum(g['oof_near'] for g in PG); of = sum(g['oof_far'] for g in PG)
    print(f'\nPrism out-of-fuel turns: near an enemy (within 8) {on} of {an} ({pct(on, an)}), else {of} of {af} ({pct(of, af)})')
    print(f'Team out-of-fuel turns: {sum(g["all_oof"] for g in G)} of {sum(g["all_turns"] for g in G)} ({pct(sum(g["all_oof"] for g in G), sum(g["all_turns"] for g in G))})')
    if dump:
        import random
        random.seed(1)
        for g, d in random.sample(D, min(dump, len(D))):
            print(f"\n{g['dir']} {g['opp']} r{d['r']} bag {d['gems']} killer {d['killer']} win {g['win']}  {g['src']}")
            for s in d['steps']:
                print(f"  r{s['q']} hp {s['hp']:.2f} cd {s['cd']} t{s['turn']} ch{s['chan']} at {s['me']} home {s['home']} e{s['ne']}@{s['de']} a{s['na']}@{s['da']} "
                      f"{' '.join(s['act'])} dmg {s['dmg']} {'stun:' + ','.join(map(str, s['stun'])) if s['stun'] else ''}")


if __name__ == '__main__':
    main()
