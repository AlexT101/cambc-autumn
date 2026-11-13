"""s2: join our Prism's kill chances (PK trace lines) with what happened next.

    python research/mac13-kronos/s2/pk_join.py BATCH_DIR [--out rows.jsonl.gz] [--threads N]

BATCH_DIR must be extracted first (node tools/replay/extract.mjs BATCH_DIR). The traced side is the one whose
stdout holds PK lines (bots/variants/s2-trace). One output row per (our Prism turn, chance target): a PK S line
(turn start) joined with its turn's PK E line (turn end), then the replay over the next 8 rounds.
"""
import argparse
import gzip
import json
import sys
import zipfile
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'replay'))
from analysis.data import ROOT as DATA_ROOT, Game, load_index  # noqa: E402

S_FIELDS = ['round', 'id', 'tgt', 'd0', 'ehp', 'hp', 'shield', 'maxhp', 'taken', 'focus', 'burst', 'cd0', 'cd1', 'ch', 'gems',
            'myhp', 'mymax', 'after', 'before_next', 'prism_d', 'echan', 'estun', 'own_ground', 'ebush', 'mebush', 'hx', 'hy',
            'ex', 'ey', 'stunned', 'near_spawn', 'engaged']
S_FLOAT = {'ehp', 'hp', 'shield', 'maxhp', 'taken', 'focus', 'burst', 'myhp', 'mymax'}
WINDOW = 8


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def parse(text):
    starts, ends = [], {}
    for line in text.splitlines():
        line = line.lstrip('\x00 \t')  # lines can start with NUL padding
        if line.startswith('PK S '):
            v = line.split()[2:]
            if len(v) != len(S_FIELDS):
                continue
            starts.append({k: float(x) if k in S_FLOAT else int(x) for k, x in zip(S_FIELDS, v)})
        elif line.startswith('PK E '):
            v = line.split()[2:]
            if len(v) < 15:
                continue
            e = {'exit': v[2], 'dec': v[3], 'calls': int(v[4]), 'search': int(v[5]), 'chose': int(v[6]), 'attacked': int(v[7]),
                 'moved': int(v[8]), 'aim': int(v[9]), 'aim_tag': v[10], 'c0': int(v[11]), 'c1': int(v[12]),
                 'x1': int(v[13]), 'y1': int(v[14]), 'tg': {}}
            for t in v[15:]:
                h, real, shadow, tus, tthem, dend, alive = t.split(':')
                e['tg'][int(h)] = {'real': real, 'shadow': shadow, 'ttk_us': int(tus), 'ttk_them': int(tthem), 'd_end': int(dend)}
            ends[(int(v[0]), int(v[1]))] = e
    return starts, ends


class Order:
    """The engine's turn order: teams alternate (A first in odd rounds), each by priority (from the round before), then id."""

    def __init__(self, g):
        self.g = g
        self.cache = {}

    def slots(self, r):
        if r in self.cache:
            return self.cache[r]
        g = self.g
        i = max(0, r - 2)  # state at the end of round r-1
        teams = []
        for t in (0, 1):
            ids = g.team_ids[t]
            ids = sorted(ids, key=lambda c: (-(g.ch(c)['prio'][i] if i < len(g.ch(c)['prio']) else 0), c))
            teams.append(ids)
        first = 0 if r % 2 == 1 else 1
        a, b = teams[first], teams[1 - first]
        out = []
        for k in range(max(len(a), len(b))):
            if k < len(a):
                out.append(a[k])
            if k < len(b):
                out.append(b[k])
        self.cache[r] = {c: s for s, c in enumerate(out)}
        return self.cache[r]


