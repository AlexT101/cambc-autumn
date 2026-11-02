# Checks simport against the bot: each `TE k=sides` followed directly by a stand (TE home) or chase (TE prey_fight)
# result in the same turn is re-simulated and compared. Self-play games by default.
import sys, os, json
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import l2lib as L

SP = 'replays/v66-analysis/simcal/selfplay'; EX = 'replays/v66-analysis/simcal/spex'


def pairs(T):
    for (r, c), lines in T.items():
        tt = [d for d in lines if d['tag'] == 'TT']
        if not tt or tt[0].get('a') != '1': continue
        last = None
        for d in lines:
            if d['tag'] == 'TE' and d.get('k') == 'sides': last = d; continue
            if d['tag'] == 'TE' and last is not None and (d.get('k') == 'prey_fight' or (d.get('k') == 'home' and d.get('why', '').startswith('stand'))):
                yield (r, c, tt[0], last, d); last = None


def main():
    cnt = Counter(); bad = []
    for m, path, gdir in L.selfplay_games(SP, EX):
        X = L.Extract(EX, gdir)
        for team in 'ab':
            T = L.turns(L.selfplay_lines(path, team))
            for r, c, tt, sides, res_line in pairs(T):
                t = L.ptrade(res_line['t'])
                typed = L.type_fighters(T[(r, c)], sides, tt['t'], c)
                if typed is None: cnt['untyped'] += 1; continue
                res = L.run(sides, *typed, X, r)
                ok = L.agrees(res, t)
                cnt[(res_line['k'], ok)] += 1
                if not ok and len(bad) < 25: bad.append((m, team, r, c, res_line['k'], res_line['t'], res['they_kill'], res['we_kill'], res['self_falls'], sides['us'], sides['them']))
    print(cnt)
    for b in bad: print(b)


if __name__ == '__main__':
    main()
