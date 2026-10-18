"""Turn-by-turn trace of a game window.

py research/hecate/losses/trace.py GAME_DIR R0 R1 [--near ID] [--radius 12]
Per round: tributed gems, then every champion (within --radius of --near, if given): position, hp/max,
carried gems, channel, what it did (events) and which enemies it saw at its turn start.
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import Game  # noqa


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('game')
    ap.add_argument('r0', type=int)
    ap.add_argument('r1', type=int)
    ap.add_argument('--near', type=int)
    ap.add_argument('--radius', type=int, default=12)
    ap.add_argument('--groups', action='store_true')
    a = ap.parse_args()
    g = Game(a.game)
    cg = {c['id']: c['group'] for c in g.map.raw['camps']}
    evs = collections.defaultdict(list)
    for e in g.events:
        if a.r0 <= e['r'] <= a.r1:
            evs[e['r']].append(e)
    bush = g.map.bushes
    print(g, 'teams', g.names, 'winner', g.winner)
    for c in g.champs:
        print(f"  {c['id']}: team {c['team']} {c['name']}")
    for r in range(a.r0, a.r1 + 1):
        i = r - 1
        if i >= len(g.rounds['round']):
            break
        print(f"--- r{r} gems A {g.gems_at(0, r)} B {g.gems_at(1, r)}")
        centre = g.pos(a.near, i) if a.near is not None else None
        acts = collections.defaultdict(list)
        for e in evs[r]:
            k = e['k']
            if k in ('recall_start',) and e.get('gems', 0) >= 0 and False:
                continue
            if k == 'move':
                acts[e['a']].append(f"mv{tuple(e['to'])}")
            elif k in ('attack', 'cast'):
                tag = 'atk' if k == 'attack' else f"cast:{e.get('ab')}"
                if e.get('camp') is not None:
                    tag += f" camp{e['camp']}(g{cg[e['camp']]})"
                if e.get('dmg'):
                    tag += ' ' + ','.join(f"{g.name_of.get(v, v)}#{v}-{round(d)}" for v, d in e['dmg'])
                if e.get('stun'):
                    tag += f" STUN{e['stun']}"
                if e.get('moved'):
                    tag += f" ->{tuple(e['moved'])}"
                acts[e['a']].append(tag)
            elif k == 'camp_attack':
                if e.get('tgt') is not None:
                    acts[e['tgt']].append(f"hit-by-camp(g{e['g']})-{e['dmg']}")
            elif k == 'death':
                acts[e['v']].append(f"DIED by {g.name_of.get(e.get('by'), 'camp')} bag{e.get('gems')}")
            elif k in ('recall_start', 'recall_cancel'):
                if k == 'recall_cancel' and e.get('cause') != 'manual':
                    acts[e['a']].append(f"recall-cancel({e.get('cause')},left{e.get('left')})")
            elif k in ('tribute_start', 'tribute_end', 'tribute_cancel', 'recall_end', 'shop', 'ward', 'lock_place', 'tribute_blocked', 'respawn'):
                acts[e['a']].append(k + ('' if k in ('ward',) else f"({e.get('gems', e.get('items', ''))})"))
            elif k in ('capture_hold', 'capture_reset', 'capture', 'group_clear', 'group_wake'):
                print(f"   [{k} g{e['g']} {g.map.group_label(e['g'])} team{e.get('team', '')} {e.get('shares', '')}{' contested' if e.get('contested') else ''}]")
        for c in g.champs:
            cid = c['id']
            ch = g.ch(cid)
            p = g.pos(cid, i)
            if centre and p and cheb(p, centre) > a.radius and cid != a.near:
                continue
            if centre and not p and not acts.get(cid):
                continue
            chan = ch['chan'][i]
            chan_s = {1: f"rec{ch['chanT'][i]}", 2: f"TRIB{ch['chanT'][i]}", 3: 'tp'}.get(chan, '')
            if chan == 1 and ch['chanT'][i] >= 4:
                chan_s = ''
            sees = ch['sees'][i] or []
            print(f"  {c['team']} {c['name'][:7]:7}#{cid:<2} {str(p) if p else 'dead':10}{'*' if p in bush else ' '} hp{round(ch['hp'][i] or 0):5}/{round(ch['maxHp'][i] or 0):<5} g{ch['gems'][i]:<4} {chan_s:6} sees{sees} {' | '.join(acts.get(cid, []))}")


if __name__ == '__main__':
    main()