def game_rows(d):
    g = Game(d)
    src = ROOT / g.meta['source']
    try:
        z = zipfile.ZipFile(src)
    except Exception:
        return []
    names = z.namelist()
    team, starts, ends = None, [], {}
    for t, f in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
        if f in names:
            s, e = parse(z.read(f).decode('utf-8', 'replace'))
            if s:
                team, starts, ends = t, s, e
    if team is None:
        return [{'game': d, 'empty': 1, 'winner_us': None}]
    order = Order(g)
    ev = g.events
    by_round = {}
    for e in ev:
        by_round.setdefault(e['r'], []).append(e)
    deaths = {}
    for e in ev:
        if e['k'] == 'death':
            deaths.setdefault(e['v'], []).append(e)
    linked = {}
    for e in ev:
        if e['k'] == 'death' and 'linked' in e:
            linked[e['v']] = e['linked']
    rows = []
    n_rounds = g.n_rounds

    def pos_end(cid, r):  # end of round r
        return g.pos(cid, r - 1)

    def pos_before_turn(cid, r, slot):
        """cid's position at the start of turn `slot` of round r."""
        p = pos_end(cid, r - 1) if r > 1 else None
        for e in by_round.get(r, []):
            if e.get('t', -1) >= slot:
                break
            if e.get('a') == cid:
                if e['k'] == 'move' or (e['k'] == 'cast' and e.get('ab') == 'Dash') or e['k'] in ('teleport_end', 'recall_end', 'respawn'):
                    p = tuple(e.get('to') or e.get('at'))
        if any(e['k'] == 'death' and e['v'] == cid and e.get('t', -1) < slot for e in by_round.get(r, [])):
            return None
        return p

    for s in starts:
        r, me, tg = s['round'], s['id'], s['tgt']
        if me not in g.idx or tg not in g.idx:
            continue
        row = dict(s)
        row['game'] = d
        row['team'] = team
        row['winner_us'] = int(g.winner == team) if g.winner in (0, 1) else None
        row['ttype'] = g.name_of[tg]
        row['myname'] = g.name_of[me]
        en = ends.get((r, me))
        row['has_end'] = int(en is not None)
        if en:
            row.update({k: en[k] for k in ('exit', 'dec', 'calls', 'search', 'chose', 'attacked', 'moved', 'aim_tag', 'c0', 'c1')})
            row['aim_is_tgt'] = int(en['aim'] == tg and en['aim_tag'] != '-')
            t = en['tg'].get(tg, {})
            row.update({'real': t.get('real', '?'), 'shadow': t.get('shadow', '?'), 'ttk_us': t.get('ttk_us', -1),
                        'ttk_them': t.get('ttk_them', -1), 'd_end': t.get('d_end', -1)})
        # Death of the target (or its linked body) in [r, r+WINDOW].
        dr, killer, kcause = None, None, None
        for vid in (tg, linked.get(tg)):
            for e in deaths.get(vid, []) if vid is not None else []:
                if r <= e['r'] <= r + WINDOW and (dr is None or e['r'] < dr):
                    dr, killer, kcause = e['r'], e.get('by'), ('camp' if 'camp' in e else 'champ')
        row['dead_r'] = dr
        row['killer_us'] = int(killer == me) if dr is not None else 0
        row['killer_team'] = int(killer is not None and g.team_of.get(killer) == team) if dr is not None else 0
        row['killer_type'] = g.name_of.get(killer) if killer is not None else kcause
        # Our own death within the window.
        md = [e['r'] for e in deaths.get(me, []) if r <= e['r'] <= r + WINDOW]
        row['me_dead_r'] = md[0] if md else None
        # Damage to the target: ours, our team's, in [r, r+WINDOW]; our casts at it.
        ours = team_dmg = 0.0
        our_casts = {'Damage': 0, 'CC': 0, 'AoE damage': 0}
        first_hit = None
        heal_in = shield_in = 0.0
        tgt_acts = []
        for rr in range(r, min(n_rounds, r + WINDOW) + 1):
            for e in by_round.get(rr, []):
                k = e['k']
                if k in ('attack', 'cast'):
                    a = e['a']
                    hit = sum(amt for v, amt in e.get('dmg', []) if v == tg)
                    if a == me and k == 'cast' and hit > 0 and e.get('ab') in our_casts:
                        our_casts[e['ab']] += 1
                    if a == me and hit > 0:
                        ours += hit
                        if first_hit is None:
                            first_hit = rr
                    if g.team_of.get(a) == team:
                        team_dmg += hit
                    heal_in += sum(amt for v, amt in e.get('heal', []) if v == tg and g.team_of.get(a) != team)
                    shield_in += sum(amt for v, amt in e.get('shield', []) if v == tg)
        row['our_dmg'] = round(ours, 1)
        row['team_dmg'] = round(team_dmg, 1)
        row['our_stun_hits'] = our_casts['CC']
        row['our_ground_hits'] = our_casts['AoE damage']
        row['our_first_hit'] = first_hit
        row['heal_in'] = round(heal_in, 1)
        row['shield_in'] = round(shield_in, 1)
        # Turn order: the target's turns between ours in round r and ours in round r+1.
        so_r, so_n = order.slots(r), order.slots(r + 1)
        my_s, my_n = so_r.get(me), so_n.get(me)
        acts = 0
        if my_s is not None and so_r.get(tg) is not None and so_r[tg] > my_s:
            acts += 1
        if my_n is not None and so_n.get(tg) is not None and so_n[tg] < my_n:
            acts += 1
        row['tgt_turns'] = acts
        # What the target did in that window: its events between our two turns.
        did = set()
        for rr, lo, hi in ((r, my_s, 99), (r + 1, -1, my_n)):
            if lo is None or hi is None:
                continue
            for e in by_round.get(rr, []):
                t = e.get('t', -1)
                if not (lo < t < hi) or e.get('a') != tg:
                    continue
                k = e['k']
                if k == 'move':
                    did.add('move')
                elif k == 'attack':
                    did.add('atk_us' if e.get('tgt') == me else 'atk')
                elif k == 'cast':
                    did.add('cast_' + (e.get('ab') or '?'))
                elif k in ('recall_start', 'tribute_start', 'teleport_start'):
                    did.add(k)
        row['tgt_did'] = ','.join(sorted(did))
        # Distances at our next turn's start (both moved since).
        if my_n is not None and r + 1 <= n_rounds:
            pm = pos_before_turn(me, r + 1, my_n)
            pt = pos_before_turn(tg, r + 1, my_n)
            row['d_next'] = cheb(pm, pt) if pm and pt else None
            row['d_next_from_end'] = cheb((en['x1'], en['y1']), pt) if en and pt and en['x1'] >= 0 else None
        else:
            row['d_next'] = row['d_next_from_end'] = None
        # Target's slot vs ours, for the bot's prediction check.
        row['slot_me'], row['slot_tg'] = my_s, so_r.get(tg)
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch')
    ap.add_argument('--out', default=str(ROOT / 'replays' / 'mac13-kronos-s2-pk.jsonl.gz'))
    ap.add_argument('--threads', type=int, default=16)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    batch = Path(a.batch).resolve().relative_to(DATA_ROOT).as_posix()
    dirs = sorted({r['dir'] for r in load_index() if r['source'].startswith(batch + '/') and r['ok']})
    if a.limit:
        dirs = dirs[:a.limit]
    print(f'{len(dirs)} games', file=sys.stderr)
    n = 0
    with Pool(a.threads) as pool, gzip.open(a.out, 'wt') as f:
        for rows in pool.imap_unordered(game_rows, dirs, chunksize=4):
            for r in rows:
                f.write(json.dumps(r) + '\n')
                n += 1
    print(f'{n} rows -> {a.out}', file=sys.stderr)


if __name__ == '__main__':
    main()
