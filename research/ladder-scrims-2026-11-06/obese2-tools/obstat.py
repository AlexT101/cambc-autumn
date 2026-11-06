"""obstat.py OUT.jsonl BATCH...: per game of CAND (bot 0), the obese census (OBESEC: dead bags in CAND's sight, by
round; P = a Prism's or a channel ending in time) and the gate's firings (KOBESE kill / bank lines), then a summary."""
import json, sys, zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def one(args):
    b, m = args
    rep = Path(b) / Path(m['replay']).name
    team = 'a' if m['order'][0] == 0 else 'b'
    r = dict(map=Path(m['map']).name, order=m['order'], cand_won=m['winner'] == 0, batch=str(b))
    try:
        z = zipfile.ZipFile(rep)
        out = z.read(f'team-{team}.stdout').replace(b'\0', b'').decode('utf-8', 'replace').splitlines()
    except Exception as e:
        r['err'] = str(e); return r
    rounds, rnp, kill, bank, own, enemy, maxg, first = set(), set(), set(), set(), set(), set(), 0, None
    for l in out:
        if l.startswith('OBESEC '):
            p = l.split(); rd = int(p[1]); g = int(p[3])
            rounds.add(rd); maxg = max(maxg, g)
            if len(p) == 4:
                rnp.add(rd); (own if p[2][0] == 'a' else enemy).add(rd)
                first = rd if first is None else min(first, rd)
        elif l.startswith('KOBESE '):
            p = l.split(); rd = int(p[1])
            (kill if p[2] == 'kill' else bank).add(rd)
    r.update(census=len(rounds), census_np=len(rnp), own=len(own), enemy=len(enemy), kill=len(kill), bank=len(bank),
             maxg=maxg, first=first)
    return r

if __name__ == '__main__':
    out, batches = sys.argv[1], sys.argv[2:]
    jobs = []
    for b in batches:
        res = json.loads((Path(b) / 'results.json').read_text())
        jobs += [(b, m) for m in res['matches'] if 'winner' in m and 'replay' in m]
    with ProcessPoolExecutor(16) as ex:
        rows = list(ex.map(one, jobs, chunksize=64))
    with open(out, 'w') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    ok = [r for r in rows if 'err' not in r]
    n = len(ok)
    def rate(rs): return f"{len(rs)} ({100*len(rs)/max(1,n):.2f}%), CAND won {100*sum(r['cand_won'] for r in rs)/max(1,len(rs)):.1f}%"
    print(f"games {n} (unread {len(rows)-n})")
    print("any dead bag in sight:", rate([r for r in ok if r['census']]))
    print("non-Prism obese bag:  ", rate([r for r in ok if r['census_np']]))
    print("  ours:", rate([r for r in ok if r['own']]), " enemy's:", rate([r for r in ok if r['enemy']]))
    print("gate fired (kill):    ", rate([r for r in ok if r['kill']]))
    print("gate fired (bank):    ", rate([r for r in ok if r['bank']]))
    fired = [r for r in ok if r['kill'] or r['bank']]
    print("gate fired (any):     ", rate(fired))
    print("rest:                 ", rate([r for r in ok if not (r['kill'] or r['bank'])]))
    fs = sorted(r['first'] for r in ok if r['first'] is not None)
    if fs: print("first obese round: min", fs[0], "median", fs[len(fs)//2], "max", fs[-1])
