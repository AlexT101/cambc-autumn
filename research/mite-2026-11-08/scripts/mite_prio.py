"""Mite's priority (its 2026-11-07 05-14 UTC submission), recovered from own-view replays.

priority(name, me, start_en, alert_prev, allies):
  name        the writer's champion name
  me          the writer at write time (alive, x, y, hp, maxHp, gems, channelType, channelTimer)
  start_en    enemies the writer saw at the start of this turn, at the positions seen then
  alert_prev  whether an enemy was within 8 at the start of the writer's previous turn (last round)
  allies      allies at write time (x, y, hp, maxHp)
Mite writes the value only when it differs from the current one.
"""
import math

TANK = {'Heart of Ruin', 'Marcella'}
MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Heart of Ruin', 'Issac'}


def cheb(a, b):
    return max(abs(a['x'] - b['x']), abs(a['y'] - b['y']))


def quiet(name, me, allies):
    h = me['hp'] / me['maxHp']
    hurt_beside_healthy = h < 0.5 and any(cheb(a, me) <= 2 and a['hp'] / a['maxHp'] >= 0.65 for a in allies)
    if name in TANK and not hurt_beside_healthy:
        return 1025 + math.floor(24 * h)
    return 1000 + math.floor(20 * h)


def offset(me, en):
    """Approximate: right on 76.5% of contact writes (60.2% without it)."""
    h = me['hp'] / me['maxHp']
    e5 = [e for e in en if cheb(e, me) <= 5]
    retreat = bool(e5) and (me['gems'] >= 10 or h <= 0.4)
    kill = any(e['hp'] / e['maxHp'] <= 0.35 for e in e5) and not (retreat and h <= 0.25)
    rich = any(e['gems'] >= 500 for e in en if cheb(e, me) <= 3)
    return 6460 * kill + ((1000 if kill else 2000) if retreat else 0) + 3000 * rich


def contact_range(name, enemy_name):
    return 4 if (name in MELEE and enemy_name in MELEE) else 6


def priority(name, me, start_en, alert_prev, allies, with_offset=True):
    if not me['alive']:
        return 1050
    if me['channelType'] and me['channelTimer'] == 1:
        return 18965
    if any(cheb(e, me) <= contact_range(name, e['name']) for e in start_en):
        base = 100 - min(cheb(e, me) for e in start_en)
        return base + (offset(me, start_en) if with_offset else 0)
    if alert_prev or any(e['d_start'] <= 8 for e in start_en):
        return 0
    return quiet(name, me, allies)
