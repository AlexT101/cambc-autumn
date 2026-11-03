"""Why our kill bids are not followed through, and why champions near a low enemy hit nothing
(ast-follow-meas's KB, FT and LW lines; follow-through.md).

usage: python3 research/turn-order-2026-11-02/scripts/follow_trace.py [--ex EXTRACT_DIR] RUN [RUN ...]
  RUN: an ab.py run name (replays/batch-*-ab-RUN-*) whose CAND is the traced bot.
  --ex: extract.mjs --out of those batches. Our hits and kills in the turn are then read from the replay: the
  trace's end-of-turn health read can miss a kill (it reads the target unchanged), so use it.

KB r me target need hp                       a kill bid won at our turn end on an enemy that had acted
FT r me tgt need hpbid | alive acted d hp0 hp1 our ourmax stun branch home line lethal strike |
   searches in_foes nodes kill_ok kill_guard hit_ok hit_guard kraw craw ctot ktot kpriced ckills failed exact | other
   at our next turn (the bid binds it). alive: 2 alive + 1 visible. acted: the target acted before us.
   hp0/hp1: its live health at our turn's start and end (-1 unseen). masks are by enemy index.
LW r me enemy d hp0 hp1 max branch home lethal strike searches kill_ok kill_guard hit_ok hit_guard other our ourmax bid
   each visible enemy under 25% health, off its spawn, within 4 at our turn's start.
"""
import glob
import json
import os
import sys
import zipfile
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HOME = {'l': 'low (recall line)', 'o': 'pack zone', 'c': 'camp trapped', 'f': 'camp fled', 'w': 'Willow threatened',
        's': 'stand lost', 'p': 'stand lost, pursued', 'L': 'stand lost, lethal tile', 'K': 'stand lost, linked',
        'F': 'self falls, lethal tile', 'k': 'self falls, linked', '-': 'none'}


def key(path):
    """A replay's batch directory and file name: runs on the same suites share file names."""
    return '/'.join(path.split('/')[-2:])


def replays(run):
    for d in sorted(glob.glob(f'replays/batch-*-ab-{run}-*')):
        for f in sorted(glob.glob(f'{d}/*.repl26a')):
            yield f


def lines(path):
    team = 'team-a.stdout' if path.endswith('-12.repl26a') else 'team-b.stdout'
    try:
        z = zipfile.ZipFile(path)
        return z.read(team).decode(errors='replace').replace('\x00', '').splitlines()
    except (KeyError, zipfile.BadZipFile, OSError):
        return []


TYPES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg',
         'Tavi', 'Heart of Ruin']


def parse_ft(l):
    a, b, c, d, e = l.split('|')
    tail = e.split()
    h = a.split()
    m = b.split()
    s = c.split()
    return dict(r=int(h[1]), me=int(h[2]), t=int(h[3]), need=int(h[4]), hpbid=int(h[5]),
                alive=int(m[0]) >= 2, vis=int(m[0]) & 1 == 1, acted=int(m[1]), d=int(m[2]), hp0=int(m[3]), hp1=int(m[4]),
                our=int(m[5]), ourmax=int(m[6]), stun=int(m[7]), branch=m[8], home=m[9], line=float(m[10]),
                lethal=int(m[11]), strike=int(m[12]),
                searches=int(s[0]), in_foes=int(s[1]), nodes=int(s[2]), kok=int(s[3], 16), kg=int(s[4], 16),
                hok=int(s[5], 16), hg=int(s[6], 16), kraw=int(s[7]), craw=int(s[8]), ctot=int(s[9]), ktot=int(s[10]),
                kpriced=int(s[11]), ckills=int(s[12]), failed=int(s[13]), exact=int(s[14]), other=int(d),
                type=TYPES[int(tail[0])], channel=int(tail[1]), tributing=int(tail[2]), ckilled=int(tail[3], 16))


def parse_lw(l):
    h = l.split()
    return dict(r=int(h[1]), me=int(h[2]), e=int(h[3]), d=int(h[4]), hp0=int(h[5]), hp1=int(h[6]), max=int(h[7]),
                branch=h[8], home=h[9], lethal=int(h[10]), strike=int(h[11]), searches=int(h[12]), kok=int(h[13], 16),
                kg=int(h[14], 16), hok=int(h[15], 16), hg=int(h[16], 16), other=int(h[17]), our=int(h[18]),
                ourmax=int(h[19]), bid=int(h[20]), type=TYPES[int(h[21])], tributing=int(h[22]))


