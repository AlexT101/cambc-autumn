"""Turn-by-turn timeline of a game: py timeline.py <analysis dir | ladder folder/pos-map> <r0> <r1> [team]"""
import sys
from collections import defaultdict

from common import Game, chebyshev, games


def resolve(arg):
    if len(arg) == 16 and '/' not in arg:
        return arg, None
    for r in games(since='2026-10-01', need_top=False):
        if f"{r['folder']}/{r['pos']}-{r['map']}".startswith(arg) or arg.endswith(f"{r['folder']}/{r['pos']}-{r['map']}"):
            return r['dir'], r['names']
    raise SystemExit('not found')


def main():
    d, names = resolve(sys.argv[1])
    r0, r1 = int(sys.argv[2]), int(sys.argv[3])
    g = Game(d)
    if names:
        g.names = names
    M = g.map
    print(g.map_name, g.names, 'winner', g.winner, 'rounds', g.n_rounds, 'spawns', M.spawn, 'altars', M.altars)
    camp_pos = {c['id']: (c['x'], c['y'], c['type'][:2], c['group']) for c in M.camps}
    acts = defaultdict(list)
    for e in g.events:
        if not (r0 <= e['r'] <= r1):
            continue
        k = e['k']
        a = e.get('a')
        if k == 'move':
            acts[(e['r'], a)].append(f"mv{tuple(e['to'])}")
        elif k in ('attack', 'cast'):
            s = 'atk' if k == 'attack' else e.get('ab', 'cast')
            tgt = ''
            if 'tgt' in e and e['tgt'] != a:
                tgt = f"->{g.name_of.get(e['tgt'], e['tgt'])}#{e['tgt']}"
            if 'camp' in e:
                cp = camp_pos.get(e['camp'])
                tgt += f"->camp{cp[2]}{cp[:2]}" if cp else ''
            if e.get('lock'):
                tgt += '->LOCK'
            dm = ''
            if e.get('dmg'):
                dm = ' dmg' + ','.join(f'{v}:{x:.0f}' for v, x in e['dmg'])
            if e.get('cdmg'):
                dm += ' cdmg' + ','.join(f'{x:.0f}' for v, x in e['cdmg'])
            if e.get('stun'):
                dm += f" STUN{e['stun']}"
            if e.get('moved'):
                dm += f" to{tuple(e['moved'])}"
            acts[(e['r'], a)].append(f"{s}{tgt}{dm}")
        elif k in ('recall_start', 'recall_end', 'tribute_start', 'tribute_end', 'ward', 'shop', 'lock_place', 'recall_cancel', 'tribute_cancel', 'consumable', 'tribute_blocked'):
            extra = e.get('gems', '')
            if k == 'ward':
                extra = tuple(e['to'])
            if k == 'shop':
                extra = e.get('items')
            if k.endswith('cancel'):
                extra = f"{e.get('cause')} {e.get('gems')}"
            acts[(e['r'], a)].append(f"{k}:{extra}")
        elif k == 'death':
            acts[(e['r'], e['v'])].append(f"DIED by {e.get('by')} gems{e['gems']}")
        elif k in ('group_clear', 'capture', 'capture_hold', 'capture_reset', 'group_wake', 'group_sleep', 'group_respawn'):
            gi = e['g']
            t0 = M.groups[gi]['tiles'][0]
            extra = f" team{e.get('team')}" if 'team' in e else ''
            extra += f" by{e.get('by')}" if 'by' in e else ''
            acts[(e['r'], 'g')].append(f"{k} g{gi}@{tuple(t0)}{extra}")
    for r in range(r0, r1 + 1):
        i = r - 1
        print(f'--- r{r} gems {g.gems_at(0, r)}-{g.gems_at(1, r)}', '; '.join(acts.get((r, 'g'), [])))
        for c in g.champs:
            cid = c['id']
            if len(sys.argv) > 4 and str(g.team_of[cid]) != sys.argv[4]:
                continue
            ch = g.ch(cid)
            if i >= len(ch['x']):
                continue
            p = (ch['x'][i], ch['y'][i]) if ch['alive'][i] else None
            bush = '~' if p in M.bushes else ''
            sees = ch['sees'][i] or []
            print(f"  {'AB'[c['team']]} {c['name'][:6]:6}#{cid:<2} {str(p):10}{bush:1} hp{ch['hp'][i]:6.0f}/{ch['maxHp'][i]:<5.0f} g{ch['gems'][i]:<4} $"
                  f"{ch['gold'][i]:<4} sees{sees} | " + ' '.join(acts.get((r, cid), [])))


if __name__ == '__main__':
    main()
