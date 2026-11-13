"""Why farm trips are abandoned: classify every farm_group switch of the h-trace side (SW lines) and the
abandoned farm streaks (trips.py's definition) by cause, from the trace and replay truth.

    python3 switch.py BATCH ANALYSIS_DIR [--examples N] [--json OUT]

SW line (bots/variants/h-trace/src/bot.cc): SW r id branch cause pick old new hp bag banking banks_bag claim crew
channelling recall_farm pk (best bv shared sv help k | -) |O <group> |N <group>; <group> is '-' or
g st state_round respawn_round holder awake allies_on claims(hex) ally_near enemy_near my_dist gems strength
[cur] [prev], a record being [-] or [round mode+stage value worth weight exposed trip rounds trips wait steps output
claimers expected late]."""
import sys, re, json, gzip, zipfile, collections, bisect, math, random
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
SW_RE = re.compile(rb'^[\s\0]*(SW .*)$', re.M)
REC_RE = re.compile(r'\[([^\]]*)\]')
AN = Path(sys.argv[2])
NEXAMPLES = 4
VISION = 8          # rules vision.champion: radius 8
CREW_ENEMY = 12     # params::crew_enemy_radius: may_expect drops a crew with an enemy this near
MAX_WAIT = 2        # params::max_wait
STICKY = 1.2        # farm.cc stickiness
LOOP = set('SKCJr')


def parse_rec(s):
    s = s.strip()
    if s == '-':
        return None
    t = s.split()
    return dict(round=int(t[0]), mode=t[1][0], stage=int(t[1][1:]), value=float(t[2]), worth=float(t[3]), weight=float(t[4]),
                exposed=float(t[5]), trip=float(t[6]), rounds=float(t[7]), trips=int(t[8]), wait=int(t[9]), steps=int(t[10]),
                output=float(t[11]), claimers=int(t[12]), expected=int(t[13]), late=int(t[14]))


def parse_grp(s):
    recs = REC_RE.findall(s)
    head = REC_RE.sub('', s).split()
    if not head or head[0] == '-':
        return None
    g = dict(g=int(head[0]), st=head[1], sr=int(head[2]), rr=int(head[3]), hold=head[4], aw=int(head[5]), on=int(head[6]),
             cl=int(head[7], 16), an=int(head[8]), en=int(head[9]), d=int(head[10]), gems=int(head[11]), strength=float(head[12]))
    g['cur'] = parse_rec(recs[0]) if recs else None
    g['prev'] = parse_rec(recs[1]) if len(recs) > 1 else None
    return g


def parse_sw(line):
    a, rest = line.split(' |O', 1)
    o, n = rest.split(' |N', 1)
    t = a.split()
    sw = dict(r=int(t[1]), id=int(t[2]), br=t[3], cause=t[4], pick=t[5], old=int(t[6]), new=int(t[7]), hp=float(t[8]), bag=int(t[9]),
              bk=int(t[10]), bb=int(t[11]), claim=int(t[12]), crew=int(t[13]), rf=int(t[15]))
    k = t.index('pk')
    if t[k + 1] != '-':
        sw.update(best=int(t[k + 1]), bv=float(t[k + 2]), shared=int(t[k + 3]), sv=float(t[k + 4]), help=int(t[k + 5]))
    sw['O'] = parse_grp(o)
    sw['N'] = parse_grp(n)
    return sw


INDEX = {}
for dd in AN.iterdir():
    if (dd / 'meta.json').exists():
        INDEX[Path(json.loads((dd / 'meta.json').read_text())['source']).name] = dd


