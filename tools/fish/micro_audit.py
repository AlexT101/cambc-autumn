"""Audit: forced vs free decisions in the Fish combat rules (COMBAT, TACTICS, DECISIONS, MICRO).

    python3 tools/fish/micro_audit.py OUT.json [--jobs N]

A row is forced when the rules (cambc-rules.yaml) leave only the predicted outcome legal, either
outright (stunned, respawn turn) or given another outcome of the same turn the rule conditions on
(walked -> no exclusive cast; the turn's one cast spent elsewhere; a ranged basic without a reset ->
no walk). A row is free when the alternative was legal. Each rule is re-scored on free rows, and
rules that condition on a same-turn outcome are restated as a turn-level choice from turn-start
state. All seven cohorts are pooled ('all'); the seventh is also reported alone.

Sources: COMBAT's own rows (replays/fish-combat/<c>-combat-v2), the micro rows
(replays/fish-micro/<c>-micro-v1) and the actor caches (heal and spawn opportunities).
"""
import argparse
import collections
import gzip
import json
import multiprocessing as mp
from pathlib import Path

import combat_rules as R
from breadth import RANGED, dist, spawn, xy
from combat_common import COHORTS, load
from misc_rows import spawn_tiles

COH = [c[0] for c in COHORTS]
NB = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
MELEE_T = {0, 2, 4, 7, 9, 10, 12}


class M:
    """Binary prediction metric with a constant baseline, per scope ('all', 'seventh')."""

    def __init__(self):
        self.c = collections.defaultdict(collections.Counter)

    def add(self, cohort, pred, actual, base):
        for s in ('all',) + (('seventh',) if cohort == 'seventh' else ()):
            c = self.c[s]
            c['n'] += 1; c['ok'] += pred == actual; c['base'] += base == actual; c['pos'] += bool(actual)

    def report(self):
        return {s: dict(n=c['n'], ok=c['ok'], acc=round(c['ok'] / c['n'], 4) if c['n'] else None,
                        base_ok=c['base'], base=round(c['base'] / c['n'], 4) if c['n'] else None,
                        positive=round(c['pos'] / c['n'], 4) if c['n'] else None) for s, c in self.c.items()}


def acceptable_start(x):
    # COMBAT's acceptable() at the start tile, from turn-start features only.
    return x['kill_self'] or (x['hpf'] > R.H_MIN and x['threat_ratio'] <= R.DANGER_MAX)


def combat_section(out):
    m = collections.defaultdict(M)
    cnt = collections.Counter()
    for name in COH:
        p = Path('replays/fish-combat') / f'{name}-combat-v2.jsonl.gz'
        for line in gzip.open(p, 'rt'):
            r = json.loads(line); x = r['x']; y = r['y']
            walks = y['moves'] > 0
            slots = [c['slot'] for c in y['casts']]
            kinds = y['kinds']
            # Exclusive unit damage spell (Cassi 0, Marcella 1, Prism 0; COMBAT's opportunity).
            s = R.damage_spell_opportunity(x)
            if s is not None:
                other = any(c != s for c in slots)
                actual = s in y['cast_champ']
                pred = (not walks) and not other
                m['C1 damage spell iff still: old (all rows)'].add(name, pred, actual, False)
                if walks or other:
                    m['C1 damage spell: forced rows (walked or cast spent)'].add(name, False, actual, False)
                    cnt['C1 forced: walked' if walks else 'C1 forced: other cast'] += 1
                else:
                    m['C1 damage spell: free rows (stood, cast unused) = always cast'].add(name, True, actual, False)
                # Turn level: ready + target within 4 at turn start -> cast it this turn?
                m['C1 turn-level: always cast (base never)'].add(name, True, actual, False)
                m['C1 turn-level: cast iff COMBAT-acceptable at the start tile (base never)'].add(
                    name, acceptable_start(x), actual, False)
            # Cassi's stun (not exclusive; one cast a turn shared with her exclusive damage spell).
            if R.cassi_stun_opportunity(x):
                actual = 1 in y['cast_champ']
                dmg_cast = 0 in slots
                pred = R.cassi_stun(x, walks)
                m['C2 Cassi stun unless still with damage ready: old (all rows)'].add(name, pred, actual, True)
                if dmg_cast:
                    m['C2 Cassi stun: forced rows (damage cast, the turn cast is spent)'].add(name, pred, actual, True)
                else:
                    m['C2 Cassi stun: free rows (no damage cast)'].add(name, pred, actual, True)
                    sub = 'walked' if walks else ('still, damage on cooldown' if x['cd'][0] else 'still, damage ready')
                    m[f'C2 Cassi stun: free rows, {sub}'].add(name, pred, actual, True)
                # Turn level, three outcomes by turn-start state.
                outcome = 'stun' if actual else ('damage' if 0 in y['cast_champ'] else 'none')
                st = 'damage ready' if x['cd'][0] == 0 else 'damage on cooldown'
                cnt[f'C2 turn-level: {st}: {outcome}'] += 1
                if x['cd'][0] == 0:
                    tl = 'damage' if acceptable_start(x) else 'stun'
                    m['C2 turn-level, both ready: damage iff COMBAT-acceptable, else stun (base: damage)'].add(
                        name, tl, outcome, 'damage')
                else:
                    m['C2 turn-level, damage on cooldown: always stun (base never)'].add(name, 'stun', outcome, 'none')
            # Heart of Ruin's shield (self, not exclusive; one cast a turn shared with its dash).
            if R.hor_shield_opportunity(x):
                actual = 0 in slots
                pred = R.hor_shield(x)
                m['C3 HoR shield iff threatened: old (all rows)'].add(name, pred, actual, False)
                if 1 in slots:
                    m['C3 HoR shield: forced rows (dash cast, the turn cast is spent)'].add(name, pred, actual, False)
                else:
                    m['C3 HoR shield: free rows (no dash)'].add(name, pred, actual, False)
                    m['C3 HoR shield: free rows, threatened'].add(name, True, actual, False) if pred else \
                        m['C3 HoR shield: free rows, not threatened'].add(name, False, actual, False)
            # Attack reset after a surviving basic (Vendetta, Issac, Marcella).
            rs = R.reset_opportunity(x, y)
            if rs is not None:
                actual = rs in slots
                other = any(c != rs for c in slots)
                if not other:
                    m['C4 reset after surviving basic: old (no other cast all turn)'].add(name, True, actual, False)
                ia = kinds.index('Attack') if 'Attack' in kinds else len(kinds)
                before = kinds[:ia].count('Cast ability')
                if before:
                    m['C4 reset: forced rows (cast spent before the basic)'].add(name, False, actual, False)
                else:
                    m['C4 turn-level: cast unused at the basic -> reset (alternatives: later other cast, none)'].add(
                        name, True, actual, False)
                    if other and not actual:
                        cnt['C4 free: other cast after the basic instead'] += 1
    out['combat'] = {k: v.report() for k, v in sorted(m.items())}
    out['combat_counts'] = dict(sorted(cnt.items()))


