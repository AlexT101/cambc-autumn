"""Candidate features for the farm2 destination logit, in named sets.

`base` is choice_model.base_features (the frozen logit's features). Other sets translate
astraeus's farm-choice terms into inputs from the actor's own perspective: farm2_data extras
(`r['e']`) where needed. Every input is causal: the actor's turn-start view and memory.
"""
import math

from breadth import dist
from choice_model import FIGHTER_HP, FIGHTER_STRENGTH, base_features

GEM_GOLD = 10.0  # gold per gem in `worth`; astraeus prices gems well above gold


def horizon(e):
    return 100 * max(1.0, max(e['width'], e['height']) / 50)


def own_strength(x):
    return max(float(x['strength']), 1.0)


def kill_rounds(x, c, ce, strength, live_hp=True):
    if c['state'] in (2, 3):
        return 0.0 if c['state'] == 2 else sum(FIGHTER_HP.get(t, 120) for t in c['types']) / strength
    hp = ce['hp_left'] if live_hp and ce else sum(FIGHTER_HP.get(t, 120) for t in c['types'])
    return hp / strength


def team_near(x, e, c, radius=4):
    """Visible allies (not on spawn) within `radius` of the group's tiles: their summed Strength."""
    tiles = [tuple(p) for p in c['tiles']]
    s = 0.0; n = 0
    for a in e['allies']:
        if a['home']:
            continue
        if min(dist((a['x'], a['y']), p) for p in tiles) <= radius:
            s += a['strength']; n += 1
    return s, n


def spawn_mates(e):
    return [a for a in e['allies'] if a['home']]


