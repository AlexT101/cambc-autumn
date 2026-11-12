"""Mite's and our Vesper's actions per game: basic attacks on champions and on camps, casts by ability (and on
champions), champion damage, and the rounds with an attack on a champion that also cast a reset.
    py vacts.py EXT [ROWS]   (ROWS: live; else local)"""
import json, os, sys, collections
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
from mstats import load
def game(job):
    ext, d, mite, extra = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    out = dict(extra)
    for side, t in (('m', mite), ('o', 1 - mite)):
        v = [c['id'] for c in meta['champions'] if c['team'] == t and c['name'] == 'Vesper Vale']
        if not v: continue
        v = v[0]; S = collections.Counter(); rounds_att = collections.Counter(); rounds_reset = set()
        for e in ev:
            if e.get('a') != v: continue
            if e['k'] == 'attack':
                if 'camp' in e: S['att_camp'] += 1
                elif e.get('tgt') in team: S['att_champ'] += 1; S['dmg_att'] += sum(a for x, a in e.get('dmg', []) if x in team); rounds_att[e['r']] += 1
            elif e['k'] == 'cast':
                S['cast_' + e.get('ab', '?')] += 1
                if e.get('ab', '').lower().startswith('attack') or 'reset' in e.get('ab', '').lower(): rounds_reset.add(e['r'])
        S['double_att_rounds'] = sum(1 for r, c in rounds_att.items() if c >= 2)
        S['att_rounds'] = len(rounds_att); S['reset_rounds'] = len(rounds_reset)
        out[side] = dict(S)
    return out
def main():
    ext = sys.argv[1]; idx = json.load(open(ext + '/index.json'))['games']; jobs = []
    rows = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else None
    for g in idx:
        if rows is not None:
            mid = os.path.basename(g['source'])[:-8]
            if mid in rows: r = rows[mid]; jobs.append((ext, g['dir'], 1 if r['side'] == 'a' else 0, {'map': r['map'].replace('_', '-'), 'side': r['side'], 'version': r['version']}))
        else:
            base = os.path.basename(g['source'])[:-8]; num, rest = base.split('-', 1); mname, o = rest.rsplit('-', 1)
            side = 'a' if o == '12' else 'b'; jobs.append((ext, g['dir'], 1 if side == 'a' else 0, {'map': mname.replace('_', '-'), 'side': side}))
    with Pool(8) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    return res
if __name__ == '__main__':
    res = main(); out = sys.argv[3] if len(sys.argv) > 3 else None
    json.dump(res, open(out, 'w')) if out else None
