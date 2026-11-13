"""Line B mechanism counts per game, by side: Prism deaths (all, r <= 300), and from the CAND side's debug stdout
the muster reads by outcome, joins (MJOIN) and forced leaves (MLEAVE). Needs a debug A/B's replays extracted by
tools/replay/extract.mjs.

    py research/mx-tethys/scripts/muster_counts.py ANALYSIS_ROOT BATCH_NAME CAND_NAME
"""
import gzip, json, re, sys, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

WT = Path('/home/ubuntu/wt/mx-tethys')
READ_RE = re.compile(rb'^[\s\0]*MREAD \d+ \d+ (\S)', re.M)


def one(args):
    dd, cand = args
    try:
        m = json.loads((dd / 'meta.json').read_text())
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(WT / m['source'])
    except Exception:
        return None
    names = [t['name'] for t in m['teams']]
    if cand not in names: return None
    ct = names.index(cand)
    prisms = {c['team']: c['id'] for c in m['champions'] if c['name'] == 'Prism'}
    out = Counter(games=1, win=int(m['result']['winner'] == ct))
    for side, t in (('cand', ct), ('ref', 1 - ct)):
        if t not in prisms: continue
        out[side + '_prism_games'] += 1
        for e in ev:
            if e['k'] == 'death' and e.get('v') == prisms[t]:
                out[side + '_deaths'] += 1
                out[side + '_early'] += e['r'] <= 300
    try:
        data = z.read('team-%s.stdout' % 'ab'[ct])
    except KeyError:
        data = b''
    for k in READ_RE.findall(data): out['read_' + k.decode()] += 1
    out['join'] = len(re.findall(rb'^[\s\0]*MJOIN ', data, re.M))
    out['leave'] = len(re.findall(rb'^[\s\0]*MLEAVE ', data, re.M))
    out['meet'] = len(re.findall(rb'^[\s\0]*MMEET ', data, re.M))
    for d, _ in re.findall(rb'^[\s\0]*MHEAR \d+ \d+ (-?\d+) (-?\d+)', data, re.M):
        out['hear_near' if int(d) <= 4 else 'hear_far'] += 1
    return out


if __name__ == '__main__':
    root, batch, cand = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    idx = json.loads((root / 'index.json').read_text())
    dirs = sorted({root / g['dir'] for g in idx['games'] if batch in g['source']})
    tot = Counter()
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(one, [(d, cand) for d in dirs], chunksize=16):
            if r: tot.update(r)
    n = tot['games']
    print('games', n, 'win %.1f%%' % (100 * tot['win'] / max(1, n)))
    for side in ('cand', 'ref'):
        g = max(1, tot[side + '_prism_games'])
        print('%s: prism games %d, prism deaths %.3f/game, early (r<=300) %.3f/game' % (side, tot[side + '_prism_games'],
              tot[side + '_deaths'] / g, tot[side + '_early'] / g))
    print('per game:', ', '.join('%s %.2f' % (k, tot[k] / n) for k in sorted(tot) if k.startswith('read_') or k in ('join', 'leave', 'meet', 'hear_near', 'hear_far')))