def truth(game, recs, key):
    """Sets each record's hp1 and other from the replay: our damage in our turn of round r to enemy `key`, and to the
    rest; hp1 = 0 when we killed it, hp0 - damage otherwise."""
    if not recs:
        return
    us = game.team[recs[0]['me']]
    enemies = [c for c in game.ids if game.team[c] != us]
    for x in recs:
        t = enemies[x[key]] if x[key] < len(enemies) else None
        dmg, other = 0.0, 0.0
        for e in game.by_round[x['r']]:
            if e.get('a') != x['me'] or e['k'] not in ('attack', 'cast'):
                continue
            for v, d in e.get('dmg') or []:
                if v == t:
                    dmg += d
                elif v in game.team and game.team[v] != us:
                    other += d
        de = game.death(t, x['r']) if t is not None else None
        killed = de is not None and de.get('by') == x['me']
        if x['hp0'] > 0:
            x['hp1'] = 0 if killed else int(x['hp0'] - dmg) if dmg > 0 else x['hp0']
            x['alive'], x['vis'] = not killed, True
        x['other'] = int(other)


def one(args):
    """One game's KB, FT and LW records, hits and kills from the replay when `d` (its extract dir) is given."""
    path, ex, d = args
    kb, ft, lw = [], [], []
    g = key(path)
    for l in lines(path):
        try:
            if l.startswith('KB '):
                h = l.split()
                kb.append(dict(g=g, r=int(h[1]), me=int(h[2]), t=int(h[3]), need=int(h[4]), hp=int(h[5])))
            elif l.startswith('FT '):
                x = parse_ft(l)
                x['g'] = g
                ft.append(x)
            elif l.startswith('LW '):
                x = parse_lw(l)
                x['g'] = g
                lw.append(x)
        except (ValueError, IndexError):
            continue
    if d is not None:
        from tolib import G
        game = G(ex, d)
        truth(game, ft, 't')
        truth(game, lw, 'e')
    return kb, ft, lw


def load(runs, ex=None):
    from concurrent.futures import ProcessPoolExecutor
    by_source = {}
    if ex:
        from tolib import index
        by_source = {key(r['source']): r['dir'] for r in index(ex) if r['ok']}
    todo = [(p, ex, by_source.get(key(p))) for run in runs for p in replays(run) if not ex or key(p) in by_source]
    kb, ft, lw = [], [], []
    games = len(todo)
    with ProcessPoolExecutor(32) as pool:
        for a, b, c in pool.map(one, todo, chunksize=8):
            kb += a
            ft += b
            lw += c
    return games, kb, ft, lw, {}


def pct(n, d):
    return f'{n} ({100 * n / d:.1f}%)' if d else f'{n}'


def search_cause(x, bit):
    """Why a strike search that ran did not hit enemy `bit` (FT or LW record)."""
    if x['kok'] & bit:
        if x.get('ckills'):
            return 'chose the kill, execution failed' if x.get('failed') else 'chose the kill (hit elsewhere?)'
        if 'kraw' in x and x['kraw'] < x['craw']:
            return 'kill offered: another plan worth more before danger'
        return 'kill offered: priced below after danger/camps/goal'
    if x['kg'] & bit:
        return 'kill only on step-guarded tiles'
    if x['hok'] & bit:
        return 'hit offered (no kill), another plan chosen'
    if x['hg'] & bit:
        return 'hit only on step-guarded tiles'
    if x.get('nodes', 0) >= 24:
        return 'no plan reaches it (node cap hit)'
    return 'no plan reaches it (walls, sight, range)'


