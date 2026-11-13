"""Recall landings that retarget, per side, from a debug batch's stdout alone: RFLAND (r <= 600) whose D farm group
changes within 5 turns (persistent: not back on X in the next 3 turns), and the C4 trace lines RFSERVED / RFWAIT.
Bot 0 of results.json `order` is CAND. Usage: py c4_trace.py BATCH_DIR"""
import json, sys, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor


def side(args):
    replay, s = args
    try: txt = zipfile.ZipFile(replay).read(f'team-{"ab"[s]}.stdout').decode(errors='replace')
    except Exception: return None
    D = {}; lands = []; c = Counter()
    for l in txt.splitlines():
        p = l.replace('\x00', '').split()
        if not p: continue
        if p[0] == 'D' and len(p) >= 6 and p[1].isdigit() and p[2].isdigit(): D[(int(p[1]), int(p[2]))] = int(p[4])
        elif p[0] == 'RFLAND' and len(p) >= 4: lands.append((int(p[1]), int(p[2]), int(p[3])))
        elif p[0] in ('RFSERVED', 'RFWAIT', 'RFCHOOSE'): c[p[0]] += 1
    for rl, cid, gl in lands:
        if rl > 600: continue
        c['land'] += 1
        sw = next((rr for rr in range(rl, rl + 6) if D.get((rr, cid), -9) >= 0 and D[(rr, cid)] != gl), None)
        if sw is None: continue
        c['switch'] += 1
        if gl not in [D.get((rr, cid), -9) for rr in range(sw + 1, sw + 4)]: c['persistent'] += 1
    return c


if __name__ == '__main__':
    j = json.load(open(f'{sys.argv[1]}/results.json'))
    jobs, who = [], []
    for m in j['matches']:
        if m.get('winner') is None: continue
        for s in (0, 1):
            jobs.append((m['replay'], s)); who.append('CAND' if m['order'][s] == 0 else 'REF')
    tot = {'CAND': Counter(), 'REF': Counter()}; n = Counter()
    with ProcessPoolExecutor(16) as ex:
        for w, c in zip(who, ex.map(side, jobs, chunksize=8)):
            if c is not None: tot[w] += c; n[w] += 1
    for w in ('CAND', 'REF'):
        c, k = tot[w], max(1, n[w])
        print(f"{w}: {n[w]} team-games; landings {c['land']/k:.2f}/tg, retarget {c['switch']/k:.2f}/tg ({c['switch']/max(1,c['land']):.0%}),"
              f" persistent {c['persistent']/k:.2f}/tg ({c['persistent']/max(1,c['land']):.0%}); RFCHOOSE {c['RFCHOOSE']/k:.1f}/tg,"
              f" RFSERVED {c['RFSERVED']/k:.2f}/tg, RFWAIT {c['RFWAIT']/k:.2f}/tg")
