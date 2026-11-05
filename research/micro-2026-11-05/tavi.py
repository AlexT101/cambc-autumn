"""Tavi's field shopping: is gold banked and spent in the turn of a champion hit (a surprise Strength spike)?

    python3 -I research/micro-2026-11-05/tavi.py replays/micro/ladder [--procs 24]
"""
import collections, glob, gzip, json, multiprocessing as mp, os, sys

TAVI = 11


def analyse(path):
    d = json.load(gzip.open(path))
    roster = {c['id']: c for c in d['roster']}
    tavis = [c for c in d['roster'] if c['type'] == TAVI]
    if not tavis:
        return {}
    st = {(row[0], row[1]): row for rows in d['rounds'] for row in rows}
    C = collections.defaultdict(collections.Counter)
    EX = collections.defaultdict(list)
    by = collections.defaultdict(list)
    for a in d['acts']:
        if roster[a['a']]['type'] == TAVI:
            by[(a['r'], a['a'])].append(a)
    for (r, cid), tn in by.items():
        side = roster[cid]['team']
        team = d['teams'][side]
        s = st.get((r, cid))
        if not s or not s[6]:
            continue
        sp = d['map']['spawn'][side]
        onspawn = sp['minX'] <= s[2] <= sp['maxX'] and sp['minY'] <= s[3] <= sp['maxY']
        hitchamp = [a for a in tn if a['k'] in (5, 6) and any(not h[2] and roster[h[0]]['team'] != side for h in a.get('hits', []))]
        buys = [a for a in tn if a['k'] == 13 and a.get('it')]
        C[team]['turns'] += 1
        C[team]['gold_sum'] += s[7]
        if hitchamp:
            C[team]['hit_turns'] += 1
            C[team]['gold_at_hit'] += s[7]
        if buys and not onspawn:
            C[team]['field_buy_turns'] += 1
            if hitchamp:
                C[team]['field_buy_hit_turns'] += 1
                first_buy = tn.index(buys[0])
                first_hit = tn.index(hitchamp[0])
                if first_buy < first_hit:
                    C[team]['buy_before_hit'] += 1
                    spent = s[7] - buys[-1]['af'][4]
                    C[team]['spent_before_hit'] += spent
                    stat = collections.Counter()
                    for b in buys:
                        for i, n in b['it']:
                            if n > 0:
                                stat[['Str', 'Foc', 'Hp'][(i % 6) // 2]] += n
                    for k, v in stat.items():
                        C[team][f'pre_hit_{k}'] += v
                    if len(EX[team]) < 5:
                        EX[team].append(f"{d['key']} r{r} gold {s[7]} spent {spent} {dict(stat)} str {s[10]}->{hitchamp[0].get('str')}")
    return {'C': C, 'EX': EX}


if __name__ == '__main__':
    files = sorted(glob.glob(os.path.join(sys.argv[1], '*.json.gz')))
    C = collections.defaultdict(collections.Counter)
    EX = collections.defaultdict(list)
    with mp.Pool(24) as pool:
        for res in pool.imap_unordered(analyse, files, chunksize=8):
            for t, c in res.get('C', {}).items():
                C[t].update(c)
            for t, L in res.get('EX', {}).items():
                EX[t].extend(L[:5 - len(EX[t])])
    print('| team | Tavi turns | mean gold | hit turns | gold at hit | field-buy turns | buy then hit | gold spent before hit | Str/Foc/Hp shards |')
    print('|---|---|---|---|---|---|---|---|---|')
    for t, c in sorted(C.items(), key=lambda kv: -kv[1]['turns']):
        if c['turns'] < 3000:
            continue
        b = max(1, c['buy_before_hit'])
        print(f"| {t} | {c['turns']} | {c['gold_sum'] / c['turns']:.0f} | {c['hit_turns']} | {c['gold_at_hit'] / max(1, c['hit_turns']):.0f} | "
              f"{c['field_buy_turns']} | {c['buy_before_hit']} | {c['spent_before_hit'] / b:.0f} | {c['pre_hit_Str']}/{c['pre_hit_Foc']}/{c['pre_hit_Hp']} |")
    for t, L in EX.items():
        if C[t]['turns'] >= 3000 and L:
            print(f'- {t}: ' + '; '.join(L))
