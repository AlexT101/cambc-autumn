"""s2: tables of our Prism's kill chances from pk_join.py's rows.

    python research/mac13-kronos/s2/report.py [rows.jsonl.gz] > research/mac13-kronos/s2/tables.md

A chance is a PK row: our Prism's turn start with a visible enemy non-Prism within 6 whose (health + shield) / taken is
under 2.5x our Focus. An episode is the chances on one target from its first, deduplicated per 10 rounds (a new episode
starts 10+ rounds after the last episode's start). Converted: the target (or its linked body) died within 8 rounds of
the episode's start. Its state and our turn are read at the episode's first chance unless a table says otherwise.
"""
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATH = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'replays' / 'mac13-kronos-s2-pk.jsonl.gz')

EXIT = {'T': 'tribute kept', 'K': 'recall kept', 'z': 'stunned', 'E': 'stop game-ender', 's': 'Prism-Willow support',
        'r': 'support retreat', 'H': 'mend on spawn', 'L': 'want_home retreat', 'M': 'join Marcella', 'Y': 'yield capture',
        'O': 'capture handoff', 'y': 'after search (dead/yield)', 'P': 'hold capture', 'f': 'goal fuel-short', 'B': 'carry_bag',
        'i': 'sealed in', 'w': 'wake ring', '$': 'shop trip', 'U': 'altar guard', 'C': 'chase', 'X': 'contest', 'g': 'farm fuel-short',
        'G': 'siege/kite', 'F': 'farm', 'p': 'teleporting', '-': 'other (Willow follow / no end)'}
GATE = {'C': 'chosen', 'c': 'chosen (comeback, fight lost)', 'P': 'chosen (we pressed it)', 'Q': 'chosen (team pressed it)',
        'v': 'refused: near its spawn / out of sight', 't': 'refused: teleporting away', 'h': 'refused: healthy (>=45%) off our ground, no bag/hold',
        'k': 'refused: pack covers it', 'L': 'refused: fight sim lost', 'F': 'refused: fight sim, linked body falls',
        'l': 'refused: fight already lost (same fight)', 'e': 'refused: escapes (chase verdict)', 'f': 'refused: fuel cut',
        'o': 'another target chosen first', '.': 'prey() not run', 'W': '?', '?': 'no end line'}


def load():
    rows, games = [], set()
    with gzip.open(PATH, 'rt') as f:
        for line in f:
            r = json.loads(line)
            games.add(r['game'])
            if not r.get('empty'):
                rows.append(r)
    return rows, games


def episodes(rows):
    by = defaultdict(list)
    for r in rows:
        by[(r['game'], r['id'], r['tgt'])].append(r)
    out = []
    for k, rs in by.items():
        rs.sort(key=lambda r: r['round'])
        cur = None
        for r in rs:
            if cur is None or r['round'] >= cur[0]['round'] + 10:
                cur = [r]
                out.append(cur)
            else:
                cur.append(r)
    return out


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '-'


def table(title, keyf, eps, tg, note='', top=None, labels=None):
    c, conv, prism = Counter(), Counter(), Counter()
    for ep in eps:
        k = keyf(ep)
        if k is None:
            continue
        c[k] += 1
        conv[k] += ep_conv(ep)
        prism[k] += ep_prism(ep)
    print(f'\n### {title}\n')
    if note:
        print(note + '\n')
    print('| key | per team-game | converted | by our Prism | missed per team-game |')
    print('|---|---|---|---|---|')
    items = sorted(c.items(), key=lambda kv: -kv[1])
    if top:
        items = items[:top]
    for k, n in items:
        lab = labels.get(k, k) if labels else k
        print(f'| {lab} | {n / tg:.2f} | {pct(conv[k], n)} | {pct(prism[k], n)} | {(n - conv[k]) / tg:.2f} |')
    n = sum(c.values())
    print(f'| all | {n / tg:.2f} | {pct(sum(conv.values()), n)} | {pct(sum(prism.values()), n)} | {(n - sum(conv.values())) / tg:.2f} |')


def ep_conv(ep):
    return int(ep[0]['dead_r'] is not None)


def ep_prism(ep):
    return int(ep[0]['dead_r'] is not None and ep[0]['killer_us'])


