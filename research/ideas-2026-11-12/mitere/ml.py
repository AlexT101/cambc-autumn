"""Loader for decoded Mite games (extract.mjs output), both sources:
- ranked: big-arm capture replays of Mite's ranked games (~/tmp-offload/mitere/ana), rows from meta.py;
- live: our scrims against the r7 pin (~/tmp-offload/mitefit/live/ext), rows from mitefit's rows-r7.json.
Each game gets mite (team index 0/1), opp, win (Mite won), ver ('r7' or the ranked epoch label)."""
import json, gzip, os, glob
import meta
ANA = os.path.expanduser('~/tmp-offload/mitere/ana')
LIVE = os.path.expanduser('~/tmp-offload/mitefit/live/ext')
LIVE_ROWS = os.path.expanduser('~/tmp-offload/mitefit/live/rows-r7.json')
_rows = None; _live = None; _maps = {}

def rows():
    global _rows
    if _rows is None: _rows = {r['match_id']: r for r in meta.rows()}
    return _rows

def live_rows():
    global _live
    if _live is None: _live = json.load(open(LIVE_ROWS))
    return _live

def eplabel(t):
    e = meta.epoch(t)
    return 'e%02d' % e

def mapj(base, h):
    k = (base, h)
    if k not in _maps: _maps[k] = json.load(open(f'{base}/maps/{h}.json'))
    return _maps[k]

def dirs(src):
    base = ANA if src == 'ranked' else LIVE
    return [(src, d) for d in sorted(glob.glob(f'{base}/*/meta.json'))]

def all_dirs():
    return dirs('ranked') + dirs('live')

def load(sd, rounds=True, events=True):
    src, d = sd
    m = json.load(open(d))
    if not m.get('validation', {}).get('ok', True): return None
    mid = os.path.basename(m['source']).split('.')[0]
    base = ANA if src == 'ranked' else LIVE
    if src == 'ranked':
        r = rows().get(mid)
        if r is None: return None
        mite = 0 if r['m_side'] == 'a' else 1
        g = {'opp': r['opp'], 'kind': r['kind'], 'created': r['created_at'], 'ver': eplabel(r['created_at']),
             'mapname': r['map'], 'mpicks': meta.names(r['m_picks'])}
    else:
        r = live_rows().get(mid)
        if r is None: return None
        mite = 1 if r['side'] == 'a' else 0
        g = {'opp': 'us-v%d' % r['version'], 'kind': 'live', 'created': r['created'], 'ver': 'r7', 'mapname': r['map'],
             'mpicks': r['opp_picks']}
    win = m['result']['winner'] == mite
    g.update({'src': src, 'meta': m, 'mid': mid, 'mite': mite, 'win': win, 'dir': os.path.dirname(d)})
    if events: g['ev'] = [json.loads(l) for l in gzip.open(g['dir'] + '/events.jsonl.gz', 'rt')]
    if rounds: g['rd'] = json.load(gzip.open(g['dir'] + '/rounds.json.gz'))
    g['map'] = mapj(base, m['map']['hash'])
    return g

def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
