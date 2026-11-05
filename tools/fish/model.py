"""Frozen, narrow Fish predictors fitted on the manifest's training games.

These predict the value of a priority write, or the target of an attack/heal that
is already being taken. They do not decide whether to perform those actions.
"""
import json
import math
from pathlib import Path

RANKS = json.loads((Path(__file__).resolve().parents[2] / 'research/fish-2026-11-05/priority-ranks.json').read_text())


def base_rank(roster_types, champion_name):
    return RANKS.get(','.join(map(str, sorted(roster_types))), {}).get(champion_name)


def ordinary_priority(hp, maxhp, shield, gems, rank, team_size):
    health = min(1.0, (hp + shield) / maxhp)
    health *= 0.65 if gems > 0 else 1.0
    band = max(0, math.floor(4 * (1 - health)))
    return -rank - (team_size + 1) * band


def predict_priority(row):
    if not row['alive'] or row['stunned'] or row['enemies'] or row['start_enemies']:
        return None
    rank = base_rank(row['rank_types'], row['type'])
    if rank is None:
        return None
    return ordinary_priority(row['hp'], row['maxhp'], row['shield'], row['gems'], rank, row['n'])


def effective_hp(champion):
    return champion['hp'] + sum(b['mag'] for b in champion['buffs'] if b['type'] == 0)


def predict_attack(row):
    """Among visible enemies in basic range, pick minimum HP plus shield."""
    return min(row['candidates'], key=lambda c: (effective_hp(c), c['id']))['id']


def heal_value(champion, focus):
    return min(champion['maxHp'] - champion['hp'], 3 * focus) / champion['maxHp']


def predict_heal(row):
    """Largest fraction of maximum health actually restored; exploratory fit."""
    return min(row['candidates'], key=lambda c: (-heal_value(c, row['focus']), c['id']))['id']