def feats(r, c, sets, opts):
    x = r['x']; e = r.get('e'); ce = e['candidates'][str(c['id'])] if e else None
    f = base_features(x, c) if 'base' in sets else {}
    wait = max(c['walk'], c['respawn'])
    S = own_strength(x)
    worth = c['gems'] * opts.get('gem_gold', GEM_GOLD) + c['gold']
    fighters = [t for t in c['types'] if t in FIGHTER_HP]
    if 'hp' in sets and ce:
        alive = c['state'] in (0, 1)
        full = sum(FIGHTER_HP[t] for t in fighters)
        left = sum(h for h in [ce['hp_left']]) if alive else 0
        f['hp_fight'] = alive * left / S / 100
        f['damaged'] = float(alive and ce['hp_left'] < sum(FIGHTER_HP.get(t, 120) for t in c['types']) - 1)
        f['awake'] = float(alive and ce['awake'] > 0)
        f['part_frac'] = alive * (1 - ce['hp_left'] / max(1.0, sum(FIGHTER_HP.get(t, 120) for t in c['types'])))
    if 'rate' in sets and ce:
        strength = S
        if 'crew' in opts:
            strength += opts['crew'] * team_near(x, e, c)[0]
        kill = kill_rounds(x, c, ce, strength, live_hp=opts.get('live_hp', True))
        cap = 0 if c['state'] == 2 else 7
        R = max(1.0, wait + kill + cap)
        H = horizon(e)
        f['lograte'] = math.log1p(worth) - math.log(R) - math.log1p(R / H)
        f['logworth'] = math.log1p(worth)
        f['logR'] = math.log(R)
    if 'home' in sets and ce:
        us, them = ce['from_us'], ce['from_them']
        share = min(1.0, 2 * them / max(1, us + them)) if us < 999 and them < 999 else 1.0
        f['logshare'] = math.log(max(share, 0.05))
        f['enemy_near'] = float(them < 999 and them <= us)
    if 'altar' in sets and ce:
        g = x['gems']
        f['carry_altar'] = (g > 0) * min(ce['to_altar'], 60) / 10
        f['carry_gems_altar'] = min(g, 100) / 100 * min(ce['to_altar'], 60) / 10
    if 'stale' in sets and ce:
        age = c['age'] if c['age'] is not None else 0
        f['empty_age'] = float(c['state'] == 2) * min(age, 100) / 10
        exp = (age - (ce['respawn_raw'] or 0)) if c['state'] == 3 else 0
        f['resp_expired'] = float(c['state'] == 3 and c['respawn'] == 0)
        f['resp_expired_age'] = float(c['state'] == 3 and c['respawn'] == 0) * min(max(exp, 0), 200) / 50
        f['alive_age'] = float(c['state'] == 1) * min(age, 200) / 50
    if 'recall' in sets and e:
        tiles = [tuple(p) for p in c['tiles']]
        for name, p in (('recall', e['recall_xy']), ('off', e['off_xy'])):
            d = min(dist(p, t) for t in tiles) if p else 30
            f[f'{name}_near'] = float(p is not None and d <= 6)
            f[f'log_{name}'] = math.log1p(min(d, 60))
    if 'danger' in sets and ce:
        dps = sum(FIGHTER_STRENGTH[t] for t in fighters) * (c['state'] in (0, 1))
        kill = kill_rounds(x, c, ce, S)
        f['danger'] = min(5.0, dps * kill / max(1.0, x['hp']))
        f['danger_max'] = min(5.0, dps * kill / max(1.0, x['maxhp']))
    if 'crew' in sets and e:
        s, n = team_near(x, e, c)
        f['crew_frac'] = s / S
        f['crew_any'] = float(n > 0)
        alive = c['state'] in (0, 1)
        f['crew_kill'] = alive * (kill_rounds(x, c, ce, S) - kill_rounds(x, c, ce, S + s)) / 10 if ce else 0
    if 'mates' in sets and e:
        # Allies on spawn with the actor: a crew forming there.
        mates = spawn_mates(e)
        f['mates_big'] = len(mates) * float(any(t in (1, 4, 5) for t in c['types']) and c['state'] in (0, 1))
    if 'size' in sets:
        f['n_types'] = len(c['types']) / 5
        f['has_elk'] = float(1 in c['types'] and c['state'] in (0, 1))
        f['wolves'] = float(0 in c['types'] and c['state'] in (0, 1))
        f['gold_only'] = float(c['gems'] == 0)
    if 'allymem' in sets and e and 'ally_memory' in e:
        tiles = [tuple(p) for p in c['tiles']]
        for lim in (10, 40):
            near = [a for a in e['ally_memory'] if 0 < a['age'] <= lim
                    and min(dist((a['x'], a['y']), p) for p in tiles) <= 3]
            f[f'mem_near{lim}'] = float(len(near))
        ra = e.get('recall_allies') or []
        f['recall_ally_near'] = float(sum(min(dist((a['x'], a['y']), p) for p in tiles) <= 3 for a in ra))
    if 'habit' in sets:
        tot = sum(k['visits'] for k in x['candidates'])
        f['log_visits'] = math.log1p(c['visits'])
        f['visit_share'] = c['visits'] / tot if tot else 0.0
        va = c['visit_age']
        f['visit_recent'] = float(va is not None and va <= 60)
        f['log_visit_age'] = math.log1p(min(va, 500)) if va is not None else math.log1p(500)
        f['log_route'] = math.log1p(c['route_count'])
    if 'follow' in sets and e and 'ally_prev' in e:
        # Off-spawn allies in sight now, also seen within the last 3 rounds: approaching this group,
        # and approaching it more than any other group (their apparent target).
        tiles = [tuple(p) for p in c['tiles']]
        n = 0; target = 0
        for a in e['allies']:
            pr = e['ally_prev'].get(str(a['id']))
            if a['home'] or not pr or pr['age'] > 3:
                continue
            gain = min(dist((pr['x'], pr['y']), p) for p in tiles) - min(dist((a['x'], a['y']), p) for p in tiles)
            if gain > 0:
                n += 1
                best = max(min(dist((pr['x'], pr['y']), tuple(p)) for p in k['tiles'])
                           - min(dist((a['x'], a['y']), tuple(p)) for p in k['tiles']) for k in x['candidates'])
                target += gain >= best
        f['follow_n'] = float(n); f['follow_target'] = float(target)
    if 'altar2' in sets and ce:
        # Carrying: walk out plus the group's walk on to an altar (spawn-to-altar is constant per episode).
        carry = float(x['gems'] > 0); big = min(x['gems'], 100) / 100
        via = (c['walk'] + min(ce['to_altar'], 80)) / 10
        f['carry_via'] = carry * via; f['carry_logvia'] = carry * math.log1p(via * 10)
        f['carry_logwait'] = carry * math.log1p(wait); f['bag_via'] = big * via
    if 'emptyworth' in sets and ce:
        em = float(c['state'] == 2)
        f['empty_logworth'] = em * math.log1p(worth)
        for v in (0, 1, 2, 3):
            f[f'empty_capture{v}'] = em * float(ce['capture'] == v)
    if 'mono_gate' in sets and ce:
        f['mono_small_team'] = float(4 in c['types'] and c['state'] in (0, 1)) * (len(e['allies']) < 4)
    return f


CORE = ['lograte', 'logwait', 'respawn_part', 'empty', 'respawning', 'unknown', 'monolith', 'clusters_only',
        'logshare', 'visited', 'route', 'last', 'ally_recent', 'ally_closer', 'allies_near', 'resp_expired', 'empty_age']


def featurizer(sets, opts=None):
    opts = opts or {}

    def run(r, cs):
        if 'core' in sets:
            full = sets + ['base', 'rate', 'home', 'stale']
            return [{k: v for k, v in feats(r, c, full, opts).items() if k in CORE} for c in cs]
        return [feats(r, c, sets, opts) for c in cs]
    return run
