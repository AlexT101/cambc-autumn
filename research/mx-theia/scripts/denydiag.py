# Why REF's winning-size tribute channels (score + bag >= 1000 at start) complete against CAND (a debug ab.py batch,
# CAND team A in -12 replays, B in -21), from CAND's DQ traces (decide_denial's verdict each turn: late / wait / cool /
# go), its D branch lines, and the replay's vision, stuns and deaths. Prints one cause per completed channel and the
# same for REF's own cancels (cause 'manual'). Args: EXTRACT_DIR [REPO].
import json, gzip, sys, os, re, zipfile, collections, statistics
from concurrent.futures import ProcessPoolExecutor
ROOT = sys.argv[1]; REPO = sys.argv[2] if len(sys.argv) > 2 else '/home/ubuntu/wt/mx-theia'
DQ = re.compile(rb'^[\s\0]*DQ (\d+) (\d+) ([TA]) (-?\d+) (-?\d+) (-?\d+) (\d) (\d) (\d+) (\w+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+)\s*$', re.M)
DL = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
MADE = re.compile(rb'^[\s\0]*DENY (\d+) (\d+) (-?\d+) (-?\d+) (-?\d+) made-(\w+)\s*$', re.M)
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def one(item):
    dn, row = item; d = os.path.join(ROOT, dn); src = row['source']
    ci = 0 if src.endswith('-12.repl26a') else 1
    try:
        meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
        z = zipfile.ZipFile(os.path.join(REPO, src)); out = z.read('team-a.stdout' if ci == 0 else 'team-b.stdout')
    except Exception as ex:
        return None
    team = {x['id']: x['team'] for x in meta['champions']}; names = {x['id']: x['name'] for x in meta['champions']}
    rd = {r: i for i, r in enumerate(R['round'])}; CH = {c['id']: c for c in R['champions']}
    dq = collections.defaultdict(list)  # handle -> [(round, kind, altar, left, stop, walk, kept, margin, verdict, cheb, steps, x, locks, cd0, cd1)]
    for m in DQ.finditer(out):
        g = m.groups(); dq[int(g[1])].append((int(g[0]), g[2].decode(), int(g[3]), int(g[4]), int(g[5]), int(g[6]), int(g[7]), int(g[8]), g[9].decode(), int(g[10]), int(g[11]), int(g[12]), int(g[13]), int(g[14]), int(g[15])))
    D = {}
    for m in DL.finditer(out): D[(int(m.group(1)), int(m.group(2)))] = m.group(3).decode()
    made = collections.defaultdict(list)
    for m in MADE.finditer(out): made[int(m.group(2))].append((int(m.group(1)), m.group(6).decode()))
    ours = [c['id'] for c in R['champions'] if c['team'] == ci]
    res = []; open_ = {}
    evs = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    deaths = collections.defaultdict(list)
    for e in evs:
        if e['k'] == 'death': deaths[e['v']].append((e['r'], e.get('by'), e.get('camp')))
    for e in evs:
        if e['k'] == 'tribute_start':
            t = team[e['a']]; i = rd.get(e['r'])
            if t != ci and i is not None and R['gems'][t][i] + e['gems'] >= 1000: open_[e['a']] = (e['r'], e['dur'], e['gems'], tuple(e['altar']))
        elif e['k'] in ('tribute_end', 'tribute_cancel') and e['a'] in open_:
            r0, dur, gems, altar = open_.pop(e['a']); r1 = e['r']
            out_ = 'done' if e['k'] == 'tribute_end' else e.get('cause')
            if out_ not in ('done', 'manual'): continue
            ch = CH[e['a']]; i0 = rd[r0]; i1 = rd.get(r1, len(R['round']) - 1)
            info = classify(R, rd, CH, ours, e['a'], r0, r1, i0, i1, dq, D, made, names, altar, deaths)
            info['outcome'] = out_; info['dur'] = dur; info['gems'] = gems; info['map'] = meta['map']['name']; info['ch'] = names[e['a']]
            res.append(info)
    return res

