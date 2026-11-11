"""What a champion knows of its teammates, from the CM2 debug lines (params::comms_trace, comms.cc / farm.cc).

    py trace.py RUN_NAME [RUN_NAME ...]      # ab.py --debug --keep-replays 0 run names under replays/ab/

A team's stdout is in turn order, so the latest W line of an ally (its claim and tile at its turn's end) is the truth a
reader's R line (its beliefs at its turn's start) is checked against.
  L handle team groups slot_width cell camp_on claim_width used W H
  G group cx cy strength gems
  W round handle index claim x y frame(0 claim, 1 tile)
  R round handle ally alive visible claim told_x told_y told_round pos_x pos_y pos_round
  A round handle ally group delay working      (farm timed an unseen claimer from its told tile)
"""
import collections, json, os, sys, zipfile, glob
R = os.path.dirname(os.path.abspath(__file__)) + '/../../../'

def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def games(run):
    s = json.load(open(f'{R}replays/ab/{run}/summary.json'))
    for suite in s['suites']:
        b = R + suite['batch']
        res = json.load(open(b + '/results.json'))
        for m in res['matches']:
            if not m.get('replay'): continue
            f = m['replay'] if os.path.isabs(m['replay']) else os.path.join(b, os.path.basename(m['replay']))
            # ab.py: bot 0 is CAND; the file stem ends in 12 (bot 0 is team A) or 21.
            side = 'a' if os.path.basename(f).rsplit('.', 1)[0].endswith('12') else 'b'
            yield f, side

def stdout_of(f, side):
    for cand in (f, f.rsplit('.', 1)[0] + '.zip'):
        if os.path.exists(cand) and zipfile.is_zipfile(cand):
            z = zipfile.ZipFile(cand)
            for n in z.namelist():
                if n.endswith(f'team-{side}.stdout'): return z.read(n).decode('utf8', 'replace')
    d = os.path.dirname(f); stem = os.path.basename(f).rsplit('.', 1)[0]
    for cand in glob.glob(f'{d}/{stem}*team-{side}.stdout') + glob.glob(f'{d}/{stem}/team-{side}.stdout'):
        return open(cand, errors='replace').read()
    return None

