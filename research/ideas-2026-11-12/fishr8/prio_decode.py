"""Fish r8's priority, decoded (see README section 5). v = (old << 20) + low, low = MASK[slot][round] ^ payload:
- old: the r2 rank code -rank - (n+1) level (v >> 20);
- MASK: a fixed 20-bit value per Fish champion slot (its index in its team, by id) and round, the same in every game;
- payload (17 bits) = ((((cd * 4 + hb) * 23 + dy + 11) * 23 + dx + 11) * ne + j) * 2 + flag, or just flag:
  flag: the sender is dead, channelling (recall / tribute) or hurt; j: its target, our champion (j - 1) mod ne by id
  (ne = our champion count); dx, dy: that target's position relative to the sender; hb: the target's health quarter
  (0-3); cd: the target's two ability-ready bits (slot 0 bit 0, slot 1 bit 1).
A value read at round r was written at round r - 1: decode it with MASK[slot][r - 1].
    py prio_decode.py [--table OUT.json]   (reads ~/tmp-offload/fishr8/prio/ds.pkl from prio_ds.py)
Prints the fit rates; --table writes the mask table (slot -> {round: mask}, rounds with >= 20 games agreeing)."""
import pickle, os, sys, json, collections
H = os.path.expanduser('~/tmp-offload/fishr8/prio/')
D = pickle.load(open(H + 'ds.pkl', 'rb'))
M = 0xFFFFF

def fish_units(g): return [u for u in g['units'] if u['team'] == g['fish']]
def our_units(g): return [u for u in g['units'] if u['team'] != g['fish']]

def masks(D, min_games=20):
    c = collections.defaultdict(collections.Counter)
    for g in D:
        for k, u in enumerate(fish_units(g)):
            for i, v in enumerate(u['prio']): c[(k, i + 1)][v & M] += 1
    out = {}
    for key, cc in c.items():
        v, n = cc.most_common(1)[0]
        # the modal value carries flag 0 or 1: the mask is the modal value with the flag the majority sends (0)
        if n >= min_games: out[key] = v
    return out

def decode(v, mask, ne):
    x = (v & M) ^ mask
    if x <= 1: return {'flag': x}
    if x >= 1 << 17: return None
    d, q = x % (2 * ne), x // (2 * ne)
    return {'flag': d & 1, 'target': (d // 2 - 1) % ne, 'dx': q % 23 - 11, 'dy': q // 23 % 23 - 11, 'hb': q // 529 % 4, 'cd': q // 2116}

def main():
    T = masks(D)
    if '--table' in sys.argv:
        out = collections.defaultdict(dict)
        for (k, r), v in T.items(): out[k][r] = v
        json.dump(out, open(sys.argv[sys.argv.index('--table') + 1], 'w'), separators=(',', ':'))
    S = collections.Counter()
    for g in D:
        O = our_units(g); ne = len(O)
        for k, u in enumerate(fish_units(g)):
            for i in range(1, len(g['rounds'])):
                m = T.get((k, i + 1))
                if m is None: continue
                S['values'] += 1
                p = decode(u['prio'][i], m, ne)
                if p is None: S['payload >= 2^17 (undecoded)'] += 1; continue
                S['flag ' + ('dead' if not u['alive'][i] else 'alive') + f" = {p['flag']}"] += 1
                if 'target' not in p: S['flag only'] += 1; continue
                S['target message'] += 1
                o = O[p['target']]
                S['  target position = sender + (dx, dy), this or last round'] += any(
                    o['x'][j] is not None and u['x'][i] is not None and (o['x'][j] - u['x'][i], o['y'][j] - u['y'][i]) == (p['dx'], p['dy']) for j in (i, i - 1))
                S['  target health quarter'] += p['hb'] in [min(3, int(4 * o['hp'][j] / o['maxHp'][j])) for j in (i, i - 1) if o['maxHp'][j] and o['hp'][j] is not None]
                S['  target ability bits'] += p['cd'] in [(o['cd0'][j] == 0) + 2 * (o['cd1'][j] == 0) for j in (i, i - 1)]
    for k in S: print(f'{k}: {S[k]}' + (f' ({S[k] / S["target message"]:.3f})' if k.startswith('  ') else f' ({S[k] / S["values"]:.3f})'))

if __name__ == '__main__': main()