def classify(R, rd, CH, ours, cid, r0, r1, i0, i1, dq, D, made, names, altar, deaths):
    ch = CH[cid]
    alive_any = any(CH[b]['alive'][j] for b in ours for j in range(i0, i1 + 1))
    seen = {b: [R['round'][j] for j in range(i0, i1 + 1) if b in (ch['seenBy'][j] or [])] for b in ours}
    lines = {b: [x for x in dq.get(b, []) if r0 <= x[0] <= r1] for b in ours}
    info = {'alive': sum(CH[b]['alive'][i0] for b in ours), 'seen_any': any(seen[b] for b in ours)}
    nearest = min([cheb((CH[b]['x'][j], CH[b]['y'][j]), altar) for b in ours for j in range(i0, i1 + 1) if CH[b]['alive'][j]] or [99])
    info['nearest_altar'] = nearest
    if not alive_any: return dict(info, cause='no body alive')
    if not any(lines[b] for b in ours):
        return dict(info, cause='seen, never targeted' if info['seen_any'] else 'never seen, no alarm')
    # Per body: verdict sequence
    gos = {b: [x for x in lines[b] if x[8] == 'go'] for b in ours}
    if any(gos[b] for b in ours):
        # the body whose go began first
        b = min((b for b in ours if gos[b]), key=lambda b: gos[b][0][0])
        g0 = gos[b][0]; rg = g0[0]
        after = [j for j in range(rd.get(rg, i0), i1 + 1)]
        died = any(not CH[b]['alive'][j] for j in after)
        stunned = any(CH[b]['stun'][j] for j in after)
        br = collections.Counter(D.get((R['round'][j], b), '?') for j in after if CH[b]['alive'][j])
        made_b = [m for m in made.get(b, []) if r0 <= m[0] <= r1]
        info.update(go_body=names[b], go_left=g0[3], go_stop=g0[4], go_kind=g0[1], go_cheb=g0[9], go_steps=g0[10], go_rounds=len(gos[b]), go_margin=g0[7], go_locks=g0[12], go_cd=(g0[13], g0[14]), branches=dict(br), made=made_b)
        if made_b: return dict(info, cause='go, stop made but channel done (?)')
        if died:
            dr = [x for x in deaths.get(b, []) if rg <= x[0] <= r1]
            if dr:
                prev = [x for x in lines[b] if x[0] <= dr[0][0]]
                info.update(death_by=('channeller' if dr[0][1] == cid else 'camp' if dr[0][1] is None else names.get(dr[0][1])), death_left=prev[-1][3] if prev else None, death_verdict=prev[-1][8] if prev else None, death_stop=prev[-1][4] if prev else None)
            return dict(info, cause='go, stopper died')
        if stunned: return dict(info, cause='go, stopper stunned')
        if br and br.most_common(1)[0][0] != 'E': return dict(info, cause='go, pre-empted (%s)' % br.most_common(1)[0][0])
        last = gos[b][-1]
        return dict(info, cause='go, arrived late' if last[3] >= 0 else 'go, ran out')
    # No go: verdict history
    allv = sorted((x for b in ours for x in lines[b]), key=lambda x: x[0])
    vs = [x[8] for x in allv]
    info.update(first=allv[0][8], last=allv[-1][8], first_left=allv[0][3], first_stop=allv[0][4], kinds=''.join(sorted({x[1] for x in allv})))
    late_lines = [x for x in allv if x[8] == 'late']
    if late_lines: info.update(late_left=late_lines[0][3], late_stop=late_lines[0][4], late_cheb=late_lines[0][9], late_steps=late_lines[0][10], late_locks=late_lines[0][12])
    if set(vs) == {'late'}: return dict(info, cause='late from first sight')
    if 'wait' in vs and 'late' in vs:
        # wait then late: did the stop estimate jump (move away / lost lock / cooldown) or did left run down past it?
        w = [x for x in allv if x[8] == 'wait'][-1]; lt = [x for x in allv if x[8] == 'late' and x[0] >= w[0]]
        if lt:
            info.update(w_left=w[3], w_stop=w[4], w_margin=w[7], l_left=lt[0][3], l_stop=lt[0][4])
            return dict(info, cause='waited, then late')
    if vs[-1] == 'wait': return dict(info, cause='wait until the end')
    if 'cool' in vs: return dict(info, cause='cooldown-bound, no go')
    return dict(info, cause='other: ' + ','.join(sorted(set(vs))))

if __name__ == '__main__':
    idx = json.load(open(ROOT + '/index.json')); rows = {}
    for g in idx['games']: rows.setdefault(g['dir'], g)
    with ProcessPoolExecutor(48) as ex: res = [x for r in ex.map(one, list(rows.items()), chunksize=4) if r for x in r]
    for outc in ('done', 'manual'):
        S = [x for x in res if x['outcome'] == outc]
        print('== REF winning channels %s: %d' % (outc, len(S)))
        C = collections.Counter(x['cause'] for x in S)
        for k, v in C.most_common(): print('  %4d  %s' % (v, k))
    json.dump(res, open('/tmp/denydiag.json', 'w'))
