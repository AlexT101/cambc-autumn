"""stance.py EXTRACT_DIR BATCH_SUBSTR: the stance variant's STANCE trace lines (debug builds), per game.
Share of champion-turns AHEAD / EVEN / BEHIND, state changes per champion-game, rounds where alive teammates
disagree, and the estimated lead against the replay's true one (score + carried gems, ours minus theirs)."""
import gzip, json, sys, zipfile, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

BATCH = sys.argv[2] if len(sys.argv) > 2 else ''

def g(d):
    meta = json.loads((d/'meta.json').read_text())
    if BATCH not in meta['source']: return None
    z = zipfile.ZipFile(meta['source'])
    lines = None
    for t, f in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
        try: txt = z.read(f).decode(errors='replace')
        except KeyError: continue
        L = [l.split() for l in txt.splitlines() if l.startswith('STANCE ') and len(l.split()) >= 6]
        if L: lines, side = L, t
    if not lines: return None
    R = json.load(gzip.open(d/'rounds.json.gz'))
    ch = R['champions']; n = len(R['round'])
    def truth(r):
        i = min(max(0, r - 1), n - 1)  # the state at our turn: the round before's end
        tot = [R['gems'][t][i] + sum(c['gems'][i] for c in ch if int(c['team']) == t and c['alive'][i]) for t in (0, 1)]
        return tot[side] - tot[1 - side]
    won = meta['result']['winner'] == side
    states = collections.Counter(); changes = collections.Counter(); bodies = set()
    by_round = collections.defaultdict(dict); err = []
    for p in lines:
        r, h, s, lead, chg = int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5])
        changes[h] += chg; bodies.add(h)
        if r % 10: continue  # lines print every 10 rounds and on a change: shares from the regular ones
        states[s] += 1; by_round[r][h] = s
        if r % 50 == 0: err.append((r, lead, truth(r)))
    split = sum(1 for r, m in by_round.items() if len(set(m.values())) > 1)
    return dict(states=states, changes=sum(changes.values()), bodies=len(bodies), rounds=len(by_round), split=split, err=err, won=won)

if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: G = [x for x in ex.map(g, dirs, chunksize=4) if x]
    S = collections.Counter()
    for x in G: S.update(x['states'])
    tot = sum(S.values())
    print(f'games {len(G)}  champion-turns sampled {tot}')
    print('share EVEN %.3f AHEAD %.3f BEHIND %.3f' % tuple(S[k] / tot for k in (0, 1, 2)))
    ch = [x['changes'] / x['bodies'] for x in G]
    print('changes per champion-game: mean %.2f  per game (all bodies) %.2f' % (sum(ch) / len(ch), sum(x['changes'] for x in G) / len(G)))
    print('games with any change %.3f' % (sum(1 for x in G if x['changes']) / len(G)))
    print('rounds where teammates disagree: %.4f of rounds' % (sum(x['split'] for x in G) / sum(x['rounds'] for x in G)))
    E = [e for x in G for e in x['err']]
    if E:
        d = [est - tr for _, est, tr in E]
        d.sort()
        print('est - true lead at r%%25: mean %.1f  median %d  p10 %d  p90 %d  |err|>=25 %.3f' % (sum(d) / len(d), d[len(d) // 2], d[len(d) // 10], d[9 * len(d) // 10], sum(1 for v in d if abs(v) >= 25) / len(d)))
        for lo, hi in ((1, 200), (201, 500), (501, 1000), (1001, 2000)):
            dd = [est - tr for r, est, tr in E if lo <= r <= hi]
            if dd: print(f'  r{lo}-{hi}: mean err {sum(dd)/len(dd):.1f} n {len(dd)}')
    # Win rate by the share of turns spent in each state
    for k, nm in ((1, 'AHEAD'), (2, 'BEHIND')):
        A = [x for x in G if x['states'][k] > 0]
        if A: print(f'games ever {nm}: {len(A)}, stance side wins {sum(x["won"] for x in A)/len(A):.3f}')
