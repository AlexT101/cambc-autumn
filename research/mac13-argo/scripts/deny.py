"""Denying a winning tribute: for the eventual winner's 100+ gem tributes while its team is rich (1000+ wealth),
what the defenders did: damage dealt to the channeller during the channel, the cancel, and within 15 rounds after
the cancel: canceller killed? channeller killed? py deny.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return []
    w = meta['result']['winner']; C = R['champions']; team = {c['id']: c['team'] for c in C}
    name = {c['id']: c['name'] for c in meta['champions']}
    rid = {r: i for i, r in enumerate(R['round'])}
    def wealth(t, i):
        return R['gems'][t][i] + sum(c['gems'][i] for c in C if c['team'] == t and c['alive'][i])
    deaths = [(e['r'], e['v'], e.get('by')) for e in ev if e['k'] == 'death']
    out = []; open_ = {}; dmg = Counter(); last_stun = {}
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast'):
            for v, amt in (e.get('dmg') or []):
                if v in open_: dmg[v] += amt
            for v in (e.get('stun') or []): last_stun[v] = (e['r'], e.get('a'))
        if k == 'tribute_start' and e['gems'] >= 100 and team[e['a']] == w and wealth(w, rid.get(e['r'] - 1, 0)) >= 1000:
            open_[e['a']] = (e['r'], e['gems'], e['dur']); dmg[e['a']] = 0
        elif k in ('tribute_end', 'tribute_cancel') and e.get('a') in open_:
            r0, g, dur = open_.pop(e['a'])
            o = dict(gems=g, dur=dur, ran=e['r'] - r0, done=k == 'tribute_end', cause=e.get('cause'), dmg=dmg[e['a']])
            if o['cause'] == 'stun':
                s = last_stun.get(e['a'])
                if s and s[0] == e['r']:
                    o['stunner'] = name.get(s[1])
                    o['stunner_died15'] = any(r0_ >= e['r'] and r0_ <= e['r'] + 15 and v == s[1] for r0_, v, _ in deaths)
            o['chan_died15'] = any(r_ >= e['r'] and r_ <= e['r'] + 15 and v == e['a'] for r_, v, _ in deaths)
            out.append(o)
    return out
if __name__ == '__main__':
    root = Path(sys.argv[1]); dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=16): rows += r
    print('rich winner tributes', len(rows))
    print('damage taken during the channel: share with any', round(sum(r['dmg'] > 0 for r in rows) / len(rows), 3), 'median when any', st.median([r['dmg'] for r in rows if r['dmg'] > 0] or [0]))
    s = [r for r in rows if r['cause'] == 'stun' and 'stunner' in r]
    print('stun cancels', len(s), 'stunner died within 15 rounds', round(sum(r['stunner_died15'] for r in s) / max(1, len(s)), 3))
    print('channeller died within 15 rounds of any cancel/end', sum(r['chan_died15'] for r in rows), 'of', len(rows))
    print('ran before cancel by cause (median):', {c: st.median([r['ran'] for r in rows if r['cause'] == c]) for c in ('stun', 'lock', 'manual')})
