"""Kills (local, BX): our branch sequence before death, the start of the final retreat run, and at the turn end
before that run began (Q): truth burst/health (cooldown-blind too) and the bot's view."""
import pickle, sys, collections
R = pickle.load(open(sys.argv[1], 'rb')); n = len(R)
RUN = collections.Counter(); PRE = collections.Counter(); QT = collections.Counter(); ex = []
for g in R:
    rows = {(x[12], x[0]): x for x in g['rows']}
    for x in g['rows']:
        if not x[7]: continue
        v, r = x[12], x[0]
        seq = []
        for k in range(0, 12):
            b = g['bx'].get((r - k, v))
            seq.append(b[7] if b else '?')
        run = 0
        while run < len(seq) and seq[run] == 'R': run += 1
        RUN[min(run, 8)] += 1
        pre = seq[run] if run < len(seq) else '#'
        PRE[pre] += 1
        q = rows.get((v, r - run))
        if run > 0 and q:
            seen = [z for z in q[11] if z[4]]
            ball = sum(z[11] for z in seen if z[1] <= 5)
            QT[('L' if q[5] >= q[2] else 'cd' if ball >= q[2] else '-')] += 1
        if len(ex) < 12 and run >= 1: ex.append((r, x[1], ''.join(seq[::-1]), x[2], x[8]))
print(f'{n} games, kill rows {sum(RUN.values())/n:.2f}/game')
print('  final retreat run length (turn ends of R before death):', {k: round(v / n, 2) for k, v in sorted(RUN.items())})
print('  branch before the run (or the death turn end itself if run 0):', {k: round(v / n, 2) for k, v in PRE.most_common()})
print('  at the run start: truth seen-lethal L / cooldown-blind lethal cd (enemies within 5) / not:', {k: round(v / n, 2) for k, v in QT.items()})
for e in ex: print('   ', e)