def rec_terms(c, p):
    """Which value term moved from p to c (records of one group): the largest log change."""
    if not c or not p or c['value'] <= 0 or p['value'] <= 0:
        return None
    terms = {}
    if c['mode'] != p['mode']:
        terms['mode ' + p['mode'] + '>' + c['mode']] = 9.0
    if c['weight'] > 0 and p['weight'] > 0 and abs(math.log(c['weight'] / p['weight'])) > 1e-3:
        terms['weight'] = abs(math.log(c['weight'] / p['weight']))
    wr = c['worth'] / p['worth'] if c['worth'] > 0 and p['worth'] > 0 else 1
    if abs(math.log(wr)) > 1e-3 and 'weight' not in terms:
        # J and C: worth is our part, which moves with the crew's output
        terms['part' if c['mode'] in 'JC' else 'worth'] = abs(math.log(wr))
    Tc, Tp = c['trip'] + c['rounds'], p['trip'] + p['rounds']
    if Tc > 0 and Tp > 0:
        if abs(c['trip'] - p['trip']) > 0.5:
            terms['trip'] = abs(c['trip'] - p['trip']) / max(Tp, 1)
        if abs(c['rounds'] - p['rounds']) > 0.05 * max(p['rounds'], 1):
            terms['crew output' if (c['output'] != p['output'] or c['expected'] != p['expected'] or c['claimers'] != p['claimers']) else 'clear rounds'] = \
                abs(c['rounds'] - p['rounds']) / max(Tp, 1)
    if c['trips'] != p['trips']:
        terms['trips home'] = 9.0 if c['trips'] > p['trips'] else 8.0
    if not terms:
        return 'none'
    return max(terms, key=terms.get)