def dist_ctx(r):
    d = r['d0']
    db = '<=3' if d <= 3 else str(d)
    stun = 'stun ready' if r['cd0'] == 0 else 'stun down'
    pr = 'enemy Prism within 8' if 0 <= r['prism_d'] <= 8 else 'no enemy Prism within 8'
    return f'd {db}, {stun}, {pr}'


def gate(r):
    return r.get('shadow', '?')


def cause(ep):
    """The primary cause of a missed episode, from its first turn (the onset) and what followed."""
    r = ep[0]
    ex = r.get('exit', '-')
    hit = any(x['our_dmg'] > 0 for x in ep)
    if r['stunned'] or ex == 'z':
        return 'we were stunned'
    if ex == 'T':
        return 'tribute channel kept'
    if ex == 'K':
        return 'recall kept'
    if ex in ('L', 'r', 'H'):
        return 'want_home / retreat'
    if ex == 'B':
        g = gate(r)
        if g in ('C', 'c', 'P', 'Q'):
            return 'carry_bag: gate would chase, carry_bag did not ask'
        return 'carry_bag: gate refuses too'
    if ex == 'C' or r.get('real') in ('C', 'c', 'P', 'Q'):
        return 'chased, no kill'
    g = gate(r)
    if g in ('C', 'c', 'P', 'Q'):
        return f'gate would chase, other branch ({EXIT.get(ex, ex)})'
    return 'gate refused: ' + GATE.get(g, g).replace('refused: ', '')


