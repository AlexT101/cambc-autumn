# Largest damage on the first target in one round-long window, per engagement. The decoder's `turn` field is a flag,
# not the slot, so the windows are rounds (shifted by one slot), merged across a stunned turn.
# window.py NAME=ROWS.pkl[:OPP][:us|them][:A+|A-|A=] ...
import sys, pickle, json, gzip, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from summ import mean
cache = {}
def game(d):
    if d not in cache:
        if len(cache) > 4: cache.clear()
        meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
        ev = []
        for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
            e = json.loads(l)
            if e['r'] > 320: break
            if e['k'] in ('attack', 'cast', 'death') : ev.append(e)
        cache[d] = (meta, R, ev)
    return cache[d]
def analyse(r):
    meta, R, ev = game(r['dir']); ch = R['champions']
    team = {c['id']: c['team'] for c in meta['champions']}
    A = [c['id'] for c in ch if (c['team'] == r['us']) == r['by_us']]
    t0 = [c for c in ch if c['team'] not in [team[a] for a in A] and meta['champions'][c['id']]['name'] == r['tgt']][0]
    tid = t0['id']; r0, r1 = r['r0'], r['r1']
    # key (round, slot); t0's usable turns
    own = []
    for rr in range(max(1, r0 - 1), min(r1 + 2, len(R['round']) + 1)):
        i = rr - 1
        stunned = t0['stun'][i - 1] > 0 if i > 0 else False   # stun counter at end of previous round: this turn is lost
        own.append(((rr, t0['turn'][i]), stunned))
    hits = [((e['r'], e['t']), e['a'], dm) for e in ev if e['k'] in ('attack', 'cast') and r0 <= e['r'] <= r1 + 1 and e['a'] in A for t, dm in e.get('dmg', []) if t == tid]
    if not hits: return None
    usable = [k for k, s in own if not s]
    def win(k):
        j = 0
        for u in usable:
            if u <= k: j += 1
        return j
    W = collections.defaultdict(lambda: [0.0, set(), set()])
    for k, a, dm in hits:
        w = W[win(k)]; w[0] += dm; w[1].add(a); w[2].add((k, a))
    best = max(W.values(), key=lambda w: w[0]); first = W[min(W)]
    hp = r['hp_t'] * r['maxhp_t']
    # back-to-back: an attacker with turns in consecutive global positions (last of round rr, first of rr+1)
    return dict(best=best[0], best_att=len(best[1]), best_turns=len(best[2]), first=first[0], first_att=len(first[1]), first_turns=len(first[2]), hp=hp,
                nwin=len(W), stun_turns=sum(1 for k, s in own if s and (r0, -1) <= k <= (r1 + 1, 99)), died=r['died'],
                one_window_kill=r['died'] and best[0] >= 0.6 * hp)
for a in sys.argv[1:]:
    name, spec = a.split('=', 1); parts = spec.split(':'); path = parts[0]
    opp = parts[1] if len(parts) > 1 else 'Inte'; by_us = len(parts) > 2 and parts[2] == 'us'; rel = parts[3] if len(parts) > 3 else 'A+'
    rows = [r for r in pickle.load(open(path, 'rb'))['rows'] if r['opp'] == opp and r['by_us'] == by_us and ((rel == 'A+' and r['nA'] > r['nD']) or (rel == 'A-' and r['nA'] < r['nD']) or (rel == 'A=' and r['nA'] == r['nD']))]
    rows.sort(key=lambda r: r['dir'])
    X = [x for x in (analyse(r) for r in rows) if x]
    print('%-14s n %3d | largest window: dmg %4.0f (%.2f of hp) attackers %.2f attacker-turns %.2f | first window: dmg %4.0f att %.2f turns %.2f | windows with dmg %.2f | stunned turns %.2f | window >=50%% hp: %.0f%%, >=80%%: %.0f%% | died %.0f%%; died given window>=50%%: %.0f%%, given <50%%: %.0f%%' % (
        name, len(X), mean([x['best'] for x in X]), mean([x['best'] / max(1, x['hp']) for x in X]), mean([x['best_att'] for x in X]), mean([x['best_turns'] for x in X]),
        mean([x['first'] for x in X]), mean([x['first_att'] for x in X]), mean([x['first_turns'] for x in X]), mean([x['nwin'] for x in X]), mean([x['stun_turns'] for x in X]),
        100 * mean([x['best'] >= 0.5 * x['hp'] for x in X]), 100 * mean([x['best'] >= 0.8 * x['hp'] for x in X]), 100 * mean([x['died'] for x in X]),
        100 * mean([x['died'] for x in X if x['best'] >= 0.5 * x['hp']]), 100 * mean([x['died'] for x in X if x['best'] < 0.5 * x['hp']])))