def report_ft(games, kb, ft, types):
    alone = [x for x in ft if x['need'] >= x['hpbid']]
    kb_alone = sum(1 for x in kb if x['need'] >= x['hp'])
    print(f'{games} games; kill bids on acted targets {len(kb)} ({len(kb) / games:.2f} a game), our blow alone enough {kb_alone}')
    print(f'FT records (bound turns, we alive): {len(ft)}; our blow alone enough: {len(alone)}')
    out = Counter()
    miss = []
    for x in alone:
        # hp0 is read at our turn's start (-1: unseen or dead); alive/vis at its end, after our hits.
        if x['hp0'] < 0:
            out['target dead before our turn' if not x['alive'] else 'target unseen at our turn'] += 1
        elif x['stun']:
            out['we were stunned'] += 1
        elif x['acted']:
            out['target acted before us (seat lost)'] += 1
        elif not x['alive'] or x['hp1'] == 0:
            out['hit it (killed)'] += 1
        elif x['vis'] and x['hp1'] < x['hp0']:
            out['hit it (short)'] += 1
        else:
            out['did not hit it'] += 1
            miss.append(x)
    n = len(alone)
    print('\n## Outcome at the bound turn (our blow alone enough)')
    for k, v in out.most_common():
        print(f'  {k}: {pct(v, n)}')
    live = n - out['target dead before our turn'] - out['target unseen at our turn']
    print(f'  of those with the target alive at our turn: not hit {pct(len(miss), live)}')
    print(f'  not hit per game: {len(miss) / games:.3f}')

    print('\n## Not hit: by branch')
    br = Counter(x['branch'] for x in miss)
    for k, v in br.most_common():
        print(f'  {k}: {pct(v, len(miss))}')
    print('\n## Not hit: cause')
    cause = Counter()
    rows = []
    for x in miss:
        bit = 1 << x['t']
        if not x['vis']:
            c = 'target out of sight'
        elif x['branch'] == 'R':
            c = f"leave: {HOME.get(x['home'], x['home'])}"
        elif x['in_foes']:
            c = 'search: ' + search_cause(x, bit)
        else:
            c = f"no search (branch {x['branch']})"
        cause[c] += 1
        rows.append((c, x))
    for k, v in cause.most_common():
        print(f'  {k}: {pct(v, len(miss))}')

    leave = [x for x in miss if x['branch'] == 'R' and x['vis']]
    if leave:
        print(f'\n## Leave branch ({len(leave)})')
        print(f"  strike at distance >= target health (possible by distance): {pct(sum(x['strike'] >= x['hp0'] for x in leave), len(leave))}")
        print(f"  our start tile lethal: {pct(sum(x['lethal'] == 1 for x in leave), len(leave))}")
        print(f"  hit another enemy: {pct(sum(x['other'] > 0 for x in leave), len(leave))}")
        print(f"  our health share: mean {sum(x['our'] / x['ourmax'] for x in leave) / len(leave):.2f}; recall line mean {sum(x['line'] for x in leave) / len(leave):.2f}")
        print(f"  target distance: {Counter(x['d'] for x in leave).most_common()}")
        print(f"  target health share of our need: mean {sum(x['hp0'] / max(1, x['need']) for x in leave) / len(leave):.2f}")
    srch = [x for x in miss if x['branch'] != 'R' and x['vis'] and x['in_foes']]
    if srch:
        print(f'\n## Searched ({len(srch)})')
        print(f"  hit another enemy: {pct(sum(x['other'] > 0 for x in srch), len(srch))}")
        print(f"  node cap hit: {pct(sum(x['nodes'] >= 24 for x in srch), len(srch))}")
        print(f"  strike at distance >= target health: {pct(sum(x['strike'] >= x['hp0'] for x in srch), len(srch))}")
        print(f"  distance: {Counter(x['d'] for x in srch).most_common()}")
        ko = [x for x in srch if x['kok'] & (1 << x['t'])]
        if ko:
            print(f"  kill offered unguarded {len(ko)}: kill raw < chosen raw {sum(x['kraw'] < x['craw'] for x in ko)};"
                  f" kill priced {sum(x['kpriced'] for x in ko)}, its total < chosen {sum(x['kpriced'] and x['ktot'] < x['ctot'] for x in ko)}")
            print(f"    mean kill raw {sum(x['kraw'] for x in ko) / len(ko):.0f}, chosen raw {sum(x['craw'] for x in ko) / len(ko):.0f},"
                  f" chosen total {sum(x['ctot'] for x in ko) / len(ko):.0f}, kill total (priced) "
                  f"{sum(x['ktot'] for x in ko if x['kpriced']) / max(1, sum(x['kpriced'] for x in ko)):.0f}")
    # by champion type and round
    print('\n## Not hit: by our champion')
    ty = Counter(x['type'] for x in miss)
    for k, v in ty.most_common():
        print(f'  {k}: {pct(v, len(miss))}')
    live_t = Counter(x['type'] for x in alone if x['hp0'] > 0 and not x['stun'] and not x['acted'])
    print('  rate (not hit / bound turns with the target alive):', ', '.join(f"{k} {100 * v / live_t[k]:.0f}% of {live_t[k]}" for k, v in ty.most_common()))
    trib = [x for x in miss if x['branch'] == 'T']
    if trib:
        print(f'\n## Tribute kept ({len(trib)})')
        print(f"  by champion: {Counter(x['type'] for x in trib).most_common()}")
        print(f"  distance: {Counter(x['d'] for x in trib).most_common()}")
        print(f"  channel turns left at turn start: {Counter(x['channel'] for x in trib).most_common()}")
    if srch:
        oth = [x for x in srch if x['ckilled'] & ~(1 << x['t'])]
        print(f"\n## Searched: the chosen plan killed another enemy {pct(len(oth), len(srch))}")
        print(f"  by champion: {Counter(x['type'] for x in srch).most_common()}")
    print('\n## Not hit: by round')
    ph = Counter('1-300' if x['r'] <= 300 else '301-800' if x['r'] <= 800 else '801-1400' if x['r'] <= 1400 else '1401+' for x in miss)
    for k in ('1-300', '301-800', '801-1400', '1401+'):
        print(f'  {k}: {pct(ph[k], len(miss))}')
    return rows