def main():
    rows, games = load()
    # Team-games: each game has one traced team.
    tg = len(games)
    print(f'# s2 tables\n\n{len(rows)} chance turns over {tg} traced team-games ({len(rows) / tg:.1f} a team-game).')
    no_end = sum(1 for r in rows if not r.get('has_end'))
    print(f'Turns without an end line (ran out of fuel, or stale): {no_end} ({pct(no_end, len(rows))}).')
    eps = episodes(rows)
    n = len(eps)
    conv = sum(ep_conv(e) for e in eps)
    pk = sum(ep_prism(e) for e in eps)
    print(f'\n**Episodes** (per target per 10 rounds): {n / tg:.2f} a team-game; converted {conv / tg:.2f} ({pct(conv, n)}), '
          f'by our Prism {pk / tg:.2f}.')
    # Killed by whom.
    kt = Counter(e[0]['killer_type'] if e[0]['killer_team'] else ('their side' if e[0]['dead_r'] is not None else None) for e in eps)
    kt.pop(None, None)
    print('Killers of converted episodes: ' + ', '.join(f'{k} {v / tg:.2f}' for k, v in kt.most_common()))
    traced_kills = Counter()
    table('By distance, stun and enemy Prism (onset)', lambda e: dist_ctx(e[0]), eps, tg)
    table('By our branch at the onset (decide exit)', lambda e: EXIT.get(e[0].get('exit', '-'), e[0].get('exit')), eps, tg)
    table('By the chase gate at the onset (prey() asked at decide start)', lambda e: GATE.get(gate(e[0]), gate(e[0])), eps, tg)
    table('Primary cause', cause, eps, tg,
          note='Onset branch first (channels, retreats, the bag), then whether a chase ran, then the gate verdict.')
    # Our Prism's channel at onset.
    table('Our channel at onset (a recall is restarted every turn end and usually cancelled)',
          lambda e: {0: 'none', 1: 'tribute', 2: 'recall (feint or kept)', 3: 'teleport'}[e[0]['ch']], eps, tg)
    table('Target turns before our next turn (engine order)', lambda e: str(e[0]['tgt_turns']), eps, tg)
    table('Target type', lambda e: e[0]['ttype'], eps, tg)
    table('Target channel at onset', lambda e: {0: 'none', 1: 'recall', 2: 'tribute', 3: 'teleport'}.get(e[0]['echan'], '?'), eps, tg)
    table('Target on its own side (own_ground false = their side)', lambda e: 'our side' if e[0]['own_ground'] else 'their side', eps, tg)
    table('Target in bush / we in bush', lambda e: f"target bush {e[0]['ebush']}, us bush {e[0]['mebush']}", eps, tg)
    table('Our bag at onset', lambda e: '0' if e[0]['gems'] == 0 else '1-49' if e[0]['gems'] < 50 else '50-149' if e[0]['gems'] < 150 else '150+', eps, tg)
    table('Target health share at onset', lambda e: f"{min(9, int(10 * e[0]['hp'] / max(1, e[0]['maxhp']))) * 10}%+", eps, tg)
    table('Burst margin (our stun+ground raw / target effective hp)', lambda e: (lambda m: '<1.2' if m < 1.2 else '1.2-1.6' if m < 1.6 else '1.6-2.5' if m < 2.5 else '2.5+')(e[0]['burst'] / max(1, e[0]['ehp'])), eps, tg)
    # Missed: what the target did and where it was at our next turn.
    missed = [e for e in eps if not ep_conv(e)]
    print(f'\n## Missed episodes ({len(missed) / tg:.2f} a team-game)')
    table('Missed: primary cause x target turns before our next', lambda e: f"{cause(e)} | {e[0]['tgt_turns']}", missed, tg, top=30)
    table('Missed: what the target did before our next turn (onset)', lambda e: e[0]['tgt_did'] or 'nothing', missed, tg, top=15)
    table('Missed: distance at our next turn (onset d -> next d)', lambda e: f"{e[0]['d0']} -> {e[0]['d_next']}", missed, tg, top=20)
    table('Missed: did our Prism damage it in the 8 rounds', lambda e: ('stun hit, ' if any(x['our_stun_hits'] for x in e) else '') + ('hit' if e[0]['our_dmg'] > 0 else 'no hit'), missed, tg)
    table('Missed: healed / shielded by its side in the 8 rounds', lambda e: f"healed {int(e[0]['heal_in'] > 0)}, shield {int(e[0]['shield_in'] > 0)}", missed, tg)
    table('Missed: we died within 8 rounds', lambda e: str(int(e[0]['me_dead_r'] is not None)), missed, tg)
    # Gate refusals for the far chances.
    table('Gate verdict x distance (onset)', lambda e: f"{GATE.get(gate(e[0]), gate(e[0]))} | d {e[0]['d0']}", eps, tg, top=30)
    table('Exit x gate (onset)', lambda e: f"{EXIT.get(e[0].get('exit', '-'), '?')} | {GATE.get(gate(e[0]), gate(e[0]))}", eps, tg, top=30)
    # Turn-level: of all chance turns, what share had the gate choose the target and the real chase run.
    print('\n## Chance turns (not deduplicated)\n')
    c = Counter((r.get('exit', '-'), r.get('real', '?'), r.get('shadow', '?')) for r in rows)
    print('| exit | real prey verdict | shadow verdict | per team-game |\n|---|---|---|---|')
    for (ex, re_, sh), k in c.most_common(25):
        print(f'| {EXIT.get(ex, ex)} | {GATE.get(re_, re_)} | {GATE.get(sh, sh)} | {k / tg:.2f} |')
    # Validation: the bot's turn windows vs the engine order.
    v = Counter((r['after'] + r['before_next'], r['tgt_turns']) for r in rows)
    print('\nBot predicted target turns (may act after us + before ours next) vs engine order: '
          + ', '.join(f'{a}->{b}: {k}' for (a, b), k in sorted(v.items())))


if __name__ == '__main__':
    main()


def acted(ep):
    """Our Prism went for the target on the onset turn: a chase, a spell cast, or a step closer."""
    r = ep[0]
    return r.get('exit') == 'C' or r.get('c0', 0) > 0 or r.get('c1', 0) > 0 or (0 <= r.get('d_end', 99) < r['d0'])


def stratum(ep):
    r = ep[0]
    return (min(max(r['d0'], 3), 6), r['cd0'] == 0, 0 <= r['prism_d'] <= 8)


