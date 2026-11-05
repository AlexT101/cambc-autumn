"""Micro-behaviour detectors over decode.mjs output: per-team counts and example (game, round) citations.

    python3 -I research/micro-2026-11-05/detect.py replays/micro/ladder --out research/micro-2026-11-05/out [--procs 24]
"""
import argparse
import collections
import glob
import gzip
import json
import multiprocessing as mp
import os

CH = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
FAM = ['Monster', 'Power', 'Durability', 'Treasure', 'Jungle', 'Home', 'Bruiser', 'Tribute', 'Capture', 'Prospector', 'Hunter',
       'Skirmish', 'Greed', 'Collectors']
STAT = ['Str', 'Foc', 'Hp']
K = dict(move=4, attack=5, cast=6, end=8, prio=9, recall=11, submit=12, shop=13, ward=14, cons=15, cancel=16, lock=20,
         tp=21, blocked=23, resign=24, sell=25, rollover=26, boterr=27)
KN = {v: k for k, v in K.items()}


def item_name(i):
    fam, rest = divmod(i, 6)
    stat, emb = divmod(rest, 2)
    return f"{FAM[fam]}{'E' if emb else 'S'}-{STAT[stat]}"


def in_rect(x, y, s):
    return s['minX'] <= x <= s['maxX'] and s['minY'] <= y <= s['maxY']


def turns(acts):
    """Consecutive acts of one champion in one round."""
    cur, key = [], None
    for a in acts:
        k = (a['r'], a['a'])
        if k != key and cur:
            yield cur
            cur = []
        key = k
        cur.append(a)
    if cur:
        yield cur


