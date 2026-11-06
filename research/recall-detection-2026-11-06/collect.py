"""Every recall in the extracted games, with its outcome and the round-end windows an observer could read.

py research/recall-detection-2026-11-06/collect.py [CACHE] > counts.json
CACHE (default replays/.analysis-recall) is extract.mjs --out of replays/.recall-detection/{scrims,selfplay,ladder}.

A window is a round-end snapshot with the recall running: what any champion acting before the recaller's next turn
reads. Window k (1-based) has chanT = full - k. Outcome: completed (recall_end), interrupted (recall_cancel by
damage, stun, death or any non-manual step), feint (recall_cancel by the champion's own Cancel channel step), open
(still running at game end).
Intent is decided at the recaller's next own turn: one taken channelling (turn code 3) is a choice to keep it. Classes:
completed; kept_int (kept, then damaged, stunned or killed); abandoned (kept, then cancelled by hand); feint
(cancelled at its first own turn); undecided (interrupted before its first own turn); open.
Output: counts of recalls by a compact key (KEY below), aggregated per team.
"""
import gzip, json, os, re, sys
from multiprocessing import Pool

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'replays', '.analysis-recall')
HOME_EMBLEMS = {31, 33, 35}
T = [0.25, 0.33, 0.50, 0.66, 0.75, 1.0]
KEY = ['team', 'full', 'cls', 'cause', 'nw', 'w1b', 'w1seen', 'w1gems', 'w1dist', 'cb', 'cseenb', 'nextkept']

SCRIMS = {}
for line in open(os.path.join(ROOT, 'research', 'ladder-scrims-2026-11-06', 'data', 'games.jsonl')):
    r = json.loads(line)
    SCRIMS[(r['group'], int(r['position']))] = r


def labels(source, meta):
    """Team label per side, or None to skip the side."""
    m = re.search(r'/scrims/([^/]+)/(\d+)-', source)
    if m:
        r = SCRIMS[(m.group(1), int(m.group(2)))]
        ours = 0 if r['side'] == 'a' else 1
        opp = {'Intercontinental Fish': 'Fish', 'Mite': 'Mite'}[r['opp_name']]
        lab = [None, None]
        lab[ours], lab[1 - ours] = f"ocean-v{r['version']}", opp
        return lab, r['created'][:10]
    if '/selfplay/' in source:
        return ['astraeus-self', 'astraeus-self'], '2026-11-06'
    m = re.search(r'/ladder/(\d{8})-', source)
    if m:
        names = [t.get('name', '') for t in meta['teams']]
        lab = [{'Intercontinental Fish': 'Fish-ladder', 'Mite': 'Mite-ladder'}.get(n) for n in names]
        d = m.group(1)
        return lab, f'{d[:4]}-{d[4:6]}-{d[6:]}'
    return [None, None], None


def spawn_dist(rect, x, y):
    dx = max(rect['minX'] - x, 0, x - rect['maxX'])
    dy = max(rect['minY'] - y, 0, y - rect['maxY'])
    return max(dx, dy)


def hb(hp):
    """Smallest index i with hp < T[i]; len(T) at full health. hp < T[i] iff hb <= i."""
    return next((i for i, t in enumerate(T) if hp < t), len(T))


