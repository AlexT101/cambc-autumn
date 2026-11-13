"""Line E diagnosis: Monolith operations in a debug batch. Reads the extracted replays (tools/replay/extract.mjs) and
both teams' stdout (MONO START/END/STAGE/ENGAGE lines).

    py research/mx-tethys/scripts/mono_diag.py ANALYSIS_ROOT BATCH_NAME [CAND_NAME]

Per game with a Monolith: wakes, damage done per wake episode (until it sleeps or is cleared), clears, captures by
side, champion deaths near an awake Monolith, Monolith hits by target, op lengths, END reasons (what the body
switched to, the Monolith's state and health, damage taken in the op).
"""
import gzip, json, re, sys, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

WT = Path('/home/ubuntu/wt/mx-tethys')
START = re.compile(r'MONO START (\d+) (\d+) g(\d+) (\S) expected (\d+) output (\S+) trips (\d+) hp (\S+)/(\S+)')
END = re.compile(r'MONO END (\d+) (\d+) g(\d+) for (\d+) taken (\S+) state (\d+) value (\S+) now g(-?\d+) (\S) value (\S+)')
ENGAGE = re.compile(r'MONO ENGAGE (\d+) (\d+) g(\d+) crew-in-sight (\d+)')
STAGE = re.compile(r'MONO STAGE (\d+) (\d+) g(\d+)')
DECLARE = re.compile(r'MONO DECLARE (\d+) (\d+) g(\d+)')
OPEND = re.compile(r'MONO OPEND (\d+) (\d+) g(\d+) (\S+) for (\d+) hp (\S+)')


def lenb(n):
    return '1' if n <= 1 else '2-5' if n <= 5 else '6-20' if n <= 20 else '21-60' if n <= 60 else '61+'


