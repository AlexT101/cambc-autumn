"""Fish farming hypotheses frozen before decoding the separate confirmation corpus.

Predict parameters of an observed basic attack, not whether to attack. Memory is
updated only from earlier basic attacks on visible camps, separately per actor.
"""
from collections import defaultdict


def camp_target(candidates, previous_group=None):
    return min(candidates, key=lambda c: (
        c['group'] != previous_group if previous_group is not None else False,
        c['hp'], c['y'], c['x'], c['id']))['id']


def opening_target(candidates):
    return max(candidates, key=lambda c: (
        (c['gold'] + 0.5*c['gems']) / (1 + c['walk'] + c['hp']/100), -c['id']))['id']
