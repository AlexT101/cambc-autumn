#!/usr/bin/env python3
"""fx.py ANALYSIS_DIR CAND [--json OUT]: perma-lock forensics from extracted replays (tools/replay/extract.mjs --out).

For every enemy tribute that lands while CAND leads in tributed gems (at the channel's start), on one-site maps:
what our lock and our bodies were doing. Classes (first that applies):
  short      the channel lasted at most 1 turn end: no lock placed between its start and end could be timed
  in_reach   one of our lock carriers stood within 3 of the altar during the channel (it could have locked)
  late       a carrier came within 4-8 (a re-lock on its way)
  no_lock    one of our bodies was within 8 but none carried a lock (the spawn-trip gap)
  away       none of ours within 8; `dead` notes 2+ of ours dead at the start
And the lock's history: broken (our lock on that tile within the 10 rounds before, removed), absent (none for 10+
rounds), other_tile (a 2-tile site: our lock on the other tile). Also whether the landing flipped the lead, and
whether the enemy's carried gems at the start already exceeded our lead (flippable).
Plus the games CAND led at some point and lost: the last round it led and the enemy tributes that overturned it."""
import collections, glob, gzip, json, os, sys

root, cand = sys.argv[1], sys.argv[2]
rows, lost = [], []
for meta_p in sorted(glob.glob(f'{root}/*/meta.json')):
    d = os.path.dirname(meta_p)
    m = json.load(open(meta_p))
    names = [t['name'] for t in m['teams']]
    if cand not in names: continue
    us = names.index(cand); them = 1 - us
    mp = json.load(open(f'{root}/maps/{m["map"]["hash"]}.json'))
    alts = [tuple(a) for a in mp['altars']]
    if not alts or len(alts) > 2 or max(max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a in alts for b in alts) > 3: continue
    ev = [json.loads(l) for l in gzip.open(f'{d}/events.jsonl.gz', 'rt')]
    R = json.load(gzip.open(f'{d}/rounds.json.gz'))
    gems = R['gems']; n = len(R['round'])
    champs = m['champions']
    ours = [i for i, c in enumerate(champs) if c['team'] == us]
    theirs = [i for i, c in enumerate(champs) if c['team'] == them]
    cid_team = {c['id']: c['team'] for c in champs}
    ch = R['champions']
    def idx(r): return max(0, min(n - 1, r - 2))  # state at the start of round r
    def lead(r): i = idx(r); return gems[us][i] - gems[them][i]
    def our_lock(i, tile):
        return any(l[0] == us and (l[1], l[2]) == tile for l in R['locks'][i])
    starts = {}
    for e in ev:
        if e['k'] == 'tribute_start': starts[e['a']] = e
        if e['k'] != 'tribute_end' or cid_team.get(e['a']) != them or e['gems'] <= 0: continue
        st = starts.get(e['a'])
        if not st: continue
        r0, r1 = st['r'], e['r']
        if lead(r0) < 1: continue
        tile = tuple(st['altar'])
        # the lock's history on this tile before the start
        hist = 'absent'
        for k in range(1, 11):
            if r0 - k >= 1 and our_lock(idx(r0 - k + 1), tile): hist = 'broken'; break
        if hist == 'absent' and any(our_lock(idx(r0), t) for t in alts if t != tile): hist = 'other_tile'
        cd = bd = 99; dead = 0
        for r in range(r0, max(r0 + 1, r1)):
            i = idx(r + 1)
            for k in ours:
                c = ch[k]
                if not c['alive'][i] or c['x'][i] is None: continue
                dd = max(abs(c['x'][i] - tile[0]), abs(c['y'][i] - tile[1]))
                bd = min(bd, dd)
                if c['cons'][i][2] > 0: cd = min(cd, dd)
        i0 = idx(r0)
        dead = sum(1 for k in ours if not ch[k]['alive'][i0])
        carried = sum(ch[k]['gems'][i0] for k in theirs if ch[k]['alive'][i0])
        cls = 'short' if r1 - r0 <= 1 else 'in_reach' if cd <= 3 else 'late' if cd <= 8 else 'no_lock' if bd <= 8 else 'away'
        ie = idx(r1 + 1)
        rows.append(dict(game=os.path.basename(d), map=m['map']['name'], r0=r0, dur=r1 - r0, gems=e['gems'], cls=cls, hist=hist,
                         dead=dead, lead=lead(r0), flip=gems[them][ie] > gems[us][ie], flippable=carried > lead(r0),
                         won=m['result']['winner'] == us))
    led = [r for r in range(1, m['result']['rounds'] + 1) if lead(r) >= 1]
    if led and m['result']['winner'] != us:
        lost.append(dict(game=os.path.basename(d), map=m['map']['name'], last_led=led[-1], led_rounds=len(led), final=m['result']['gems'],
                         rounds=m['result']['rounds'], enemy_1000=m['result']['gems'][them] >= 1000))

N = len({r['game'] for r in rows}) or 1
games = len(glob.glob(f'{root}/*/meta.json'))
print(f'{len(rows)} enemy tributes landed while {cand} led ({sum(r["gems"] for r in rows)} gems)')
c = collections.Counter((r['cls'], r['hist']) for r in rows)
g = collections.Counter();
for r in rows: g[(r['cls'], r['hist'])] += r['gems']
print('| class | lock history | tributes | gems | flipped the lead | flippable at start | in games we lost |')
print('|---|---|---|---|---|---|---|')
for (cl, h), k in sorted(c.items(), key=lambda x: -x[1]):
    sub = [r for r in rows if r['cls'] == cl and r['hist'] == h]
    print(f'| {cl} | {h} | {k} | {g[(cl, h)]} | {sum(r["flip"] for r in sub)} | {sum(r["flippable"] for r in sub)} | {sum(not r["won"] for r in sub)} |')
print(f'2+ of ours dead at the start: {sum(r["dead"] >= 2 for r in rows)}; channels of 10+ turns: {sum(r["dur"] >= 10 for r in rows)}')
print(f'\n{len(lost)} games {cand} led at some point and lost; enemy reached 1000 in {sum(x["enemy_1000"] for x in lost)}')
import statistics as st
if lost:
    print('last round led: median', st.median(x['last_led'] for x in lost), '| rounds led median', st.median(x['led_rounds'] for x in lost),
          '| led after round 1000:', sum(x['last_led'] >= 1000 for x in lost), '| after 1500:', sum(x['last_led'] >= 1500 for x in lost))
    flips = [r for r in rows if r['flip'] and not r['won']]
    print(f'tributes that flipped the lead in lost games: {len(flips)}:', collections.Counter(r['cls'] for r in flips).most_common())
if '--json' in sys.argv: json.dump(dict(rows=rows, lost=lost), open(sys.argv[sys.argv.index('--json') + 1], 'w'))
