"""Long tribute channels: how each ended, and the state at its start.

usage: chanforensics.py EXTRACT_DIR MODE RACE_PKL OUT.json
MODE: 'scrim' (our side from data/games.jsonl; enemy channels too), 'mirror' (self-play: both teams are ours) or
'ab' (an ab.py batch: CAND is 'us', REF 'them', by the -12/-21 suffix). RACE_PKL '-': no margins.
RACE_PKL: race-model samples (load_live.py output; for 'mirror', built by this script's --race step).
Each row: side (us/them), opp, champion, round, bag, turns, altar, end (done, death, stun, lock, manual, gameend),
killer, enemies within 6 at death, our bodies within 3/6 at start, enemy bodies within 6 at start, a lock of ours
on the altar, seen by an enemy at start, race margin at start (the channeller's side's view, every 10 rounds).
"""
import gzip, json, os, pickle, sys
sys.path.insert(0, '/tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad/race')
import racemodel as rm

P = rm.Params(rate_window=600, lag=80, stale_score=0, stale_growth=0, risk_delay=1, lock_delay=15)
REPO = '/home/ubuntu/cambc-autumn'
ext, mode, race_pkl, out = sys.argv[1:5]
MIN = 10

# margin[(dir, team)][round] -> margin from that team's view (the channeller's own sample when there is one)
margin = {}
for g in (pickle.load(open(race_pkl, 'rb')) if race_pkl != '-' else []):
    d = os.path.basename(g['replay']) if g['replay'].startswith('live-analysis') else g['replay']
    team = 0 if g['team_a'] else 1
    m = margin.setdefault((d, team), {})
    for smp in g['samples']:
        m.setdefault(smp['r'], {})[smp['h']] = smp