def game(row):
    d = os.path.join(CACHE, row['dir'])
    meta = json.load(open(os.path.join(d, 'meta.json')))
    lab, date = labels(row['source'], meta)
    if not any(lab):
        return {}
    mp = json.load(open(os.path.normpath(os.path.join(d, meta['mapFile']))))
    R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    rix = {r: i for i, r in enumerate(R['round'])}
    ch = {c['id']: c for c in R['champions']}
    types = {c['id']: c['type'] for c in meta['champions']}
    out, open_ = [], {}
    for e in ev:
        k = e['k']
        if k == 'recall_start':
            open_[e['a']] = e
        elif k in ('recall_end', 'recall_cancel') and e['a'] in open_:
            s = open_.pop(e['a'])
            out.append((s, e))
    for a, s in open_.items():
        out.append((s, None))
    recs = []
    for s, e in out:
        a = s['a']; c = ch[a]; team = c['team']
        if lab[team] is None:
            continue
        r0 = s['r']; i0 = rix.get(r0)
        if i0 is None:
            continue
        items = c['items'][i0] or []
        home = any(items[j] in HOME_EMBLEMS and items[j + 1] > 0 for j in range(0, len(items), 2))
        full = 3 if home else 5
        if e is None:
            r1, cause = None, None
        else:
            r1, cause = e['r'], (None if e['k'] == 'recall_end' else e['cause'])
        last = (r1 - 1) if r1 is not None else R['round'][-1]
        wins = []
        for r in range(r0, last + 1):
            i = rix.get(r)
            if i is None or c['chan'][i] != 1:
                break
            seen = bool(c['seenBy'][i]) or (i + 1 < len(R['round']) and bool(c['seenBy'][i + 1]))
            wins.append((r - r0 + 1, c['hp'][i] / c['maxHp'][i], c['gems'][i],
                         spawn_dist(mp['spawn'][team], c['x'][i], c['y'][i]), seen))
        end = r1 if r1 is not None else R['round'][-1]
        dec = sum(1 for r in range(r0 + 1, end + 1) if r in rix and c['turn'][rix[r]] == 3)
        if e is None: cls = 'open'
        elif e['k'] == 'recall_end': cls = 'completed'
        elif dec >= 1: cls = 'abandoned' if cause == 'manual' else 'kept_int'
        else: cls = 'feint' if cause == 'manual' else 'undecided'
        if cause not in (None, 'manual', 'damage', 'stun', 'death'):
            cause = 'other'
        w1 = next((w for w in wins if w[0] == 1), None)
        later = [w for w in wins if w[0] >= 2]
        seenl = [w for w in later if w[4]]
        recs.append({'a': a, 'r0': r0, 'r1': r1, 'team': lab[team], 'full': full, 'cls': cls, 'cause': cause,
                     'nw': min(len(wins), 3),
                     'w1b': hb(w1[1]) if w1 else -1, 'w1seen': int(w1[4]) if w1 else -1,
                     'w1gems': (0 if w1[2] == 0 else 1 if w1[2] < 10 else 2) if w1 else -1,
                     'w1dist': (0 if w1[3] == 0 else 1 if w1[3] <= 5 else 2) if w1 else -1,
                     'cb': min(hb(w[1]) for w in later) if later else -1,
                     'cseenb': min(hb(w[1]) for w in seenl) if seenl else -1, 'nextkept': -1})
    # Undecided: was the same champion's next recall, started within 2 rounds of the interruption, kept?
    by = {}
    for r in recs:
        by.setdefault(r['a'], []).append(r)
    for lst in by.values():
        lst.sort(key=lambda r: r['r0'])
        for j, r in enumerate(lst):
            if r['cls'] == 'undecided' and j + 1 < len(lst) and lst[j + 1]['r0'] <= r['r1'] + 2:
                r['nextkept'] = int(lst[j + 1]['cls'] in ('completed', 'kept_int', 'abandoned'))
    cnt = {}
    for r in recs:
        k = '|'.join(str(r[f]) for f in KEY)
        cnt[k] = cnt.get(k, 0) + 1
    return {'counts': cnt, 'date': date, 'teams': [l for l in lab if l]}


if __name__ == '__main__':
    ix = json.load(open(os.path.join(CACHE, 'index.json')))
    seen, rows = set(), []
    for g in ix['games']:
        if g.get('ok') is False or g['dir'] in seen:
            continue
        seen.add(g['dir']); rows.append(g)
    total, games, dates = {}, {}, {}
    with Pool(8) as p:
        for res in p.imap_unordered(game, rows, chunksize=4):
            for k, v in res.get('counts', {}).items():
                total[k] = total.get(k, 0) + v
            for t in set(res.get('teams', [])):
                games[t] = games.get(t, 0) + 1
                dates.setdefault(t, set()).add(res['date'])
    json.dump({'key': KEY, 'thresholds': T, 'games': games, 'dates': {t: sorted(d) for t, d in dates.items()},
               'counts': total}, sys.stdout)