def report_lw(games, lw, types):
    n = len(lw)
    print(f'\n# Champions within 4 of a low enemy (LW): {n} ({n / games:.1f} a game)')
    cls = Counter()
    sub = Counter()
    killable = Counter()
    for x in lw:
        bit = 1 << x['e']
        k = x['strike'] >= x['hp0']
        if x['hp1'] < x['hp0']:
            c = 'hit it'
        elif x['branch'] in ('T', 'K', 't', 'k', 'Q'):
            c = 'other: channel'
        elif x['branch'] == 'R':
            c = 'retreated'
            sub[('retreated', HOME.get(x['home'], x['home']) + (', start lethal' if x['lethal'] == 1 else ''))] += 1
        elif x['other'] > 0:
            c = 'chose another target'
            sub[('chose another target', search_cause(x, bit) if x['searches'] % 100 or x['hok'] | x['kok'] else 'no search')] += 1
        elif x['strike'] <= 0:
            c = "couldn't reach (distance)"
        elif (x['hok'] | x['kok']) & bit:
            c = 'reachable, chose no hit on it'
            sub[(c, search_cause(x, bit))] += 1
        elif (x['hg'] | x['kg']) & bit:
            c = 'only step-guarded tiles hit it'
        elif x['searches'] >= 100 or x['hok'] or x['kok'] or x['hg'] or x['kg']:
            c = "couldn't reach (no legal plan)"
        else:
            c = f"other: no search (branch {x['branch']})"
        cls[c] += 1
        killable[(c, k)] += 1
    for c, v in cls.most_common():
        print(f'  {c}: {pct(v, n)}; our modelled strike kills it {killable[(c, True)]}')
    print('  sub-causes:')
    for (c, s), v in sorted(sub.items(), key=lambda kv: -kv[1]):
        print(f'    {c} / {s}: {v}')
    miss = [x for x in lw if x['hp1'] >= x['hp0']]
    print(f'  hit nothing at all (neither it nor another): {pct(sum(x["other"] == 0 for x in miss), n)}')
    ty = Counter(x['type'] for x in miss if x['other'] == 0)
    print('  hit nothing, by champion:', ', '.join(f'{k} {v}' for k, v in ty.most_common()))


def main():
    args = sys.argv[1:]
    ex = None
    if args[0] == '--ex':
        ex, args = args[1], args[2:]
    games, kb, ft, lw, types = load(args, ex)
    report_ft(games, kb, ft, types)
    report_lw(games, lw, types)


if __name__ == '__main__':
    main()
