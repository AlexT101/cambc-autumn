"""Frozen surrogate combat rules for Intercontinental Fish (fit on the discovery cohorts).

Each rule takes only causal turn-start features (combat_data.py `x`, combat_tiles.py `x`).
Thresholds are grid/tree split points on discovery data, not recovered source constants.
"""
from breadth import RANGED
from combat_common import KIT

H_MIN = 0.49       # own health / max health must exceed this to stay in or enter contact
DANGER_MAX = 0.28  # and the tile's one-turn enemy damage reach / own effective HP at most this


def acceptable(x, tile, use_kill=True):
    """Fish keeps or takes a tile within enemy reach iff it can kill from it, or is healthy and the
    tile is not too dangerous."""
    if use_kill and tile['kill']:
        return True
    return x['hpf'] > H_MIN and tile['danger'] <= DANGER_MAX


def contexts(x):
    """The three positioning decisions of combat_tiles rows, with Fish's possible answers.

    Returns (context, candidate tiles that count as 'engage') or None.
    m2: melee two tiles from the nearest enemy: engage = step adjacent to an enemy.
    m1: melee adjacent: engage = stay adjacent (it attacks either way; leaving is hit-and-run).
    r:  ranged within 3: engage = do not increase the distance to the nearest enemy.
    """
    if x['at_home']:
        return None
    t = x['tiles']; st = t[0]
    rng = x['type'] in RANGED
    if not rng and st['dmin'] == 2:
        ap = [q for q in t if q['dmin'] == 1]
        return ('m2', ap) if ap else None
    if not rng and st['dmin'] == 1:
        return ('m1', [q for q in t if q['dmin'] == 1]) if any(q['dmin'] > 1 for q in t) else None
    if rng and st['dmin'] <= 3:
        if not any(q['dmin'] > st['dmin'] for q in t):
            return None
        # Staying is where a ranged champion can attack without a reset.
        return 'r', [st]
    return None


def engage(x, use_kill=True):
    c = contexts(x)
    if c is None:
        return None
    name, tiles = c
    return name, any(acceptable(x, q, use_kill) for q in tiles)


def engaged(x, y):
    """The label: did the turn engage, per context (a spell hit from two tiles counts for m2)."""
    t = x['tiles']; st = t[0]; ch = t[y['choice']]
    name, _ = contexts(x)
    if name == 'm2':
        return ch['dmin'] == 1 or y['hit']
    if name == 'm1':
        return ch['dmin'] == 1
    return ch['dmin'] <= st['dmin']


# Spells. x is a combat_data.py row's x.
EXCLUSIVE_DAMAGE = {3: 0, 5: 0, 6: 0, 7: 1, 11: 1}  # slot of the unit damage spell (excludes walking)


def damage_spell_opportunity(x):
    s = EXCLUSIVE_DAMAGE.get(x['type'])
    if s is None or x['at_home'] or x['channel'] > 1 or x['cd'][s] != 0:
        return None
    return s if any(e['d'] <= 4 for e in x['enemies']) else None


def cassi_stun_opportunity(x):
    if x['type'] != 3 or x['at_home'] or x['channel'] > 1 or x['cd'][1] != 0:
        return False
    return any(e['d'] <= 4 and e['type'] != 7 and e['stun'] <= 0 for e in x['enemies'])


def cassi_stun(x, walks):
    """Given whether Cassi walks this turn: stun unless she stands with her damage spell ready."""
    return walks or x['cd'][0] != 0


def hor_shield_opportunity(x):
    return x['type'] == 12 and not x['at_home'] and x['channel'] <= 1 and x['cd'][0] == 0


def hor_shield(x):
    """Shield iff a visible, unstunned enemy can damage it before its next turn (Chebyshev reach)."""
    return x['threat'] > 0


def reset_opportunity(x, y):
    """Melee reset champions after a basic attack on a champion that its Strength does not kill."""
    if x['type'] not in (2, 4, 7):
        return None
    rs = KIT[x['type']][0]
    if x['cd'][rs] != 0:
        return None
    basics = [h for h in y['hits'] if h[0] == 'basic']
    if not basics:
        return None
    e = next((e for e in x['enemies'] if e['id'] == basics[0][3][0]), None)
    if e is None or e['ehp'] <= x['str']:
        return None
    return rs


# Chase. x, y: a combat_data.py row; prev_y: the same actor's previous-round row's y.
CHASE_TARGET_HPF = 0.37   # chase a fleeing target at or below this health fraction regardless
CHASE_RATIO = 1.24        # else chase iff (own + visible allies within 8) / visible enemies EHP > this
CHASE_H = 0.44            # and own gem-adjusted health fraction above this


def gem_health(x):
    return min(1.0, x['ehp'] / x['maxhp']) * (0.65 if x['gems'] > 0 else 1.0)


def chase_opportunity(x, prev_y):
    """The target of last turn's last hit, now the nearest visible enemy and out of basic range."""
    if x['at_home'] or x['channel'] > 1 or not prev_y or not prev_y['hits']:
        return None
    tgt = prev_y['hits'][-1][3][0]
    e = x['enemies'][0]
    if e['id'] != tgt or e['d'] <= (3 if x['ranged'] else 1):
        return None
    return e


def chase(x, e):
    ratio = (x['ally_ehp'] + x['ehp']) / max(1.0, x['enemy_ehp'])
    return e['hp'] / e['maxhp'] <= CHASE_TARGET_HPF or (ratio > CHASE_RATIO and gem_health(x) > CHASE_H)


def chased(y, e):
    return any(e['id'] in h[3] for h in y['hits']) or (not y['hit'] and y['dd'] < 0)
