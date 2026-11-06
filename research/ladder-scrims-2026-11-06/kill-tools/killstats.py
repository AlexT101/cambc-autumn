"""Kills by big-bag carriers, Tribute emblems and channel lengths, from extract.mjs output.

usage: killstats.py EXTRACT_DIR OURS [--json OUT]
OURS: 'scrim' (our side from research/ladder-scrims-2026-11-06/data/games.jsonl by replay name),
      'both' (count both teams: self-play), or 'bot:N' (batch: bot N, 0-based, from the -12/-21 suffix).
"""
import collections, gzip, json, math, os, sys

ext, ours = sys.argv[1], sys.argv[2]
out = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
REPO = '/home/ubuntu/cambc-autumn'

side_of, opp_of = {}, {}
if ours == 'scrim':
    for l in open(f'{REPO}/research/ladder-scrims-2026-11-06/data/games.jsonl'):
        r = json.loads(l)
        if r.get('replay'):
            g = r['replay'].split('/')[-2]
            b = os.path.basename(r['replay'])[:-4]
            side_of[f'{g}-{b}'] = 0 if r['side'] == 'a' else 1
            opp_of[f'{g}-{b}'] = r['opp_name'].split()[0]

ix = json.load(open(f'{ext}/index.json'))
seen = set()
C = collections.Counter()
kill_rows, chan_rows, emb_rows = [], [], []
for g in ix['games']:
    if g['dir'] in seen or not g['ok']:
        continue
    seen.add(g['dir'])
    name = os.path.basename(g['source']).rsplit('.', 1)[0]
    if ours == 'scrim':
        if name not in side_of:
            continue
        teams = [side_of[name]]
        opp = opp_of[name]
    elif ours == 'both':
        teams, opp = [0, 1], 'self'
    else:
        n = int(ours.split(':')[1])
        suf = name.rsplit('-', 1)[1]
        teams = [0 if (suf == '12') == (n == 0) else 1]
        opp = 'local'
    d = f"{ext}/{g['dir']}"
    meta = json.load(open(f'{d}/meta.json'))
    R = json.load(gzip.open(f'{d}/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(f'{d}/events.jsonl.gz', 'rt')]
    champs = {c['id']: c for c in R['champions']}
    name_of = {c['id']: c['name'] for c in meta['champions']}
    team_of = {c['id']: c['team'] for c in meta['champions']}
    rix = {r: i for i, r in enumerate(R['round'])}
    won = g['winner']
    for t in teams:
        C['games'] += 1
        C['wins'] += won == t
    def at(cid, key, r):
        i = rix.get(r)
        return champs[cid][key][i] if i is not None else None
    for e in ev:
        k = e['k']
        if k == 'death' and 'by' in e and team_of.get(e['by']) in teams and e['by'] is not None:
            killer, r = e['by'], e['r']
            t = team_of[killer]
            pre = at(killer, 'gems', r - 1) or 0
            trib = R['gems'][t][rix[r - 1]] if r - 1 in rix else 0
            etrib = R['gems'][1 - t][rix[r - 1]] if r - 1 in rix else 0
            gain = e.get('gemsTo', 0) or 0
            # allies (alive, not the killer, not the linked partner's death) within 4 of the victim
            vx, vy = e['at']
            near = 0
            for cid, c in champs.items():
                if cid == killer or team_of[cid] != t:
                    continue
                i = rix.get(r - 1)
                if i is None or not c['alive'][i] or c['x'][i] is None:
                    continue
                if max(abs(c['x'][i] - vx), abs(c['y'][i] - vy)) <= 4:
                    near += 1
            kill_rows.append(dict(game=name, opp=opp, r=r, killer=name_of[killer], pre=pre, gain=gain, trib=trib,
                                  etrib=etrib, wins_pre=pre + trib >= 1000, near=near, assists=len(e.get('assists', [])),
                                  linked=e.get('linked') is not None, won=won == t, tribute_emblem=False))
            # what the killer's bag did next: banked (tribute_end) or lost (death) first
            kill_rows[-1]['fate'] = None
            for f in ev:
                if f['s'] <= e['s']:
                    continue
                if f['k'] == 'tribute_end' and f['a'] == killer:
                    kill_rows[-1]['fate'] = ('banked', f['gems'], f['r'] - r)
                    break
                if f['k'] == 'death' and f['v'] == killer:
                    kill_rows[-1]['fate'] = ('died', f['gems'], f['r'] - r)
                    break
        if k == 'tribute_start' and team_of.get(e['a']) in teams:
            chan_rows.append(dict(game=name, opp=opp, a=name_of[e['a']], gems=e['gems'], dur=e['dur'], r=e['r'], end=None))
        if k in ('tribute_end', 'tribute_cancel') and team_of.get(e['a']) in teams:
            for c in reversed(chan_rows):
                if c['game'] == name and c['a'] == name_of[e['a']] and c['end'] is None:
                    c['end'] = 'done' if k == 'tribute_end' else e.get('cause')
                    c['ran'] = e['r'] - c['r']
                    break
        if k == 'shop' and team_of.get(e['a']) in teams:
            for it, n in e.get('items', {}).items():
                if 'Tribute Emblem' in it and n > 0:
                    emb_rows.append(dict(game=name, opp=opp, a=name_of[e['a']], r=e['r'], bag=at(e['a'], 'gems', e['r'])))

def pr(*a):
    print(*a)

pr(f"games {C['games']} wins {C['wins']}")
K = kill_rows
pr(f"kills by ours: {len(K)} ({len(K)/C['games']:.2f}/game); with victim bag>0: {sum(1 for k in K if k['gain']>0)}")
for label, pred in [('pre>=50', lambda k: k['pre'] >= 50), ('pre>=100', lambda k: k['pre'] >= 100),
                    ('pre>=150 (15+ turns)', lambda k: k['pre'] >= 150), ('pre>=300', lambda k: k['pre'] >= 300),
                    ('pre>=600', lambda k: k['pre'] >= 600), ('pre>=1000', lambda k: k['pre'] >= 1000),
                    ('pre+trib>=1000 (bag wins)', lambda k: k['wins_pre']),
                    ('pre+gain>=300', lambda k: k['pre'] + k['gain'] >= 300), ('pre+gain>=600', lambda k: k['pre'] + k['gain'] >= 600),
                    ('pre+gain>=1000', lambda k: k['pre'] + k['gain'] >= 1000)]:
    s = [k for k in K if pred(k)]
    if not s:
        pr(f'  {label}: 0'); continue
    g = [k['gain'] for k in s]
    near = sum(1 for k in s if k['near'] > 0)
    fates = collections.Counter(k['fate'][0] if k['fate'] else 'none' for k in s)
    lost = sum(k['fate'][1] for k in s if k['fate'] and k['fate'][0] == 'died')
    by = collections.Counter(k['killer'] for k in s)
    pr(f"  {label}: {len(s)} ({len(s)/C['games']:.3f}/game), gained {sum(g)} (mean {sum(g)/len(s):.0f}, gain>0 {sum(1 for x in g if x>0)}),"
       f" ally within 4: {near}, fate {dict(fates)} (gems lost after {lost}), won {sum(k['won'] for k in s)}/{len(s)}, by {dict(by.most_common(4))}")
pr(f"Tribute emblems bought: {len(emb_rows)} in {C['games']} games; {collections.Counter(e['a'] for e in emb_rows)}; bags at purchase {[e['bag'] for e in emb_rows][:20]}")
done = [c for c in chan_rows if c['end'] == 'done']
canc = [c for c in chan_rows if c['end'] not in ('done', None)]
def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None
pr(f"channels started {len(chan_rows)}: completed {len(done)} (dur median {q([c['dur'] for c in done],.5)}, p90 {q([c['dur'] for c in done],.9)}, max {max([c['dur'] for c in done], default=0)});"
   f" cancelled {len(canc)} (dur median {q([c['dur'] for c in canc],.5)}, p90 {q([c['dur'] for c in canc],.9)}) by {dict(collections.Counter(c['end'] for c in canc))}")
for lo, hi in [(1, 5), (6, 15), (16, 30), (31, 60), (61, 1000)]:
    s = [c for c in chan_rows if lo <= c['dur'] <= hi and c['end']]
    if s:
        dn = sum(1 for c in s if c['end'] == 'done')
        pr(f"  dur {lo}-{hi}: {len(s)} starts, {dn} completed ({dn/len(s):.0%}), gems started {sum(c['gems'] for c in s)}, banked {sum(c['gems'] for c in s if c['end']=='done')}")
if out:
    json.dump(dict(counts=C, kills=K, chans=chan_rows, emblems=emb_rows), open(out, 'w'))