def one(f):
    f = Path(f)
    d = INDEX.get(f.name)
    if d is None:
        return None
    try:
        z = zipfile.ZipFile(f)
    except Exception:
        return None
    meta = json.loads((d / 'meta.json').read_text())
    T = [i for i, t in enumerate(meta['teams']) if t.get('name') == 'h-trace']
    if not T:
        return None
    T = T[0]
    mp = json.loads((d / meta['mapFile']).read_text())
    gt = {g['id']: set(map(tuple, g['tiles'])) for g in mp['groups']}
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    R = json.load(gzip.open(d / 'rounds.json.gz'))
    r0 = R['round'][0]
    ch = {c['id']: c for c in R['champions']}
    gtl = collections.defaultdict(list)
    for row in R['groups']:
        gtl[row[1]].append((row[0], row[2:]))
    gkeys = {g: [x[0] for x in L] for g, L in gtl.items()}

    def tstate(g, r):  # end of round r: [state, team, timer, respawn, awake, hp]
        L = gtl.get(g, [])
        i = bisect.bisect_right(gkeys.get(g, []), r) - 1
        return L[i][1] if i >= 0 else None

    def return_round(g, r):  # first round >= r at whose end the group has monsters
        for (rr, row) in gtl.get(g, []):
            if rr >= r and row[0] == 1:
                return rr
        return None

    def first_state_round(g, r, state):  # last change row at or before r with state
        L = gtl.get(g, [])
        i = bisect.bisect_right(gkeys.get(g, []), r) - 1
        return L[i][0] if i >= 0 else None

    caps = collections.defaultdict(list)
    hits = collections.defaultdict(list)
    for l in gzip.open(d / 'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        k = e.get('k')
        if k == 'capture':
            caps[e['g']].append((e['r'], e['team'], [s[0] for s in e.get('shares') or []]))
        elif k in ('attack', 'cast') and 'a' in e:
            for cd in e.get('cdmg') or []:
                hits[(e['a'], camp_group.get(cd[0]))].append(e['r'])
    for v in hits.values():
        v.sort()
    raw = z.read('team-a.stdout' if T == 0 else 'team-b.stdout')
    rows = collections.defaultdict(list)
    for m in D_RE.finditer(raw):
        rows[int(m[2])].append((int(m[1]), m[3].decode(), int(m[4])))
    sws = collections.defaultdict(dict)
    for m in SW_RE.finditer(raw):
        try:
            s = parse_sw(m[1].decode(errors='replace'))
        except Exception:
            continue
        sws[s['id']][s['r']] = s
    st = collections.Counter()
    ex = collections.defaultdict(list)
    terms = collections.Counter()
    game = f.name
    rounds_total = meta['result']['rounds']

    def pos(cid, r):
        C = ch[cid]
        i = r - r0
        return (C['x'][i], C['y'][i]) if 0 <= i < len(C['x']) else None

    def worked(cid, g, a, b):
        hs = hits.get((cid, g), [])
        i = bisect.bisect_left(hs, a)
        if i < len(hs) and hs[i] <= b:
            return True
        tiles = gt.get(g, ())
        return any(pos(cid, r) in tiles for r in range(a, b + 1))

    for cid, L in rows.items():
        if cid not in ch or ch[cid]['team'] != T:
            continue
        S = sws.get(cid, {})
        # The start SW of each trip: latest SW with new == g at or before r.
        sw_rounds = sorted(S)

        def start_sw(g, r):
            i = bisect.bisect_right(sw_rounds, r) - 1
            while i >= 0:
                s = S[sw_rounds[i]]
                if s['new'] == g:
                    return s
                if s['old'] == g or s['new'] != g and s['old'] != g and False:
                    pass
                i -= 1
            return None

        def enemy_close(r, radius=VISION):
            me = pos(cid, r)
            if not me or me[0] is None:
                return False
            for e in ch.values():
                if e['team'] == T:
                    continue
                p = pos(e['id'], r)
                if p and p[0] is not None and max(abs(p[0] - me[0]), abs(p[1] - me[1])) <= radius:
                    return True
            return False

        def classify(s):
            """Cause of switch s (old -> new), with its feature tags."""
            g, h, r = s['old'], s['new'], s['r']
            O, N = s['O'], s['N']
            s0 = start_sw(g, r - 1)
            b0 = s0['N'] if s0 else None
            t_start = s0['r'] if s0 else r
            oc = O['cur'] if O else None
            op = O['prev'] if O else None
            nc = N['cur'] if N else None
            npv = N['prev'] if N else None
            tags = []
            cap_after = [(cr, tm, sh) for (cr, tm, sh) in caps.get(g, []) if t_start <= cr <= r + 10]
            ts = tstate(g, r)
            ts0 = tstate(g, t_start)
            enemy_took = any(tm != T for (_, tm, _) in cap_after) or (ts and ts[0] == 2 and ts[1] not in (T, 2) and ts[1] is not None)
            ally_took = any(tm == T and cid not in sh for (_, tm, sh) in cap_after) or (ts and ts[0] == 2 and ts[1] == T and pos(cid, r) not in gt.get(g, ()))
            # Belief at the trip's start against truth then.
            wrong = None
            if b0 and ts0:
                if b0['st'] == 'A' and ts0[0] == 3:
                    wrong = 'believed alive, was respawning'
                elif b0['st'] == 'A' and ts0[0] == 2:
                    wrong = 'believed alive, was cleared'
                elif b0['st'] == 'R':
                    ret = return_round(g, t_start)
                    if ret is not None and b0['rr'] >= 0 and ret > b0['rr'] + MAX_WAIT:
                        wrong = 'respawn later than believed'
            stage = oc['stage'] if oc and oc['round'] == r else -1
            if s['br'] != 'F':
                if s['br'] in 'RC' and enemy_close(r):
                    return 'c enemy: branch ' + s['br'] + ' near enemy', tags
                return 'e situation: branch ' + s['br'], tags
            if s['cause'] in ('Y', 'h', 'm'):
                return 'b ally: yield/handoff', tags
            if s['cause'] == 'g':
                return 'e situation: altar guard', tags
            if s['cause'] in ('U', 'W', 'A', 'M'):
                return 'f other: ' + {'U': 'pick-up', 'W': 'kept-target', 'A': 'partial', 'M': 'melee step'}[s['cause']], tags
            if O is None:
                return 'f other: no old', tags
            # The old group's own state now, as believed.
            if O['hold'] == 'e' or (O['st'] in 'CR' and enemy_took):
                return 'c enemy: holds/took it', tags
            if O['hold'] == 'a' or O['on'] > 0 or (O['st'] in 'CR' and ally_took):
                return 'b ally: holds/took it', tags
            if wrong:
                return 'a belief: ' + wrong, tags
            if O['st'] == 'R' and b0 and b0['st'] == 'A':
                return 'a belief: respawned unseen', tags
            if O['st'] == 'R' and stage == 5 and oc['wait'] > MAX_WAIT:
                return 'a belief: respawn wait grew', tags
            if O['st'] == 'C' and b0 and b0['st'] == 'A':
                return 'f other: cleared by nobody seen', tags
            if O['cl'] and stage == 7:
                return 'b ally: claimed, pruned', tags
            if O['cl'] and oc and op and stage == 8 and oc['mode'] == 'J' and op['mode'] != 'J':
                return 'b ally: ally claimed it', tags
            if s['pick'] in 'TGLQP':
                return 'f other: pick ' + s['pick'], tags
            if s['pick'] == 'H':
                return 'f other: help call', tags
            if oc and stage == 8 and oc['late']:
                return 'e situation: too late', tags
            if s0 and (s['bb'] != s0['bb'] or s['bag'] != s0['bag']):
                return 'e situation: bag/banking', tags
            if op and oc and stage == 8 and op['round'] >= r - 2 and oc['trips'] > op['trips']:
                return 'e situation: health (trips home)', tags
            if O['en'] <= CREW_ENEMY and oc and op and stage == 8 and oc['expected'] < op['expected']:
                return 'c enemy: near, crew dropped', tags
            # The old group unchanged: the new one rose, or values moved.
            nv = s.get('sv') if s['pick'] == 'J' else s.get('bv')
            if nc and nc['round'] == r and nc['value'] > 0:
                nv = nc['value']
            recent_np = npv if npv and npv['round'] >= r - 2 else None
            recent_op = op if op and op['round'] >= r - 2 else None
            if stage == 8 and oc['value'] > 0 and nv:
                margin = nv / oc['value']
                tags.append(('margin', margin))
                tags.append(('term_o', rec_terms(oc, recent_op)))
                tags.append(('term_n', rec_terms(nc, recent_np)))
                tags.append(('odrop', oc['value'] / recent_op['value'] if recent_op and recent_op['value'] > 0 else None))
                tags.append(('nrise', nc['value'] / recent_np['value'] if nc and recent_np and recent_np['value'] > 0 else None))
                fresh = N and N['sr'] == r
                if not recent_np or recent_np['stage'] < 8 or recent_np['value'] <= 0:
                    why = ('respawn within max_wait' if recent_np and recent_np['stage'] == 5
                           else 'was filtered' if recent_np and recent_np['stage'] == 1
                           else 'was pruned by bound' if recent_np and recent_np['stage'] in (6, 7)
                           else 'not reached last turn')
                    return 'f new appeared: ' + why + (' (seen now)' if fresh else ''), tags
                if margin < STICKY:
                    return 'd flicker', tags
                return 'f value shift', tags
            if stage in (6, 7):
                return 'f other: old pruned by bound', tags
            if stage in (3, 4):
                return 'f other: unreachable', tags
            if stage == 2:
                return 'c enemy: mono contested', tags
            if stage == 1:
                return 'f other: filtered', tags
            return 'f other: no old value', tags

        # Switches.
        sw_class = {}
        for r in sw_rounds:
            s = S[r]
            if s['old'] < 0 or s['old'] == s['new']:
                continue
            c, tags = classify(s)
            s0 = start_sw(s['old'], r - 1)
            if worked(cid, s['old'], s0['r'] if s0 else r, r + 40):
                sw_class[r] = ('z done', tags)
                st['sw'] += 1
                st['sw|z done'] += 1
                continue
            sw_class[r] = (c, tags)
            st['sw'] += 1
            st['swab'] += 1
            st['sw|' + c] += 1
            st['swpick|' + s['pick'] + '|' + c.split(':')[0]] += 1
            dt = dict(tags)
            if c in ('d flicker', 'f value shift') or c.startswith('f new appeared'):
                key = 'd' if c == 'd flicker' else 'v' if c == 'f value shift' else 'n'
                terms[key + '|old ' + str(dt.get('term_o'))] += 1
                terms[key + '|new ' + str(dt.get('term_n'))] += 1
                od, nr = dt.get('odrop'), dt.get('nrise')
                terms[key + '|dir ' + ('?' if od is None or nr is None else 'old fell' if od < 0.98 and nr <= 1.02 else 'new rose' if nr > 1.02 and od >= 0.98 else 'both' if od < 0.98 else 'neither')] += 1
                mg = dt.get('margin')
                terms[key + '|margin ' + ('<1.05' if mg < 1.05 else '<1.1' if mg < 1.1 else '<1.2' if mg < 1.2 else '<1.5' if mg < 1.5 else '>=1.5')] += 1
                terms[key + '|pick ' + s['pick'] + ' old ' + (s['O']['cur']['mode'] if s['O']['cur'] else '-')] += 1
                terms[key + '|new state ' + (s['N']['st'] if s['N'] else '-')] += 1
            if len(ex[c]) < 60:
                ex[c].append(dict(game=game, r=r, id=cid, old=s['old'], new=s['new'], pick=s['pick'], hp=s['hp'], bag=s['bag'],
                                  O={k: s['O'][k] for k in ('st', 'sr', 'rr', 'hold', 'on', 'cl', 'en', 'd')} if s['O'] else None,
                                  N={k: s['N'][k] for k in ('st', 'sr', 'rr', 'hold', 'on', 'cl', 'en', 'd')} if s['N'] else None,
                                  oc=s['O']['cur'] if s['O'] else None, op=s['O']['prev'] if s['O'] else None,
                                  nc=s['N']['cur'] if s['N'] else None, np=s['N']['prev'] if s['N'] else None,
                                  bv=s.get('bv'), sv=s.get('sv'), tags=[(k, v) for k, v in tags]))
        # A-B-A within 30 rounds over switches.
        seq = [(S[r]['old'], S[r]['new'], r) for r in sw_rounds if S[r]['old'] >= 0 and S[r]['new'] >= 0 and S[r]['old'] != S[r]['new']]
        for i in range(1, len(seq)):
            if seq[i][1] == seq[i - 1][0] and seq[i][0] == seq[i - 1][1] and seq[i][2] - seq[i - 1][2] <= 30:
                st['ABA30'] += 1
                st['ABA30|' + sw_class.get(seq[i - 1][2], ('?',))[0]] += 1
        # Streaks (trips.py).
        streak = None
        Lr = [x[0] for x in L]

        def close(sk, nxt):
            if not sk:
                return
            g, start, end, n = sk
            st['streaks'] += 1
            st['turns'] += n
            wk = worked(cid, g, start, end + 40)
            # Features at the streak's start, for every streak: abandonment rate by feature.
            tiles_ = gt.get(g, ())
            cx_ = sum(x for x, _ in tiles_) / max(1, len(tiles_)); cy_ = sum(y for _, y in tiles_) / max(1, len(tiles_))
            j0 = start - r0
            me0 = pos(cid, start)
            seen_ids = ch[cid]['sees'][j0] if 0 <= j0 < len(ch[cid].get('sees', [])) else []
            feats = []
            if me0 and me0[0] is not None:
                dus = max(abs(me0[0] - cx_), abs(me0[1] - cy_))
                den = 99
                for eid in seen_ids:
                    p_ = pos(eid, start)
                    if p_ and p_[0] is not None:
                        den = min(den, max(abs(p_[0] - cx_), abs(p_[1] - cy_)))
                feats.append('seen enemy nearer group than us' if den < dus else 'seen enemy, we nearer' if den < 99 else 'no enemy seen')
                feats.append('dist ' + ('<10' if dus < 10 else '<20' if dus < 20 else '>=20'))
            s0w = start_sw(g, start)
            if s0w and s0w['N']:
                b = s0w['N']
                age = start - b['sr']
                side_ = mp['groups'][g].get('side', -1)
                sn = 'own' if side_ == T else 'enemy' if side_ == 1 - T else 'mid'
                feats.append('belief %s age %s %s' % (b['st'], '<100' if age < 100 else '>=100', sn))
                ts_ = tstate(g, start)
                feats.append('belief %s truth %s' % (b['st'], {1: 'A', 2: 'C', 3: 'R'}.get(ts_[0] if ts_ else 0, '?')))
                if b['st'] == 'A' and sn == 'enemy' and age >= 100:
                    feats.append('stale-enemy-A truth %s%s' % ({1: 'A', 2: 'C', 3: 'R'}.get(ts_[0] if ts_ else 0, '?'), ' never seen' if b['sr'] == 0 else ''))
                if b['st'] == 'A' and sn == 'enemy':
                    feats.append('enemy-A x ' + ('seen enemy nearer' if feats[0].startswith('seen enemy nearer') else 'other'))
            if n >= 11:
                for f_ in feats:
                    st['lfeat|' + f_ + '|turns'] += n
                    if not wk:
                        st['lfeat|' + f_ + '|ab'] += n
                st['lturns'] += n
                st['lab'] += 0 if wk else n
            for f_ in feats:
                st['feat|' + f_ + '|streaks'] += 1
                st['feat|' + f_ + '|turns'] += n
                if not wk:
                    st['feat|' + f_ + '|ab'] += n
            if wk:
                return
            st['abandoned'] += 1
            st['ab_turns'] += n
            # What ended it.
            if nxt is None:
                c = 'g game end' if end >= rounds_total - 2 else 'g trace ends'
            else:
                rn, brn, fgn = nxt
                if rn - end > 2:
                    alive = ch[cid]['alive'][end + 1 - r0] if 0 <= end + 1 - r0 < len(ch[cid]['alive']) else 1
                    c = 'e situation: died' if not alive else 'g gap'
                elif rn in sw_class and S[rn]['old'] == g:
                    c = sw_class[rn][0]
                elif brn != 'F':
                    c = ('c enemy: branch ' + brn + ' near enemy (kept group)' if brn in 'RCAX' and enemy_close(rn)
                         else 'e situation: branch ' + brn + ' (kept group)')
                else:
                    c = 'g other end'
            st['abt|' + c] += n
            st['abs|' + c] += 1
            if n >= 11:
                st['labt|' + c] += n
            if len(ex['streak|' + c]) < 40 and n >= 5:
                s0w = start_sw(g, start)
                ex['streak|' + c].append(dict(game=game, id=cid, g=g, start=start, end=end, n=n, nxt=nxt,
                                              b0={k: s0w['N'][k] for k in ('st', 'sr', 'rr', 'd', 'en')} if s0w and s0w['N'] else None,
                                              v0=s0w['N']['cur']['value'] if s0w and s0w['N'] and s0w['N']['cur'] else None,
                                              truth0=tstate(g, start), truth_end=tstate(g, end),
                                              caps=[(cr, t) for (cr, t, _) in caps.get(g, []) if start - 80 <= cr <= end + 40]))
            side = mp['groups'][g].get('side', -1) if g < len(mp['groups']) else -1
            sname = 'own side' if side == T else 'enemy side' if side == 1 - T else 'mid'
            tiles = gt.get(g, ())
            cx = sum(x for x, _ in tiles) / max(1, len(tiles)); cy = sum(y for _, y in tiles) / max(1, len(tiles))
            i0 = start - r0
            seen0 = bool(ch[cid]['sees'][i0]) if 0 <= i0 < len(ch[cid].get('sees', [])) else False

            def det(k):
                st['det|' + c + '|' + k] += n
            det(sname)
            det('enemy seen at start' if seen0 else 'no enemy seen at start')
            if c.startswith('c enemy: branch'):
                rn = nxt[0]
                near_grp = False
                for e in ch.values():
                    if e['team'] == T:
                        continue
                    p = pos(e['id'], rn)
                    if p and p[0] is not None and max(abs(p[0] - cx), abs(p[1] - cy)) <= VISION:
                        near_grp = True
                me = pos(cid, rn)
                det('enemy within 8 of group' if near_grp else 'enemy not near group')
                if me and me[0] is not None:
                    dg = max(abs(me[0] - cx), abs(me[1] - cy))
                    det('we were within 8 of group' if dg <= VISION else 'we were >8 from group')
                tk = [t for (cr, t, _) in caps.get(g, []) if start <= cr <= end + 40]
                det('enemy captured it within 40' if any(t != T for t in tk) else 'ally captured it within 40' if tk else 'nobody captured it within 40')
            if c.startswith('a belief'):
                prior = [(cr, t) for (cr, t, _) in caps.get(g, []) if cr <= start]
                det('last capture by ' + ('none' if not prior else 'ally' if prior[-1][1] == T else 'enemy'))
                s0w = start_sw(g, start)
                if s0w and s0w['N']:
                    age = start - s0w['N']['sr']
                    det('belief age ' + ('<40' if age < 40 else '<100' if age < 100 else '<300' if age < 300 else '>=300'))
                    det('start dist ' + ('<10' if s0w['N']['d'] < 10 else '<20' if s0w['N']['d'] < 20 else '>=20'))
            # Truth over the streak: respawning throughout?
            s0 = tstate(g, start)
            allresp = s0 and s0[0] == 3 and all((tstate(g, r) or [0])[0] == 3 for r in range(start, end + 1, 3))
            if allresp:
                st['ab_resp_turns'] += n
                st['ab_resp|' + c] += n

        for i, (r, br, fg) in enumerate(L):
            if br == 'F' and fg >= 0:
                if streak and streak[0] == fg and r - streak[2] <= 2:
                    streak = (fg, streak[1], r, streak[3] + 1)
                else:
                    close(streak, (r, br, fg))
                    streak = (fg, r, r, 1)
            else:
                close(streak, (r, br, fg))
                streak = None
        close(streak, None)
    return st, dict(ex), terms


if __name__ == '__main__':
    files = sorted(Path(sys.argv[1]).glob('*.repl26a'))
    tot = collections.Counter()
    terms = collections.Counter()
    exs = collections.defaultdict(list)
    with ProcessPoolExecutor(24) as pool:
        for o in pool.map(one, files, chunksize=4):
            if not o:
                continue
            st, ex, tm = o
            tot.update(st)
            terms.update(tm)
            for k, v in ex.items():
                exs[k].extend(v)
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    print('switches', tot['sw'], 'abandoning', tot['swab'], 'streaks', tot['streaks'], 'abandoned', tot['abandoned'], 'ab_turns', tot['ab_turns'], 'of turns', tot['turns'],
          'share %.3f' % (tot['ab_turns'] / max(1, tot['turns'])), 'ABA30', tot['ABA30'], 'resp-throughout turns', tot['ab_resp_turns'])
    cats = sorted({k.split('|', 1)[1] for k in tot if k.startswith(('sw|', 'abt|'))})
    print('%-46s %8s %6s %9s %6s %8s' % ('cause', 'switches', '%ab', 'ab_turns', '%', 'resp-thr'))
    for c in sorted(cats, key=lambda c: -tot['abt|' + c] - tot['sw|' + c]):
        print('%-46s %8d %6.1f %9d %6.1f %8d' % (c, tot['sw|' + c], 100 * tot['sw|' + c] / max(1, tot['swab']), tot['abt|' + c],
                                                  100 * tot['abt|' + c] / max(1, tot['ab_turns']), tot['ab_resp|' + c]))
    print('\nby letter: share of abandoning switches, share of abandoned turns')
    let = collections.Counter(); lett = collections.Counter()
    for k, v in tot.items():
        if k.startswith('sw|') and k != 'sw|z done':
            let[k[3]] += v
        if k.startswith('abt|'):
            lett[k[4]] += v
    for L_ in sorted(set(let) | set(lett)):
        print('   %s %6.1f%% %6.1f%%' % (L_, 100 * let[L_] / max(1, tot['swab']), 100 * lett[L_] / max(1, tot['ab_turns'])))
    print('\ndetails (abandoned turns)')
    for k, v in sorted(((k, v) for k, v in tot.items() if k.startswith('det|')), key=lambda x: (x[0].split('|')[1], -x[1])):
        c = k.split('|')[1]
        if tot['abt|' + c] > 0.03 * tot['ab_turns']:
            print('   %-55s %-32s %6.1f%%' % (c, k.split('|')[2], 100 * v / tot['abt|' + c]))
    print('\nstreak features at start: streaks, turns, abandoned share of turns, share of all abandoned turns')
    fs = sorted({k.split('|')[1] for k in tot if k.startswith('feat|')})
    for f_ in fs:
        t_ = tot['feat|' + f_ + '|turns']
        print('   %-45s %8d %9d %6.1f%% %6.1f%%' % (f_, tot['feat|' + f_ + '|streaks'], t_, 100 * tot['feat|' + f_ + '|ab'] / max(1, t_),
                                                100 * tot['feat|' + f_ + '|ab'] / max(1, tot['ab_turns'])))
    print('\nstreaks of 11+ turns: turns %d, abandoned %d' % (tot['lturns'], tot['lab']))
    for k, v in sorted(((k, v) for k, v in tot.items() if k.startswith('labt|')), key=lambda x: -x[1])[:16]:
        print('   %-55s %6.1f%%' % (k[5:], 100 * v / max(1, tot['lab'])))
    for f_ in sorted({k.split('|')[1] for k in tot if k.startswith('lfeat|')}):
        t_ = tot['lfeat|' + f_ + '|turns']
        print('   %-45s %9d %6.1f%% %6.1f%%' % (f_, t_, 100 * tot['lfeat|' + f_ + '|ab'] / max(1, t_), 100 * tot['lfeat|' + f_ + '|ab'] / max(1, tot['lab'])))
    print('\nABA30 by first switch cause')
    for k, v in sorted(((k, v) for k, v in tot.items() if k.startswith('ABA30|')), key=lambda x: -x[1]):
        print('  ', k[6:], v)
    print('\npick x cause')
    for k, v in sorted(((k, v) for k, v in tot.items() if k.startswith('swpick|')), key=lambda x: -x[1])[:30]:
        print('  ', k[7:], v)
    print('\nvalue terms (d = flicker, v = value shift)')
    for k, v in sorted(terms.items()):
        print('  ', k, v)
    if out:
        random.seed(1)
        sample = {k: random.sample(v, min(NEXAMPLES * 3, len(v))) for k, v in exs.items()}
        out.write_text(json.dumps(dict(totals=tot, terms=terms, examples=sample), indent=1))
