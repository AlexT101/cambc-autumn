# Death episodes (level 2): for each death of ours, the turns from the last one at 80%+ health; the stand verdicts
# then, and whether the champions that damaged us in the episode were in the stand sim.
# usage: episodes.py ladder|selfplay
import sys, os, json, gzip
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'extract'))
import l2lib as L
import collect_l2 as CL

OUT = 'replays/v66-analysis/simcal'


def episodes(src, key, opp, lines, X, team, r0, r1):
    TR = CL.Truth(X)
    T = L.turns(lines, r0, r1)
    bych = defaultdict(dict)
    for (r, c), turn in T.items(): bych[c][r] = turn
    out = []
    for c, turns in bych.items():
        for d in TR.deaths.get(c, []):
            if d > r1 or d < r0 + 15: continue
            rs = sorted(r for r in turns if r < d)
            if not rs: continue
            start = None
            for r in reversed(rs):
                tt = [x for x in turns[r] if x['tag'] == 'TT']
                if tt and tt[0].get('a') == '1' and float(tt[0]['hp']) >= 0.8 * float(tt[0]['mh']): start = r; break
            if start is None or d - start > 40: continue
            ep = [r for r in rs if r >= start]
            dmgers = Counter()
            for r in range(start, d + 1):
                for (a, v, amt, _) in TR.by_r[r]:
                    if v == c: dmgers[a] += amt
            killer = None
            for e in X.ev:
                if e['k'] == 'death' and e['v'] == c and e['r'] == d: killer = e.get('by'); break
            # stand verdicts through the episode, with the sim roster from the sides line
            verdicts = []
            for r in ep:
                turn = turns[r]
                tts = [x for x in turn if x['tag'] == 'TT']
                if not tts: continue
                tt = tts[0]
                last = None
                for x in turn:
                    if x['tag'] == 'TE' and x.get('k') == 'sides': last = x; continue
                    if x['tag'] == 'TE' and x.get('k') == 'home':
                        why = x.get('why'); t = x.get('t')
                        roster = None; marg = None; lost = None
                        if why and why.startswith('stand') and last is not None:
                            ty = L.type_fighters(turn, last, tt['t'], c)
                            if ty:
                                res = L.run(last, *ty, X, r)
                                if L.agrees(res, L.ptrade(t)):
                                    roster = [f['h'] for f in ty[1]]
                                    for side, fs in ((res['U'], ty[0]), (res['T'], ty[1])):
                                        for g, f in zip(side.f, fs): g.health0 = f['health']
                                    marg = CL.margin(res)
                        verdicts.append(dict(r=r, why=why, t=t, roster=roster, margin=marg, d=tt.get('d'), hp=float(tt['hp']), mh=float(tt['mh'])))
                        break
                    if x['tag'] == 'TE' and x.get('k') == 'sides': last = x
            out.append(dict(src=src, key=key, opp=opp, c=c, typ=X.ctype.get(c), death=d, start=start, killer=killer,
                            dmgers={str(k): round(v) for k, v in dmgers.items()}, verdicts=verdicts))
    return out


def one_ladder(key):
    import common as C
    MAN = {g['group'][:8] + '-' + str(g['position']): g['replay'] for g in json.load(open('replays/v66/manifest.json'))['games']}
    SRC = {g['source']: g for g in C.games(distinct=False)}
    g = SRC[MAN[key]]
    v = json.load(open(f'{OUT}/l2batch/{key}/trace_validation.json'))
    trust = v.get('ladder_trusted_through') or 0
    X = L.Extract(C.EX, g['dir'])
    lines = gzip.open(f'{OUT}/l2batch/{key}/trace.stdout.gz', 'rt', errors='replace').read().splitlines()
    return episodes('ladder', key, g['opp'], lines, X, g['us'], 1, min(260, trust))


def one_self(arg):
    m, path, gdir = arg
    X = L.Extract(OUT + '/spex', gdir)
    out = []
    for i, team in enumerate('ab'):
        out += episodes('self', m + '-' + team, 'self', L.selfplay_lines(path, team), X, i, 1, 260)
    return out


if __name__ == '__main__':
    from concurrent.futures import ProcessPoolExecutor
    src = sys.argv[1]
    if src == 'ladder':
        args = sorted(k for k in os.listdir(OUT + '/l2batch') if os.path.exists(f'{OUT}/l2batch/{k}/trace_validation.json')); fn = one_ladder
    else:
        args = L.selfplay_games(OUT + '/selfplay', OUT + '/spex'); fn = one_self
    rows = []
    with ProcessPoolExecutor(20) as ex:
        for r in ex.map(fn, args): rows += r
    json.dump(rows, open(f'{OUT}/episodes_{src}.json', 'w'))
    print(src, 'episodes', len(rows))
