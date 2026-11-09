"""Observation tokens: which known encoding a visible enemy's priority matches."""
import math

CHAMPS = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'Heart of Ruin']
BASE_HP = {'Ryth': 1200, 'Vesper Vale': 1000, 'Vendetta': 900, 'Cassi': 600, 'Issac': 900, 'Stellar': 650, 'Prism': 700,
           'Marcella': 1200, 'Willow': 700, 'Ren': 900, 'Varg': 1000, 'Tavi': 900, 'Heart of Ruin': 1000}
TIE = {n: i for i, n in enumerate(CHAMPS)}
TIE['Heart of Ruin'] = 9.5  # Fish orders HoR before Varg (both 1000)
MITE_TANK = {'Heart of Ruin', 'Marcella'}

def fish_ranks(roster):
    order = sorted(range(len(roster)), key=lambda j: (-BASE_HP[roster[j]], TIE[roster[j]]))
    rk = [0] * len(roster)
    for pos, j in enumerate(order): rk[j] = 2 + pos
    return rk

def fish_band(hp, maxhp, shield, gems):
    h = min(1.0, (hp + shield) / maxhp) if maxhp > 0 else 1.0
    if gems > 0: h *= 0.65
    return max(0, math.floor(4 * (1 - h)))

# token ids
TOK = ['zero', 'fish_quiet', 'fish_contact', 'fish_mod', 'res_same', 'mite_quiet', 'mite_near', 'mite_chan',
       'mite_contact', 'mite_offset', 'other']
T = {n: i for i, n in enumerate(TOK)}

def token(v, j, roster, ranks, hp, maxhp, gems, shield, res0=None, fish_level=True, fish_rank=True, mite_quiet=True):
    """One token per observation, most specific first. res0: this champion's residue mod (N+1) at its
    first counted nonzero value (None if none yet)."""
    v = int(v)
    if v == 0: return T['zero']
    n1 = len(roster) + 1
    res = (-v) % n1
    fish = fish_rank and res == ranks[j] % n1
    if fish and fish_level:
        L = (-v - ranks[j]) // n1
        b = fish_band(hp, maxhp, shield, gems)
        # Health read after the write can be lower (one band up) than when Fish wrote it.
        if L >= 0 and (b - 1 <= L <= b or b + 4 <= L <= b + 5): return T['fish_quiet']
        if 99 <= L <= 116 or -117 <= L <= -101: return T['fish_contact']
    name = roster[j]
    f = hp / maxhp if maxhp > 0 else 1.0
    q = [1000 + math.floor(20 * f)]
    if name in MITE_TANK: q.append(1025 + math.floor(24 * f))
    if mite_quiet:
        if v in q: return T['mite_quiet']
        if v == 18965: return T['mite_chan']
        if 1000 <= v <= 1049 and min(abs(v - x) for x in q) <= 2: return T['mite_near']
    if 90 <= v <= 100: return T['mite_contact']
    for off in (2000, 3000, 5000, 6460, 7460, 9460):
        if 90 <= v - off <= 100: return T['mite_offset']
    if fish: return T['fish_mod']
    if res0 is not None and res == res0 and res != 0: return T['res_same']
    return T['other']