def analyse(path):
    d = json.load(gzip.open(path))
    gk = d['key']
    teams = d['teams']
    roster = {c['id']: c for c in d['roster']}
    spawn = d['map']['spawn']
    C = collections.defaultdict(collections.Counter)  # team -> counter
    EX = collections.defaultdict(list)  # (team, tag) -> examples
    PR = collections.defaultdict(list)  # team -> priority values (champion type, round, value)
    SEQ = collections.defaultdict(collections.Counter)

    def ex(team, tag, r, note=''):
        L = EX[(team, tag)]
        if len(L) < 6:
            L.append(f"{gk} r{r} {note}".strip())

    # Round-start hp by (round, id) for heal checks.
    for t in d['rounds']:
        for c in t:
            pass
    for tn in turns(d['acts']):
        a0 = tn[0]
        cid, r = a0['a'], a0['r']
        c = roster[cid]
        team = teams[c['team']]
        typ = CH[c['type']]
        C[team]['turns'] += 1
        kinds = [a['k'] for a in tn if a['k'] != K['end']]
        SEQ[team][(typ, tuple(KN.get(k, k) for k in kinds if k != K['prio']))] += 1
        nprio = sum(k == K['prio'] for k in kinds)
        if nprio:
            C[team]['turns_prio'] += 1
            if nprio > 1:
                C[team]['turns_multi_prio'] += 1
                ex(team, 'multi_prio', r, f"{typ} {[a.get('pr') for a in tn if a['k'] == K['prio']]}")
        for a in tn:
            if a['k'] == K['prio']:
                PR[team].append((typ, r, a['pr']))
        if K['rollover'] in kinds:
            C[team]['rollover'] += 1
        if K['boterr'] in kinds:
            C[team]['boterr'] += 1
        # Position state across the turn.
        shops = [a for a in tn if a['k'] in (K['shop'], K['sell'])]
        if shops:
            alive = shops[0]['b'][5]
            x, y = shops[0]['b'][0], shops[0]['b'][1]
            where = 'dead' if not alive else ('spawn' if in_rect(x, y, spawn[c['team']]) else 'field')
            C[team][f'shopturn_{where}'] += 1
            nb = sum(a['k'] == K['shop'] for a in shops)
            ns = sum(a['k'] == K['sell'] for a in shops)
            if ns:
                C[team][f'sellturn_{typ}'] += 1
                ex(team, f'sell_{typ}', r, f"{where} " + ' '.join(
                    ('+' if a['k'] == K['shop'] else '-') + ','.join(f"{item_name(i)}x{n}" for i, n in a.get('it', [])) for a in shops))
                if typ != 'Tavi':
                    C[team]['sell_nonTavi'] += 1
                if nb and ns:
                    C[team]['buy_and_sell_same_turn'] += 1
                    seq = ''.join('B' if a['k'] == K['shop'] else 'S' for a in shops)
                    if 'BS' in seq or 'SB' in seq:
                        ex(team, 'buy_sell_cycle', r, f"{typ} {where} {seq} hp {shops[0]['b'][2]}->{shops[-1]['af'][2]}/{shops[-1]['af'][3]}")
            # Health shards on spawn while hurt: immediate heal.
            for a in shops:
                hb, ha, mb, ma = a['b'][2], a['af'][2], a['b'][3], a['af'][3]
                if a['k'] == K['shop'] and alive and ha - hb > 0.5:
                    C[team]['heal_by_buy'] += 1
                    C[team]['heal_by_buy_hp'] += round(ha - hb)
                    if hb < mb - 0.5:
                        C[team]['heal_by_buy_hurt'] += 1
                if a['k'] == K['sell'] and alive and (ha != hb or ma != mb):
                    C[team]['sell_hp_change'] += 1
                    ex(team, 'sell_hp_change', r, f"{typ} hp {hb}/{mb} -> {ha}/{ma}")
            # Leave spawn in the same turn after a heal-buy.
            idx = tn.index(shops[-1])
            later_moves = [a for a in tn[idx + 1:] if a['k'] in (K['move'], K['cast']) and a.get('af')]
            if where == 'spawn' and any(a['af'][2] - a['b'][2] > 0.5 for a in shops if a['k'] == K['shop']) and later_moves:
                end = later_moves[-1]['af']
                if not in_rect(end[0], end[1], spawn[c['team']]):
                    C[team]['heal_buy_then_leave'] += 1
                    ex(team, 'heal_buy_then_leave', r, f"{typ} hp {shops[0]['b'][2]}->{shops[-1]['af'][2]}/{shops[-1]['af'][3]}")
            # Field buys (Tavi) relative to attacks in the same turn.
            if where == 'field':
                C[team][f'fieldbuy_{typ}'] += 1
                first_shop = tn.index(shops[0])
                hit_after = [a for a in tn[first_shop:] if a['k'] in (K['attack'], K['cast']) and any(h[2] == 0 for h in a.get('hits', []))]
                hit_before = [a for a in tn[:first_shop] if a['k'] in (K['attack'], K['cast']) and any(h[2] == 0 for h in a.get('hits', []))]
                champ_after = [a for a in hit_after if any(roster.get(h[0], {}).get('team', c['team']) != c['team'] for h in a['hits'])]
                stats = collections.Counter(item_name(i).split('-')[1] for a in shops for i, n in a.get('it', []) if n > 0)
                if champ_after:
                    C[team]['fieldbuy_then_hit_champ'] += 1
                    ex(team, 'fieldbuy_then_hit_champ', r, f"{typ} bought {dict(stats)} str {champ_after[0].get('str')}")
                elif hit_after:
                    C[team]['fieldbuy_then_hit_camp'] += 1
                if hit_before:
                    C[team]['fieldbuy_after_hit'] += 1
                for s, n in stats.items():
                    C[team][f'fieldbuy_stat_{s}'] += n
            if where == 'dead':
                C[team]['shop_dead'] += 1
        # Blocked moves and what follows.
        for i, a in enumerate(tn):
            if a['k'] == K['blocked']:
                C[team]['blocked'] += 1
                nxt = [b for b in tn[i + 1:] if b['k'] in (K['attack'], K['cast']) and b.get('to') == a['to']]
                if nxt:
                    C[team]['blocked_then_hit_tile'] += 1
                    ex(team, 'blocked_then_hit', r, f"{typ} at {a['to']}")
                mv = [b for b in tn[i + 1:] if b['k'] == K['move']]
                if mv:
                    C[team]['blocked_then_move'] += 1
        # Channels.
        for i, a in enumerate(tn):
            if a['k'] == K['cancel']:
                ct = a['b'][7]
                C[team][f'cancel_ch{ct}'] += 1
                started_same_turn = any(b['k'] in (K['recall'], K['submit']) for b in tn[:i])
                if started_same_turn:
                    C[team][f'cancel_same_turn_ch{ct}'] += 1
                    ex(team, f'cancel_same_turn_ch{ct}', r, typ)
            if a['k'] == K['recall']:
                C[team]['recall_start'] += 1
            if a['k'] == K['submit']:
                C[team]['submit'] += 1
                if a['b'][6] == 0:
                    C[team]['submit_zero_gems'] += 1
            if a['k'] == K['lock']:
                C[team]['lock_place'] += 1
            if a['k'] == K['tp']:
                C[team]['teleport'] += 1
            if a['k'] == K['ward']:
                C[team]['ward'] += 1
            if a['k'] == K['cons']:
                C[team]['consumable'] += 1
            if a['k'] == K['attack']:
                C[team]['attack'] += 1
                if not a.get('hits'):
                    C[team]['attack_nohit'] += 1
                if any(h[2] == 1 for h in a.get('hits', [])):
                    C[team]['attack_hit_ally'] += 1
            if a['k'] == K['cast']:
                C[team]['cast'] += 1
        # Melee hit and run: attack then move away; ranged walk+reset+attack.
        ks = [a['k'] for a in tn]
        if K['attack'] in ks and K['move'] in ks and ks.index(K['attack']) < len(ks) - 1 - ks[::-1].index(K['move']):
            C[team][f'attack_then_move_{typ}'] += 1
    return dict(C=C, EX=EX, PR=PR, SEQ=SEQ, teams=teams, key=gk)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--out', required=True)
    ap.add_argument('--procs', type=int, default=24)
    o = ap.parse_args()
    files = sorted(glob.glob(os.path.join(o.dir, '*.json.gz')))
    C = collections.defaultdict(collections.Counter)
    EX = collections.defaultdict(list)
    SEQ = collections.defaultdict(collections.Counter)
    games = collections.Counter()
    os.makedirs(o.out, exist_ok=True)
    prf = open(o.dir.rstrip('/') + '-priority.tsv', 'w')  # ~1 GB for the 2.0.0 set: kept beside the decode, not in research/
    with mp.Pool(o.procs) as pool:
        for res in pool.imap_unordered(analyse, files, chunksize=8):
            for t in res['teams']:
                games[t] += 1
            for t, c in res['C'].items():
                C[t].update(c)
            for k, L in res['EX'].items():
                if len(EX[k]) < 8:
                    EX[k].extend(L[:8 - len(EX[k])])
            for t, c in res['SEQ'].items():
                SEQ[t].update(c)
            for t, L in res['PR'].items():
                for typ, r, v in L:
                    prf.write(f"{t}\t{res['key']}\t{typ}\t{r}\t{v}\n")
    prf.close()
    json.dump({'games': games, 'C': C, 'EX': {f'{k[0]}|{k[1]}': v for k, v in EX.items()},
               'SEQ': {t: [[list(k), n] for k, n in c.most_common(400)] for t, c in SEQ.items()}},
              open(os.path.join(o.out, 'summary.json'), 'w'), indent=0, default=list)
    print(len(files), 'games')


if __name__ == '__main__':
    main()