def analyse(run):
    T = collections.Counter(); H = collections.defaultdict(list)
    n_games = 0
    for f, side in games(run):
        out = stdout_of(f, side)
        if out is None: T['no-stdout'] += 1; continue
        n_games += 1
        truth = {}       # index -> (round, claim, x, y, frame)
        prev_claim = {}  # index -> claim at its previous W
        centre = {}
        index = {}       # handle -> index
        cell = None
        for line in out.split('\n'):
            if not line.startswith('CM2 ') or '\x00' in line: continue
            p = line.split()
            if len(p) < 2: continue
            k = p[1]
            if len(p) != {'L': 12, 'G': 7, 'W': 9, 'R': 14, 'A': 8, 'B': 8, 'C': 13}.get(k, -1): continue  # a line the 1 MiB stdout cap cut
            if k == 'L':
                if cell is None:
                    cell = int(p[6]); H['slot_width'].append(int(p[5])); H['cell'].append(cell); T['layouts'] += 1; T['tiles-fit'] += cell > 0
            elif k == 'G': centre[int(p[2])] = (int(p[3]), int(p[4]), int(p[5]))
            elif k == 'W':
                r, idx, claim, x, y, frame = int(p[2]), int(p[4]), int(p[5]), int(p[6]), int(p[7]), int(p[8])
                if x >= 0:
                    T['turns'] += 1; T['tile-frames'] += frame
                    if idx in prev_claim and prev_claim[idx] != claim: T['claim-changes'] += 1
                prev_claim[idx] = claim
                truth[idx] = (r, claim, x, y, frame)
                index[p[3]] = idx
            elif k == 'R':
                r, j, alive, vis, claim, tx, ty, tr, px, py, pr = (int(v) for v in (p[2], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], p[12], p[13]))
                t = truth.get(j)
                if not alive or t is None or t[2] < 0 or t[0] < r - 1: continue
                T['pairs'] += 1
                key = 'seen' if vis else 'unseen'
                T[key] += 1
                T[f'{key}-claim-wrong'] += claim != t[1]
                if vis: continue
                at = (t[2], t[3])
                # The position a consumer would use: the last sighting within 2 rounds, a told tile within 3, the claim's centre.
                T['unseen-sighted2'] += pr >= r - 2
                told = tr >= r - 4 and tr > pr
                T['unseen-told3'] += tr >= r - 3 and tr > pr
                T['unseen-told4'] += told
                if told: H['told-err'].append(cheb((tx, ty), at))
                if claim in centre: H['centre-err'].append(cheb(centre[claim][:2], at))
                else: T['unseen-no-claim'] += 1
                if pr >= 0: H['sighting-age'].append(r - pr)
                if (me := truth.get(index.get(p[3]))) and me[2] >= 0: H['unseen-dist'].append(cheb(at, (me[2], me[3])))
                # An unseen claimer: how far it really is from the group it claims (farm counts its work from now).
                if t[1] in centre and claim == t[1]:
                    c = centre[t[1]]
                    H['claimer-dist'].append(cheb(c[:2], at))
                    if c[2] > 0: H['claimer-dist-strong'].append(cheb(c[:2], at))
            elif k == 'C':
                prev, now, unseen, bh, oh, mh, mine, d = int(p[5]), int(p[6]), int(p[7]), float(p[8]), float(p[9]), float(p[10]), int(p[11]), int(p[12])
                names = 'ACR'
                T['camp-sights'] += 1; T['camp-sights-claim'] += mine
                T[f'camp {names[prev]}->{names[now]}'] += 1
                if mine: T[f'claim {names[prev]}->{names[now]}'] += 1
                if prev == 0 and now == 0 and mh > 0:
                    T['camp-alive'] += 1; T['camp-alive-cheaper'] += oh < 0.75 * bh; T['camp-alive-dearer'] += oh > 1.25 * bh + 1
                    if mine: T['claim-alive'] += 1; T['claim-alive-cheaper'] += oh < 0.75 * bh
            elif k == 'B': T['late-repriced'] += 1
            elif k == 'A':
                T['arrival-told'] += 1; H['arrival-delay'].append(int(p[6]))
                T['arrival-told-late'] += int(p[6]) > 0
    def q(v, qs=(.5, .75, .9, .99)):
        v = sorted(v)
        return [v[min(len(v) - 1, int(len(v) * x))] for x in qs] if v else None
    def share(v, f): return round(100 * sum(1 for x in v if f(x)) / max(1, len(v)), 1)
    pct = lambda a, b: round(100 * T[a] / max(1, T[b]), 2)
    print(f'== {run}: {n_games} games, {T["turns"]} live turns, {T["pairs"]} reader-ally pairs')
    print(f'  layout: tiles fit {pct("tiles-fit", "layouts")}% of games; slot width {q(H["slot_width"], (0, .1, .5, .9))}, cell {q([c for c in H["cell"] if c], (.1, .5, .9, .99))}')
    print(f'  writer: tile frames {pct("tile-frames", "turns")}% of live turns; claim changes {pct("claim-changes", "turns")}% of turns')
    print(f'  ally in sight {pct("seen", "pairs")}% of pairs; claim wrong: in sight {pct("seen-claim-wrong", "seen")}%, unseen {pct("unseen-claim-wrong", "unseen")}%')
    print(f'  unseen ally: sighted within 2 rounds {pct("unseen-sighted2", "unseen")}%, told within 3 {pct("unseen-told3", "unseen")}% / 4 {pct("unseen-told4", "unseen")}%, no claim {pct("unseen-no-claim", "unseen")}%')
    e = H['unseen-dist']
    print(f'  unseen ally distance from the reader: median/75/90/99 {q(e)}, within 8: {share(e, lambda x: x <= 8)}%, within 12: {share(e, lambda x: x <= 12)}%')
    e = H['told-err']
    print(f'  told tile error (tiles): median/75/90/99 {q(e)}, within 2: {share(e, lambda x: x <= 2)}%, within 4: {share(e, lambda x: x <= 4)}%')
    e = H['centre-err']
    print(f'  claim-centre error: median/75/90/99 {q(e)}, within 2: {share(e, lambda x: x <= 2)}%, within 5: {share(e, lambda x: x <= 5)}%, 15+: {share(e, lambda x: x >= 15)}%')
    e = H['claimer-dist']
    print(f'  unseen claimer to its group centre: median/75/90/99 {q(e)}, 6+: {share(e, lambda x: x >= 6)}%, 10+: {share(e, lambda x: x >= 10)}%; strong groups {q(H["claimer-dist-strong"])} ({len(H["claimer-dist-strong"])})')
    if T['camp-sights']:
        g = n_games
        print(f'  groups back in view after 4+ rounds: {T["camp-sights"] / g:.0f} a game ({T["camp-sights-claim"] / g:.1f} our claim); believed->seen, a game: '
              + ', '.join(f'{k[5:]} {v / g:.1f}' for k, v in sorted(T.items()) if k.startswith('camp ') and k[5] != k[8]))
        print(f'    our claim: ' + ', '.join(f'{k[6:]} {v / g:.2f}' for k, v in sorted(T.items()) if k.startswith('claim ') and '->' in k)
              + f'; alive with under 75% of the health believed: all {pct("camp-alive-cheaper", "camp-alive")}%, our claim {pct("claim-alive-cheaper", "claim-alive")}%; over 125%: {pct("camp-alive-dearer", "camp-alive")}%')
    if T['late-repriced']: print(f'  late-claimer repricings: {T["late-repriced"] / n_games:.1f} a game')
    if T['arrival-told']:
        print(f'  farm arrivals timed from a told tile: {T["arrival-told"] / n_games:.0f} a game, {pct("arrival-told-late", "arrival-told")}% with a delay; delay {q(H["arrival-delay"])}')
    return T, H

if __name__ == '__main__':
    for run in sys.argv[1:]: analyse(run)