def actor_game(args):
    """Willow heal (DECISIONS) and spawn healing (TACTICS) opportunities from one actor cache."""
    name, cache, entry = args
    g = load(cache, entry)
    m = g['map']
    home = spawn(m, g['side'])               # breadth.spawn: the half-open spawn bounds (MISC correction)
    wide = spawn_tiles(m, g['side'])         # micro_rows used this widened set
    static = set(map(tuple, m['walls'] + m['holes'] + m['altars'])) | spawn(m, 1 - g['side'])
    C = collections.Counter()
    by = collections.defaultdict(list)
    for t in g['turns']:
        by[t['id']].append(t)
    for aid, ts in by.items():
        for i, t in enumerate(ts):
            s = t['start']; me = s['me']
            if not me['alive'] or 'x' not in me:
                continue
            pos = xy(me)
            done = t.get('finish') == 'End turn' and 'end' in t and 'x' in t['end']['me']
            stunned = any(b['type'] == 1 for b in me['buffs'])
            casts = [a['slot'] for a in t['actions'] if a['kind'] == 'Cast ability']
            en = [e for e in s['enemies'] if 'x' in e]
            if en and min(dist(pos, xy(e)) for e in en) <= 6:
                C['contact6 turns'] += 1
                C['contact6 turns on the widened ring (counted as spawn by micro_rows)'] += pos in wide and pos not in home
            # DECISIONS heal: eligible, cast flag, Willow heal ready, a visible ally within 4.
            if (me['type'] == 8 and done and not stunned and me['channelType'] in (0, 1) and me['roundFlags'] & 1024
                    and me['cd'][0] == 0):
                near = [c for c in s['allies'] if 'x' in c and dist(pos, xy(c)) <= 4]
                if near:
                    inj = any(c['hp'] < c['maxHp'] for c in near)
                    heal = 0 in casts
                    key = 'forced (reset cast: the turn cast is spent)' if 1 in casts else 'free'
                    for k in ('all', key):
                        C[('heal', k, 'n')] += 1
                        C[('heal', k, 'ok')] += inj == heal
                        C[('heal', k, 'always heal ok')] += heal
                        if inj:
                            C[('heal', k, 'injured n')] += 1
                            C[('heal', k, 'injured healed')] += heal
            # TACTICS spawn: alive start on own spawn, short of full health, completed, not channelling a
            # tribute or teleport, an off-spawn neighbour free. Label: ends off the spawn.
            if pos in home and done and me['channelType'] in (0, 1) and me['hp'] < me['maxHp']:
                occ = {xy(c) for c in s['allies'] + en if 'x' in c}
                free_nb = [(pos[0] + dx, pos[1] + dy) for dx, dy in NB
                           if 0 <= pos[0] + dx < m['width'] and 0 <= pos[1] + dy < m['height']
                           and (pos[0] + dx, pos[1] + dy) not in static | home | occ]
                if free_nb:
                    left = xy(t['end']['me']) not in home
                    prev_dead = i > 0 and not ts[i - 1]['start']['me']['alive']
                    key = 'forced (stunned or respawn turn: cannot walk)' if stunned or prev_dead else 'free'
                    for k in ('all', key):
                        C[('spawn', k, 'n')] += 1
                        C[('spawn', k, 'stays')] += not left
    return name, C