def one(args):
    dd, cand = args
    try:
        m = json.loads((dd / 'meta.json').read_text())
        mp = json.loads((dd / m['mapFile']).read_text())
    except Exception:
        return None
    camps = {c['id']: c for c in mp['camps']}
    mono_groups = {g['id'] for g in mp['groups'] if 'Monolith' in g['types']}
    if not mono_groups:
        return None
    try:
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
        rounds = json.load(gzip.open(dd / 'rounds.json.gz', 'rt'))
        z = zipfile.ZipFile(WT / m['source'])
    except Exception:
        return None
    names = [t['name'] for t in m['teams']]
    ct = names.index(cand) if cand in names else 0
    out = Counter(games=1)
    lists = defaultdict(list)
    win = m['result']['winner']
    team_of = {c['id']: c['team'] for c in m['champions']}
    name_of = {c['id']: c['name'] for c in m['champions']}
    mono_camps = {cid for cid, c in camps.items() if c['type'] == 'Monolith'}
    mono_tiles = {g['id']: [(camps[c]['x'], camps[c]['y']) for c in g['camps'] if camps[c]['type'] == 'Monolith'] for g in mp['groups'] if g['id'] in mono_groups}
    out['monoliths'] += len(mono_camps)
    # Group hp by round (groupCols round, group, state, team, timer, respawn, awake, hp).
    hp = defaultdict(dict)
    awake = defaultdict(dict)
    for row in rounds['groups']:
        r, g = row[0], row[1]
        if g in mono_groups:
            hp[g][r] = row[7]
            awake[g][r] = row[6]
    caps = Counter()
    last_clear = {}
    for e in ev:
        k = e['k']
        if k == 'capture' and e['g'] in mono_groups:
            t = e['team']
            lc = last_clear.get(e['g'])
            if lc is not None and lc != t:
                out['stolen_from_' + ('cand' if lc == ct else 'ref')] += 1
            caps[t] += 1
            side = 'cand' if t == ct else 'ref'
            out['cap_' + side] += 1
            out['cap_r_sum'] += e['r']
            lists['cap_round'].append(e['r'])
            holders = len(e.get('shares', []))
            out['cap_holders_%d' % holders] += 1
            for sh in e.get('shares', []):
                out['cap_by_' + name_of.get(sh[0], '?')] += 1
        elif k == 'group_clear' and e['g'] in mono_groups:
            out['clears'] += 1
            by = e.get('by')
            last_clear[e['g']] = team_of.get(by)
            out['clear_by_' + ('cand' if team_of.get(by) == ct else 'ref')] += 1
        elif k == 'group_wake' and e['g'] in mono_groups:
            out['wakes'] += 1
            by = e.get('by')
            out['wake_by_' + ('cand' if team_of.get(by) == ct else 'ref')] += 1
        elif k == 'camp_attack' and e.get('camp') in mono_camps:
            out['mono_hits'] += 1
            out['mono_hit_dmg'] += e.get('dmg', 0)
            out['mono_hit_' + name_of.get(e.get('tgt'), '?')] += 1
        elif k == 'death':
            at = e.get('at')
            for g in mono_groups:
                if at and awake[g].get(e['r']) and min(max(abs(at[0] - x), abs(at[1] - y)) for x, y in mono_tiles[g]) <= 6:
                    side = 'cand' if team_of.get(e['v']) == ct else 'ref'
                    out[side + '_deaths_at_awake_mono'] += 1
                    break
    if caps:
        out['games_capture'] += 1
        if caps[0] != caps[1]:
            out['games_capture_diff'] += 1
            out['more_caps_won'] += int((caps[0] > caps[1]) == (win == 0))
    # Wake episodes (group rows are written on change): from a wake to sleep or clear; damage done in it.
    import bisect
    rows_of = defaultdict(list)
    for row in rounds['groups']:
        if row[1] in mono_groups: rows_of[row[1]].append(row)
    for g, rows in rows_of.items():
        ep = None
        prev_hp = None
        for row in rows:
            r, st, aw, h = row[0], row[2], row[6], row[7]
            if ep is None and aw == 1 and h > 0:
                ep = [r, prev_hp if prev_hp is not None else h]
            elif ep is not None and (aw != 1 or h <= 0):
                tiles = mono_tiles[g]
                crew = [0.0, 0.0]
                for c in rounds['champions']:
                    for rr in range(ep[0], r):
                        i = rr - 1
                        if i < len(c['x']) and c['alive'][i] and min(max(abs(c['x'][i] - x), abs(c['y'][i] - y)) for x, y in tiles) <= 5:
                            crew[c['team']] += 1
                span = max(1, r - ep[0])
                main = max(crew) / span
                lists['ep_crew_' + ('clear' if h <= 0 else 'left')].append(main)
                lists['ep_both_' + ('clear' if h <= 0 else 'left')].append(min(crew) / span)
                lists['ep_len_' + ('clear' if h <= 0 else 'left')].append(r - ep[0])
                lists['ep_len'].append(r - ep[0])
                lists['ep_dmg'].append(ep[1] - h)
                out['episodes'] += 1
                out['ep_cleared'] += int(h <= 0)
                if h > 0: lists['ep_sleep_hp'].append(h)
                ep = None
            prev_hp = h
    def at(g, r):
        rows = rows_of.get(g)
        if not rows: return None
        i = bisect.bisect_right([x[0] for x in rows], r) - 1
        return rows[i] if i >= 0 else None
    for c in rounds['champions']:
        if name_of.get(c['id']) == 'Prism':
            side = 'cand' if c['team'] == ct else 'ref'
            for rr in (250, 500):
                if rr - 1 < len(c['foc']): lists['%s_prism_focus_%d' % (side, rr)].append(c['foc'][rr - 1])
    # Stdout traces, both teams.
    for t, tag in ((0, 'a'), (1, 'b')):
        side = 'cand' if t == ct else 'ref'
        try:
            data = z.read('team-%s.stdout' % tag).decode('latin1')
        except KeyError:
            continue
        for mm in START.finditer(data):
            out[side + '_start'] += 1
            out[side + '_start_mode_' + mm.group(4)] += 1
        for mm in ENGAGE.finditer(data):
            out[side + '_engage'] += 1
        for mm in STAGE.finditer(data):
            out[side + '_stage'] += 1
        for mm in DECLARE.finditer(data):
            out[side + '_declare'] += 1
        for mm in OPEND.finditer(data):
            out[side + '_opend_' + mm.group(4)] += 1
            lists[side + '_op_len_' + mm.group(4)].append(int(mm.group(5)))
            lists[side + '_op_hp_' + mm.group(4)].append(float(mm.group(6)))
        for mm in END.finditer(data):
            r, cid, g, n, taken, state, v, now, mode, w = mm.groups()
            r, n, g, state = int(r), int(n), int(g), int(state)
            out[side + '_end'] += 1
            out[side + '_end_len_' + lenb(n)] += 1
            out[side + '_end_state_' + state.__str__()] += 1
            out[side + '_end_mode_' + mode] += 1
            out[side + '_end_who_' + name_of.get(int(cid), '?')] += 1
            if float(taken) > 0: out[side + '_end_hurt'] += 1
            row = at(g, r)
            if row is not None:
                if row[7] > 0: lists[side + '_end_hp_alive'].append(row[7])
                out[side + '_end_awake_%d' % row[6]] += 1
                if row[6] == 1: lists[side + '_end_len_awake'].append(n)
            if float(v) >= 0 and float(w) > 0:
                lists[side + '_end_ratio'].append(float(v) / float(w))
            else:
                out[side + '_end_unseen'] += 1
    return out, dict(lists)


def q(xs, ps=(0.1, 0.25, 0.5, 0.75, 0.9)):
    if not xs: return '-'
    xs = sorted(xs)
    return ' '.join('%g' % round(xs[min(len(xs) - 1, int(p * len(xs)))], 3) for p in ps)


if __name__ == '__main__':
    root, batch = Path(sys.argv[1]), sys.argv[2]
    cand = sys.argv[3] if len(sys.argv) > 3 else ''
    idx = json.loads((root / 'index.json').read_text())
    dirs = sorted({root / g['dir'] for g in idx['games'] if batch in g['source']})
    tot = Counter()
    lists = defaultdict(list)
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(one, [(d, cand) for d in dirs], chunksize=8):
            if r:
                tot.update(r[0])
                for k, v in r[1].items(): lists[k] += v
    n = max(1, tot['games'])
    print('mono games', tot['games'], 'of', len(dirs))
    for k in sorted(tot):
        print('%-28s %8d  %.3f/game' % (k, tot[k], tot[k] / n))
    for k in sorted(lists):
        print('%-16s n %6d mean %.3g  q10/25/50/75/90 %s' % (k, len(lists[k]), sum(lists[k]) / max(1, len(lists[k])), q(lists[k])))
