"""PTN (rival/nemesis, since 2026-10-16 21:18) against top teams: where the gem gap comes from."""
import sys
from collections import Counter, defaultdict
from statistics import mean
from common import games, TOP, US, SHORT, ref
from features import feat as feat1
from deep import feat as feat2
from multiprocessing import Pool

SINCE = sys.argv[1] if len(sys.argv) > 1 else '2026-10-16T21:18'


def both(r):
    return feat1(r), feat2(r)


if __name__ == '__main__':
    recs = [r for r in games(since=SINCE) if US in r['names'] and any(n in TOP for n in r['names'])]
    with Pool(14) as p:
        res = p.map(both, recs)
    tot = Counter()
    acts = defaultdict(Counter)
    rows = []
    for f, d in res:
        t = f['names'].index(US)
        o = 1 - t
        opp = f['names'][o]
        s = Counter()
        for c in f['captures']:
            s[('cap', c['team'])] += c['gems']
            s[('capn', c['team'])] += 1
            if c['type'] == 'M':
                s[('mono', c['team'])] += c['gems']
            if c['side'] == 1 - c['team']:
                s[('steal', c['team'])] += c['gems']
        for x in f['deaths']:
            if x['linked']:
                continue
            if x['by'] is None:
                s[('campdeath', x['vt'])] += 1
                s[('campgems', x['vt'])] += x['gems']
            else:
                s[('death', x['vt'])] += 1
                s[('baglost', x['vt'])] += x['gems']
        for k in d['kills']:
            vt = f['team_of'][k['v']]
            if vt == t:
                for a in k['act']:
                    acts[opp][a] += 1
                acts[opp]['n'] += 1
                acts[opp]['enemyhalf' if k['half'] == 1 else 'ownhalf'] += 1
        win = f['winner'] == t
        rows.append((ref(f['rec']), opp, 'W' if win else 'L', f['N'], f['tributed'][t], f['tributed'][o], s[('cap', t)], s[('cap', o)], s[('mono', t)], s[('mono', o)],
                     s[('steal', o)], s[('death', t)], s[('baglost', t)], s[('death', o)], s[('baglost', o)], s[('campdeath', t)], f['gems100'][t][2], f['gems100'][o][2]))
        for k, v in s.items():
            tot[(opp, 'us' if k[1] == t else 'them', k[0])] += v
        tot[(opp, 'games', '')] += 1
        tot[(opp, 'wins', '')] += win
    print(f'games since {SINCE}: {len(rows)}')
    print('| game | opp | res | rounds | tributed us/them | captured gems us/them | monolith gems us/them | their captures on our side | our deaths (bag gems lost) | their deaths (bags) | our camp deaths | tributed at r300 us/them |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for r in rows:
        print(f'| {r[0]} | {SHORT[r[1]]} | {r[2]} | {r[3]} | {r[4]}/{r[5]} | {r[6]}/{r[7]} | {r[8]}/{r[9]} | {r[10]} | {r[11]} ({r[12]}) | {r[13]} ({r[14]}) | {r[15]} | {r[16]}/{r[17]} |')
    print()
    for opp in sorted({k[0] for k in tot}):
        G = tot[(opp, 'games', '')]
        print(f"- vs {SHORT.get(opp, opp)}: {G} games, PTN won {tot[(opp,'wins','')]}; per game captured {tot[(opp,'us','cap')]/G:.0f} vs {tot[(opp,'them','cap')]/G:.0f} gems "
              f"({tot[(opp,'us','capn')]/G:.1f} vs {tot[(opp,'them','capn')]/G:.1f} captures); deaths {tot[(opp,'us','death')]/G:.1f} vs {tot[(opp,'them','death')]/G:.1f}; "
              f"bag gems lost {tot[(opp,'us','baglost')]/G:.0f} vs {tot[(opp,'them','baglost')]/G:.0f}; camp deaths {tot[(opp,'us','campdeath')]/G:.2f}")
        a = acts[opp]
        n = max(1, a['n'])
        print('  our deaths to them: ' + ', '.join(f'{k} {100*v/n:.0f}%' for k, v in a.most_common() if k != 'n') + f' (n={a["n"]})')