def actor_section(out, jobs):
    tasks = []
    for name, manifest, cache in COHORTS:
        tasks += [(name, cache, e) for e in json.loads(Path(manifest).read_text())]
    tot = collections.defaultdict(collections.Counter)
    with mp.Pool(min(jobs, 6)) as pool:
        for name, C in pool.imap_unordered(actor_game, tasks, chunksize=4):
            tot['all'].update(C)
            if name == 'seventh':
                tot['seventh'].update(C)
    out['actor'] = {s: {' | '.join(map(str, k)) if isinstance(k, tuple) else k: v for k, v in sorted(c.items(), key=str)}
                    for s, c in tot.items()}


def micro_section(out):
    m = collections.defaultdict(M)
    cnt = collections.Counter()
    for name in COH:
        p = Path('replays/fish-micro') / f'{name}-micro-v1.jsonl.gz'
        for line in gzip.open(p, 'rt'):
            r = json.loads(line)
            acts = r['y']['acts']
            walked = any(a[0] == 'Move' for a in acts)
            slots = [a[2] for a in acts if a[0] == 'Cast ability']
            if not r['done'] or r['stunned'] or r['at_home']:
                continue
            near4 = [e for e in r['enemies'] if e['d'] <= 4]
            # Prism (both spells exclusive) and Ren (stun exclusive).
            if r['type'] in (6, 9) and near4 and r['ch'] in (0, 1):
                nm = 'Prism' if r['type'] == 6 else 'Ren'
                ready = [s for s in ((0, 1) if r['type'] == 6 else (0,)) if r['cd'][s] == 0]
                if ready:
                    cast = any(s in slots for s in ready)
                    other = any(s not in ready for s in slots)
                    pred = not walked and not other
                    m[f'M1 {nm} cast iff still: old-style (all rows)'].add(name, pred, cast, False)
                    if walked or other:
                        m[f'M1 {nm}: forced rows (walked or cast spent)'].add(name, False, cast, False)
                    else:
                        m[f'M1 {nm}: free rows (stood) = always cast'].add(name, True, cast, False)
                    m[f'M1 {nm} turn-level: always cast (base never)'].add(name, True, cast, False)
                    if r['type'] == 6 and r['cd'] == [0, 0] and not walked and cast:
                        m['M1 Prism both ready, stood and cast: slot 0 (free slot choice)'].add(name, 0, min(s for s in slots if s in (0, 1)), 1)
            # Marcella's reset-stun re-hit.
            if r['type'] == 7:
                bs = {b['step']: b for b in r['y']['b']}
                for i, a in enumerate(acts):
                    if a[0] == 'Cast ability' and a[2] == 0:
                        nxt = next((y for y in acts[i + 1:] if y[0] == 'Attack'), None)
                        prv = next((y for y in reversed(acts[:i]) if y[0] == 'Attack'), None)
                        if not nxt or not prv or nxt[4] not in bs or prv[4] not in bs:
                            continue
                        b, pb = bs[nxt[4]], bs[prv[4]]
                        tgt = next((e[0] for e in b['en'] if [e[1], e[2]] == nxt[1]), None)
                        first = next((e[0] for e in pb['en'] if [e[1], e[2]] == prv[1]), None)
                        if tgt is None or first is None:
                            continue
                        cand = [e for e in b['en'] if dist(b['pos'], (e[1], e[2])) <= 1]
                        mn = min(cand, key=lambda e: (e[3] + e[4], e[0]))[0]
                        if len(cand) < 2:
                            m['M2 Marcella re-hit: forced rows (one enemy in range)'].add(name, first, tgt, first)
                        else:
                            m['M2 Marcella re-hit: free rows (2+ in range), same as first'].add(name, first, tgt, mn)
                            if mn != first:
                                m['M2 Marcella re-hit: meaningful (min-EHP is another enemy), same as first'].add(name, first, tgt, mn)
            # Melee walks and ends adjacent: "adjacent to the weakest reachable enemy". Coupled to the
            # target rule when it walks and then hits that enemy (melee range 1 makes the end tile adjacent).
            if r['type'] not in RANGED and walked and r['ch'] in (0, 1) and r['y']['end'] and not any(
                    a[0] == 'Cast ability' and a[3] == 6 for a in acts) and min(e['d'] for e in r['enemies']) <= 5:
                live = r['enemies']
                tiles = [tuple(t[:2]) for t in r['tiles']]
                end = tuple(r['y']['end'])
                dn = lambda q: min(dist(q, (e['x'], e['y'])) for e in live)
                adj = [q for q in tiles if dn(q) <= 1]
                if end in tiles and dn(end) <= 1 and len(adj) >= 2:
                    reach = [e for e in live if any(dist(q, (e['x'], e['y'])) <= 1 for q in adj)]
                    w = min(reach, key=lambda e: (e['hp'] + e['sh'], e['id']))
                    vals = [dist(q, (w['x'], w['y'])) <= 1 for q in adj]
                    if any(vals) and not all(vals):
                        last_move = max(a[4] for a in acts if a[0] == 'Move')
                        hit_after = any(a['step'] > last_move and any(c['id'] == w['id'] and c['foe'] and c['dmg'] > 0
                                                                      for c in a['champs']) for a in r['y']['eff'])
                        ok = dist(end, (w['x'], w['y'])) <= 1
                        key = 'coupled (hits the weakest after its last step)' if hit_after else 'free (no hit on it after the step)'
                        for k in ('all', key):
                            cnt[f'M6 melee engage beside weakest: {k}: n'] += 1
                            cnt[f'M6 melee engage beside weakest: {k}: ok'] += ok
                            cnt[f'M6 melee engage beside weakest: {k}: random x1000'] += round(1000 * sum(vals) / len(vals))
            # Ranged end distance to melee: forced when a basic attack without a reset ruled out walking.
            if r['type'] in RANGED and r['ch'] in (0, 1):
                melee = [e for e in r['enemies'] if e['type'] in MELEE_T]
                if melee and min(e['d'] for e in r['enemies']) <= 5 and r['y']['end']:
                    attacked = any(a[0] == 'Attack' for a in acts)
                    reset = any(a[0] == 'Cast ability' and a[3] == 1 for a in acts)
                    end = tuple(r['y']['end'])
                    dm = min(dist(end, (e['x'], e['y'])) for e in melee)
                    tiles = [tuple(t[:2]) for t in r['tiles']]
                    share = sum(min(dist(q, (e['x'], e['y'])) for e in melee) >= 3 for q in tiles) / len(tiles)
                    forced = attacked and not reset and not walked
                    key = 'forced (attacked, no reset: could not walk)' if forced else 'free'
                    for k in ('all', key):
                        cnt[f'M4 ranged end >= 3 from melee: {k}: n'] += 1
                        cnt[f'M4 ranged end >= 3 from melee: {k}: ok'] += dm >= 3
                        cnt[f'M4 ranged end >= 3 from melee: {k}: random tile x1000'] += round(1000 * share)
                    # Turn level: a melee enemy within 2 at start and a tile >= 3 from every melee enemy.
                    if min(e['d'] for e in melee) <= 2 and share > 0:
                        m['M5 ranged, melee within 2 at start, escape tile exists: ends >= 3 (turn level, base: stays within 2)'].add(
                            name, True, dm >= 3, False)
    # Kill securing, restated: does the first capable actor kill?
    f = json.loads(Path('research/fish-2026-11-05/micro-focus.json').read_text())['tallies']
    ks = {}
    for s, c in f.items():
        ks[s] = dict(killable=c['killable_n'], died=c['killable_died_this_round'],
                     killer_first_capable=c['killable_killer_is_first_capable'],
                     old_share_of_deaths=round(c['killable_killer_is_first_capable'] / c['killable_died_this_round'], 4),
                     first_capable_kills=round(c['killable_killer_is_first_capable'] / c['killable_n'], 4))
    out['micro'] = {k: v.report() for k, v in sorted(m.items())}
    out['micro_counts'] = dict(sorted(cnt.items()))
    out['kill_securing'] = ks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--jobs', type=int, default=6)
    a = p.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f'refusing to overwrite {a.out}')
    out = dict(cohorts=COH)
    combat_section(out)
    micro_section(out)
    actor_section(out, a.jobs)
    Path(a.out).write_text(json.dumps(out, indent=1))
    for sec in ('combat', 'micro'):
        for k, v in out[sec].items():
            d = v['all']
            print(f"{k}: {d['ok']}/{d['n']} ({100 * d['acc']:.1f}%, base {100 * d['base']:.1f}%, positive {100 * d['positive']:.1f}%)")
    for k, v in out['combat_counts'].items():
        print(k, v)
    for k, v in out['micro_counts'].items():
        print(k, v)
    print(out['kill_securing'])
    for k, v in out['actor']['all'].items():
        print(k, v)


if __name__ == '__main__':
    main()