def margin_of(key, r, h=None):
    """The race margin from side `key`'s view at round r // 10 * 10: body h's sample, else any; None if none."""
    mm = margin.get(key, {}).get(r // 10 * 10, {})
    smp = mm.get(h) if h in mm else next(iter(mm.values()), None)
    if smp is None:
        return None
    v = rm.evaluate(smp, P)
    return None if v is None else rm.margin(v[0], v[1])

side_of, opp_of = {}, {}
if mode == 'scrim':
    for l in open(f'{REPO}/research/ladder-scrims-2026-11-06/data/games.jsonl'):
        r = json.loads(l)
        if r.get('replay'):
            key = f"{r['replay'].split('/')[-2]}-{os.path.basename(r['replay'])[:-4]}"
            side_of[key] = 0 if r['side'] == 'a' else 1
            opp_of[key] = r['opp_name'].split()[0]

ix = json.load(open(f'{ext}/index.json'))
rows, seen = [], set()
for g in ix['games']:
    if g['dir'] in seen or not g['ok']:
        continue
    seen.add(g['dir'])
    name = os.path.basename(g['source']).rsplit('.', 1)[0]
    if mode == 'scrim':
        if name not in side_of:
            continue
        ours_teams, opp = [side_of[name]], opp_of[name]
    elif mode == 'ab':
        ours_teams, opp = [0 if name.rsplit('-', 1)[1] == '12' else 1], 'ref'
    else:
        ours_teams, opp = [0, 1], 'mirror'
    d = f"{ext}/{g['dir']}"
    meta = json.load(open(f'{d}/meta.json'))
    R = json.load(gzip.open(f'{d}/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(f'{d}/events.jsonl.gz', 'rt')]
    champs = {c['id']: c for c in R['champions']}
    name_of = {c['id']: c['name'] for c in meta['champions']}
    team_of = {c['id']: c['team'] for c in meta['champions']}
    rix = {r: i for i, r in enumerate(R['round'])}
    last = R['round'][-1]

    def pos(cid, r):
        i = rix.get(r)
        c = champs[cid]
        if i is None or not c['alive'][i] or c['x'][i] is None:
            return None
        return c['x'][i], c['y'][i]

    def within(team, p, r, k, skip=None):
        n = 0
        for cid in champs:
            if team_of[cid] != team or cid == skip:
                continue
            q = pos(cid, r)
            if q and max(abs(q[0] - p[0]), abs(q[1] - p[1])) <= k:
                n += 1
        return n

    open_ = {}
    first_row = len(rows)
    for e in ev:
        k = e['k']
        if k == 'tribute_start':
            a = e['a']
            t = team_of[a]
            if e['dur'] < MIN or (t not in ours_teams and mode not in ('scrim', 'ab')):
                continue
            r = e['r']
            p = tuple(e['at'])
            i = rix.get(r)
            lock = any(lk[0] == t and (lk[1], lk[2]) == tuple(e['altar']) for lk in (R['locks'][i] if i is not None else []))
            elock = any(lk[0] != t and (lk[1], lk[2]) == tuple(e['altar']) for lk in (R['locks'][i] if i is not None else []))
            seen_by = bool(champs[a]['seenBy'][i]) if i is not None else None
            mg = margin_of((g['dir'], t), r, a)
            # their side's channel in a scrim: our view of the race, as theirs (negated)
            if mode != 'mirror' and t not in ours_teams:
                mg = margin_of((g['dir'], 1 - t), r)
                mg = -mg if mg is not None else None
            rows.append(dict(game=g['dir'], cid=a, side='us' if t in ours_teams else 'them', opp=opp, a=name_of[a], r=r,
                             bag=e['gems'], turns=e['dur'], altar=e['altar'], end=None, killer=None, enemies_at_death=None,
                             ours3=within(t, p, r, 3, a), ours6=within(t, p, r, 6, a), enemies6=within(1 - t, p, r, 6),
                             lock=lock, enemy_lock=elock, seen=seen_by, margin=mg,
                             trib=R['gems'][t][i] if i is not None else None, etrib=R['gems'][1 - t][i] if i is not None else None,
                             sees=bool(champs[a]['sees'][i]) if i is not None else None,
                             won=meta['result']['winner'] == t, last=last))
            open_[a] = rows[-1]
        elif k in ('tribute_end', 'tribute_cancel') and e['a'] in open_:
            row = open_.pop(e['a'])
            row['end'] = 'done' if k == 'tribute_end' else e.get('cause', 'other')
            row['ended'] = e['r']
            j = rix.get(e['r'])
            q = pos(e['a'], e['r']) or tuple(row.get('at', (0, 0)))
            row['enemies6_end'] = within(1 - team_of[e['a']], q, e['r'], 6) if pos(e['a'], e['r']) else None
            row['enemies3_end'] = within(1 - team_of[e['a']], q, e['r'], 3) if pos(e['a'], e['r']) else None
            row['seen_end'] = bool(champs[e['a']]['seenBy'][j]) if j is not None else None
            row['bag_end'] = e.get('gems')
            if row['end'] == 'death':
                for f in ev:
                    if f['k'] == 'death' and f['v'] == e['a'] and abs(f['r'] - e['r']) <= 1:
                        row['killer'] = name_of.get(f.get('by'))
                        row['enemies_at_death'] = within(1 - team_of[e['a']], tuple(f['at']), max(1, f['r'] - 1), 6)
                        break
    for row in open_.values():
        row['end'] = 'gameend'
        row['ended'] = last
    # The bag's fate after a failed channel: banked by the same body later (a tribute ending with at least 90% of
    # it), lost at its death, or still carried at the game's end; and the rounds to that.
    by_body = {}
    for e in ev:
        if e['k'] in ('tribute_end', 'death', 'tribute_start'):
            by_body.setdefault(e.get('a', e.get('v')), []).append(e)
    for row in rows[first_row:]:
        cid = row['cid']
        row['fate'], row['fate_r'], row['restarts'] = 'carried', last, 0
        for f in by_body.get(cid, []):
            if f['r'] < row['r'] or (f['r'] == row['r'] and f['k'] == 'tribute_start'):
                continue
            if f['k'] == 'tribute_start' and f['r'] <= row['ended'] + 3 and f['r'] >= row['ended']:
                row['restarts'] += 1
            if f['k'] == 'tribute_end' and f['gems'] >= 0.9 * row['bag']:
                row['fate'], row['fate_r'] = 'banked', f['r']
                break
            if f['k'] == 'death':
                row['fate'], row['fate_r'] = 'lost', f['r']
                break
json.dump(rows, open(out, 'w'))
print(len(rows), 'channels of', MIN, '+ turns in', len(seen), 'games ->', out)
