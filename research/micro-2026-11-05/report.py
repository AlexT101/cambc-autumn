"""Per-team rate tables from detect.py's summary.json.

    python3 -I research/micro-2026-11-05/report.py research/micro-2026-11-05/out [--min-games 150]
"""
import json
import sys

out = sys.argv[1]
mg = int(sys.argv[sys.argv.index('--min-games') + 1]) if '--min-games' in sys.argv else 150
s = json.load(open(f'{out}/summary.json'))
G, C = s['games'], s['C']
teams = sorted([t for t in C if G.get(t, 0) >= mg], key=lambda t: -G[t])

COLS = [
    ('games', lambda c, t: G[t]),
    ('prio%turns', lambda c, t: 100 * c.get('turns_prio', 0) / c['turns']),
    ('ward/1kT', lambda c, t: 1000 * c.get('ward', 0) / c['turns']),
    ('oof/1kT', lambda c, t: 1000 * c.get('rollover', 0) / c['turns']),
    ('blocked/1kT', lambda c, t: 1000 * c.get('blocked', 0) / c['turns']),
    ('recall/1kT', lambda c, t: 1000 * c.get('recall_start', 0) / c['turns']),
    ('lock/g', lambda c, t: c.get('lock_place', 0) / G[t]),
    ('tp/g', lambda c, t: c.get('teleport', 0) / G[t]),
    ('shopSpawn/g', lambda c, t: c.get('shopturn_spawn', 0) / G[t]),
    ('shopField/g', lambda c, t: c.get('shopturn_field', 0) / G[t]),
    ('shopDead/g', lambda c, t: c.get('shopturn_dead', 0) / G[t]),
    ('sellTurns', lambda c, t: sum(v for k, v in c.items() if k.startswith('sellturn_'))),
    ('sellNonTavi', lambda c, t: c.get('sell_nonTavi', 0)),
    ('buy+sell', lambda c, t: c.get('buy_and_sell_same_turn', 0)),
    ('healBuyLeave/g', lambda c, t: c.get('heal_buy_then_leave', 0) / G[t]),
    ('fieldBuy>hitChamp', lambda c, t: c.get('fieldbuy_then_hit_champ', 0)),
    ('fieldBuy>hitCamp', lambda c, t: c.get('fieldbuy_then_hit_camp', 0)),
    ('multiPrio', lambda c, t: c.get('turns_multi_prio', 0)),
    ('cancelSameTurn', lambda c, t: sum(v for k, v in c.items() if k.startswith('cancel_same_turn'))),
    ('submit0gems', lambda c, t: c.get('submit_zero_gems', 0)),
    ('blocked>hit', lambda c, t: c.get('blocked_then_hit_tile', 0)),
    ('boterr', lambda c, t: c.get('boterr', 0)),
]


def fmt(v):
    return f'{v:.1f}' if isinstance(v, float) else str(v)


print('| team | ' + ' | '.join(n for n, _ in COLS) + ' |')
print('|' + '---|' * (len(COLS) + 1))
for t in teams:
    c = C[t]
    print(f'| {t} | ' + ' | '.join(fmt(f(c, t)) for _, f in COLS) + ' |')
print()
for k, v in sorted(s['EX'].items()):
    t, tag = k.split('|', 1)
    if G.get(t, 0) >= mg:
        print(f'- {t} {tag}: ' + '; '.join(v[:4]))