def sizing(eps, tg):
    """Per cause: kills a team-game if its onset turns had acted at the rate of acting turns in the same stratum
    (distance 3-/4/5/6, stun ready, enemy Prism within 8). An upper bound: the acting turns are selected (the
    strike search or the gate took them because they looked good)."""
    act_n, act_c = Counter(), Counter()
    for e in eps:
        if acted(e):
            s = stratum(e)
            act_n[s] += 1
            act_c[s] += ep_conv(e)
    rate = {s: act_c[s] / act_n[s] for s in act_n if act_n[s] >= 30}
    by = defaultdict(lambda: [0, 0, 0.0])
    for e in eps:
        if acted(e):
            continue
        k = cause(e)
        s = stratum(e)
        by[k][0] += 1
        by[k][1] += ep_conv(e)
        by[k][2] += max(0.0, rate.get(s, 0) - 0) - ep_conv(e)
    print('\n### Sizing: onset turns that did not act on the target, against acting turns in the same stratum\n')
    print('Acting turns (chase, cast or step in at onset) by stratum: '
          + ', '.join(f'd{s[0]}{" stun" if s[1] else ""}{" eP" if s[2] else ""} {100 * rate[s]:.0f}%' for s in sorted(rate)) + '.\n')
    print('| cause (onset turn did not act) | per team-game | converted | acting-rate conversion | added kills per team-game (upper bound) |')
    print('|---|---|---|---|---|')
    for k, (n, c, add) in sorted(by.items(), key=lambda kv: -kv[1][2]):
        if n / tg < 0.05:
            continue
        print(f'| {k} | {n / tg:.2f} | {pct(c, n)} | {pct(c + add, n)} | {add / tg:+.2f} |')
    n = sum(v[0] for v in by.values())
    print(f'| all | {n / tg:.2f} | {pct(sum(v[1] for v in by.values()), n)} | {pct(sum(v[1] + v[2] for v in by.values()), n)} | {sum(v[2] for v in by.values()) / tg:+.2f} |')


if __name__ == '__main__' and len(sys.argv) > 2 and sys.argv[2] == '--sizing':
    _rows, _games = load()
    sizing(episodes(_rows), len(_games))


def windows(rows, tg):
    """Lethal windows by turn (each target counted once per 10 rounds): the burst (stun + ground, raw) beats its effective hp."""
    seen, firsts = {}, defaultdict(list)
    lethal = lambda r: r['ehp'] < r['burst']
    kinds = [('d<=4, stun ready, ground back by our next turn', lambda r: r['d0'] <= 4 and r['cd0'] == 0 and r['cd1'] <= 1),
             ('d5, stun ready, ground back by our next turn', lambda r: r['d0'] == 5 and r['cd0'] == 0 and r['cd1'] <= 1),
             ('d6, stun ready', lambda r: r['d0'] == 6 and r['cd0'] == 0)]
    for r in sorted(rows, key=lambda r: (r['game'], r['id'], r['tgt'], r['round'])):
        if not lethal(r):
            continue
        for name, f in kinds:
            if not f(r):
                continue
            k = (name, r['game'], r['id'], r['tgt'])
            if k in seen and r['round'] < seen[k] + 10:
                continue
            seen[k] = r['round']
            firsts[name].append(r)
    print('\n### Lethal windows (burst > effective hp), first turn per target per 10 rounds\n')
    print('| window | onset branch / what we did | per team-game | converted |\n|---|---|---|---|')
    for name, _ in kinds:
        rs = firsts[name]
        conv = sum(r['dead_r'] is not None for r in rs)
        print(f'| **{name}** | all | {len(rs) / tg:.2f} | {pct(conv, len(rs))} |')
        c, cv = Counter(), Counter()
        for r in rs:
            did = 'stun' if r.get('c0') else 'ground' if r.get('c1') else 'step in' if 0 <= r.get('d_end', 99) < r['d0'] else 'no act'
            k = f"{EXIT.get(r.get('exit', '-'), '?')}, {did}"
            c[k] += 1
            cv[k] += r['dead_r'] is not None
        for k, n in c.most_common(6):
            print(f'| | {k} | {n / tg:.2f} | {pct(cv[k], n)} |')
    # The bot's next-round window for the target against the engine's order.
    v = Counter()
    for r in rows:
        if r['slot_me'] is None or r['slot_tg'] is None:
            continue
        v[(r['before_next'], r['tgt_turns'] - int(r['slot_tg'] > r['slot_me']))] += 1
    print('\n### enemy_turn_before_ours_next for the target vs the engine order (chance turns)\n')
    print('| bot says | engine: acts before our next turn | engine: does not |\n|---|---|---|')
    for b in (1, 0):
        print(f'| {"acts" if b else "does not act"} | {v[(b, 1)]} | {v[(b, 0)]} |')
    print('\n`enemy_may_act_after_us` (this round) matched the engine on every chance turn.')


if __name__ == '__main__' and len(sys.argv) > 2 and sys.argv[2] == '--windows':
    _rows, _games = load()
    windows(_rows, len(_games))
