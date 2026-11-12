"""Fish r8 priorities per unit and round from the live replays, with each unit's state: a pickle of games
{mid, fish team, names, rounds, units: [{id, name, prio, x, y, hp, maxHp, gems, alive, gold, str, chan, items}]}.
py prio_ds.py [OUT.pkl]"""
import json, gzip, os, sys, pickle
from multiprocessing import Pool
H = os.path.expanduser('~/tmp-offload/fishr8/')
rows = json.load(open(H + 'live/rows-r8-all.json')); idx = json.load(open(H + 'live/ext/index.json'))['games']
KEYS = ('prio', 'x', 'y', 'hp', 'maxHp', 'gems', 'alive', 'gold', 'str', 'chan', 'chanT', 'shield', 'stun', 'cd0', 'cd1', 'kills', 'deaths', 'items', 'sees', 'ward')
def one(job):
    mid, d, fish = job
    try:
        m = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
    except Exception: return None
    names = {c['id']: c['name'] for c in m['champions']}
    U = [{'id': c['id'], 'team': c['team'], 'name': names[c['id']], **{k: c.get(k) for k in KEYS}} for c in R['champions']]
    return {'mid': mid, 'fish': fish, 'rounds': R['round'], 'units': U, 'map': m['map'], 'winner': m['result'].get('winner'), 'seed': m.get('seed')}
def main():
  jobs = []
  for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid in rows: jobs.append((mid, H + 'live/ext/' + g['dir'], 1 if rows[mid]['side'] == 'a' else 0))
  with Pool(16) as p: out = [x for x in p.map(one, jobs) if x]
  pickle.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else H + 'prio/ds.pkl', 'wb'))
  print(len(out), 'games')
if __name__ == '__main__': main()
